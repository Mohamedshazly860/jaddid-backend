from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusTracking
from marketplace.models import Product, MaterialListing
from django.db import transaction

class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    material_name = serializers.CharField(source='material_listing.material.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'material_listing', 'quantity', 'unit_price', 'product_title', 'material_name']
        read_only_fields = ['unit_price', 'product_title', 'material_name', 'order']

    def validate(self, data):
        product = data.get('product')
        listing = data.get('material_listing')
        if (product and listing) or (not product and not listing):
            raise serializers.ValidationError("Each item must have either product or material_listing, not both or none.")

        order = self.context.get('order')
        if order:
            if order.order_type == Order.PRODUCT and listing:
                raise serializers.ValidationError("Product order cannot have a material listing item.")
            if order.order_type == Order.MATERIAL and product:
                raise serializers.ValidationError("Material order cannot have a product item.")
        return data


class OrderStatusTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusTracking
        fields = ['log_id', 'order', 'old_status', 'new_status', 'changed_at']
        read_only_fields = ['log_id', 'order', 'old_status', 'new_status', 'changed_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    status_logs = OrderStatusTrackingSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'buyer', 'buyer_email', 'seller', 'seller_email',
            'order_type', 'delivery_address', 'total_price', 'order_status',
            'payment_status', 'payment_method', 'created_at', 'updated_at',
            'delivered_at', 'cancelled_at', 'items', 'status_logs'
        ]
        read_only_fields = ['total_price', 'order_status', 'payment_status', 'created_at', 'updated_at', 'delivered_at', 'cancelled_at']
        ref_name = 'OrdersOrderSerializer'

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['buyer'] = self.context['request'].user

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            total_price = 0
            for item_data in items_data:
                if item_data.get('product'):
                    product = Product.objects.get(pk=item_data['product'].id)
                    item_data['unit_price'] = product.price
                elif item_data.get('material_listing'):
                    listing = MaterialListing.objects.get(pk=item_data['material_listing'].id)
                    item_data['unit_price'] = listing.price_per_unit

                OrderItem.objects.create(order=order, **item_data)
                total_price += item_data['quantity'] * item_data['unit_price']

            order.total_price = total_price
            order.save()
            OrderStatusTracking.objects.create(order=order, old_status=None, new_status=Order.IN_PROGRESS)

        return order
