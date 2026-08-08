/**
 * MealDeals venue category taxonomy (parent filters + subcategory grouping).
 * Keep in sync with backend/app/scrapers/categories.py and .cursor/skills/scrape.
 */

export const PARENT_CATEGORIES = [
  {
    id: "restaurants-cafes-bistros",
    label: "Restaurants, Cafe's & Bistro's",
  },
  {
    id: "food-trucks-takeaways",
    label: "Food Trucks & Takeaway's",
  },
  {
    id: "wine-farms-entertainment",
    label: "Wine Farms & Entertainment Venues",
  },
  {
    id: "delis-grocers",
    label: "Deli's and Grocers",
  },
  {
    id: "clubs-bars-pubs",
    label: "Clubs, Bars & Pubs",
  },
  {
    id: "hotels-resorts-bbs",
    label: "Hotels, Resorts & B&B's",
  },
] as const;

export type ParentCategoryId = (typeof PARENT_CATEGORIES)[number]["id"];

/** Subcategories grouped under each parent filter. */
export const CATEGORY_GROUPS: Record<ParentCategoryId, readonly string[]> = {
  "restaurants-cafes-bistros": [
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
  "food-trucks-takeaways": [
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
  "wine-farms-entertainment": [
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
  "delis-grocers": [
    "Delicatessens",
    "Convenience stores with hot-food counters",
    "Petrol stations with food service",
  ],
  "clubs-bars-pubs": [
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
  "hotels-resorts-bbs": [
    "Hotels",
    "Resorts",
    "Inns",
    "Lodges",
    "Guesthouse restaurants",
    "Bed-and-breakfast dining rooms",
  ],
};

const PARENT_IDS = new Set<string>(PARENT_CATEGORIES.map((c) => c.id));

/** Keyword rules → parent id (order matters; first match wins). Keep in sync with backend categories.py. */
const CATEGORY_RULES: { id: ParentCategoryId; pattern: RegExp }[] = [
  {
    id: "delis-grocers",
    pattern:
      /deli|delicatessen|grocery|grocer|convenience|petrol|gas station|supermarket(?!\s*café)|hypermarket|tesco|sainsbury|woolworth|coles|walmart|lidl|aldi|carrefour|loblaw|fairprice|whole\s*foods|trader\s*joe|dunnes|centra|supervalu|countdown|new\s*world|checkers|shoprite|albert\s*heijn|\bjumbo\b|\bhema\b|big\s*c|foodland|lulu\s*hyper|migros|\bcoop\b|mercadona|rewe|\bnetto\b|rema\s*1000|spar\b|billa|delhaize|colruyt|pao\s*de\s*acucar|spinneys|prisma|k-market|casino\s*cameroon|groupe\s*casino|casino\s*supermarket|casino\s*hyper|géant\s*casino|geant\s*casino/i,
  },
  {
    id: "food-trucks-takeaways",
    pattern:
      /food\s*truck|takeaway|take-away|fast\s*food|quick.?service|drive.?through|street.?food|food\s*hall|food.?market|mobile\s*food|chipotle|kfc|subway|greggs|mcdonald|burger\s*king|dominos|\bqsr\b|jollibee|mang\s*inasal|juici\s*patties|hungry\s*jack|guzman|debonairs|hell\s*pizza|mostaza|presto|habib/i,
  },
  {
    id: "wine-farms-entertainment",
    pattern:
      /wine\s*farm|wine\s*estate|vineyard|winery|cellar\s*door|domaine\b|ch[aâ]teau\b|bodega\b|weingut\b|cantina\b|quinta\b|estate\s*wine|wine\s*tasting|museum|gallery|theatre|theater|cinema|bowling|casino\s*(restaurant|resort|hotel|bar|dining|cafe|café)|golf.?club|country.?club|sports.?club|theme.?park|zoo|aquarium|holiday.?park|campsite|banquet|wedding\s*venue|conference|event\s*venue|function\s*room|catering|garden.?centre|visitor.?attraction/i,
  },
  {
    id: "hotels-resorts-bbs",
    pattern:
      /\bhotel\b|\bresort\b|\binn\b|\blodge\b|guesthouse|guest\s*house|b&b|bed.?and.?breakfast|hostel|hilton|marriott|hyatt|radisson|sheraton|westin|novotel|ibis|premier\s*inn|travelodge|holiday\s*inn|best\s*western|four\s*seasons|intercontinental|crowne\s*plaza|accor|citizenm|motel\s*one|melia|tsogo|city\s*lodge|sandals|atlantis|taj\s*hotels|apa\s*hotel|marina\s*bay\s*sands/i,
  },
  {
    id: "clubs-bars-pubs",
    pattern:
      /\bpub\b|gastropub|sports\s*bar|cocktail|wine\s*bar|taproom|taphouse|brewery|beer\s*garden|\bbar\b|nightclub|members.?\s*club|social\s*club|comedy\s*club|music\s*venue|wetherspoon|greene\s*king|all\s*bar\s*one|yard\s*house|buffalo\s*wild\s*wings|brewerkz|rum\s*bar|singha\s*bar|augustiner|100\s*montaditos|earls\s*kitchen/i,
  },
  {
    id: "restaurants-cafes-bistros",
    pattern:
      /restaurant|bistro|brasserie|café|cafe|coffee|tea\s*leaf|tea\s*room|diner|pizzeria|steak|seafood|sushi|tapas|mezze|grill|buffet|vegan|vegetarian|brunch|breakfast|noodle|creperie|pancake|waffle|juice\s*bar|smoothie|farm.?to.?table|canteen|airport|railway|ferry|cruise|shopping.?centre|department.?store|pop.?up|supper\s*club|private\s*dining|bakery|patisserie|sandwich|salad\s*bar|starbucks|costa|nandos|nando.?s|pizzaexpress|olive\s*garden|applebee|ihop|tim\s*horton|pret|second\s*cup|insomnia|gloria\s*jean|ya\s*kun|toast\s*box|luckin|vapiano|hard\s*rock|spur|ocean\s*basket|barbeque\s*nation|ichiran|yakiniku|outback|boston\s*pizza|the\s*keg|grill.?d|eddie\s*rocket|burgerfuel|max.?s\s*restaurant|mk\s*restaurant|loetje|hippopotamus|vips|old\s*wild\s*west|scotchies|after\s*you|jones\s*the\s*grocer|bootleggers|cafe\s*coffee\s*day|coffee\s*club/i,
  },
];

export function parseCategoryParam(
  value: string | undefined | null,
): ParentCategoryId | "all" {
  if (!value || value === "all") return "all";
  return PARENT_IDS.has(value) ? (value as ParentCategoryId) : "all";
}

export function parentCategoryLabel(id: ParentCategoryId | "all"): string {
  if (id === "all") return "All categories";
  return PARENT_CATEGORIES.find((c) => c.id === id)?.label ?? id;
}

/** Infer parent category from merchant / venue name (client-side filter). */
export function categorizeVenue(merchantName: string): ParentCategoryId {
  const name = (merchantName || "").trim();
  if (!name) return "restaurants-cafes-bistros";
  for (const rule of CATEGORY_RULES) {
    if (rule.pattern.test(name)) return rule.id;
  }
  return "restaurants-cafes-bistros";
}

/** Resolve stored venue_category (id or legacy label) or fall back to name inference. */
export function resolveVenueCategory(
  category: string | null | undefined,
  restaurantName = "",
): ParentCategoryId {
  const raw = (category || "").trim();
  if (raw && PARENT_IDS.has(raw)) return raw as ParentCategoryId;
  const byLabel = PARENT_CATEGORIES.find((c) => c.label === raw);
  if (byLabel) return byLabel.id;
  return categorizeVenue(restaurantName);
}

/** Filter (optional) then always order by parent category list order. */
export function filterDealsByCategory<
  T extends { restaurantName: string; category?: string | null },
>(deals: T[], category: ParentCategoryId | "all"): T[] {
  // Keep caller order (featured-first + shuffled rest). Category sections are
  // handled by groupDealsByCategory in the grid.
  if (category === "all") return deals;
  return deals.filter(
    (d) => resolveVenueCategory(d.category, d.restaurantName) === category,
  );
}

/** Group deals into parent sections (same order as the category filter). */
export function groupDealsByCategory<
  T extends { restaurantName: string; category?: string | null },
>(deals: T[]): { id: ParentCategoryId; label: string; deals: T[] }[] {
  const buckets = new Map<ParentCategoryId, T[]>();
  for (const parent of PARENT_CATEGORIES) {
    buckets.set(parent.id, []);
  }
  for (const deal of deals) {
    const id = resolveVenueCategory(deal.category, deal.restaurantName);
    buckets.get(id)?.push(deal);
  }
  return PARENT_CATEGORIES.map((parent) => ({
    id: parent.id,
    label: parent.label,
    deals: buckets.get(parent.id) ?? [],
  })).filter((section) => section.deals.length > 0);
}
