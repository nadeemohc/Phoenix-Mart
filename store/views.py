import json
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from store.models import Product, CustomUser, Address
from cart.models import Cart, CartItem
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db import transaction


def index(request):
    products = Product.objects.filter(in_stock=1).select_related('category', 'subcategory')

    cart = None
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated and not getattr(request.user, "is_guest", False):
        try:
            # Use select_related to pre-fetch product data for cart items
            cart = Cart.objects.prefetch_related(
                models.Prefetch('items', queryset=CartItem.objects.select_related('product'))
            ).get(user=request.user)
        except Cart.DoesNotExist:
            pass
    else:
        if request.session.session_key:
            try:
                cart = Cart.objects.prefetch_related(
                    models.Prefetch('items', queryset=CartItem.objects.select_related('product'))
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

    return render(
        request,
        "store/index.html",
        {"products": products, "cart_items": cart_items, "cart_total": cart_total},
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

