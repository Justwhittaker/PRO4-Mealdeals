from django.test import TestCase
from memberships.models import Customer


class TestCustomer(TestCase):
    """
    Test Order Model
    """

    @classmethod
    def CustomerTestData(self):
  
        # expect failure if trying to create an order without an owner
        product = ServiceLevel.objects.get(pk=1)
        user = User.objects.get(pk=1)
        num_orders = Order.objects.filter(user=user).count()
        Order.objects.create(
            payment_status="payment_collected",
            total=product.price,
            product=product,
            user=user,
        )
        user = User.objects.get(pk=1)
        self.assertEqual(num_orders + 1, Order.objects.filter(user=user).count())