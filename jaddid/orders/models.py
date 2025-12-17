import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User
from marketplace.models import Product, MaterialListing

class Order(models.Model):
    """Main Order model"""

    PRODUCT = 'product'
    MATERIAL = 'material'
    ORDER_TYPE_CHOICES = [
        (PRODUCT, 'Product'),
        (MATERIAL, 'Material')
    ]

    IN_PROGRESS = 'in_progress'
    IN_WAY = 'in_way'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    ORDER_STATUS_CHOICES = [
        (IN_PROGRESS, 'In Progress'),
        (IN_WAY, 'In Way'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled')
    ]

    PAID = 'paid'
    UNPAID = 'unpaid'
    PAYMENT_STATUS_CHOICES = [
        (PAID, 'Paid'),
        (UNPAID, 'Unpaid')
    ]
    
    COD = 'cash_on_delivery'
    PAYMENT_METHOD_CHOICES = [
        (COD, 'Cash on Delivery')
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_seller')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    delivery_address = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default=IN_PROGRESS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=UNPAID)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=COD)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['order_status']),
        ]

    def __str__(self):
        return f"Order {self.order_id} from {self.buyer.email} to {self.seller.email}"


class OrderItem(models.Model):
    """Individual items in an order"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    material_listing = models.ForeignKey(MaterialListing, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self):
        if self.product:
            return f"{self.quantity} x {self.product.title}"
        elif self.material_listing:
            return f"{self.quantity} x {self.material_listing.material.name}"
        return f"OrderItem {self.id}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.product and self.material_listing) or (not self.product and not self.material_listing):
            raise ValidationError("Each item must have either product or material_listing, not both or none.")


class OrderStatusTracking(models.Model):
    """Tracks every order status change"""

    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['new_status']),
        ]

    def __str__(self):
        return f"Order {self.order.order_id} status change: {self.old_status} → {self.new_status}"
