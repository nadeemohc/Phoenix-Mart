from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('auth/', views.handle_auth_modal, name='handle_auth_modal'),
]