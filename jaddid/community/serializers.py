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

    def validate(self, attrs):
        """
        Enforce logical guards for reviews:
        - order_id is required
        - product_id is required
        - prevent duplicate review for same reviewer + order + product
        """
        request = self.context.get("request")
        reviewer = request.user if request else None

        order_id = attrs.get("order_id")
        product_id = attrs.get("product_id")

        if not order_id:
            raise serializers.ValidationError({
                "order_id": "order_id is required to create a review."
            })

        if not product_id:
            raise serializers.ValidationError({
                "product_id": "product_id is required to create a review."
            })

        # Prevent duplicate reviews for the same order + product by the same user
        if reviewer and Review.objects.filter(
            reviewer=reviewer,
            order_id=order_id,
            product_id=product_id
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this product for this order."
            )

        return attrs



class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user',)



