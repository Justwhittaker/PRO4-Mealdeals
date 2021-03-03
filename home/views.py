from django.shortcuts import render
from .models import deal
# Create your views here.


def all_deals(request):
    """ A view to show all products, including sorting and search queries """

    deals = deal.objects.all()

    context = {
        'deals': deals,
    }

    return render(request, 'home/index.html', context)


def index(request):
    """view to return index page"""
    return render(request, 'home/index.html')


def privacy(request):
    return render(request, 'home/privacy_policy.html')


def about(request):
    return render(request, 'home/about.html')
