import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from store.models import Product, CustomUser, Order, OrderItem, Address
from cart.models import Cart
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db import transaction


def index(request):
    # products = Product.objects.all()
    products = Product.objects.filter(in_stock=1)

    # Always initialize cart
    cart = None
    cart_count = 0
    cart_items = []
    cart_total = 0

    if request.user.is_authenticated and not getattr(request.user, "is_guest", False):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    else:
        # Ensure the session exists
        if not request.session.session_key:
            request.session.create()

        try:
            cart = Cart.objects.get(session_key=request.session.session_key, is_guest=True)
        except Cart.DoesNotExist:
            cart = None

    if cart:
        cart_items_with_totals = []
        for item in cart.items.all():
            item_data = {
                "id": item.id,
                "product": item.product,
                "quantity": item.quantity,
                "line_total": item.line_total,  # Assuming you defined @property line_total in model
            }
            cart_items_with_totals.append(item_data)

        cart_count = len(cart_items_with_totals)
        cart_total = sum(item["line_total"] for item in cart_items_with_totals)
        cart_items = cart_items_with_totals

    # Add cart info into request (optional, useful for middleware/templates)
    request.cart_count = cart_count
    request.cart_items = cart_items
    request.cart_total = cart_total

    return render(
        request,
        "store/index.html",
        {"products": products, "cart_items": cart_items, "cart_total": cart_total},
    )



def logout_view(request):
    logout(request)
    return redirect('store:index')


@login_required
@transaction.atomic
def confirm_order(request):
    if request.method == "POST":
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.items.count() == 0:
            return redirect("store:index")

        cart_items = cart.items.all()
        cart_total = sum(item.product.price * item.quantity for item in cart_items)

        # Check stock before creating order
        for item in cart_items:
            if item.quantity > item.product.stock:
                return render(
                    request,
                    "store/order_failed.html",
                    {"message": f"Not enough stock for {item.product.name}"},
                )

        # Create Order
        order = Order.objects.create(
            user=request.user,
            delivery_address=f"{request.POST['street']}, {request.POST['city']}, {request.POST['zipcode']}, {request.POST['country']}",
            total_price=cart_total,
            COD=True
        )

        # Add Address
        Address.objects.create(
            order=order,
            full_name=request.POST['full_name'],
            phone=request.POST['phone'],
            street=request.POST['street'],
            city=request.POST['city'],
            state=request.POST.get('state', ''),
            zipcode=request.POST['zipcode'],
            country=request.POST['country'],
        )

        # Create Order Items + Reduce stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Reduce stock
            item.product.stock -= item.quantity
            item.product.save(update_fields=["stock"])

        # Clear Cart
        cart.items.all().delete()

        return render(request, "store/order_success.html", {"order": order})

    return redirect("store:index")
    

@require_POST
@login_required
def update_profile(request):
    try:
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')

        request.user.first_name = full_name.split(' ')[0]
        request.user.last_name = ' '.join(full_name.split(' ')[1:])
        request.user.phone_number = phone_number
        request.user.save()

        return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

