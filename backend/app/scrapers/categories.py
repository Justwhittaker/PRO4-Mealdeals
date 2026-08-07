"""Hospitality venue category tagging for scrape reports + feed filters.

Parent buckets match the MealDeals UI category filter. Keep in sync with
frontend/lib/categories.ts and .cursor/skills/scrape/SKILL.md.
"""

from __future__ import annotations

import re

# Parent filter labels (UI + scrape tally order).
CATEGORY_ORDER: list[str] = [
    "Restaurants, Cafe's & Bistro's",
    "Food Trucks & Takeaway's",
    "Wine Farms & Entertainment Venues",
    "Deli's and Grocers",
    "Clubs, Bars & Pubs",
    "Hotels, Resorts & B&B's",
]

# Subcategories grouped under each parent (scrape / marketing taxonomy).
CATEGORY_GROUPS: dict[str, list[str]] = {
    "Restaurants, Cafe's & Bistro's": [
        "Restaurants",
        "Casual dining restaurants",
        "Fine-dining restaurants",
        "Family restaurants",
        "Independent restaurants",
        "Chain restaurants",
        "Hotel restaurants",
        "Bistro restaurants",
        "Brasseries",
        "Gastropubs",
        "Cafés",
        "Coffee shops",
        "Tea rooms",
        "Bakeries with café seating",
        "Patisseries with café seating",
        "Sandwich shops",
        "Salad bars",
        "Soup cafés",
        "Breakfast cafés",
        "Brunch restaurants",
        "Diners",
        "Roadside diners",
        "Pizzerias",
        "Burger restaurants",
        "Steak houses",
        "Seafood restaurants",
        "Fish-and-chip shops",
        "Barbecue restaurants",
        "Carveries",
        "Buffet restaurants",
        "All-you-can-eat restaurants",
        "Grill restaurants",
        "Rotisserie restaurants",
        "Noodle bars",
        "Sushi restaurants",
        "Tapas bars",
        "Mezze restaurants",
        "Dessert cafés",
        "Ice-cream parlours with drinks",
        "Creperies",
        "Pancake houses",
        "Waffle cafés",
        "Juice bars serving food",
        "Smoothie bars serving food",
        "Health-food cafés",
        "Vegetarian restaurants",
        "Vegan restaurants",
        "Farm-to-table restaurants",
        "Farm cafés",
        "Workplace canteens",
        "University canteens",
        "College cafés",
        "Hospital cafés",
        "Airport restaurants",
        "Railway-station cafés",
        "Ferry restaurants",
        "Cruise-ship restaurants",
        "Service-station restaurants",
        "Motorway-service cafés",
        "Department-store cafés",
        "Shopping-centre restaurants",
        "Supermarket cafés",
        "Pop-up restaurants",
        "Supper clubs",
        "Private dining venues",
        "Meal-preparation kitchens with collection service",
    ],
    "Food Trucks & Takeaway's": [
        "Takeaway restaurants",
        "Fast-food restaurants",
        "Quick-service restaurants",
        "Drive-through restaurants",
        "Food trucks",
        "Mobile food vans",
        "Street-food stalls",
        "Food-market vendors",
        "Food halls",
        "Market cafés",
    ],
    "Wine Farms & Entertainment Venues": [
        "Wine farms",
        "Vineyards",
        "Wineries",
        "Garden-centre cafés",
        "Museum cafés",
        "Gallery cafés",
        "Theatre restaurants or bars",
        "Cinema cafés or bars",
        "Bowling-alley restaurants",
        "Casino restaurants",
        "Golf-club restaurants",
        "Country-club restaurants",
        "Sports-club restaurants",
        "Theme-park restaurants",
        "Visitor-attraction cafés",
        "Zoo cafés",
        "Aquarium cafés",
        "Holiday-park restaurants",
        "Campsite cafés",
        "Banqueting venues",
        "Wedding venues",
        "Conference centres",
        "Event venues",
        "Function rooms",
        "Catering companies",
        "Entertainment venues serving food",
    ],
    "Deli's and Grocers": [
        "Delicatessens",
        "Convenience stores with hot-food counters",
        "Petrol stations with food service",
    ],
    "Clubs, Bars & Pubs": [
        "Pubs",
        "Bars serving food",
        "Sports bars",
        "Cocktail bars serving food",
        "Wine bars serving food",
        "Taprooms serving food",
        "Breweries with kitchens",
        "Microbreweries with food service",
        "Beer gardens",
        "Social clubs",
        "Members’ clubs",
        "Nightclubs serving food",
        "Music venues serving food",
        "Comedy clubs serving food",
        "Hostel cafés or bars",
    ],
    "Hotels, Resorts & B&B's": [
        "Hotels",
        "Resorts",
        "Inns",
        "Lodges",
        "Guesthouse restaurants",
        "Bed-and-breakfast dining rooms",
    ],
}

