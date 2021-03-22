from django.shortcuts import render, redirect, reverse


from .forms import OrderForm


def checkout(request):

    order_form = OrderForm()
    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
    }

    return render(request, template, context)
