from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import transaction

# Create your views here.


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