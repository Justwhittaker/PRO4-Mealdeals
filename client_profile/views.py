from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import UserProfile
from .forms import DealForm, UserProfileForm
from home.models import Deal


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
   
        if not request.user.is_superuser:
            author = UserProfile.objects.get(user=request.user)
            deals = Deal.objects.filter(author=author)
        else:
            deals = Deal.objects.all()

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

        # if request.user.is_authenticated:
        #     profile = UserProfile.objects.get(user=request.user)
        #     form = DealForm(initial={
        #             'email': profile.user.email,
        #             'phone_number': profile.default_phone_number,
        #         })

    template = 'add_deal.html'
    context = {
        'form': form, }

    return render(request, template, context)


@login_required
def edit_deal(request, deal_id):
    """ Edit a deals in the profile """
    product = get_object_or_404(Deal, pk=deal_id)
    
    if request.method == 'POST':
        form = DealForm(request.POST, request.FILES, instance=Deal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect('profile')
        else:
            messages.error(request, 'Failed to update product.'
                           ' Please ensure the form is valid.')
    else:
        form = DealForm(instance=Deal)
        messages.info(request, f'You are editing {Deal.name}')

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
