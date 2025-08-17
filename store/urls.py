from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    # path('register/', views.register_view, name='register'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('register/', views.RegisterView.as_view(), name='register'),
]