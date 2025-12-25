from math import perm
import stat
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import F, Q
from yaml import serialize
from decimal import Decimal
import stripe
from django.conf import settings
from .models import Order, OrderItem, OrderStatusTracking
from accounts.models import User
from .serializers import OrderSerializer
from marketplace.models import Product, MaterialListing, Cart, CartItem
from django.contrib.auth import get_user_model


stripe.api_key = settings.STRIPE_SECRET_KEY

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]


    User = get_user_model()

    def create(self, request, *args, **kwargs):
        """Create a new order"""
        raw_data = request.data
        order_data = raw_data.get('order_data', raw_data)
        from marketplace.models import Product, MaterialListing
        try:
            with transaction.atomic():
            # 1. Create the Main Order
                order = Order.objects.create(
                    buyer=request.user,
                    seller_id=order_data.get('seller_id'),
                    delivery_address=order_data.get('delivery_address'),
                    customer_lat=order_data.get('customer_lat'),
                    customer_lng=order_data.get('customer_lng'),
                    order_type=order_data.get('order_type', 'product'),
                    order_status=order_data.get('status', 'pending'),
                    stripe_payment_intent_id=order_data.get('stripe_payment_id'),
                    payment_status='paid' if order_data.get('stripe_payment_id') else 'pending'
                )

            # 2. Create Order Items
                items_data = order_data.get('items', [])
                total_order_price = 0

                for item in items_data:
                    p_id = item.get('product_id')
                    m_id = item.get('material_listing_id')
                    qty = int(item.get('quantity', 1))
                
                    price = 0
                    if p_id:
                        product = Product.objects.get(id=p_id)
                        price = product.price
                    elif m_id:
                        material = MaterialListing.objects.get(id=m_id)
                        price = material.price_per_unit
                
                # Create the Item with the required unit_price
                    OrderItem.objects.create(
                        order=order,
                        product_id=p_id,
                        material_listing_id=m_id,
                        quantity=qty,
                        unit_price=price  # <--- FIXED: Not null anymore
                    )
                
                    total_order_price += (price * qty)

            # 3. Update the Order total_price field
                order.total_price = total_order_price
                order.save()

            order.refresh_from_db() # This pulls the new courier data into the 'order' object
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"CRITICAL ERROR: {str(e)}")
            return Response(
                {'error': f"Failed to create order items: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def confirm(self, request, pk=None):
        """Seller confirms the order - changes status from IN_PROGRESS to CONFIRMED"""
        order = get_object_or_404(Order, pk=pk)
        
        #only seller can confirm
        if order.seller != request.user:
            return Response({
                'error': 'Only the seller can confirm this order'
            }, status=status.HTTP_403_FORBIDDEN)

        old_status = order.order_status
        order.order_status = 'confirmed'
        order.save()

        OrderStatusTracking.objects.create(
            order=order,
            old_status=old_status,
            new_status='confirmed'
        )

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)



    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def update_status(self, request, pk=None):
        """update order status by the logistics system"""
        """Standardized status update logic"""
        order = self.get_object()
        new_status = request.data.get('status')
        
        # List of valid transitions can be added here
        old_status = order.order_status
        order.order_status = new_status
        
        if new_status == Order.DELIVERED:
            order.delivered_at = timezone.now()
            order.payment_status = 'paid' # Mark as paid if it was COD

        order.save()
        OrderStatusTracking.objects.create(order=order, old_status=old_status, new_status=new_status)
        
        return Response(self.get_serializer(order).data)



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

        #restore inventory
        for item in order.items.all():
            if item.product:
                item.product.quantity = F('quantity') + item.quantity
                item.product.save()
            elif item.material_listing:
                item.material_listing.quantity = F('quantity') + item.quantity
                item.material_listing.save()

        #update cart items
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
    


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_orders(self, request):
        """get current user's order as buyer"""
        orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def seller_orders(self, request):
        """Get current user's order as seller"""
        orders = Order.objects.filter(seller=request.user).order_by('-created-at')
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """
    Create a Stripe PaymentIntent for the order
    """
    try:
        # Get amount from request
        amount = request.data.get('amount')
        
        if not amount:
            return Response({
                'error': 'Amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert to cents and ensure it's an integer
        try:
            amount_decimal = Decimal(str(amount))
            amount_cents = int(amount_decimal * 100)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure minimum amount (50 cents for USD)
        if amount_cents < 50:
            return Response({
                'error': 'Amount must be at least $0.50'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create PaymentIntent
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                metadata={
                    'user_id': str(request.user.id),
                    'user_email': request.user.email,
                }
            )
            
            return Response({
                'clientSecret': intent.client_secret,
                'paymentIntentId': intent.id
            }, status=status.HTTP_200_OK)
            
        except stripe.error.CardError as e:
            # Card was declined
            return Response({
                'error': str(e.user_message)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters
            return Response({
                'error': f'Invalid request: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe failed
            return Response({
                'error': 'Payment authentication failed. Please contact support.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except stripe.error.APIConnectionError as e:
            # Network communication failed
            return Response({
                'error': 'Network error. Please try again.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        except stripe.error.StripeError as e:
            # Generic Stripe error
            return Response({
                'error': f'Payment error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        # Catch any other errors
        return Response({
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order_with_payment(request):
    """
    Create order and process Stripe payment
    """
    try:
        # Extract data from request
        seller_id = request.data.get('seller_id')
        delivery_address = request.data.get('delivery_address')
        customer_lat = request.data.get('customer_lat')
        customer_lng = request.data.get('customer_lng')
        order_type = request.data.get('order_type')
        items = request.data.get('items', [])
        payment_method_id = request.data.get('payment_method_id')
        
        # Calculate total amount
        total_amount = sum(
            item.get('unit_price', 0) * item.get('quantity', 0)
            for item in items
        )
        
        # Convert to cents for Stripe
        amount_cents = int(total_amount * 100)
        
        # Create Stripe PaymentIntent
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'
                },
                metadata={
                    'seller_id': seller_id,
                    'buyer_id': str(request.user.id),
                    'order_type': order_type,
                }
            )
            
            # Check payment status
            if payment_intent.status == 'succeeded':
                # Create the order
                order = Order.objects.create(
                    seller_id=seller_id,
                    buyer=request.user,
                    delivery_address=delivery_address,
                    customer_lat=customer_lat,
                    customer_lng=customer_lng,
                    order_type=order_type,
                    payment_method_id=payment_method_id,
                    stripe_payment_intent_id=payment_intent.id,
                    payment_status='paid',
                    total_price=total_amount,
                    status='pending'
                )
                
                # Create order items
                for item_data in items:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item_data.get('product_id'),
                        material_listing_id=item_data.get('material_listing_id'),
                        quantity=item_data.get('quantity'),
                        unit_price=item_data.get('unit_price'),
                        unit=item_data.get('unit', 'piece')
                    )
                
                return Response({
                    'id': str(order.id),
                    'payment_status': 'paid',
                    'message': 'Order created and payment successful'
                }, status=status.HTTP_201_CREATED)
            
            else:
                return Response({
                    'error': 'Payment not completed',
                    'payment_status': payment_intent.status
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except stripe.error.CardError as e:
            return Response({
                'error': f'Card error: {str(e.user_message)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.StripeError as e:
            return Response({
                'error': f'Payment error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'error': f'Order creation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """
    Create a Stripe PaymentIntent for the order
    """
    try:
        # Get amount from request
        amount = request.data.get('amount')
        
        if not amount:
            return Response({
                'error': 'Amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert to cents and ensure it's an integer
        try:
            amount_decimal = Decimal(str(amount))
            amount_cents = int(amount_decimal * 100)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure minimum amount (50 cents for USD)
        if amount_cents < 50:
            return Response({
                'error': 'Amount must be at least $0.50'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create PaymentIntent
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                metadata={
                    'user_id': str(request.user.id),
                    'user_email': request.user.email,
                }
            )
            
            return Response({
                'clientSecret': intent.client_secret,
                'paymentIntentId': intent.id
            }, status=status.HTTP_200_OK)
            
        except stripe.error.CardError as e:
            # Card was declined
            return Response({
                'error': str(e.user_message)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters
            return Response({
                'error': f'Invalid request: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe failed
            return Response({
                'error': 'Payment authentication failed. Please contact support.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except stripe.error.APIConnectionError as e:
            # Network communication failed
            return Response({
                'error': 'Network error. Please try again.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        except stripe.error.StripeError as e:
            # Generic Stripe error
            return Response({
                'error': f'Payment error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        # Catch any other errors
        return Response({
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment_and_create_order(request):
    """
    Verify payment succeeded and create the order
    """
    try:
        payment_intent_id = request.data.get('payment_intent_id')
        order_data = request.data.get('order_data')
        
        if not payment_intent_id or not order_data:
            return Response({
                'error': 'Payment intent ID and order data are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify payment with Stripe
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status != 'succeeded':
                return Response({
                    'error': f'Payment not completed. Status: {payment_intent.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except stripe.error.StripeError as e:
            return Response({
                'error': f'Failed to verify payment: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Payment successful, create the order
        from .models import Order, OrderItem
        
        try:
            order = Order.objects.create(
                seller_id=order_data.get('seller_id'),
                buyer=request.user,
                delivery_address=order_data.get('delivery_address'),
                customer_lat=order_data.get('customer_lat'),
                customer_lng=order_data.get('customer_lng'),
                order_type=order_data.get('order_type'),
                stripe_payment_intent_id=payment_intent_id,
                payment_status='paid',
                status='pending'
            )
            
            # Create order items
            total_price = Decimal('0')
            for item_data in order_data.get('items', []):
                unit_price = Decimal(str(item_data.get('unit_price', 0)))
                quantity = int(item_data.get('quantity', 1))
                total_price += unit_price * quantity
                
                OrderItem.objects.create(
                    order=order,
                    product_id=item_data.get('product_id'),
                    material_listing_id=item_data.get('material_listing_id'),
                    quantity=quantity,
                    unit_price=unit_price,
                    unit=item_data.get('unit', 'piece')
                )
            
            order.total_price = total_price
            order.save()
            
            return Response({
                'id': str(order.id),
                'status': order.status,
                'payment_status': 'paid',
                'message': 'Order created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to create order: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'error': f'An unexpected error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

