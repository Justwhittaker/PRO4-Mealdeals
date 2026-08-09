"""First-wave hospitality merchant pack for MealDeals scrapers.

Adds hotels, pubs/bars (happy hours), takeaway/QSR (BOGO deals),
grocery spend/money-off vouchers, restaurants, cafés, and wine-farm /
cellar-door venues alongside existing retail sources so worldwide scrapes
cover lower-volume categories.
"""

from __future__ import annotations

# Clubs, Bars & Pubs — happy hour / drink specials pages.
# Merchant names should include pub/bar/brewery/cocktail tokens for tagging.
BARS_PUBS_PACK: dict[str, list[dict[str, str]]] = {
    "GB": [
        {"merchant": "BrewDog Bar", "url": "https://www.brewdog.com/uk/bars"},
        {"merchant": "O'Neill's Pub", "url": "https://www.oneills.co.uk/"},
        {"merchant": "Slug and Lettuce Bar", "url": "https://www.slugandlettuce.co.uk/offers"},
        {"merchant": "Revolution Bar", "url": "https://www.revolution-bars.co.uk/offers/"},
        {"merchant": "Be At One Cocktail Bar", "url": "https://www.beatone.co.uk/"},
        {"merchant": "Stonegate Pubs", "url": "https://www.stonegatepubs.com/offers"},
    ],
    "IE": [
        {"merchant": "O'Neill's Pub", "url": "https://www.oneills.ie/"},
        {"merchant": "The Quays Bar Galway", "url": "https://www.thequaysgalway.com/"},
        {"merchant": "The Bierhaus Pub Galway", "url": "https://www.bierhausgalway.com/"},
        {"merchant": "Against the Grain Bar", "url": "https://www.againstthegrain.ie/"},
        {"merchant": "The Church Cafe Bar", "url": "https://www.thechurch.ie/"},
        {"merchant": "Wetherspoons", "url": "https://www.jdwetherspoon.com/menu/"},
    ],
    "US": [
        {"merchant": "TGI Fridays Bar", "url": "https://www.tgifridays.com/menu/"},
        {"merchant": "Buffalo Wild Wings", "url": "https://www.buffalowildwings.com/menu/"},
        {"merchant": "Yard House Bar", "url": "https://www.yardhouse.com/menu"},
        {"merchant": "Hooters Bar", "url": "https://www.hooters.com/menu/"},
        {"merchant": "Dave and Busters Bar", "url": "https://www.daveandbusters.com/"},
    ],
    "CA": [
        {"merchant": "Earls Kitchen Bar", "url": "https://earls.ca/menu"},
        {"merchant": "The Keg Steakhouse Bar", "url": "https://thekeg.com/en/menu"},
        {"merchant": "Cactus Club Bar", "url": "https://www.cactusclubcafe.com/"},
        {"merchant": "Boston Pizza Bar", "url": "https://bostonpizza.com/en/menu.html"},
    ],
    "AU": [
        {"merchant": "The Local Taphouse Pub", "url": "https://thelocaltaphouse.com/"},
        {"merchant": "Young Henrys Brewery Bar", "url": "https://younghenrys.com/"},
        {"merchant": "Australian Hotel Pub", "url": "https://australianhotel.com.au/"},
    ],
    "NZ": [
        {"merchant": "Garage Project Taproom Bar", "url": "https://garageproject.co.nz/"},
        {"merchant": "Hashigo Zake Bar", "url": "https://hashigozake.co.nz/"},
    ],
    "DE": [
        {"merchant": "Augustiner Keller Pub", "url": "https://www.augustiner-keller.de/"},
        {"merchant": "Hofbraeuhaus Pub", "url": "https://www.hofbraeuhaus.de/en/"},
    ],
    "FR": [
        {"merchant": "Cafe Oz Bar", "url": "https://www.cafe-oz.com/"},
        {"merchant": "The Frog Pub", "url": "https://www.frogpubs.com/"},
    ],
    "ES": [
        {"merchant": "100 Montaditos Bar", "url": "https://spain.100montaditos.com/"},
        {"merchant": "Mahou Bar", "url": "https://www.mahou.es/"},
    ],
    "NL": [
        {"merchant": "Brown Cafe Bar", "url": "https://www.iamsterdam.com/en"},
        {"merchant": "Beer Temple Bar", "url": "https://www.beertemple.nl/"},
    ],
    "SG": [
        {"merchant": "Brewerkz Bar", "url": "https://www.brewerkz.com/"},
        {"merchant": "Level Up Bar", "url": "https://www.levelup.sg/"},
    ],
    "ZA": [
        {"merchant": "Truth Coffee Bar", "url": "https://www.truthcoffee.com/"},
        {"merchant": "Banana Bar Pub", "url": "https://www.facebook.com/bananabarct/"},
    ],
    "IN": [
        {"merchant": "Social Bar", "url": "https://socialoffline.in/"},
        {"merchant": "Toit Brewpub", "url": "https://www.toit.in/"},
    ],
}

