from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from community.services import NotificationService
from community.models import Notification


@receiver(post_save, sender=Order)
def notify_order_status_change(sender, instance, created, **kwargs):
    """Send notification when order status changes to DELIVERED"""
    if not created and instance.order_status == Order.DELIVERED:
        # Notify buyer
        NotificationService.create_notification(
            user=instance.buyer,
            notification_type=Notification.ORDER_STATUS,
            title_en="Order Delivered",
            title_ar="تم تسليم الطلب",
            msg_en=f"Your order {instance.order_id} has been delivered successfully.",
            msg_ar=f"تم تسليم طلبك {instance.order_id} بنجاح.",
            order_id=instance.order_id
        )

        # Notify seller
        NotificationService.create_notification(
            user=instance.seller,
            notification_type=Notification.ORDER_STATUS,
            title_en="Order Delivered",
            title_ar="تم تسليم الطلب",
            msg_en=f"Order {instance.order_id} has been delivered to the buyer.",
            msg_ar=f"تم تسليم الطلب {instance.order_id} للمشتري.",
            order_id=instance.order_id
        )