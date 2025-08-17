from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem

@receiver(user_logged_in)
def merge_carts(sender, request, user, **kwargs):
    if request.session.session_key:
        # Get anonymous cart if exists
        anonymous_cart = Cart.objects.filter(
            session_key=request.session.session_key,
            user__isnull=True
        ).first()
        
        if anonymous_cart:
            # Get or create user cart
            user_cart, created = Cart.objects.get_or_create(user=user)
            
            # Move items from anonymous to user cart
            for item in anonymous_cart.items.all():
                user_item, created = user_cart.items.get_or_create(
                    product=item.product,
                    defaults={'quantity': item.quantity}
                )
                if not created:
                    user_item.quantity += item.quantity
                    user_item.save()
            
            # Delete anonymous cart
            anonymous_cart.delete()