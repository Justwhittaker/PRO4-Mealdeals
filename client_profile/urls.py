from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_deals, name='deals'),
    path('<int:deal_id>/', views.deal_detail, name='deal_detail'),
    path('add/', views.add_deal, name='add_deal'),
]
