from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from order.models import Order, OrderItem
from django.contrib.auth import get_user_model


class CustomUserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            # For OAuth users, no password is required
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    # Make email the primary identifier
    email = models.EmailField(_('email address'), unique=True)
    username = None  # We don't need username
    
    # Additional fields for e-commerce
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    default_address = models.TextField(blank=True, null=True)
    
    # Guest user flag
    is_guest = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'  # Use email as the username field
    REQUIRED_FIELDS = []  # Email and password are required by default
    
    objects = CustomUserManager()  # Use the custom manager
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return self.email

class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    
    class Meta:
        unique_together = ('category', 'slug')
        verbose_name_plural = "Subcategories"
    
    def __str__(self):
        return f"{self.category.name} → {self.name}"

class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="products"
    )
    name = models.CharField(max_length=200)  # Base product name (e.g. Mackerel)
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this product from the frontend")

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    subcategory = models.ForeignKey(
        SubCategory, on_delete=models.CASCADE, related_name="variants"
    )
    name = models.CharField(max_length=200)  # e.g. "Mackerel - Cleaned"
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='product_variants/', blank=True, null=True)
    in_stock = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this variant from the frontend")

    class Meta:
        unique_together = ('product', 'subcategory')  # one variant per subcategory

    def __str__(self):
        return f"{self.product.name} - {self.subcategory.name}"

    def save(self, *args, **kwargs):
        # Check if this is a manual admin save (when in_stock is being explicitly changed)
        # If not, auto-update in_stock based on stock quantity
        if not hasattr(self, '_manual_in_stock_override'):
            self.in_stock = self.stock > 0
        super().save(*args, **kwargs)


# Get the custom user model
User = get_user_model()

class Address(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="address")
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.full_name}, {self.city}"