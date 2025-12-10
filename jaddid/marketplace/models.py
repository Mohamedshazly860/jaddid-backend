import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import User


class Category(models.Model):
    """Product Category Model for organizing recyclable materials"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Category Name"), max_length=100, unique=True)
    name_ar = models.CharField(_("Arabic Name"), max_length=100, blank=True)
    description = models.TextField(_("Description"), blank=True)
    icon = models.ImageField(
        _("Category Icon"), 
        upload_to="categories/%Y/%m/", 
        null=True, 
        blank=True
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subcategories',
        null=True,
        blank=True,
        verbose_name=_("Parent Category")
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Recyclable Product Listing Model"""
    
    # Product Condition Choices
    NEW = 'new'
    LIKE_NEW = 'like_new'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    
    CONDITION_CHOICES = [
        (NEW, _('New')),
        (LIKE_NEW, _('Like New')),
        (GOOD, _('Good')),
        (FAIR, _('Fair')),
        (POOR, _('Poor')),
    ]
    
    # Product Status Choices
    DRAFT = 'draft'
    ACTIVE = 'active'
    SOLD = 'sold'
    RESERVED = 'reserved'
    DELETED = 'deleted'
    
    STATUS_CHOICES = [
        (DRAFT, _('Draft')),
        (ACTIVE, _('Active')),
        (SOLD, _('Sold')),
        (RESERVED, _('Reserved')),
        (DELETED, _('Deleted')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_("Seller")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_("Category")
    )
    
    # Basic Information
    title = models.CharField(_("Product Title"), max_length=200)
    title_ar = models.CharField(_("Arabic Title"), max_length=200, blank=True)
    description = models.TextField(_("Description"))
    description_ar = models.TextField(_("Arabic Description"), blank=True)
    
    # Pricing & Quantity
    price = models.DecimalField(
        _("Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(
        _("Quantity"),
        default=1,
        validators=[MinValueValidator(1)]
    )
    unit = models.CharField(
        _("Unit"),
        max_length=50,
        default='kg',
        help_text=_("Unit of measurement (kg, ton, piece, etc.)")
    )
    
    # Product Details
    condition = models.CharField(
        _("Condition"),
        max_length=20,
        choices=CONDITION_CHOICES,
        default=GOOD
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT
    )
    
    # Location
    location = models.CharField(_("Location"), max_length=255)
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Engagement Metrics
    views_count = models.PositiveIntegerField(_("Views Count"), default=0)
    favorites_count = models.PositiveIntegerField(_("Favorites Count"), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(_("Published At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-published_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.seller.email}"
    
    def save(self, *args, **kwargs):
        if self.status == self.ACTIVE and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Product Images Model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_("Product")
    )
    image = models.ImageField(
        _("Image"),
        upload_to="products/%Y/%m/"
    )
    is_primary = models.BooleanField(_("Primary Image"), default=False)
    order = models.PositiveIntegerField(_("Order"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"Image for {self.product.title}"


class Favorite(models.Model):
    """User Favorites/Wishlist Model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_("User")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name=_("Product")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Favorite")
        verbose_name_plural = _("Favorites")
        unique_together = ['user', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.product.title}"


class Order(models.Model):
    """Order/Purchase Model"""
    
    # Order Status Choices
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (CONFIRMED, _('Confirmed')),
        (IN_PROGRESS, _('In Progress')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
        (REFUNDED, _('Refunded')),
    ]
    
    # Payment Status
    UNPAID = 'unpaid'
    PAID = 'paid'
    PARTIAL = 'partial'
    
    PAYMENT_STATUS_CHOICES = [
        (UNPAID, _('Unpaid')),
        (PAID, _('Paid')),
        (PARTIAL, _('Partial')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        _("Order Number"),
        max_length=50,
        unique=True,
        editable=False
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name=_("Buyer")
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name=_("Seller")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_("Product")
    )
    
    # Order Details
    quantity = models.PositiveIntegerField(_("Quantity"))
    unit_price = models.DecimalField(
        _("Unit Price"),
        max_digits=10,
        decimal_places=2
    )
    total_price = models.DecimalField(
        _("Total Price"),
        max_digits=10,
        decimal_places=2
    )
    
    # Status
    status = models.CharField(
        _("Order Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    payment_status = models.CharField(
        _("Payment Status"),
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=UNPAID
    )
    
    # Additional Information
    notes = models.TextField(_("Notes"), blank=True)
    delivery_address = models.TextField(_("Delivery Address"), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(_("Confirmed At"), null=True, blank=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f"ORD-{timestamp}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        
        super().save(*args, **kwargs)


class Review(models.Model):
    """Product Review and Rating Model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_("Product")
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        verbose_name=_("Reviewer")
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name=_("Order")
    )
    
    # Review Content
    rating = models.PositiveIntegerField(
        _("Rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(_("Review Title"), max_length=200, blank=True)
    comment = models.TextField(_("Comment"), blank=True)
    
    # Review Status
    is_verified_purchase = models.BooleanField(_("Verified Purchase"), default=False)
    is_approved = models.BooleanField(_("Approved"), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ['-created_at']
        unique_together = ['product', 'reviewer', 'order']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['reviewer']),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.email} for {self.product.title}"


class Message(models.Model):
    """Messaging System between Buyers and Sellers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_("Sender")
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name=_("Recipient")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name=_("Product")
    )
    
    # Message Content
    subject = models.CharField(_("Subject"), max_length=200, blank=True)
    message = models.TextField(_("Message"))
    
    # Status
    is_read = models.BooleanField(_("Read"), default=False)
    read_at = models.DateTimeField(_("Read At"), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender.email} to {self.recipient.email}"


class Report(models.Model):
    """Product/User Report Model for flagging inappropriate content"""
    
    # Report Reasons
    SPAM = 'spam'
    INAPPROPRIATE = 'inappropriate'
    FRAUD = 'fraud'
    DUPLICATE = 'duplicate'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SPAM, _('Spam')),
        (INAPPROPRIATE, _('Inappropriate Content')),
        (FRAUD, _('Fraud/Scam')),
        (DUPLICATE, _('Duplicate Listing')),
        (OTHER, _('Other')),
    ]
    
    # Report Status
    PENDING = 'pending'
    REVIEWING = 'reviewing'
    RESOLVED = 'resolved'
    DISMISSED = 'dismissed'
    
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (REVIEWING, _('Reviewing')),
        (RESOLVED, _('Resolved')),
        (DISMISSED, _('Dismissed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name=_("Reporter")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name=_("Product")
    )
    
    # Report Details
    reason = models.CharField(
        _("Reason"),
        max_length=20,
        choices=REASON_CHOICES
    )
    description = models.TextField(_("Description"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    
    # Admin Response
    admin_notes = models.TextField(_("Admin Notes"), blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_resolved',
        verbose_name=_("Resolved By")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(_("Resolved At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"Report by {self.reporter.email} on {self.product.title}"