# Food Trucks & Takeaway — pizza / QSR promo & deals pages (BOGO, meal deals).
# Prefer /deals /offers /coupons URLs; names should match takeaway tagging.
TAKEAWAY_PACK: dict[str, list[dict[str, str]]] = {
    "GB": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.co.uk/deals"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.co.uk/offers/"},
        {"merchant": "Papa John's Takeaway", "url": "https://www.papajohns.co.uk/offers"},
        {"merchant": "Subway Takeaway", "url": "https://www.subway.com/en-gb/deals"},
        {"merchant": "KFC Takeaway", "url": "https://www.kfc.co.uk/offers"},
        {"merchant": "McDonald's Takeaway", "url": "https://www.mcdonalds.com/gb/en-gb/offers.html"},
    ],
    "IE": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.ie/en/pages/deals/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.ie/offers"},
        {"merchant": "Papa John's Takeaway", "url": "https://www.papajohns.ie/"},
        {"merchant": "Supermac's Takeaway", "url": "https://www.supermacs.ie/"},
        {"merchant": "Apache Pizza Takeaway", "url": "https://www.apache.ie/"},
        {"merchant": "Subway Takeaway", "url": "https://www.subway.com/en-ie"},
    ],
    "US": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com/en/pages/order/#!/deals"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.com/deals"},
        {"merchant": "Papa John's Takeaway", "url": "https://www.papajohns.com/deals"},
        {"merchant": "Chipotle Takeaway", "url": "https://www.chipotle.com/"},
        {"merchant": "Wingstop Takeaway", "url": "https://www.wingstop.com/"},
        {"merchant": "Little Caesars Takeaway", "url": "https://littlecaesars.com/en-us/"},
    ],
    "CA": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.ca/en/pages/order/menu#!/menu/category/coupons/"},
        {"merchant": "Pizza Pizza Takeaway", "url": "https://www.pizzapizza.ca/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.ca/"},
        {"merchant": "Subway Takeaway", "url": "https://www.subway.com/en-ca"},
    ],
    "AU": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com.au/menu/deals"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.com.au/deals"},
        {"merchant": "Crust Pizza Takeaway", "url": "https://www.crust.com.au/"},
        {"merchant": "Hungry Jack's Takeaway", "url": "https://www.hungryjacks.com.au/menu"},
    ],
    "NZ": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.co.nz/"},
        {"merchant": "Hell Pizza Takeaway", "url": "https://www.hellpizza.com/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.co.nz/"},
    ],
    "DE": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.de/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.de/"},
    ],
    "FR": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.fr/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.fr/"},
    ],
    "ES": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.es/"},
        {"merchant": "Telepizza Takeaway", "url": "https://www.telepizza.es/"},
    ],
    "NL": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.nl/"},
        {"merchant": "New York Pizza Takeaway", "url": "https://www.newyorkpizza.nl/"},
    ],
    "ZA": [
        {"merchant": "Debonairs Pizza Takeaway", "url": "https://www.debonairspizza.co.za/"},
        {"merchant": "Roman's Pizza Takeaway", "url": "https://www.romanspizza.co.za/"},
        {"merchant": "Chicken Licken Takeaway", "url": "https://www.chickenlicken.co.za/"},
    ],
    "IN": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.co.in/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.co.in/"},
    ],
    "SG": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com.sg/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.com.sg/"},
    ],
    "PH": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com.ph/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.com.ph/"},
        {"merchant": "Jollibee Takeaway", "url": "https://www.jollibee.com.ph/"},
    ],
    "TH": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominospizza.co.th/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.co.th/"},
    ],
    "JP": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.jp/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.jp/"},
    ],
    "BR": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com.br/"},
        {"merchant": "Pizza Hut Takeaway", "url": "https://www.pizzahut.com.br/"},
    ],
    "MX": [
        {"merchant": "Domino's Pizza Takeaway", "url": "https://www.dominos.com.mx/"},
        {"merchant": "Little Caesars Takeaway", "url": "https://littlecaesars.com.mx/"},
    ],
}

