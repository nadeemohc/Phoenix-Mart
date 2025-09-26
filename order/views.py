import sweetify, re
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from store.models import Product, Address
from cart.models import Cart, CartItem
from decimal import Decimal # Import Decimal for precision


@login_required
@transaction.atomic
def confirm_order(request):
    # Determine the redirect location on failure (likely the index page where the modal lives)
    failure_redirect_url = request.META.get('HTTP_REFERER') or redirect("store:index")

    if request.method == 'POST':
        # --- 1. Extract POST Data ---
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')

        # --- 1.5. SERVER-SIDE VALIDATION WITH SWEETIFY ---
        
        # Check for empty required fields
        required_fields = {
            'full_name': full_name, 'phone': phone, 'street': street, 
            'city': city, 'postcode': postcode, 'country': country,
        }
        
        for field_name, value in required_fields.items():
            if not value or not str(value).strip():
                error_msg = f"The field '{field_name.replace('_', ' ').title()}' is required."
                sweetify.error(request, 'Missing Information', text=error_msg, timer=3000)
                return redirect(failure_redirect_url)
        
        # Basic validation for phone and postcode patterns
        if not re.fullmatch(r'^[0-9]{10,15}$', phone):
            sweetify.error(request, 'Invalid Phone', text="Invalid phone number format (10-15 digits expected).", timer=3000)
            return redirect(failure_redirect_url)

        if not re.fullmatch(r'^[A-Za-z0-9\s\-]{4,10}$', postcode):
            sweetify.error(request, 'Invalid Postcode', text="Invalid postcode format (4-10 characters expected).", timer=3000)
            return redirect(failure_redirect_url)
        
        # --- 2. Determine Items to Process ---
        buy_now_product_id = request.GET.get('buy_now')
        
        items_to_process = []
        if buy_now_product_id:
            try:
                product = get_object_or_404(Product, id=buy_now_product_id)
                quantity = int(request.POST.get('quantity', 1))
                
                items_to_process.append({'product': product, 'quantity': quantity,})
            except Product.DoesNotExist:
                sweetify.error(request, 'Error', text='Product not found.', timer=3000)
                return redirect(failure_redirect_url)
        else:
            # Regular cart checkout
            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart)
                if not cart_items.exists():
                    sweetify.error(request, 'Error', text='Your cart is empty.', timer=3000)
                    return redirect("store:index")

                for item in cart_items:
                    items_to_process.append({'product': item.product, 'quantity': item.quantity,})
            except Cart.DoesNotExist:
                 sweetify.error(request, 'Error', text='Cart not found.', timer=3000)
                 return redirect("store:index")


        # --- 3. Stock Check and Total Price Calculation ---
        order_items_to_create = []
        total_price = Decimal('0.00')

        for item_data in items_to_process:
            product = item_data['product']
            quantity = item_data['quantity']

            # Check stock
            if quantity > product.stock:
                stock_error = f"Not enough stock for {product.name}. Available: {product.stock}"
                sweetify.error(request, 'Stock Error', text=stock_error, timer=5000)
                return redirect(failure_redirect_url) # Redirect back to display alert
            
            item_price = product.price * quantity
            total_price += item_price
            
            order_items_to_create.append({
                'product': product,
                'quantity': quantity,
                'price': product.price,
                'product_instance': product,
            })

        # --- 4. Create Order Object and Save ---
        order = Order(user=request.user, total_price=total_price)
        order.save()
        
        # --- 5-7. Create Items, Reduce Stock, Clear Cart, Create Address (Unchanged) ---
        order_items = []
        for item_data in order_items_to_create:
            product = item_data['product_instance']
            quantity = item_data['quantity']
            
            order_items.append(OrderItem(
                order=order, product=product, quantity=quantity, price=item_data['price']
            ))
            product.stock -= quantity
            product.save(update_fields=["stock"])

        OrderItem.objects.bulk_create(order_items)

        if not buy_now_product_id and 'cart' in locals():
            cart.items.all().delete()

        Address.objects.update_or_create(
            order=order,
            defaults={'full_name': full_name, 'phone': phone, 'street': street, 
                      'city': city, 'state': state, 'zipcode': postcode, 'country': country}
        )
        
        # --- 8. Final Redirect: Success ---
        return redirect('order:order_success', order_id=order.id)

    # --- GET Request Logic ---
    return redirect("store:index")


@login_required
def order_success_page(request, order_id):
    """
    Displays the final success page using the existing template.
    """
    # Get the order and related items to pass to the template
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # You will need to make sure your order_success.html can access 'order'
    context = {
        'order': order,
        # If your success page needs the items, you can pass them too:
        'order_items': OrderItem.objects.filter(order=order), 
    }
    # NOTE: The template path has changed to match your existing file
    return render(request, 'store/order_success.html', context)