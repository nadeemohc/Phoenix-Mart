import sweetify, re
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from store.models import Product, ProductVariant, Address
from cart.models import Cart, CartItem
from decimal import Decimal # Import Decimal for precision


@login_required
@transaction.atomic
def confirm_order(request):
    # Determine the redirect location on failure (likely the index page where the modal lives)
    failure_redirect_url = request.META.get('HTTP_REFERER') or redirect("store:index")

    if request.method == 'POST':
        # --- 1. Extract POST Data and Validate ---
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        street = request.POST.get('street')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')

        # --- 1.5. SERVER-SIDE VALIDATION WITH SWEETIFY ---
        
        # Check for empty required fields (existing logic retained)
        required_fields = {
            'full_name': full_name, 'phone': phone, 'street': street, 
            'city': city, 'postcode': postcode, 'country': country,
        }
        
        for field_name, value in required_fields.items():
            if not value or not str(value).strip():
                error_msg = f"The field '{field_name.replace('_', ' ').title()}' is required."
                sweetify.error(request, 'Missing Information', text=error_msg, timer=3000)
                return redirect(failure_redirect_url)
        
        # Basic validation for phone and postcode patterns (existing logic retained)
        if not re.fullmatch(r'^[0-9]{10,15}$', phone):
            sweetify.error(request, 'Invalid Phone', text="Invalid phone number format (10-15 digits expected).", timer=3000)
            return redirect(failure_redirect_url)

        if not re.fullmatch(r'^[A-Za-z0-9\s\-]{4,10}$', postcode):
            sweetify.error(request, 'Invalid Postcode', text="Invalid postcode format (4-10 characters expected).", timer=3000)
            return redirect(failure_redirect_url)
        
        # --- 2. Determine Items to Process (FIXED LOGIC) ---
        
        buy_now_variant_id = request.POST.get('variant_id') 
        items_to_process = []
        is_buy_now = False

        if buy_now_variant_id:
            # --- BUY NOW PATH ---
            is_buy_now = True
            try:
                # Ensure quantity is safely converted
                quantity = int(request.POST.get('quantity', 0))
                if quantity <= 0:
                    raise ValueError("Quantity must be positive.")
                    
                variant = get_object_or_404(ProductVariant, id=buy_now_variant_id) 
                
                # Use 'variant' in the dictionary for consistency
                items_to_process.append({'variant': variant, 'quantity': quantity,})
            except (ValueError, TypeError) as e:
                sweetify.error(request, 'Error', text='Invalid quantity for Buy Now.', timer=3000)
                # Ensure Buy Now session data is cleared on error during processing
                if 'buy_now_item' in request.session:
                    del request.session['buy_now_item']
                return redirect(failure_redirect_url)
            except ProductVariant.DoesNotExist:
                sweetify.error(request, 'Error', text='Product variant not found.', timer=3000)
                if 'buy_now_item' in request.session:
                    del request.session['buy_now_item']
                return redirect(failure_redirect_url)

        else:
            # --- REGULAR CART CHECKOUT PATH ---
            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related('product')
                
                if not cart_items.exists():
                    # THIS IS THE ERROR WE ARE TRYING TO BYPASS IF BUY NOW IS ACTIVE
                    sweetify.error(request, 'Error', text='Your cart is empty.', timer=3000)
                    return redirect("store:index")

                for item in cart_items:
                    # CartItem.product should link to the ProductVariant object
                    items_to_process.append({'variant': item.product, 'quantity': item.quantity,}) 
            except Cart.DoesNotExist:
                 sweetify.error(request, 'Error', text='Cart not found.', timer=3000)
                 return redirect("store:index")
        
        # FINAL CHECK: If no items, something went wrong.
        if not items_to_process:
            sweetify.error(request, 'Error', text='No items were found to create an order.', timer=3000)
            return redirect(failure_redirect_url)


        # --- 3. Stock Check and Total Price Calculation on VARIANT (retained logic) ---
        order_items_to_create = []
        total_price = Decimal('0.00')

        for item_data in items_to_process:
            variant = item_data['variant']  # This is the ProductVariant object
            quantity = item_data['quantity']

            # Check stock on the VARIANT 
            if quantity > variant.stock: 
                # Construct a descriptive error message
                variant_name = getattr(variant, 'name', f"{variant.product.name} ({variant.subcategory.name})")
                stock_error = f"Not enough stock for {variant_name}. Available: {variant.stock}"
                sweetify.error(request, 'Stock Error', text=stock_error, timer=5000)
                return redirect(failure_redirect_url) 
            
            item_price = variant.price * quantity
            total_price += item_price
            
            order_items_to_create.append({
                'variant': variant,
                'quantity': quantity,
                'price': variant.price,
            })

        # --- 4. Create Order Object and Save (retained logic) ---
        order = Order(user=request.user, total_price=total_price)
        order.save()
        
        # --- 5-7. Create Items, Reduce Stock, Clear Cart/Session, Create Address ---
        order_items = []
        for item_data in order_items_to_create:
            variant = item_data['variant']
            quantity = item_data['quantity']
            
            order_items.append(OrderItem(
                order=order, 
                product=variant, # OrderItem.product links to the ProductVariant
                quantity=quantity, 
                price=item_data['price']
            ))
            
            # Reduce stock on the VARIANT
            variant.stock -= quantity
            variant.save(update_fields=["stock"])

        OrderItem.objects.bulk_create(order_items)

        # Clear the cart/session only if items were successfully processed
        if is_buy_now:
            # FIX: Clear the Buy Now session data now that the order is placed
            if 'buy_now_item' in request.session:
                del request.session['buy_now_item']
        elif 'cart' in locals():
            # Clear the cart only if it was a standard cart purchase
            cart.items.all().delete()

        # Create or update the Address linked to the new Order (retained logic)
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