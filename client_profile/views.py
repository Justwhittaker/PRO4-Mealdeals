from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.db.models import Q
from django.db.models.functions import Lower

from .models import Deal, Category
from .forms import ProductForm

# Create your views here.


def add_deal(request):
    """ Add a deal """
    form = DealForm()
    template = 'client_profile/add_deal.html'
    context = {
        'form': form,
    }

return render(request, template, context)