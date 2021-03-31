from django.db import models
from client_profile.models import UserProfile

"""
Created my models by using the logic from 
the Boutique ado project on CI tutorial
"""


class Category(models.Model):
    """
    A Category model for maintaining default
    information and deals info history
    """
    class Meta:
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=300)
    friendly_name = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class Deal(models.Model):
    """
    A deal model for maintaining default
    information and deals info history
    """
    category = models.ForeignKey('Category',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)
    restaurant_name = models.CharField(max_length=254)
    number_phone = models.CharField(max_length=48)
    address = models.CharField(max_length=254)
    website_address = models.CharField(max_length=254)
    name = models.CharField(max_length=80)
    description = models.TextField(max_length=2054)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(blank=True)
    author = models.ForeignKey(UserProfile,
                               on_delete=models.CASCADE,
                               null=True, blank=True)

    def __str__(self):
        return self.name
