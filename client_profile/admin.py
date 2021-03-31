from django.contrib import admin
from .models import UserProfile

"""Ensure that the User Profile is saved to the DB"""
admin.site.register(UserProfile)
