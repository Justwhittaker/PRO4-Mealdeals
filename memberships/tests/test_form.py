from django.test import TestCase
from memberships.forms import CustomSignupForm


class TestCustomSignupForm(TestCase):

    def test_item_name_is_required(self):
        form = CustomSignupForm({'restaurant_name': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('restaurant_name', form.errors.keys())
        self.assertEqual(form.errors[
            'restaurant_name'][0], 'this field is required.')

    def test_done_field_is_not_required(self):
        form = CustomSignupForm({'restaurant_name':''})
        self.assertTrue(form.is_valid)