# Deli's and Grocers — spend-threshold, % off, and money-off shop vouchers.
# Prefer /offers /promotions /vouchers pages; names should match grocery tagging.
GROCERS_PACK: dict[str, list[dict[str, str]]] = {
    "IE": [
        {"merchant": "Dunnes Stores", "url": "https://www.dunnesstores.com/offers"},
        {"merchant": "Supervalu", "url": "https://shop.supervalu.ie/shopping/offers"},
        {"merchant": "Centra", "url": "https://www.centra.ie/offers"},
        {"merchant": "Tesco Ireland", "url": "https://www.tesco.ie/groceries/en-IE/promotions"},
        {"merchant": "Lidl Ireland", "url": "https://www.lidl.ie/"},
        {"merchant": "Aldi Ireland", "url": "https://www.aldi.ie/offers"},
    ],
    "GB": [
        {"merchant": "Tesco", "url": "https://www.tesco.com/groceries/en-GB/promotions"},
        {"merchant": "Sainsbury's", "url": "https://www.sainsburys.co.uk/gol-ui/promotions"},
        {"merchant": "Asda", "url": "https://www.asda.com/groceries/offers"},
        {"merchant": "Morrisons", "url": "https://groceries.morrisons.com/products?tags=Offer"},
        {"merchant": "Aldi UK", "url": "https://www.aldi.co.uk/offers"},
        {"merchant": "Lidl UK", "url": "https://www.lidl.co.uk/c/specials/s10004745"},
        {"merchant": "Waitrose", "url": "https://www.waitrose.com/ecom/shop/offers"},
        {"merchant": "Co-op Grocery", "url": "https://www.coop.co.uk/products/deals"},
    ],
    "US": [
        {"merchant": "Walmart", "url": "https://www.walmart.com/shop/deals"},
        {"merchant": "Kroger", "url": "https://www.kroger.com/savings/weeklyad"},
        {"merchant": "Safeway", "url": "https://www.safeway.com/shop/deals.html"},
        {"merchant": "Target Grocery", "url": "https://www.target.com/c/grocery-deals/-/N-5q0f4"},
        {"merchant": "Trader Joe's", "url": "https://www.traderjoes.com/home/products"},
        {"merchant": "Whole Foods Market", "url": "https://www.wholefoodsmarket.com/sales-flyer"},
    ],
    "CA": [
        {"merchant": "Loblaws", "url": "https://www.loblaws.ca/en/offers"},
        {"merchant": "Sobeys", "url": "https://www.sobeys.com/en/flyer/"},
        {"merchant": "Metro Grocery", "url": "https://www.metro.ca/en/find-a-flyer"},
        {"merchant": "Walmart Canada", "url": "https://www.walmart.ca/en/savings"},
    ],
    "AU": [
        {"merchant": "Woolworths", "url": "https://www.woolworths.com.au/shop/browse/specials"},
        {"merchant": "Coles", "url": "https://www.coles.com.au/on-special"},
        {"merchant": "Aldi Australia", "url": "https://www.aldi.com.au/specials"},
        {"merchant": "IGA Australia", "url": "https://www.iga.com.au/specials/"},
    ],
    "NZ": [
        {"merchant": "Countdown", "url": "https://www.woolworths.co.nz/shop/specials"},
        {"merchant": "New World", "url": "https://www.newworld.co.nz/specials"},
        {"merchant": "Pak'nSave", "url": "https://www.paknsave.co.nz/shop/specials"},
    ],
    "DE": [
        {"merchant": "Lidl Germany", "url": "https://www.lidl.de/c/angebote/s10004745"},
        {"merchant": "Aldi Süd", "url": "https://www.aldi-sued.de/de/angebote.html"},
        {"merchant": "REWE", "url": "https://www.rewe.de/angebote/"},
    ],
    "FR": [
        {"merchant": "Carrefour France", "url": "https://www.carrefour.fr/promotions"},
        {"merchant": "Auchan", "url": "https://www.auchan.fr/catalogue"},
        {"merchant": "Intermarché", "url": "https://www.intermarche.com/promotions"},
    ],
    "ES": [
        {"merchant": "Mercadona", "url": "https://www.mercadona.es/"},
        {"merchant": "Carrefour Spain", "url": "https://www.carrefour.es/promociones"},
        {"merchant": "Lidl Spain", "url": "https://www.lidl.es/"},
    ],
    "NL": [
        {"merchant": "Albert Heijn", "url": "https://www.ah.nl/bonus"},
        {"merchant": "Jumbo", "url": "https://www.jumbo.com/aanbiedingen"},
        {"merchant": "Lidl Netherlands", "url": "https://www.lidl.nl/"},
    ],
    "ZA": [
        {"merchant": "Checkers", "url": "https://www.checkers.co.za/specials"},
        {"merchant": "Shoprite", "url": "https://www.shoprite.co.za/specials"},
        {"merchant": "Woolworths South Africa", "url": "https://www.woolworths.co.za/cat/Food/_/N-1z13sk5"},
    ],
    "SG": [
        {"merchant": "FairPrice", "url": "https://www.fairprice.com.sg/promotions"},
        {"merchant": "Cold Storage", "url": "https://coldstorage.com.sg/promotions"},
    ],
    "IN": [
        {"merchant": "Big Bazaar", "url": "https://www.bigbazaar.com/"},
        {"merchant": "Reliance Fresh", "url": "https://www.relianceretail.com/"},
    ],
    "PH": [
        {"merchant": "SM Supermarket", "url": "https://www.smsupermarket.com/"},
        {"merchant": "Puregold", "url": "https://puregold.com.ph/"},
    ],
    "TH": [
        {"merchant": "Big C", "url": "https://www.bigc.co.th/"},
        {"merchant": "Foodland", "url": "https://www.foodland.co.th/"},
    ],
    "JP": [
        {"merchant": "Aeon Grocery", "url": "https://www.aeon.info/"},
        {"merchant": "Seiyu", "url": "https://www.seiyu.co.jp/"},
    ],
    "BR": [
        {"merchant": "Pao de Acucar", "url": "https://www.paodeacucar.com/ofertas"},
        {"merchant": "Carrefour Brazil", "url": "https://www.carrefour.com.br/promocoes"},
    ],
    "MX": [
        {"merchant": "Walmart Mexico", "url": "https://www.walmart.com.mx/"},
        {"merchant": "Soriana", "url": "https://www.soriana.com/"},
    ],
}

