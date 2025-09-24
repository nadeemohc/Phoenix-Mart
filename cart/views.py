import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from cart.models import Cart, CartItem
from store.models import Product
from django.http import JsonResponse
from django.template.loader import render_to_string



@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get("quantity", 1))

    # Get or create cart
    if request.user.is_authenticated and not request.user.is_guest:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"is_guest": False})
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key, defaults={"is_guest": True}
        )

    # Increment if exists, otherwise create
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity
    cart_item.save()

    return _cart_response(cart)


@require_POST
def update_cart_item(request, item_id):
    try:
        data = json.loads(request.body)
        quantity = int(data.get("quantity", 1))

        cart_item = CartItem.objects.get(id=item_id)
        cart = cart_item.cart

        if quantity > 0:
            cart_item.quantity = quantity  # absolute set
            cart_item.save()
        else:
            cart_item.delete()

        return _cart_response(cart)

    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Item not found"})
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "message": "Invalid quantity."})


@require_POST
def remove_cart_item(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        cart = cart_item.cart
        cart_item.delete()
        return _cart_response(cart)
    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Item not found"})


def _cart_response(cart):
    cart_items = CartItem.objects.filter(cart=cart).select_related("product")

    cart_items_with_totals = [
        {
            "id": item.id,
            "name": item.product.name,
            "image_url": item.product.image.url,
            "price": item.product.price,
            "quantity": item.quantity,
            "line_total": item.line_total,
        }
        for item in cart_items
    ]

    cart_count = len(cart_items_with_totals)
    cart_total = sum(item["line_total"] for item in cart_items_with_totals)

    cart_html = render_to_string(
        "store/partials/cart_items.html",
        {"cart_items": cart_items_with_totals},
    )

    return JsonResponse({
        "success": True,
        "cart_count": cart_count,
        "cart_total": f"{cart_total:.2f}",
        "cart_html": cart_html,
    })



def get_cart_summary(request):
    """
    Returns the updated cart summary HTML for the checkout modal.
    """
    cart_items = []
    cart_total = 0
    
    # Get the correct cart
    if request.user.is_authenticated and not request.user.is_guest:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    else:
        if request.session.session_key:
            try:
                cart = Cart.objects.get(session_key=request.session.session_key, is_guest=True)
            except Cart.DoesNotExist:
                cart = None

    if cart:
        # Create a new list to hold the items with their calculated totals
        cart_items_with_totals = []
        for item in cart.items.all():
            item_data = {
                'id': item.id,
                'product': item.product,
                'quantity': item.quantity,
                'line_total': item.line_total  # Read the property
            }
            cart_items_with_totals.append(item_data)
        
        cart_total = sum(item['line_total'] for item in cart_items_with_totals)
        cart_items = cart_items_with_totals # Use this new list

    summary_html = render_to_string(
        'store/partials/checkout_summary.html',
        {
            'cart_items': cart_items,
            'cart_total': cart_total
        },
        request=request
    )
    
    return JsonResponse({
        'success': True,
        'summary_html': summary_html
    })