from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from .models import deal
from django.db.models import Q
# Create your views here.


def all_deals(request):
    """ A view to show all deals, including sorting and search queries """

    deals = deal.objects.all()
    query = None

    if request.GET:
        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(request,
                               "You did not enter any search critria!")
                return redirect(reverse('home'))

            queries = Q(category__name__icontains=query) | Q(
                restaurant_name__icontains=query) | Q(name__icontains=query)
            deals = deals.filter(queries)

    context = {
        'deals': deals,
        'search_term': query,
    }

    return render(request, 'home/index.html', context)


def index(request):
    """view to return index page"""
    return render(request, 'home/index.html')


def privacy(request):
    return render(request, 'home/privacy_policy.html')


def about(request):
    return render(request, 'home/about.html')
