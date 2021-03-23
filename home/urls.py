from django.urls import path
from . import views

urlpatterns = [
    path('', views.all_deals, name="home"),
    path('privacy/', views.privacy, name="privacy"),
    path('about/', views.about, name="about"),
    path('deal/<deal_id>/', views.deals_display, name="deals_display"),
]
