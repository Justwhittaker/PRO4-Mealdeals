"""
/products URL Configuration
"""
from django.urls import path
from . import views
from .webhooks import webhook


urlpatterns = [
    path('join/', views.join, name='join'),
    path('checkout/', views.checkout, name='checkout'),
    # path('auth/settings', views.settings, name='settings'),
    path('auth/signup', views.SignUp.as_view(), name='signup'),
    path('cache_checkout_data/',
         views.cache_checkout_data, name='cache_checkout_data'),
    path('wh/', webhook, name='webhook'),
]
