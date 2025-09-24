from django.db import models
from django.conf import settings  # ✅ use this for the user model


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,   # ✅ safer than importing get_user_model()
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts"
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_guest = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest cart ({self.session_key})"

    def merge_with(self, other_cart):
        """Merge items from another cart into this one"""
        for item in other_cart.items.all():
            existing_item, created = self.items.get_or_create(
                product=item.product,
                defaults={"quantity": item.quantity}
            )
            if not created:
                existing_item.quantity += item.quantity
                existing_item.save()
        other_cart.delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("store.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"
