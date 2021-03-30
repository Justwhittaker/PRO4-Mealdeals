from django.contrib import admin
from .models import Deal, Category
"""Ensure that deals and categories are saved to the DB"""


class deal_admin(admin.ModelAdmin):
    list_display = (
        'restaurant_name',
        'address',
        'website_address',
        'number_phone',
        'name',
        'category',
        'price',
        'image',
        'author',
    )

    ordering = ('name',)


class category_admin(admin.ModelAdmin):
    list_display = (
        'friendly_name',
        'name',
    )


admin.site.register(Deal, deal_admin)
admin.site.register(Category, category_admin)
