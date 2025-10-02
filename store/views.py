import json
from django.db import models, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from store.models import Product, CustomUser, Address, Category, ProductVariant
from cart.models import Cart, CartItem
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q


# store/views.py

# ... (Existing imports) ...
from store.models import Product, CustomUser, Address, Category # Make sure to import Category
# ... (Other imports) ...

def index(request):
    # --- 1. Prefetch only active products that have at least one active in-stock variant ---
    products_qs = Product.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.filter(in_stock=True, is_active=True),
            to_attr='available_variants'  # each product will now have this attr
        )
    ).filter(
        variants__in_stock=True, variants__is_active=True  # only include products with at least one active in-stock variant
    ).distinct().order_by('name')

    # --- 2. Prefetch products for each category ---
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=products_qs)
    ).distinct()

    # --- 3. Cart Logic (Remains the same) ---
    cart = None
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated and not getattr(request.user, "is_guest", False):
        try:
            cart = Cart.objects.prefetch_related(
                Prefetch('items', queryset=CartItem.objects.select_related('product'))
            ).get(user=request.user)
        except Cart.DoesNotExist:
            pass
    else:
        if request.session.session_key:
            try:
                cart = Cart.objects.prefetch_related(
                    Prefetch('items', queryset=CartItem.objects.select_related('product'))
                ).get(session_key=request.session.session_key, is_guest=True)
            except Cart.DoesNotExist:
                pass

    cart_items = []
    if cart:
        cart_items_with_totals = []
        for item in cart.items.all():
            item_data = {
                "id": item.id,
                "product": item.product,
                "quantity": item.quantity,
                "line_total": item.line_total,
            }
            cart_items_with_totals.append(item_data)

        cart_count = len(cart_items_with_totals)
        cart_total = sum(item["line_total"] for item in cart_items_with_totals)
        cart_items = cart_items_with_totals

    request.cart_count = cart_count
    request.cart_items = cart_items
    request.cart_total = cart_total

    # --- 4. Render template ---
    return render(
        request,
        "store/index.html",
        {
            "categories": categories,
            "cart_items": cart_items,
            "cart_total": cart_total,
        },
    )




def logout_view(request):
    logout(request)
    return redirect('store:index')


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



def buy_now(request, product_id):
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
            variant_id = int(request.POST.get("variant_id"))
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Invalid quantity or variant."}, status=400)
            
        product = get_object_or_404(Product, id=product_id)
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
        
        if not variant.in_stock:
            return JsonResponse({"success": False, "message": "This variant is out of stock."}, status=400)

        # Store the Buy Now item data in the session
        # This is a temporary "cart" for the checkout process
        request.session['buy_now_item'] = {
            'variant_id': variant.id,
            'name': f"{product.name} - {variant.subcategory.name}",
            'quantity': quantity,
            'price': float(variant.price),
            'line_total': float(variant.price * quantity)
        }
        
        # This part remains the same to render the summary for the modal
        temp_item = {
            "product": variant,  # Use variant instead of product
            "quantity": quantity,
            "line_total": variant.price * quantity,
        }

        summary_html = render_to_string(
            "store/partials/checkout_summary.html",
            {
                "cart_items": [temp_item],
                "cart_total": temp_item["line_total"],
                "is_buy_now": True,
            },
            request=request,
        )

        return JsonResponse({
            "success": True,
            "summary_html": summary_html,
        })

    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)
