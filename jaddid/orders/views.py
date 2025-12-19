from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import F

from .models import Order, OrderItem, OrderStatusTracking
from .serializers import OrderSerializer
from marketplace.models import Product, MaterialListing, Cart, CartItem

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(buyer=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        buyer = request.user
        seller_id = data.get('seller_id')
        order_type = data.get('order_type')
        delivery_address = data.get('delivery_address', '')
        payment_method = data.get('payment_method', 'cash_on_delivery')
        items_data = data.get('items', [])

        if not seller_id or not order_type or not items_data:
            return Response({"detail": "seller_id, order_type, and items are required."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            buyer=buyer,
            seller_id=seller_id,
            order_type=order_type,
            delivery_address=delivery_address,
            payment_method=payment_method,
            order_status=Order.IN_PROGRESS,
            payment_status=Order.UNPAID,
            total_price=0
        )

        total_price = 0
        for item in items_data:
            if order_type == 'product':
                product = get_object_or_404(Product, pk=item.get('product_id'))
                quantity = int(item.get('quantity', 1))
                if quantity > product.quantity:
                    quantity = product.quantity
                OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=product.price)
                total_price += quantity * product.price
            elif order_type == 'material':
                listing = get_object_or_404(MaterialListing, pk=item.get('material_listing_id'))
                quantity = float(item.get('quantity', 1))
                if quantity > listing.quantity:
                    quantity = listing.quantity
                OrderItem.objects.create(order=order, material_listing=listing, quantity=quantity, unit_price=listing.price_per_unit)
                total_price += quantity * listing.price_per_unit

        order.total_price = total_price
        order.save()
        OrderStatusTracking.objects.create(order=order, old_status=None, new_status=Order.IN_PROGRESS)

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def buyer_update(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk, buyer=request.user)
        if order.order_status != Order.IN_PROGRESS:
            return Response({'detail': 'Cannot update after order is confirmed.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        delivery_address = data.get('delivery_address')
        items_data = data.get('items', [])

        if delivery_address:
            order.delivery_address = delivery_address

        total_price = 0
        for item_data in items_data:
            item = get_object_or_404(OrderItem, pk=item_data['id'], order=order)

            if item.product:
                max_qty = item.product.quantity
            elif item.material_listing:
                max_qty = item.material_listing.quantity
            else:
                continue

            requested_qty = item_data.get('quantity', item.quantity)
            if requested_qty > max_qty:
                requested_qty = max_qty

            item.quantity = requested_qty
            item.save()
            total_price += item.quantity * item.unit_price

        order.total_price = total_price
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk, buyer=request.user)
        if order.order_status in [Order.DELIVERED, Order.CANCELLED]:
            return Response({'detail': 'Cannot cancel delivered or already cancelled orders.'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = order.order_status
        order.order_status = Order.CANCELLED
        order.cancelled_at = timezone.now()
        order.save()
        OrderStatusTracking.objects.create(order=order, old_status=old_status, new_status=Order.CANCELLED)

        for item in order.items.all():
            if item.product:
                item.product.quantity = F('quantity') + item.quantity
                item.product.save()
            elif item.material_listing:
                item.material_listing.quantity = F('quantity') + item.quantity
                item.material_listing.save()

        carts = Cart.objects.filter(items__product__in=[i.product for i in order.items.all() if i.product])
        for cart in carts:
            for cart_item in cart.items.all():
                if cart_item.product and cart_item.product.quantity < cart_item.quantity:
                    cart_item.quantity = cart_item.product.quantity
                    if cart_item.quantity == 0:
                        cart_item.delete()
                    else:
                        cart_item.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
