from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


class category(models.Model):

    class Meta:
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=300)
    friendly_name = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class deal(models.Model):
    category = models.ForeignKey('Category',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)
    restaurant_name = models.CharField(max_length=254)
    number_phone = models.CharField(max_length=48)
    address = models.CharField(max_length=254)
    website_address = models.CharField(max_length=254)
    name = models.CharField(max_length=254)
    description = models.TextField(max_length=2054)
    image = models.ImageField(blank=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    A user profile model for maintaining default
    delivery information and order history
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    default_phone_number = models.CharField(max_length=20, blank=True)
    default_street_address1 = models.CharField(max_length=80, blank=True)
    default_street_address2 = models.CharField(max_length=80, blank=True)
    default_town_or_city = models.CharField(max_length=40, blank=True)
    default_county = models.CharField(max_length=80, blank=True)
    default_postcode = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile
    """
    if created:
        UserProfile.objects.create(user=instance)
    # Existing users: just save the profile
    instance.userprofile.save()
