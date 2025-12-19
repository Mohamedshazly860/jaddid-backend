from django.forms import ValidationError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from accounts.serializers import ProfileSerializer
from orders import permissions
from .models import Review, Notification
from .serializers import ReviewSerializer, NotificationSerializer
from accounts.models import Profile


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer
    # permission_classes=[permissions.]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_backend = ['rating', 'target_user']
    ordering_fields = ['rating', 'created_at']

    def perform_create(self, serializer):
        """ensures the reviewer is automatically set to the logged-in user
        and if the item belongs to user he will not be able to review themselves"""
        target_user = serializer.validated_data.get('target_user')
        if target_user == self.request.user:
            raise ValidationError("You Cannot review yourself")
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    # permission_classes=[permissions.IsAuthenticated]

    def get_queryset(self):
        """users will be able to view notifications sent to them only"""
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    

    def perform_create(self, serializer):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)
    
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