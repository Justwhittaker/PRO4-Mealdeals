from django.shortcuts import render, redirect
from .forms import ContactForm
from django.http import HttpResponse
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError


def contact(request):
    """ Display the contact us form. """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = "Marketing Enquiry"
            body = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'restaurant_name': form.cleaned_data['restaurant_name'],
                'email_address': form.cleaned_data['email_address'],
                'deal_description': form.cleaned_data['deal_description'],
            }
            message = "\n".join(body.values())
            messages.success(request, 'Your Email was sent successfully')
        else:
            messages.error(request,
                           'Email failed. Please ensure the form is valid.')
            try:
                send_mail(subject, message,
                          'just.whittaker@gmail.com',
                          ['mealdealsireland@gmail.com'])
            except BadHeaderError:
                return HttpResponse('Invalid header found')
            return redirect("home")

    form = ContactForm()
    return render(request, "contact.html", {'form': form})
