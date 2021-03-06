from django.shortcuts import render, redirect
from .models import Customer
from django.contrib.auth.decorators import login_required
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import authenticate, login
from mealdeals.settings import STRIPE_SECRET_KEY

import stripe

stripe.api_key = STRIPE_SECRET_KEY


@login_required
def join(request):
    """view to return Join page"""
    return render(request, 'membership/join.html')


# def settings(request):
#     return render(request, 'registration/settings.html')


def success(request):
    """view to Success index page"""
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
    """view to return Cancel page"""
    return render(request, 'membership/cancel.html')


@login_required
def checkout(request):
    """ Display the checkout if not signed up for the user to subscribe. """
    try:
        if request.user.customer.membership:
            return redirect('profile')
    except Customer.DoesNotExist:
        pass

    if request.method == 'POST':
        pass
    else:
        """
        Create Stripe payment amount from
        the product ids stored in stripe
        """
        membership = 'registration'
        final_dollar = 2
        membership_id = 'price_1Iae8BIFzPFZzgCPlrmTpzZ2'
        if request.method == 'GET' and 'membership' in request.GET:
            if request.GET['membership'] == 'monthly':
                membership = 'monthly'
                membership_id = 'price_1IYfthIFzPFZzgCPFbLoedwj'
                final_dollar = 20

        """Create Strip Checkout"""
        """
        So note this success_url and cancel_url will
        only work on the deployed app https://mealdeals-pro.herokuapp.com/
        """
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=request.user.email,
            line_items=[{
                'price': membership_id,
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True,
            success_url=(
                'https://mealdeals-pro.herokuapp.com/'\
                f"{'success?session_id={CHECKOUT_SESSION_ID}'}"
            ),
            cancel_url="https://mealdeals-pro.herokuapp.com/cancel",
        )

        return render(request, 'membership/checkout.html', {
            'final_dollar': final_dollar, 'session_id': session.id})


class SignUp(generic.CreateView):
    """ Display the Sign Up form for the user to subscribe. """
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')

    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get(
            'username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid


def cache_checkout_data(request):
    return render(request,)
