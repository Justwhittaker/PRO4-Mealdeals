from django.shortcuts import render, redirect
from .forms import ContactForm
from django.http import HttpResponse
from django.core.mail import send_mail, BadHeaderError


# Create your views here.


def contact(request):
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

            try:
                send_mail(subject, message,
                          'just.whittaker@gmail.com',
                          ['just.whittaker@gmail.com'])
            except BadHeaderError:
                return HttpResponse('Invalid header found')
            return redirect("contact.html")

    form = ContactForm()
    return render(request, "contact.html", {'form': form})