# First match wins — more specific buckets before generic restaurants.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "Deli's and Grocers",
        re.compile(
            r"deli|delicatessen|grocery|grocer|convenience|petrol|"
            r"gas station|supermarket(?!\s*café)|hypermarket|"
            r"tesco|sainsbury|woolworth|coles|walmart|lidl|aldi|"
            r"carrefour|loblaw|fairprice|whole\s*foods|trader\s*joe|"
            r"dunnes|centra|supervalu|countdown|new\s*world|checkers|"
            r"shoprite|albert\s*heijn|\bjumbo\b|\bhema\b|big\s*c|"
            r"foodland|lulu\s*hyper|migros|\bcoop\b|mercadona|"
            r"rewe|\bnetto\b|rema\s*1000|spar\b|billa|delhaize|"
            r"colruyt|pao\s*de\s*acucar|spinneys|prisma|k-market|"
            # Grocery chains that must not match entertainment "casino"
            r"casino\s*cameroon|groupe\s*casino|casino\s*supermarket|"
            r"casino\s*hyper|géant\s*casino|geant\s*casino",
            re.I,
        ),
    ),
    (
        "Food Trucks & Takeaway's",
        re.compile(
            r"food\s*truck|takeaway|take-away|fast\s*food|quick.?service|"
            r"drive.?through|street.?food|food\s*hall|food.?market|"
            r"mobile\s*food|chipotle|kfc|subway|greggs|mcdonald|"
            r"burger\s*king|dominos|\bqsr\b|jollibee|mang\s*inasal|"
            r"juici\s*patties|hungry\s*jack|guzman|debonairs|"
            r"hell\s*pizza|mostaza|presto|habib",
            re.I,
        ),
    ),
    (
        "Wine Farms & Entertainment Venues",
        re.compile(
            # Wine farms / cellar doors first (name tokens used in WINE_FARM_PACK)
            r"wine\s*farm|wine\s*estate|vineyard|winery|cellar\s*door|"
            r"domaine\b|ch[aâ]teau\b|bodega\b|weingut\b|cantina\b|"
            r"quinta\b|estate\s*wine|wine\s*tasting|"
            # Entertainment venues with F&B (avoid bare "casino" = grocery FP)
            r"museum|gallery|theatre|theater|cinema|bowling|"
            r"casino\s*(restaurant|resort|hotel|bar|dining|cafe|café)|"
            r"golf.?club|country.?club|sports.?club|theme.?park|zoo|"
            r"aquarium|holiday.?park|campsite|banquet|wedding\s*venue|"
            r"conference|event\s*venue|function\s*room|catering|"
            r"garden.?centre|visitor.?attraction",
            re.I,
        ),
    ),
    (
        "Hotels, Resorts & B&B's",
        re.compile(
            r"\bhotel\b|\bresort\b|\binn\b|\blodge\b|guesthouse|"
            r"guest\s*house|b&b|bed.?and.?breakfast|hostel|"
            r"hilton|marriott|hyatt|radisson|sheraton|westin|novotel|"
            r"ibis|premier\s*inn|travelodge|holiday\s*inn|best\s*western|"
            r"four\s*seasons|intercontinental|crowne\s*plaza|accor|"
            r"citizenm|motel\s*one|melia|tsogo|city\s*lodge|sandals|"
            r"atlantis|taj\s*hotels|apa\s*hotel|marina\s*bay\s*sands",
            re.I,
        ),
    ),
    (
        "Clubs, Bars & Pubs",
        re.compile(
            r"\bpub\b|gastropub|sports\s*bar|cocktail|wine\s*bar|taproom|"
            r"taphouse|brewery|beer\s*garden|\bbar\b|nightclub|"
            r"members.?\s*club|social\s*club|comedy\s*club|music\s*venue|"
            r"wetherspoon|greene\s*king|all\s*bar\s*one|yard\s*house|"
            r"buffalo\s*wild\s*wings|brewerkz|rum\s*bar|singha\s*bar|"
            r"augustiner|100\s*montaditos|earls\s*kitchen",
            re.I,
        ),
    ),
    (
        "Restaurants, Cafe's & Bistro's",
        re.compile(
            r"restaurant|bistro|brasserie|café|cafe|coffee|tea\s*leaf|"
            r"tea\s*room|diner|pizzeria|steak|seafood|sushi|tapas|mezze|"
            r"grill|buffet|vegan|vegetarian|brunch|breakfast|noodle|"
            r"creperie|pancake|waffle|juice\s*bar|smoothie|"
            r"farm.?to.?table|canteen|airport|railway|ferry|cruise|"
            r"shopping.?centre|department.?store|pop.?up|supper\s*club|"
            r"private\s*dining|bakery|patisserie|sandwich|salad\s*bar|"
            r"starbucks|costa|nandos|nando.?s|pizzaexpress|olive\s*garden|"
            r"applebee|ihop|tim\s*horton|pret|second\s*cup|insomnia|"
            r"gloria\s*jean|ya\s*kun|toast\s*box|luckin|vapiano|"
            r"hard\s*rock|spur|ocean\s*basket|barbeque\s*nation|"
            r"ichiran|yakiniku|outback|boston\s*pizza|the\s*keg|"
            r"grill.?d|eddie\s*rocket|burgerfuel|max.?s\s*restaurant|"
            r"mk\s*restaurant|loetje|hippopotamus|vips|old\s*wild\s*west|"
            r"scotchies|after\s*you|jones\s*the\s*grocer|bootleggers|"
            r"cafe\s*coffee\s*day|coffee\s*club",
            re.I,
        ),
    ),
]


def categorize_venue(merchant_name: str) -> str:
    """Map a merchant / venue name to a parent hospitality category."""
    name = (merchant_name or "").strip()
    if not name:
        return "Restaurants, Cafe's & Bistro's"
    for category, pattern in _RULES:
        if pattern.search(name):
            return category
    return "Restaurants, Cafe's & Bistro's"
