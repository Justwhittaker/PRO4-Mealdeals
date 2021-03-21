from django.db import models


class category(models.Model):

    class Meta:
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=254)
    friendly_name = models.CharField(max_length=254, blank=True)

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class deal(models.Model):
    category = models.ForeignKey('Category',
                                 null=True,
                                 blank=True, on_delete=models.SET_NULL)
    deal_name = models.CharField(max_length=254)
    description = models.TextField()
    Serves = models.DecimalField(
                                 max_digits=6,
                                 decimal_places=2,
                                 null=True, blank=True)
    contact = models.TextField()
    valid = models.BooleanField(default=False, null=True, blank=True)
    image_url = models.URLField(
                                max_length=1024, blank=True)
    image = models.ImageField(blank=True)

    def __str__(self):
        return self.name
