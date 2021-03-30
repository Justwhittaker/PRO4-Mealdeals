from django.contrib import admin
from .models import UserProfile
# Register your models here.
"""Ensure that the User Profile is saved to the DB"""
admin.site.register(UserProfile)
