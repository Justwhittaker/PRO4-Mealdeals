from django.urls import path
from . import views
"""URL links for the home to ensure that they dont break and deployment"""
urlpatterns = [
    path('', views.all_deals, name="home"),
    path('privacy/', views.privacy, name="privacy"),
    path('about/', views.about, name="about"),
    path('faq/', views.faq, name="faq"),
    path('deal/<deal_id>/', views.deals_display, name="deals_display"),
]
