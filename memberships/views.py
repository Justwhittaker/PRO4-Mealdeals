from django.shortcuts import render
from .models import MembershipTier


# Create your views here.
def all_products(request):
    products = MembershipTier.objects.all().order_by('price')
    owned_product = False
    if hasattr(request.user, 'profile') and request.user.profile.product_level:
        owned_product = request.user.profile.product_level
    return render(request, "products.html", {"products": products, 'owned_product': owned_product})
