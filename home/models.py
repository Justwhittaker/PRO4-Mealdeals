from django.db import models

# Create your models here.


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
    paginate_by = 2
    category = models.ForeignKey('Category',
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL)
    restaurant_name = models.CharField(max_length=254)
    name = models.CharField(max_length=254)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(blank=True)

    def __str__(self):
        return self.name
