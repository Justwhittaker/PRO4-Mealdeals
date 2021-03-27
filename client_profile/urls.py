from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('add/', views.add_deal, name='add_deal'),
    path('edit/<int:deal_id>/', views.edit_deal, name='edit_deal'),
    path('delete/<int:deal_id>/', views.delete_deal, name='delete_deal'),
]
