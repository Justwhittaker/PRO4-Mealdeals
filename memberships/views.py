from django.shortcuts import render, redirect
from .models import MembershipTier, Customer
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import authenticate, login
from django.conf import settings

import stripe
import os

# stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_key = 'pk_test_51I9BnOIFzPFZzgCPco3JakcxMvcGpwP5AYfRK1zdVJajM6LOuA57tqI4h2wd6Bxg8NC3egFwWndvYPAlJsAdJbax00mvKkqXib'

# Create your views here.


def all_products(request):
    products = MembershipTier.objects.all().order_by('price')
    owned_product = False
    if hasattr(request.user, 'profile') and request.user.profile.product_level:
        owned_product = request.user.profile.product_level
    return render(request, "products.html", {"products": products,
                                             'owned_product': owned_product})


@login_required
def join(request):
    return render(request, 'membership/join.html')


def success(request):
    if request.method == 'GET' and 'session_id' in request.GET:
        session = stripe.checkout.Session.retrieve(request.GET['session_id'],)
        customer = Customer()
        customer.user = request.user
        customer.stripeid = session.customer
        customer.membership = True
        customer.cancel_at_period_end = False
        customer.stripe_subscription_id = session.subscription
        customer.save()
    return render(request, 'membership/success.html')


def cancel(request):
    return render(request, 'membership/cancel.html')


@login_required
def checkout(request):

    try:
        if request.user.customer.membership:
            return redirect('settings')
    except Customer.DoesNotExist:
        pass

    if request.method == 'POST':
        pass
    else:
        membership = 'registration'
        final_dollar = 10
        membership_id = 'price_1IYh7eIFzPFZzgCPKsuPzfdG'
        if request.method == 'GET' and 'membership' in request.GET:
            if request.GET['membership'] == 'monthly':
                membership = 'monthly'
                membership_id = 'price_1IYh7eIFzPFZzgCP0jB4Ldjx'
                final_dollar = 20

        # Create Strip Checkout
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=request.user.email,
            line_items=[{
                'price': membership_id,
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True,
            success_url='http://127.0.0.1:8000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/cancel',
        )

        return render(request, 'membership/checkout.html', {
            'final_dollar': final_dollar, 'session_id': session.id})


class SignUp(generic.CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')

    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get(
            'username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        # restaurant_name, street_address1, town_or_city = form.cleaned_data.get(
        #     'restaurant_name'), form.cleaned_data.get(
        #     'street_address1'), form.cleaned_data.get(
        #     'town_or_city'),
        # county, street_address2, postcode = form.cleaned_data.get(
        #     'county'), form.cleaned_data.get(
        #     'street_address2'), form.cleaned_data.get(
        #     'postcode'),
        login(self.request, new_user)
        return valid
