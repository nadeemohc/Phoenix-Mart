from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
import uuid
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def validate_user_email(email):
    try:
        validate_email(email)
        if email.split('@')[1] in ['example.com', 'test.com', 'mailinator.com']:
            return False
        return True
    except ValidationError:
        return False


def handle_auth_modal(request):
    print(f"Auth request method: {request.method}")
    print(f"Is AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
    
    if request.method == 'POST':
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Get action from POST data
        action = request.POST.get('action')
        print(f"Auth action: {action}")
        
        if not action:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': ['Missing action parameter']}
                }, status=400)
            return redirect('store:index')
            
        if action == 'login':
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                if is_ajax:
                    return JsonResponse({'success': True})
                return redirect('store:index')
                
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.get_json_data()
                }, status=400)
            return redirect('store:index')
        
        elif action == 'register':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user)
                if is_ajax:
                    return JsonResponse({'success': True})
                return redirect('store:index')
                
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.get_json_data()
                }, status=400)
            return redirect('store:index')
        
        elif action == 'guest':
            email = request.POST.get('email', '').strip()
            if not email:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': {'email': ['Email is required']}
                    }, status=400)
                return redirect('store:index')
                
            if not validate_user_email(email):
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': {'email': ['Please enter a valid email']}
                    }, status=400)
                return redirect('store:index')
            
            try:
                username = f"guest_{uuid.uuid4().hex[:10]}"
                password = User.objects.make_random_password()
                user = User.objects.create_user(username, email, password)
                
                send_mail(
                    'Complete your registration',
                    f'Set your password here: {settings.SITE_URL}/accounts/password_reset/',
                    settings.DEFAULT_FROM_EMAIL,
                    [email]
                )
                
                login(request, user)
                if is_ajax:
                    return JsonResponse({'success': True})
                return redirect('store:index')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': {'__all__': [str(e)]}
                    }, status=400)
                return redirect('store:index')
    
    # If not a POST request or something went wrong
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'errors': {'__all__': ['Invalid request method']}
        }, status=400)
    return redirect('store:index')