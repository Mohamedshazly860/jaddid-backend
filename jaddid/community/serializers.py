from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Review, Notification

User = get_user_model()


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.StringRelatedField(read_only=True)
    target_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ('reviewer',)
        ref_name = "CommunityReview"


class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user',)