# Wine regions: cellar-door / vineyard dining + tasting lunch offers.
# Merchant names MUST include vineyard/winery/wine farm/estate tokens so
# categorize_venue tags them as "Wine Farms & Entertainment Venues".
WINE_FARM_PACK: dict[str, list[dict[str, str]]] = {
    "ZA": [
        {
            "merchant": "Spier Wine Farm",
            "url": "https://www.spier.co.za/eat/",
        },
        {
            "merchant": "Boschendal Wine Estate",
            "url": "https://www.boschendal.com/eat-drink/",
        },
        {
            "merchant": "Warwick Wine Estate",
            "url": "https://www.warwickwine.com/",
        },
        {
            "merchant": "Vergelegen Wine Estate",
            "url": "https://www.vergelegen.co.za/",
        },
        {
            "merchant": "Tokara Wine Estate",
            "url": "https://www.tokarawinery.co.za/",
        },
    ],
    "US": [
        {
            "merchant": "Robert Mondavi Winery",
            "url": "https://www.robertmondaviwinery.com/",
        },
        {
            "merchant": "Domaine Chandon Winery",
            "url": "https://www.chandon.com/",
        },
        {
            "merchant": "Beringer Vineyard",
            "url": "https://www.beringer.com/",
        },
        {
            "merchant": "Castello di Amorosa Winery",
            "url": "https://castellodiamorosa.com/",
        },
    ],
    "AU": [
        {
            "merchant": "Jacob's Creek Cellar Door",
            "url": "https://www.jacobscreek.com/",
        },
        {
            "merchant": "Penfolds Magill Estate Winery",
            "url": "https://www.penfolds.com/",
        },
        {
            "merchant": "d'Arenberg Winery",
            "url": "https://www.darenberg.com.au/",
        },
        {
            "merchant": "Seppeltsfield Wine Estate",
            "url": "https://seppeltsfield.com.au/",
        },
    ],
    "NZ": [
        {
            "merchant": "Cloudy Bay Winery",
            "url": "https://www.cloudybay.com/",
        },
        {
            "merchant": "Mission Estate Winery",
            "url": "https://www.missionestate.co.nz/",
        },
        {
            "merchant": "Villa Maria Winery",
            "url": "https://www.villamaria.co.nz/",
        },
    ],
    "FR": [
        {
            "merchant": "Château Smith Haut Lafitte",
            "url": "https://www.smith-haut-lafitte.com/",
        },
        {
            "merchant": "Domaine Laroche Winery",
            "url": "https://www.larochewines.com/",
        },
        {
            "merchant": "Château de Pommard Wine Estate",
            "url": "https://www.chateaudepommard.com/",
        },
    ],
    "IT": [
        {
            "merchant": "Antinori Wine Estate",
            "url": "https://www.antinori.it/",
        },
        {
            "merchant": "Banfi Winery",
            "url": "https://www.banfiwines.com/",
        },
        {
            "merchant": "Ruffino Wine Estate",
            "url": "https://www.ruffino.com/",
        },
    ],
    "ES": [
        {
            "merchant": "Marqués de Riscal Wine Estate",
            "url": "https://www.marquesderiscal.com/",
        },
        {
            "merchant": "Torres Winery",
            "url": "https://www.torres.es/",
        },
        {
            "merchant": "Bodegas Muga Winery",
            "url": "https://www.bodegasmuga.com/",
        },
    ],
    "PT": [
        {
            "merchant": "Quinta do Crasto Wine Estate",
            "url": "https://www.quintadocrasto.pt/",
        },
        {
            "merchant": "Quinta da Pacheca Wine Estate",
            "url": "https://www.quintadapacheca.com/",
        },
        {
            "merchant": "Symington Port Wine Estate",
            "url": "https://www.symington.com/",
        },
    ],
    "CL": [
        {
            "merchant": "Concha y Toro Winery",
            "url": "https://www.conchaytoro.com/",
        },
        {
            "merchant": "Santa Rita Wine Estate",
            "url": "https://www.santarita.com/",
        },
        {
            "merchant": "Casas del Bosque Winery",
            "url": "https://www.casasdelbosque.cl/",
        },
    ],
    "AR": [
        {
            "merchant": "Catena Zapata Winery",
            "url": "https://www.catenazapata.com/",
        },
        {
            "merchant": "Luigi Bosca Wine Estate",
            "url": "https://www.luigibosca.com/",
        },
        {
            "merchant": "Norton Winery",
            "url": "https://www.norton.com.ar/",
        },
    ],
    "DE": [
        {
            "merchant": "Dr. Loosen Weingut",
            "url": "https://www.drloosen.com/",
        },
        {
            "merchant": "Schloss Johannisberg Wine Estate",
            "url": "https://www.schloss-johannisberg.de/",
        },
        {
            "merchant": "Reichsgraf von Kesselstatt Weingut",
            "url": "https://www.kesselstatt.com/",
        },
    ],
    "GB": [
        {
            "merchant": "Chapel Down Winery",
            "url": "https://www.chapeldown.com/",
        },
        {
            "merchant": "Nyetimber Winery",
            "url": "https://nyetimber.com/",
        },
        {
            "merchant": "Ridgeview Wine Estate",
            "url": "https://www.ridgeview.co.uk/",
        },
    ],
}

