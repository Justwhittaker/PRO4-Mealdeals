from django.contrib import admin
from .models import deal, category

# Register your models here.


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
    )

    ordering = ('name',)


class category_admin(admin.ModelAdmin):
    list_display = (
        'friendly_name',
        'name',
    )


admin.site.register(deal, deal_admin)
admin.site.register(category, category_admin)
