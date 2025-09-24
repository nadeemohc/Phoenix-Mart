# in store/context_processors.py
from cart.models import Cart, CartItem

def cart_context(request):
    cart_count = 0
    cart_items = []
    cart_total = 0
    
    if request.user.is_authenticated and not request.user.is_guest:
        # For authenticated users
        try:
            cart = Cart.objects.get(user=request.user)
            # Corrected logic: sum the quantities of all items
            cart_count = sum(item.quantity for item in cart.items.all())
            cart_items = cart.items.all()
            cart_total = sum(item.product.price * item.quantity for item in cart_items)
        except Cart.DoesNotExist:
            pass
    else:
        # For guest users
        if request.session.session_key:
            try:
                cart = Cart.objects.get(session_key=request.session.session_key, is_guest=True)
                # Corrected logic: sum the quantities of all items
                cart_count = sum(item.quantity for item in cart.items.all())
                cart_items = cart.items.all()
                cart_total = sum(item.product.price * item.quantity for item in cart_items)
            except Cart.DoesNotExist:
                pass
    
    return {
        'cart_count': cart_count,
        'cart_items': cart_items,
        'cart_total': cart_total
    }