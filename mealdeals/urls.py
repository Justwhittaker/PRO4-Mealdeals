"""mealdeals URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

from memberships import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('memberships/', include('memberships.urls')),
    path('', include('home.urls')),
    path("contact_us/", include('contact_us.urls')),
    path('client_profile/', include('client_profile.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
    path('favicon.ico', RedirectView.as_view(
        url=staticfiles_storage.url
        ('media/img/favicon.png'))),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
