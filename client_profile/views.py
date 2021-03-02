from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.db.models import Q
from django.db.models.functions import Lower

from .models import Deal, Category
from .forms import DealForm

# Create your views here.


def client_deals(request):
    """ A veiw to show the specific clients delas in thier profile"""

    deals = Deal.objects.all()
    query = None
    categories = None
    sort = None

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
        sort = sortkey
        if sortkey == 'name':
            sortkey = 'lower_name'
            deals == deals.annotate(lower_name=Lower('name'))
        if sortkey == 'category':
            sortkey = 'category_name'
        deals = deals.order_by(sortkey)

        if 'category' in request.GET:
            categories = request.GET['category'].split(',')
            deals = deals.filter(category__name__in=categories)
            categories = Category.objects.filter(name__in=categories)

        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(request, "You didn't enter any search criteria!")
                return redirect(reverse('index.html'))

            queries = Q(name__icontains=query) | Q(description__icontains=query)
            deals = deals.filter(queries)

    current_sorting = f'{sort}_{deals}'

    context = {
        'deals': deals,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
    }

    return render(request, 'client_profile/client_profile.html', context)


def deal_detail(request, deal_id):
    """ A view to show individual deal details """

    deals = get_object_or_404(Deal, pk=deal_id)

    context = {
        'deals': deals,
    }

    return render(request, 'client_profile/deal_detail.html', context)


def add_deal(request):
    """ Add a deal """
    form = DealForm()
    template = 'client_profile/add_deal.html'
    context = {
        'form': form,
    }

    return render(request, template, context)
