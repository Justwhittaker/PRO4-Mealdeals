from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_deals, name="deals_display"),
    path('<int:deal_id>/', views.deal_detail, name='deal_detail'),
    path('add/', views.add_deal, name='add_deal'),
]
