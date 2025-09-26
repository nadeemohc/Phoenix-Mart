# in store/urls.py
from django.urls import path
from order import views

app_name = 'order'

urlpatterns = [
    path("confirm-order/", views.confirm_order, name="confirm_order"),
    path('success/<int:order_id>/', views.order_success_page, name='order_success'), # New URL name
]