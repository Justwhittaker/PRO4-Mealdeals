from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from .models import Deal
from django.db.models import Q


def all_deals(request):
    """ A view to show all deals, including sorting and search queries """

    deals = Deal.objects.all()
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
    """view to return Privacy page"""
    return render(request, 'home/privacy_policy.html')


def about(request):
    """view to return About page"""
    return render(request, 'home/about.html')


def faq(request):
    """view to return FAQ page"""
    return render(request, 'home/faq.html')


def deals_display(request, deal_id):
    """ A view to show individual deal details """

    deals = get_object_or_404(Deal, pk=deal_id)

    context = {
        'deals': deals,
    }
    return render(request, 'home/deal_detail.html', context)
