from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.

class MembershipTier(models.Model):
    """
    Products for Mealdeals App are subscription based
    """
    name = models.CharField(max_length=254, default='')
    price = models.DecimalField(max_digits=6, decimal_places=2,
                                validators=[
                                    MinValueValidator(0.00),
                                    MaxValueValidator(1500.00)
                                ],
                                default=20.00)
    stripeid = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    cancel_at_period_end = models.BooleanField(default=False)
    membership = models.BooleanField(default=False)
    description = models.TextField(max_length=200)
    max_submission_size_in_MB = models.PositiveIntegerField(validators=[MaxValueValidator(10000)])
    image = models.ImageField(upload_to='images/products', null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name