# Seed + major markets get a fuller hospitality mix.
HOSPITALITY_PACK: dict[str, list[dict[str, str]]] = {
    "GB": [
        {"merchant": "Premier Inn", "url": "https://www.premierinn.com/gb/en/deals.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Wetherspoons", "url": "https://www.jdwetherspoon.com/menu/"},
        {"merchant": "Greene King Pubs", "url": "https://www.greeneking.co.uk/offers"},
        {"merchant": "All Bar One", "url": "https://www.allbarone.co.uk/offers"},
        {"merchant": "Costa Coffee", "url": "https://www.costa.co.uk/"},
        {"merchant": "Nando's Restaurant", "url": "https://www.nandos.co.uk/food/menu"},
        {"merchant": "PizzaExpress", "url": "https://www.pizzaexpress.com/offers"},
    ],
    "US": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/offers.mi"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Buffalo Wild Wings", "url": "https://www.buffalowildwings.com/menu/"},
        {"merchant": "Yard House Bar", "url": "https://www.yardhouse.com/menu"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com/menu"},
        {"merchant": "Olive Garden Restaurant", "url": "https://www.olivegarden.com/specials"},
        {"merchant": "Applebee's Restaurant", "url": "https://www.applebees.com/en/specials"},
        {"merchant": "IHOP Restaurant", "url": "https://www.ihop.com/en/menu"},
    ],
    "CA": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-ca/offers.mi"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Boston Pizza Restaurant", "url": "https://bostonpizza.com/en/menu.html"},
        {"merchant": "Earls Kitchen Bar", "url": "https://earls.ca/menu"},
        {"merchant": "Second Cup Coffee", "url": "https://secondcup.com/"},
        {"merchant": "The Keg Steakhouse", "url": "https://thekeg.com/en/menu"},
    ],
    "AU": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "The Local Taphouse Pub", "url": "https://thelocaltaphouse.com/"},
        {"merchant": "Grill'd Restaurant", "url": "https://www.grilld.com.au/menu"},
        {"merchant": "Gloria Jean's Coffee", "url": "https://www.gloriajeans.com.au/"},
        {"merchant": "Hungry Jack's", "url": "https://www.hungryjacks.com.au/menu"},
    ],
    "IE": [
        {"merchant": "Premier Inn", "url": "https://www.premierinn.com/ie/en/deals.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Wetherspoons", "url": "https://www.jdwetherspoon.com/menu/"},
        {"merchant": "Insomnia Coffee", "url": "https://www.insomniacoffee.ie/"},
        {"merchant": "Nando's Restaurant", "url": "https://www.nandos.ie/food/menu"},
        {"merchant": "Eddie Rocket's Diner", "url": "https://www.eddierockets.ie/"},
    ],
    "NZ": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "BurgerFuel Restaurant", "url": "https://www.burgerfuel.com/nz/menu"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.co.nz/"},
        {"merchant": "Hell Pizza", "url": "https://www.hellpizza.com/"},
    ],
    "PH": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-us/hotels/mnlmc-manila-marriott-hotel/overview/"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Max's Restaurant", "url": "https://maxschicken.com/"},
        {"merchant": "Coffee Bean Tea Leaf", "url": "https://www.coffeebean.com.ph/"},
        {"merchant": "The Alley Bar", "url": "https://www.thealley.com.ph/"},
    ],
    "TH": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-us/offers.mi"},
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "After You Cafe", "url": "https://www.afteryoudessertcafe.com/"},
        {"merchant": "MK Restaurant", "url": "https://www.mkrestaurant.com/"},
        {"merchant": "Singha Bar", "url": "https://www.singha.com/"},
    ],
    "NL": [
        {"merchant": "CitizenM Hotel", "url": "https://www.citizenm.com/offers"},
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Brown Cafe Bar", "url": "https://www.iamsterdam.com/en"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.nl/"},
        {"merchant": "Loetje Restaurant", "url": "https://www.loetje.nl/"},
    ],
    "BS": [
        {"merchant": "Atlantis Resort", "url": "https://www.atlantisbahamas.com/offers"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Bahamian Club Restaurant", "url": "https://www.atlantisbahamas.com/dining"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com/"},
    ],
    "JM": [
        {"merchant": "Sandals Resort", "url": "https://www.sandals.com/specials/"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Scotchies Jerk Restaurant", "url": "https://www.scotchiesjerk.com/"},
        {"merchant": "Usain Bolt Tracks Bar", "url": "https://www.tracksbarandgrill.com/"},
    ],
    "AE": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-ae/offers.mi"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Riva Beach Bar", "url": "https://www.rivabeachbar.com/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.ae/"},
        {"merchant": "Jones the Grocer Cafe", "url": "https://jonesthegrocer.com/"},
    ],
    "DE": [
        {"merchant": "Motel One Hotel", "url": "https://www.motel-one.com/en/offers/"},
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Augustiner Keller Pub", "url": "https://www.augustiner-keller.de/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.de/"},
        {"merchant": "Vapiano Restaurant", "url": "https://vapiano.com/"},
    ],
    "FR": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Ibis Hotel", "url": "https://all.accor.com/hotel/ibis/index.en.shtml"},
        {"merchant": "Cafe de Flore", "url": "https://cafedeflore.fr/"},
        {"merchant": "Hippopotamus Restaurant", "url": "https://www.hippopotamus.fr/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.fr/"},
    ],
    "ES": [
        {"merchant": "Melia Hotels", "url": "https://www.melia.com/en/offers"},
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "100 Montaditos Bar", "url": "https://spain.100montaditos.com/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.es/"},
        {"merchant": "Vips Restaurant", "url": "https://www.vips.es/"},
    ],
    "IT": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Autogrill Cafe", "url": "https://www.autogrill.com/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.it/"},
        {"merchant": "Old Wild West Restaurant", "url": "https://www.oldwildwest.it/"},
    ],
    "ZA": [
        {"merchant": "Tsogo Sun Hotels", "url": "https://www.tsogosun.com/specials"},
        {"merchant": "City Lodge Hotel", "url": "https://www.clhg.com/"},
        {"merchant": "Spur Restaurant", "url": "https://www.spursteakranches.com/"},
        {"merchant": "Ocean Basket Restaurant", "url": "https://www.oceanbasket.com/"},
        {"merchant": "Bootleggers Coffee", "url": "https://www.bootleggers.co.za/"},
    ],
    "SG": [
        {"merchant": "Marina Bay Sands Hotel", "url": "https://www.marinabaysands.com/offers.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Ya Kun Cafe", "url": "https://yakun.com/"},
        {"merchant": "Brewerkz Bar", "url": "https://www.brewerkz.com/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com.sg/"},
    ],
    "IN": [
        {"merchant": "Taj Hotels", "url": "https://www.tajhotels.com/en-in/offers/"},
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-in/offers.mi"},
        {"merchant": "Cafe Coffee Day", "url": "https://www.cafecoffeeday.com/"},
        {"merchant": "Barbeque Nation Restaurant", "url": "https://www.barbequenation.com/"},
        {"merchant": "Social Bar", "url": "https://socialoffline.in/"},
    ],
    "JP": [
        {"merchant": "APA Hotel", "url": "https://www.apahotel.com/en/"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.co.jp/"},
        {"merchant": "Ichiran Ramen Restaurant", "url": "https://en.ichiran.com/"},
        {"merchant": "Yakiniku Like Restaurant", "url": "https://yakiniku-like.com/"},
    ],
    "BR": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Outback Restaurant", "url": "https://www.outback.com.br/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com.br/"},
        {"merchant": "Bar do Mineiro", "url": "https://www.bardomineiro.com.br/"},
    ],
    "MX": [
        {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/en-us/offers.mi"},
        {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
        {"merchant": "Vips Restaurant", "url": "https://www.vips.com.mx/"},
        {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com.mx/"},
        {"merchant": "La Casa de Toño Restaurant", "url": "https://www.lacasadetono.com.mx/"},
    ],
}

# Applied to every TARGET_MARKET that does not already define a local pack.
_DEFAULT_HOSPITALITY: list[dict[str, str]] = [
    {"merchant": "Marriott Hotels", "url": "https://www.marriott.com/offers.mi"},
    {"merchant": "Hilton Hotels", "url": "https://www.hilton.com/en/offers/"},
    {"merchant": "Ibis Hotel", "url": "https://all.accor.com/hotel/ibis/index.en.shtml"},
    {"merchant": "Starbucks Coffee", "url": "https://www.starbucks.com/menu"},
    {"merchant": "Local Pub & Grill", "url": "https://www.tripadvisor.com/Restaurants"},
]

# Region overlays for markets without a dedicated pack (merged on top of defaults).
_REGION_OVERLAYS: dict[str, list[dict[str, str]]] = {
    "EU": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Hard Rock Cafe", "url": "https://www.hardrockcafe.com/"},
    ],
    "AF": [
        {"merchant": "City Lodge Hotel", "url": "https://www.clhg.com/"},
        {"merchant": "Debonairs Pizza Restaurant", "url": "https://www.debonairspizza.co.za/"},
    ],
    "AS": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "Toast Box Cafe", "url": "https://www.toastbox.com.sg/"},
    ],
    "AM": [
        {"merchant": "Holiday Inn Hotel", "url": "https://www.ihg.com/holidayinn/hotels/us/en/reservation"},
        {"merchant": "Chili's Restaurant", "url": "https://www.chilis.com/menu"},
    ],
    "OC": [
        {"merchant": "Accor Hotels", "url": "https://all.accor.com/a/en/offers.html"},
        {"merchant": "The Coffee Club Cafe", "url": "https://www.coffeeclub.com.au/"},
    ],
    "CB": [
        {"merchant": "Sandals Resort", "url": "https://www.sandals.com/specials/"},
        {"merchant": "Rum Bar", "url": "https://www.tripadvisor.com/Restaurants"},
    ],
}

