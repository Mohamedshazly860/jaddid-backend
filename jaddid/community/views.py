from django.forms import ValidationError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from accounts.serializers import ProfileSerializer
from .models import Review, Notification
from .serializers import ReviewSerializer, NotificationSerializer
from accounts.models import Profile
from .services import NotificationService
from orders.models import Order



class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_backend = ['rating', 'target_user']
    ordering_fields = ['rating', 'created_at']

    def perform_create(self, serializer):
        """
        - Assign reviewer correctly
        - Prevent self-review
        - Ensure order_id exists (extra safety)
        """
        reviewer = self.request.user

        order = serializer.validated_data.get('order')
        product = serializer.validated_data.get('product')
        material = serializer.validated_data.get('material_listing')

        if not order:
            raise ValidationError("Order is required to create a review.")

        if order.buyer != reviewer:
            raise ValidationError("You can only review orders you purchased.")

        if order.order_status not in [Order.DELIVERED, Order.COMPLETED]:
            raise ValidationError("You can only review delivered orders.")

        item_exists = order.items.filter(
            product=product if product else None,
            material_listing=material if material else None
        ).exists()

        if not item_exists:
            raise ValidationError("This product is not part of this order.")

        if Review.objects.filter(
            reviewer=reviewer,
            order=order,
            product=product,
            material_listing=material
        ).exists():
            raise ValidationError("You already reviewed this item for this order.")

        serializer.save(
            reviewer=reviewer,
            is_verified_purchase=True
        )

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()  # ← سطر الحل
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """users will be able to view notifications sent to them only"""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    

    # def perform_create(self, serializer):
    #     return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})

    # @action(detail=False, methods=['post'])
    # def mark_all_as_read(self, request):
    #     Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    #     return Response({'status': 'all notifications marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})
    

class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.filter(review_count__gt=0).order_by('-average_rating')
    serializer_class = ProfileSerializer

    @action(detail=False, methods=['get'])
    def top_rated(self, requested):
        "returns top sellers with atleast 1 review"
        top_sellers = self.queryset()
        serializer = self.get_serializer(top_sellers, many=True)
        return Response(serializer.data)


