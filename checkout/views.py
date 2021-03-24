from django.shortcuts import render, redirect, reverse


from .forms import OrderForm

import stripe
import json

# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/account/apikeys
stripe.api_key = "sk_test_51I9BnOIFzPFZzgCPlXnvCkzhPtXAjqnidnmc0VzkIEE1ZMpDmmLdXpBcLByLZ9syPvWFsG7oWq4I2s6OU4Vqbkdx00RIMhQFV1"


# @app.route('/create-subscription', methods=['POST'])
# def createSubscription():
#     data = json.loads(request.data)
#     try:
#         # Attach the payment method to the customer
#         stripe.PaymentMethod.attach(
#             data['paymentMethodId'],
#             customer=data['customerId'],
#         )
#         # Set the default payment method on the customer
#         stripe.Customer.modify(
#             data['customerId'],
#             invoice_settings={
#                 'default_payment_method': data['paymentMethodId'],
#             },
#         )

#         # Create the subscription
#         subscription = stripe.Subscription.create(
#             customer=data['customerId'],
#             items=[
#                 {
#                     'price': 'price_HGd7M3DV3IMXkC'
#                 }
#             ],
#             expand=['latest_invoice.payment_intent'],
#         )
#         return jsonify(subscription)
#     except Exception as e:
#         return jsonify(error={'message': str(e)}), 200


# @app.route('/retry-invoice', methods=['POST'])
# def retrySubscription():
#     data = json.loads(request.data)
#     try:

#         stripe.PaymentMethod.attach(
#             data['paymentMethodId'],
#             customer=data['customerId'],
#         )
#         # Set the default payment method on the customer
#         stripe.Customer.modify(
#             data['customerId'],
#             invoice_settings={
#                 'default_payment_method': data['paymentMethodId'],
#             },
#         )

#         invoice = stripe.Invoice.retrieve(
#             data['invoiceId'],
#             expand=['payment_intent'],
#         )
#         return jsonify(invoice)
#     except Exception as e:
#         return jsonify(error={'message': str(e)}), 200

# @app.route('/checkout-session', methods=['GET'])
# def get_checkout_session():
#     id = request.args.get('sessionId')
#     checkout_session = stripe.checkout.Session.retrieve(id)
#     return jsonify(checkout_session)


# @app.route('/customer-portal', methods=['POST'])
# def customer_portal():
#     data = json.loads(request.data)
#     # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
#     # Typically this is stored alongside the authenticated user in your database.
#     checkout_session_id = data['sessionId']
#     checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)

#     # This is the URL to which the customer will be redirected after they are
#     # done managing their billing with the portal.
#     return_url = os.getenv("DOMAIN")

#     session = stripe.billing_portal.Session.create(
#         customer=checkout_session.customer,
#         return_url=return_url)
#     return jsonify({'url': session.url})


# @app.route('/stripe-webhook', methods=['POST'])
# def webhook_received():
#     # You can use webhooks to receive information about asynchronous payment events.
#     # For more about our webhook events check out https://stripe.com/docs/webhooks.
#     webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
#     request_data = json.loads(request.data)

#     if webhook_secret:
#         # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
#         signature = request.headers.get('stripe-signature')
#         try:
#             event = stripe.Webhook.construct_event(
#                 payload=request.data, sig_header=signature, secret=webhook_secret)
#             data = event['data']
#         except Exception as e:
#             return e
#         # Get the type of webhook event sent - used to check the status of PaymentIntents.
#         event_type = event['type']
#     else:
#         data = request_data['data']
#         event_type = request_data['type']

#     data_object = data['object']

#     if event_type == 'invoice.paid':
#         # Used to provision services after the trial has ended.
#         # The status of the invoice will show up as paid. Store the status in your
#         # database to reference when a user accesses your service to avoid hitting rate
#         # limits.
#         print(data)

#     if event_type == 'invoice.payment_failed':
#         # If the payment fails or the customer does not have a valid payment method,
#         # an invoice.payment_failed event is sent, the subscription becomes past_due.
#         # Use this webhook to notify your user that their payment has
#         # failed and to retrieve new card details.
#         print(data)

#     if event_type == 'customer.subscription.deleted':
#         # handle subscription cancelled automatically based
#         # upon your subscription settings. Or if the user cancels it.
#         print(data)

#     return jsonify({'status': 'success'})


# @app.route('/cancel-subscription', methods=['POST'])
# def cancelSubscription():
#     data = json.loads(request.data)
#     try:
#          # Cancel the subscription by deleting it
#         deletedSubscription = stripe.Subscription.delete(data['subscriptionId'])
#         return jsonify(deletedSubscription)
#     except Exception as e:
#         return jsonify(error=str(e)), 403


def checkout(request):

    order_form = OrderForm()
    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
    }

    return render(request, template, context)