_MARKET_REGION: dict[str, str] = {
    "AG": "CB",
    "AR": "AM",
    "AT": "EU",
    "BB": "CB",
    "BE": "EU",
    "BW": "AF",
    "BZ": "AM",
    "CH": "EU",
    "CL": "AM",
    "CM": "AF",
    "CN": "AS",
    "CO": "AM",
    "CZ": "EU",
    "DK": "EU",
    "EG": "AF",
    "FI": "EU",
    "FJ": "OC",
    "FM": "OC",
    "GD": "CB",
    "GH": "AF",
    "GM": "AF",
    "GR": "EU",
    "GY": "AM",
    "HR": "EU",
    "ID": "AS",
    "IL": "AS",
    "IS": "EU",
    "JO": "AS",
    "KE": "AF",
    "KI": "OC",
    "KN": "CB",
    "KR": "AS",
    "LR": "AF",
    "LS": "AF",
    "MA": "AF",
    "MH": "OC",
    "MT": "EU",
    "MW": "AF",
    "MY": "AS",
    "NA": "AF",
    "NG": "AF",
    "NO": "EU",
    "NR": "OC",
    "PG": "OC",
    "PK": "AS",
    "PL": "EU",
    "PT": "EU",
    "PW": "OC",
    "QA": "AS",
    "RW": "AF",
    "SB": "OC",
    "SE": "EU",
    "SI": "EU",
    "SK": "EU",
    "SL": "AF",
    "SS": "AF",
    "SZ": "AF",
    "TN": "AF",
    "TO": "OC",
    "TR": "EU",
    "TT": "CB",
    "TV": "OC",
    "UG": "AF",
    "VC": "CB",
    "VN": "AS",
    "VU": "OC",
    "WS": "OC",
    "ZM": "AF",
    "ZW": "AF",
}


