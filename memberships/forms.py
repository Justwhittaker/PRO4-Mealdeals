from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(max_length=255, required=True)
    # restaurant_name = forms.CharField(max_length=100)
    # phone_number = forms.CharField(max_length=20)
    # postcode = forms.CharField(max_length=20)
    # town_or_city = forms.CharField(max_length=40)
    # street_address1 = forms.CharField(max_length=80)
    # street_address2 = forms.CharField(max_length=80)
    # county = forms.CharField(max_length=80)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',)
    #               'restaurant_name', 'phone_number',
    #               'street_address1', 'street_address2',
    #               'town_or_city', 'postcode',
    #               'county',)

    # def __init__(self, *args, **kwargs):
    #     """
    #     Add placeholders and classes, remove auto-generated
    #     labels and set autofocus on first field
    #     """
    #     super().__init__(*args, **kwargs)
    #     placeholders = {
    #         'username': 'Username',
    #         'email': 'Email Address',
    #         'password1': 'Password',
    #         'password2': 'Resubmit Password',
    #         'restaurant_name': 'Restaurant Name',
    #         'phone_number': 'Phone Number',
    #         'town_or_city': 'Town or City',
    #         'street_address1': 'Street Address 1',
    #         'street_address2': 'Street Address 2',
    #         'county': 'County',
    #         'postcode': 'Postal Code',
    #     }

    #     self.fields['full_name'].widget.attrs['autofocus'] = True
    #     for field in self.fields:
    #         if self.fields[field].required:
    #             placeholder = f'{placeholders[field]} *'
    #         else:
    #             placeholder = placeholders[field]
    #         self.fields[field].widget.attrs['placeholder'] = placeholder
    #         self.fields[field].widget.attrs['class'] = 'stripe-style-input'
    #         self.fields[field].label = False

