# in store/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.http import JsonResponse
from .models import Product, CustomUser
from .forms import CustomAuthenticationForm, CustomUserCreationForm
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

# in store/views.py
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'store/register.html'
    success_url = reverse_lazy('store:index')
    
    def form_valid(self, form):
        # Add debugging
        print("Form is valid")
        print("Form data:", form.cleaned_data)
        
        response = super().form_valid(form)
        
        # Check if user was created
        email = form.cleaned_data.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            print("User created successfully:", user)
        except CustomUser.DoesNotExist:
            print("User was not created")
        
        # Authenticate and login
        raw_password = form.cleaned_data.get('password1')
        user = authenticate(username=email, password=raw_password)
        if user:
            print("Authentication successful")
            login(self.request, user)
        else:
            print("Authentication failed")
        
        return response
    
    def form_invalid(self, form):
        # Add debugging for invalid forms
        print("Form is invalid")
        print("Form errors:", form.errors)
        return super().form_invalid(form)


def index(request):
    products = Product.objects.all()
    return render(request, 'store/index.html', {'products': products})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid email or password.'})
    return render(request, 'store/login.html', {'form': CustomAuthenticationForm()})

# def register_view(request):
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             email = form.cleaned_data.get('email')
#             raw_password = form.cleaned_data.get('password1')
#             # Authenticate using the email as username
#             from django.contrib.auth import authenticate
#             user = authenticate(username=email, password=raw_password)
#             login(request, user)
#             return redirect('store:index')
#     else:
#         form = CustomUserCreationForm()
#     return render(request, 'store/register.html', {'form': form})

def add_to_cart(request, product_id):
    # This is a placeholder for your add to cart functionality
    # You'll implement this later
    if not request.user.is_authenticated:
        return redirect('store:login')
    
    # Add product to cart logic here
    return redirect('store:index')