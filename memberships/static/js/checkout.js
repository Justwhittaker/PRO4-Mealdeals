var stripe = Stripe(window.STRIPE_PUBLIC_KEY);

var checkoutButton = document.getElementById('checkout-button');

checkoutButton.addEventListener('click', function () {
    stripe.redirectToCheckout({
        sessionId: sessionid
    }).then(function (result) {
        if (result.error) {
            console.error(result.error.message);
        }
    });
});
