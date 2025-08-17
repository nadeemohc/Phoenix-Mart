from .models import Cart, CartItem

def cart_context(request):
    context = {}
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        if request.session.session_key:
            cart = Cart.objects.filter(
                session_key=request.session.session_key,
                user__isnull=True
            ).first()
        else:
            cart = None
    
    if cart:
        cart_items = cart.items.all()
        context.update({
            'cart_count': sum(item.quantity for item in cart_items),
            'cart_items': cart_items,
            'cart_total': sum(item.product.price * item.quantity for item in cart_items)
        })
    else:
        context.update({
            'cart_count': 0,
            'cart_items': [],
            'cart_total': 0
        })
    return context