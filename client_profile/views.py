from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import UserProfile
from .forms import DealForm, UserProfileForm
from home.models import Deal
from memberships.models import Customer


@login_required
def profile(request):
    """ Display the user's profile if signed up else user must subscribe. """
    try:
        if request.user.customer.membership:
            pass
    except Customer.DoesNotExist:
        return redirect('join')
    """ Display the user's profile. """
    profile = get_object_or_404(UserProfile, user=request.user)
    deals = Deal.objects.all()
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
        if not request.user.is_superuser:
            author = UserProfile.objects.get(user=request.user)
            deals = Deal.objects.filter(author=author)

    template = 'profile.html'
    context = {
        'form': form,
        'deals': deals,
        'on_profile_page': True
    }

    return render(request, template, context)


def add_deal(request):
    """ Add a deal """
    if request.method == 'POST': 
        form = DealForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.author = UserProfile.objects.get(user=request.user)
            product.save()
            messages.success(request,
                             'Congratulations'
                             'you have Successfully added a Deal!')
            return redirect('profile')
        else:
            messages.error(request,
                           'Failed to add product'
                           'Please ensure the form is valid.')
    else:
        form = DealForm()

    template = 'add_deal.html'
    context = {
        'form': form, }

    return render(request, template, context)


@login_required
def edit_deal(request, deal_id):
    """ Edit a deals in the profile """
    deal = get_object_or_404(Deal, pk=deal_id)

    if request.method == 'POST':
        form = DealForm(request.POST, request.FILES, instance=deal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect('profile')
        else:
            messages.error(request, 'Failed to update product.'
                           ' Please ensure the form is valid.')
    else:
        form = DealForm(instance=deal)
        messages.info(request, f'You are editing {deal}')

    template = 'edit_deal.html'
    context = {
        'form': form,
    }

    return render(request, template, context)


@login_required
def delete_deal(request, deal_id):
    """ Delete a deal from the store """

    product = get_object_or_404(Deal, pk=deal_id)
    product.delete()
    messages.success(request, 'Deal deleted!')
    return redirect('profile')
