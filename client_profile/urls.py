from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_deals, name='deals'),
    path('add/', views.add_deal, name='add_deal'),
]
