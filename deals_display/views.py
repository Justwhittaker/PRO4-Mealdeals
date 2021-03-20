from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower

from .models import deal, category
from .forms import DealForm


def all_deals(request):
    """ A view to show all deals, including sorting and search queries """

    deals = deal.objects.all()
    query = None
    categories = None
    sort = None
    direction = None

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
            sort = sortkey
            if sortkey == 'name':
                sortkey = 'lower_name'
                deals = deals.annotate(lower_name=Lower('name'))
            if sortkey == 'category':
                sortkey = 'category__name'
            if 'direction' in request.GET:
                direction = request.GET['direction']
                if direction == 'desc':
                    sortkey = f'-{sortkey}'
            deals = deals.order_by(sortkey)

        if 'category' in request.GET:
            categories = request.GET['category'].split(',')
            deals = deals.filter(category__name__in=categories)
            categories = category.objects.filter(name__in=categories)

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

    current_sorting = f'{sort}_{direction}'

    context = {
        'deals': deals,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
    }

    return render(request, 'deals_display/deal_detail.html', context)


def deal_detail(request, product_id):
    """ A view to show individual deal details """

    deals = get_object_or_404(deal, pk=deal_id)

    context = {
        'deals': deals,
    }

    return render(request, 'deals_display/deal_detail.html', context)


def add_deal(request):
    """ Add a deal to the landing page """
    form = DealForm()
    template = 'deals_display/add_deal.html'
    context = {
        'form': form,
    }

    return render(request, template, context)
