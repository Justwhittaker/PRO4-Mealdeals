from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import UserProfile
from .forms import DealForm, UserProfileForm

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
            messages.error(request,
                           'Update failed. Please ensure the form is valid.')
    else:
        form = UserProfileForm(instance=profile)
        # deals = profile.deal.all()

    template = 'profile.html'
    context = {
        'form': form,
        'on_profile_page': True
    }

    return render(request, template, context)


def add_deal(request):
    """ Add a deal """
    if request.method == 'POST':
        form = DealForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.author = request.UserProfile
            product.save()
            messages.success(request,
                             'Congratulations'
                             'you have Successfully added a Deal!')
            return redirect(reverse('profile', args=[product.id]))
        else:
            messages.error(request,
                           'Failed to add product'
                           'Please ensure the form is valid.')
    else:
        form = DealForm()
    # if DealForm.is_valid():
    #     deal = DealForm.save(commit=False)
    #     deal.save()
    #     if request.user.is_authenticated:
    #         try:
    #             profile = UserProfile.objects.get(user=request.user)
    #             order_form = UserProfileForm(initial={
    #                 'email': profile.user.email,
    #                 'phone_number': profile.default_phone_number,
    #             })
    # else:
    #     messages.error(request, 'Deal failed. Please ensure the form is valid.')
    
    template = 'add_deal.html'
    context = {
        'form': form, }

    return render(request, template, context)
