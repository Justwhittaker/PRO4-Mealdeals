from django import forms

# Create your models here.


class ContactForm(forms.Form):
    first_name = forms.CharField(max_length=45)
    last_name = forms.CharField(max_length=45)
    restaurant_name = forms.CharField(max_length=200)
    email_address = forms.EmailField(max_length=200)
    deal_description = forms.CharField(widget=forms.Textarea, max_length=2000)
