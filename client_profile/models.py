from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    A user profile model for maintaining default
    information and deals history
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # is_subscribed = models.BooleanField(default=False)
    default_restaurant_name = models.CharField(max_length=120, blank=True)
    default_phone_number = models.CharField(max_length=20, blank=True)
    default_street_address1 = models.CharField(max_length=80, blank=True)
    default_street_address2 = models.CharField(max_length=80, blank=True)
    default_town_or_city = models.CharField(max_length=40, blank=True)
    default_county = models.CharField(max_length=80, blank=True)
    default_postcode = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username


# @cached_property
# def has_active_subscription(self):
#  """Checks if a user has an active subscription."""
# return subscriber_has_active_subscription(self)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile
    """
    if created:
        UserProfile.objects.create(user=instance)
    # Existing users: just save the profile
    instance.userprofile.save()
