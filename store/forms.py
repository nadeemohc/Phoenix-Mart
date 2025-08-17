# in store/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model, authenticate  # Add authenticate to the import
from django.core.exceptions import ValidationError

# Get the custom user model
User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = User  # Now this references your CustomUser model
        fields = ("email", "password1", "password2", "phone_number")
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if a user with this email already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.is_active = True  # Ensure the user is active
        
        if commit:
            user.save()
        
        return user

class CustomAuthenticationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct email and password.",
        'inactive': "This account is inactive.",
    }
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            # Use the authenticate function directly
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                # Add debugging
                try:
                    user = User.objects.get(email=email)
                    if not user.check_password(password):
                        print("Password check failed")
                    if not user.is_active:
                        print("User is not active")
                except User.DoesNotExist:
                    print("User does not exist")
                
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data
    
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )
    
    def get_user(self):
        return self.user_cache