from django.test import TestCase
from memberships.views import success


class Testsuccess(TestCase):

    def test_item_name_is_required(self):
        view = success({'Customer': ''})
        self.assertFalse(view.is_valid())
        self.assertEqual(view.errors[
            'Customer'][0], 'this field is required.')
