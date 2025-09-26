# in store/urls.py
from django.urls import path
from store import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path("logout/", views.logout_view, name="logout"),
    path('profile/update/', views.update_profile, name='update_profile'),
    path("buy-now/<int:product_id>/", views.buy_now, name="buy_now"),
]