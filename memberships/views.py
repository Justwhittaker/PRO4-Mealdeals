from django.shortcuts import render
from .models import MembershipTier
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import authenticate, login


# Create your views here.
def all_products(request):
    products = MembershipTier.objects.all().order_by('price')
    owned_product = False
    if hasattr(request.user, 'profile') and request.user.profile.product_level:
        owned_product = request.user.profile.product_level
    return render(request, "products.html", {"products": products,
                                             'owned_product': owned_product})


def home(request):
    return render(request, 'memberships/home.html')


@login_required
def settings(request):
    return render(request, 'registration/settings.html')


class SignUp(generic.CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get('username'),
        form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid
