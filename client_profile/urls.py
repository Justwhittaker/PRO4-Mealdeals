from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('add/', views.add_deal, name='add_deal'),
]