def _dedupe_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for source in sources:
        key = source["merchant"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(source))
    return out


def wine_farm_sources_for(country_code: str) -> list[dict[str, str]]:
    """Return real cellar-door / vineyard dining sources for a wine market."""
    code = country_code.strip().upper()
    return list(WINE_FARM_PACK.get(code, []))


def bars_pubs_sources_for(country_code: str) -> list[dict[str, str]]:
    """Return happy-hour / pub & bar promo sources for a market."""
    code = country_code.strip().upper()
    return list(BARS_PUBS_PACK.get(code, []))


def takeaway_sources_for(country_code: str) -> list[dict[str, str]]:
    """Return takeaway / QSR promo sources (BOGO, deals pages) for a market."""
    code = country_code.strip().upper()
    return list(TAKEAWAY_PACK.get(code, []))


def grocers_sources_for(country_code: str) -> list[dict[str, str]]:
    """Return grocery spend-threshold / % off / money-off promo sources."""
    code = country_code.strip().upper()
    return list(GROCERS_PACK.get(code, []))


def hospitality_sources_for(country_code: str) -> list[dict[str, str]]:
    """Return deduped hospitality + specialty pack sources for a market."""
    code = country_code.strip().upper()
    if code in HOSPITALITY_PACK:
        merged: list[dict[str, str]] = list(HOSPITALITY_PACK[code])
    else:
        merged = list(_DEFAULT_HOSPITALITY)
        region = _MARKET_REGION.get(code)
        if region:
            merged.extend(_REGION_OVERLAYS.get(region, []))

    merged.extend(bars_pubs_sources_for(code))
    merged.extend(takeaway_sources_for(code))
    merged.extend(grocers_sources_for(code))
    merged.extend(wine_farm_sources_for(code))
    return _dedupe_sources(merged)


def merge_hospitality_into_sources(
    market_sources: dict[str, list[dict[str, str]]],
    market_codes: list[str],
) -> dict[str, list[dict[str, str]]]:
    """Append hospitality + specialty pack merchants onto each market's sources."""
    for code in market_codes:
        upper = code.strip().upper()
        existing = market_sources.setdefault(upper, [])
        seen = {s["merchant"].strip().lower() for s in existing}
        for source in hospitality_sources_for(upper):
            key = source["merchant"].strip().lower()
            if key in seen:
                continue
            existing.append(dict(source))
            seen.add(key)
    return market_sources
