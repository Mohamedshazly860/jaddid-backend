from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Category, Product, ProductImage, Favorite,
    Order, Review, Message, Report
)
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, ProductImageSerializer, FavoriteSerializer,
    OrderSerializer, ReviewSerializer, MessageSerializer, ReportSerializer
)
from .permissions import IsSellerOrReadOnly, IsOwnerOrReadOnly


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations
    - List all categories
    - Retrieve single category
    - Create/Update/Delete (admin only)
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_ar', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products in a category"""
        category = self.get_object()
        products = Product.objects.filter(
            category=category,
            status='active'
        ).select_related('seller', 'category')
        
        serializer = ProductListSerializer(
            products,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree structure"""
        root_categories = self.queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations
    - List all products (public)
    - Retrieve single product (public)
    - Create product (authenticated users)
    - Update/Delete (owner only)
    """
    queryset = Product.objects.all().select_related(
        'seller', 'category'
    ).prefetch_related('images', 'reviews')
    permission_classes = [IsAuthenticatedOrReadOnly, IsSellerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'condition', 'status', 'seller']
    search_fields = ['title', 'title_ar', 'description', 'location']
    ordering_fields = ['price', 'created_at', 'views_count', 'favorites_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status for non-owners
        if self.action == 'list':
            if not self.request.user.is_authenticated:
                queryset = queryset.filter(status='active')
            else:
                # Show user's own products regardless of status
                queryset = queryset.filter(
                    Q(status='active') | Q(seller=self.request.user)
                )
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving a product"""
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_products(self, request):
        """Get current user's products"""
        products = self.queryset.filter(seller=request.user)
        page = self.paginate_queryset(products)
        
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_favorite(self, request, pk=None):
        """Add or remove product from favorites"""
        product = self.get_object()
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            favorite.delete()
            product.favorites_count = max(0, product.favorites_count - 1)
            product.save(update_fields=['favorites_count'])
            return Response({
                'message': 'Product removed from favorites',
                'is_favorited': False
            })
        else:
            product.favorites_count += 1
            product.save(update_fields=['favorites_count'])
            return Response({
                'message': 'Product added to favorites',
                'is_favorited': True
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for a product"""
        product = self.get_object()
        reviews = product.reviews.filter(is_approved=True).select_related('reviewer')
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """Publish a draft product"""
        product = self.get_object()
        
        if product.seller != request.user:
            return Response(
                {'error': 'You can only publish your own products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if product.status != 'draft':
            return Response(
                {'error': 'Product is not in draft status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product.status = 'active'
        product.published_at = timezone.now()
        product.save()
        
        serializer = self.get_serializer(product)
        return Response(serializer.data)


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user favorites/wishlist
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Favorite.objects.filter(
            user=self.request.user
        ).select_related('product', 'product__seller', 'product__category')
    
    def create(self, request, *args, **kwargs):
        """Add product to favorites"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if already favorited
        product_id = serializer.validated_data['product_id']
        if Favorite.objects.filter(user=request.user, product_id=product_id).exists():
            return Response(
                {'error': 'Product already in favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        
        # Update product favorites count
        product = Product.objects.get(id=product_id)
        product.favorites_count += 1
        product.save(update_fields=['favorites_count'])
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, *args, **kwargs):
        """Remove product from favorites"""
        instance = self.get_object()
        product = instance.product
        
        # Update product favorites count
        product.favorites_count = max(0, product.favorites_count - 1)
        product.save(update_fields=['favorites_count'])
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order management
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status']
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Users can only see their own orders (as buyer or seller)"""
        return Order.objects.filter(
            Q(buyer=self.request.user) | Q(seller=self.request.user)
        ).select_related('buyer', 'seller', 'product')
    
    @action(detail=False, methods=['get'])
    def purchases(self, request):
        """Get user's purchases (as buyer)"""
        orders = self.get_queryset().filter(buyer=request.user)
        page = self.paginate_queryset(orders)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Get user's sales (as seller)"""
        orders = self.get_queryset().filter(seller=request.user)
        page = self.paginate_queryset(orders)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm an order (seller only)"""
        order = self.get_object()
        
        if order.seller != request.user:
            return Response(
                {'error': 'Only seller can confirm orders'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'pending':
            return Response(
                {'error': 'Order is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark order as completed (seller only)"""
        order = self.get_object()
        
        if order.seller != request.user:
            return Response(
                {'error': 'Only seller can complete orders'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status not in ['confirmed', 'in_progress']:
            return Response(
                {'error': 'Order must be confirmed or in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.save()
        
        # Update product status if quantity is depleted
        product = order.product
        if product.quantity <= order.quantity:
            product.status = 'sold'
            product.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        # Both buyer and seller can cancel
        if order.buyer != request.user and order.seller != request.user:
            return Response(
                {'error': 'You are not authorized to cancel this order'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot cancel completed or already cancelled orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product Reviews
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Review.objects.filter(is_approved=True).select_related(
            'reviewer', 'product'
        )
        
        # Filter by product if specified
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_reviews(self, request):
        """Get current user's reviews"""
        reviews = Review.objects.filter(reviewer=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for messaging between users
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get messages sent to or by the current user"""
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).select_related('sender', 'recipient', 'product')
    
    @action(detail=False, methods=['get'])
    def inbox(self, request):
        """Get received messages"""
        messages = self.get_queryset().filter(recipient=request.user)
        page = self.paginate_queryset(messages)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get sent messages"""
        messages = self.get_queryset().filter(sender=request.user)
        page = self.paginate_queryset(messages)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        
        if message.recipient != request.user:
            return Response(
                {'error': 'You can only mark your own messages as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not message.is_read:
            message.is_read = True
            message.read_at = timezone.now()
            message.save()
        
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread messages"""
        count = self.get_queryset().filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for reporting products
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Report.objects.all().select_related(
            'reporter', 'product', 'resolved_by'
        )
        
        # Regular users can only see their own reports
        if not self.request.user.is_staff:
            queryset = queryset.filter(reporter=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_reports(self, request):
        """Get current user's reports"""
        reports = Report.objects.filter(reporter=request.user)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)
