from django.contrib import admin

# Register your models here.
from .models import deal, category

# Register your models here.


class deal_admin(admin.ModelAdmin):
    list_display = (
        'restaurant_name',
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
