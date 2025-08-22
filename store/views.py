# in store/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .models import Product, CustomUser, Cart, CartItem, Order, OrderItem, Address
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db import transaction


def index(request):
    products = Product.objects.all()
    
    # Get cart information for the user
    cart_count = 0
    cart_items = []
    cart_total = 0
    
    if request.user.is_authenticated and not request.user.is_guest:
        # For authenticated users
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.items.count()
            cart_items = cart.items.all()
            cart_total = sum(item.product.price * item.quantity for item in cart_items)
        except Cart.DoesNotExist:
            pass
    else:
        # For guest users
        if request.session.session_key:
            try:
                cart = Cart.objects.get(session_key=request.session.session_key, is_guest=True)
                cart_count = cart.items.count()
                cart_items = cart.items.all()
                cart_total = sum(item.product.price * item.quantity for item in cart_items)
            except Cart.DoesNotExist:
                pass
    
    # Add cart information to the request
    request.cart_count = cart_count
    request.cart_items = cart_items
    request.cart_total = cart_total
    
    return render(request, 'store/index.html', {'products': products})


def logout_view(request):
    logout(request)
    return redirect('store:index')

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

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity}
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return _cart_response(cart)


@require_POST
def update_cart_item(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        cart = cart_item.cart
        quantity = int(request.POST.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        return _cart_response(cart)
    except CartItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Item not found"})


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
    """Helper to return consistent cart JSON with rendered HTML."""
    cart_items = cart.items.all()
    cart_count = sum(item.quantity for item in cart_items)
    cart_total = sum(item.product.price * item.quantity for item in cart_items)

    cart_html = render_to_string(
        "store/partials/cart_items.html",
        {"cart_items": cart_items}
    )

    return JsonResponse({
        "success": True,
        "cart_count": cart_count,
        "cart_total": str(cart_total),
        "cart_html": cart_html,
    })

@login_required
@transaction.atomic
def confirm_order(request):
    if request.method == "POST":
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.items.count() == 0:
            return redirect("store:index")

        # Create Order
        order = Order.objects.create(
            user=request.user,
            delivery_address=f"{request.POST['street']}, {request.POST['city']}, {request.POST['zipcode']}, {request.POST['country']}",
            total_price=request.cart_total,
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

        # Create Order Items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

        # Clear Cart
        cart.items.all().delete()

        return render(request, "store/order_success.html", {"order": order})
    
    return redirect("store:index")


    # def login_view(request):
    # if request.method == 'POST':
    #     form = CustomAuthenticationForm(request, data=request.POST)
    #     if form.is_valid():
    #         user = form.get_user()
    #         login(request, user)
    #         return JsonResponse({'success': True})
    #     else:
    #         return JsonResponse({'success': False, 'message': 'Invalid email or password.'})
    # return render(request, 'store/login.html', {'form': CustomAuthenticationForm()})


    # class RegisterView(CreateView):
    # form_class = CustomUserCreationForm
    # template_name = 'store/register.html'
    # success_url = reverse_lazy('store:index')
    
    # def form_valid(self, form):
    #     response = super().form_valid(form)
        
    #     # Get the newly created user
    #     email = form.cleaned_data.get('email')
    #     user = CustomUser.objects.get(email=email)
        
    #     # Check if there was a guest cart for this session
    #     if self.request.session.session_key:
    #         guest_cart = Cart.objects.filter(
    #             session_key=self.request.session.session_key,
    #             is_guest=True
    #         ).first()
            
    #         if guest_cart:
    #             # Create a user cart
    #             user_cart = Cart.objects.create(user=user, is_guest=False)
                
    #             # Merge items from guest cart to user cart
    #             for item in guest_cart.items.all():
    #                 user_item, created = user_cart.items.get_or_create(
    #                     product=item.product,
    #                     defaults={'quantity': item.quantity}
    #                 )
    #                 if not created:
    #                     user_item.quantity += item.quantity
    #                     user_item.save()
                
    #             # Delete the guest cart
    #             guest_cart.delete()
        
    #     # Authenticate and login the user
    #     raw_password = form.cleaned_data.get('password1')
    #     authenticated_user = authenticate(username=email, password=raw_password)
    #     if authenticated_user:
    #         login(self.request, authenticated_user)
        
    #     return response