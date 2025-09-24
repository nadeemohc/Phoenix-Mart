# in store/urls.py
from django.urls import path
from order import views

app_name = 'order'

urlpatterns = [
    path("confirm-order/", views.confirm_order, name="confirm_order"),
]