from rest_framework import serializers
from django.db import transaction
from .models import (
    Category, Product, ProductImage, Favorite,
    Order, Review, Message, Report
)
from accounts.models import User


class CategorySerializer(serializers.ModelSerializer):
    """Category Serializer"""
    
    subcategories = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'name_ar', 'description', 'icon',
            'parent', 'subcategories', 'is_active', 
            'product_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(
                obj.subcategories.filter(is_active=True), 
                many=True, 
                context=self.context
            ).data
        return []
    
    def get_product_count(self, obj):
        return obj.products.filter(status='active').count()


class ProductImageSerializer(serializers.ModelSerializer):
    """Product Image Serializer"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Product List Serializer - Lightweight for list views"""
    
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'title_ar', 'price', 'quantity', 'unit',
            'condition', 'status', 'location', 'seller_name', 
            'seller_email', 'category_name', 'primary_image',
            'views_count', 'favorites_count', 'is_favorited',
            'created_at', 'published_at'
        ]
        read_only_fields = ['id', 'views_count', 'favorites_count', 'created_at', 'published_at']
    
    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
        return None
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product Detail Serializer - Complete information"""
    
    seller = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'category', 'title', 'title_ar',
            'description', 'description_ar', 'price', 'quantity',
            'unit', 'condition', 'status', 'location', 'latitude',
            'longitude', 'images', 'views_count', 'favorites_count',
            'is_favorited', 'average_rating', 'review_count',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'views_count', 'favorites_count', 
            'created_at', 'updated_at', 'published_at'
        ]
    
    def get_seller(self, obj):
        return {
            'id': str(obj.seller.id),
            'name': obj.seller.get_full_name(),
            'email': obj.seller.email,
            'role': obj.seller.role
        }
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0.0
    
    def get_review_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product Create/Update Serializer"""
    
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'title', 'title_ar', 'description',
            'description_ar', 'price', 'quantity', 'unit', 'condition',
            'status', 'location', 'latitude', 'longitude', 'images',
            'uploaded_images'
        ]
        read_only_fields = ['id']
    
    @transaction.atomic
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        validated_data['seller'] = self.context['request'].user
        product = Product.objects.create(**validated_data)
        
        # Create product images
        for idx, image in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(idx == 0),
                order=idx
            )
        
        return product
    
    @transaction.atomic
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images if provided
        if uploaded_images:
            current_count = instance.images.count()
            for idx, image in enumerate(uploaded_images):
                ProductImage.objects.create(
                    product=instance,
                    image=image,
                    is_primary=(current_count == 0 and idx == 0),
                    order=current_count + idx
                )
        
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    """Favorite Serializer"""
    
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """Order Serializer"""
    
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'buyer', 'buyer_name', 'seller',
            'seller_name', 'product', 'product_id', 'product_title',
            'quantity', 'unit_price', 'total_price', 'status',
            'payment_status', 'notes', 'delivery_address',
            'created_at', 'updated_at', 'confirmed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'buyer', 'seller', 'total_price',
            'created_at', 'updated_at', 'confirmed_at', 'completed_at'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        product_id = validated_data.pop('product_id', None)
        
        if product_id:
            product = Product.objects.get(id=product_id)
            validated_data['product'] = product
            validated_data['seller'] = product.seller
        
        validated_data['buyer'] = request.user
        validated_data['unit_price'] = validated_data['product'].price
        
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """Review Serializer"""
    
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'product_id', 'product_title', 'reviewer',
            'reviewer_name', 'order', 'rating', 'title', 'comment',
            'is_verified_purchase', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reviewer', 'is_verified_purchase', 
            'is_approved', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        product_id = validated_data.pop('product_id', None)
        
        if product_id:
            product = Product.objects.get(id=product_id)
            validated_data['product'] = product
        
        validated_data['reviewer'] = request.user
        
        # Check if this is a verified purchase
        if validated_data.get('order'):
            order = validated_data['order']
            if order.buyer == request.user and order.status == 'completed':
                validated_data['is_verified_purchase'] = True
        
        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    """Message Serializer"""
    
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    recipient_id = serializers.UUIDField(write_only=True, required=False)
    product_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_id',
            'recipient_name', 'product', 'product_id', 'product_title',
            'subject', 'message', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at']
    
    def create(self, validated_data):
        request = self.context['request']
        recipient_id = validated_data.pop('recipient_id', None)
        product_id = validated_data.pop('product_id', None)
        
        if recipient_id:
            validated_data['recipient'] = User.objects.get(id=recipient_id)
        
        if product_id:
            validated_data['product'] = Product.objects.get(id=product_id)
        
        validated_data['sender'] = request.user
        
        return super().create(validated_data)


class ReportSerializer(serializers.ModelSerializer):
    """Report Serializer"""
    
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_name', 'product', 'product_id',
            'product_title', 'reason', 'description', 'status',
            'admin_notes', 'resolved_by', 'created_at', 'updated_at',
            'resolved_at'
        ]
        read_only_fields = [
            'id', 'reporter', 'status', 'admin_notes', 
            'resolved_by', 'created_at', 'updated_at', 'resolved_at'
        ]
    
    def create(self, validated_data):
        request = self.context['request']
        product_id = validated_data.pop('product_id', None)
        
        if product_id:
            validated_data['product'] = Product.objects.get(id=product_id)
        
        validated_data['reporter'] = request.user
        
        return super().create(validated_data)
