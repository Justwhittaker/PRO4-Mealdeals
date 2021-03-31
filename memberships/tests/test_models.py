from django.test import TestCase
from memberships.models import Customer
from django.contrib.auth.models import User


class TestCustomer(TestCase):
    """
    Test Order Model
    """

    @classmethod
    def CustomerTestData(self):

        # expect failure if trying to create an order without an owner
        product = Customer.get(pk=1)
        user = User.objects.get(pk=1)
        num_orders = Customer.objects.filter(user=user).count()
        Customer.objects.create(
            payment_status="payment_collected",
            total=product.price,
            product=product,
            user=user,
        )
        user = User.objects.get(pk=1)
        self.assertEqual(
            num_orders + 1, Customer.objects.filter(user=user).count())
