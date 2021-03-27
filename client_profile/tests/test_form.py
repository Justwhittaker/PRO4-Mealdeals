from django.test import TestCase
from .forms import DealForm, UserProfileForm


class TestDealForm(TestCase):

    def test_item_name_is_required(self):
        form = DealForm({'restaurant_name': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('restaurant_name', form.errors.keys())
        self.assertEqual(form.errors[
            'restaurant_name'][0], 'this field is required.')


class TestUserProfileForm(TestCase):

    def test_item_name_is_required(self):
        form = UserProfileForm({'restaurant_name': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('restaurant_name', form.errors.keys())
        self.assertEqual(form.errors[
            'restaurant_name'][0], 'this field is required.')
