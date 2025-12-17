from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]