from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from .forms import UserProfileForm

from .models import deal, category
from .forms import DealForm

# Create your views here.


def client_deals(request):
    """ A veiw to show the specific clients delas in thier profile"""

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

    return render(request, 'profile.html', context)


@login_required
def profile(request):
    """ Display the user's profile. """
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Update failed. Please ensure the form is valid.')
    else:
        form = UserProfileForm(instance=profile)
    orders = profile.orders.all()

    template = 'signup_profile.html'
    context = {
        'form': form,
        'orders': orders,
        'on_profile_page': True
    }

    return render(request, template, context)


# def order_history(request, order_number):
#     order = get_object_or_404(Order, order_number=order_number)

#     messages.info(request, (
#         f'This is a past confirmation for order number {order_number}. '
#         'A confirmation email was sent on the order date.'
#     ))

#     template = '#'
#     context = {
#         'order': order,
#         'from_profile': True,
#     }

#     return render(request, template, context)


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
    template = 'add_deal.html'
    context = {
        'form': form,
    }

    return render(request, template, context)


