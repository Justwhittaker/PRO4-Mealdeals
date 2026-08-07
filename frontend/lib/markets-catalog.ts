/** Auto-generated from backend TARGET_MARKETS / MARKET_CITIES. Do not edit by hand. */
export interface MarketCityOption {
  country: string;
  city: string;
  label: string;
}

export interface MarketCountryOption {
  /** Frontend route slug (uk for GB). */
  code: string;
  /** ISO country code used by the API (GB, US, …). */
  iso: string;
  label: string;
  cities: MarketCityOption[];
}

export const MARKET_COUNTRIES: MarketCountryOption[] = [
  {
    code: "uk",
    iso: "GB",
    label: "United Kingdom",
    cities: [
      {
        country: "uk",
        city: "london",
        label: "London",
      },
      {
        country: "uk",
        city: "manchester",
        label: "Manchester",
      },
      {
        country: "uk",
        city: "birmingham",
        label: "Birmingham",
      },
      {
        country: "uk",
        city: "leeds",
        label: "Leeds",
      },
      {
        country: "uk",
        city: "glasgow",
        label: "Glasgow",
      },
      {
        country: "uk",
        city: "edinburgh",
        label: "Edinburgh",
      },
      {
        country: "uk",
        city: "liverpool",
        label: "Liverpool",
      },
      {
        country: "uk",
        city: "bristol",
        label: "Bristol",
      },
      {
        country: "uk",
        city: "sheffield",
        label: "Sheffield",
      },
      {
        country: "uk",
        city: "newcastle",
        label: "Newcastle",
      },
      {
        country: "uk",
        city: "cardiff",
        label: "Cardiff",
      },
      {
        country: "uk",
        city: "belfast",
        label: "Belfast",
      },
      {
        country: "uk",
        city: "nottingham",
        label: "Nottingham",
      },
      {
        country: "uk",
        city: "leicester",
        label: "Leicester",
      },
      {
        country: "uk",
        city: "brighton",
        label: "Brighton",
      },
      {
        country: "uk",
        city: "southampton",
        label: "Southampton",
      },
      {
        country: "uk",
        city: "coventry",
        label: "Coventry",
      },
      {
        country: "uk",
        city: "reading",
        label: "Reading",
      },
      {
        country: "uk",
        city: "cambridge",
        label: "Cambridge",
      },
      {
        country: "uk",
        city: "oxford",
        label: "Oxford",
      },
      {
        country: "uk",
        city: "aberdeen",
        label: "Aberdeen",
      },
      {
        country: "uk",
        city: "plymouth",
        label: "Plymouth",
      },
      {
        country: "uk",
        city: "swansea",
        label: "Swansea",
      },
      {
        country: "uk",
        city: "york",
        label: "York",
      },
      {
        country: "uk",
        city: "bath",
        label: "Bath",
      },
    ],
  },
  {
    code: "us",
    iso: "US",
    label: "United States",
    cities: [
      {
        country: "us",
        city: "new-york",
        label: "New York",
      },
      {
        country: "us",
        city: "los-angeles",
        label: "Los Angeles",
      },
      {
        country: "us",
        city: "chicago",
        label: "Chicago",
      },
      {
        country: "us",
        city: "houston",
        label: "Houston",
      },
      {
        country: "us",
        city: "phoenix",
        label: "Phoenix",
      },
      {
        country: "us",
        city: "philadelphia",
        label: "Philadelphia",
      },
      {
        country: "us",
        city: "san-antonio",
        label: "San Antonio",
      },
      {
        country: "us",
        city: "san-diego",
        label: "San Diego",
      },
      {
        country: "us",
        city: "dallas",
        label: "Dallas",
      },
      {
        country: "us",
        city: "san-jose",
        label: "San Jose",
      },
      {
        country: "us",
        city: "austin",
        label: "Austin",
      },
      {
        country: "us",
        city: "jacksonville",
        label: "Jacksonville",
      },
      {
        country: "us",
        city: "san-francisco",
        label: "San Francisco",
      },
      {
        country: "us",
        city: "seattle",
        label: "Seattle",
      },
      {
        country: "us",
        city: "denver",
        label: "Denver",
      },
      {
        country: "us",
        city: "boston",
        label: "Boston",
      },
      {
        country: "us",
        city: "nashville",
        label: "Nashville",
      },
      {
        country: "us",
        city: "detroit",
        label: "Detroit",
      },
      {
        country: "us",
        city: "portland",
        label: "Portland",
      },
      {
        country: "us",
        city: "las-vegas",
        label: "Las Vegas",
      },
      {
        country: "us",
        city: "miami",
        label: "Miami",
      },
      {
        country: "us",
        city: "atlanta",
        label: "Atlanta",
      },
      {
        country: "us",
        city: "washington",
        label: "Washington",
      },
      {
        country: "us",
        city: "minneapolis",
        label: "Minneapolis",
      },
      {
        country: "us",
        city: "charlotte",
        label: "Charlotte",
      },
      {
        country: "us",
        city: "tampa",
        label: "Tampa",
      },
      {
        country: "us",
        city: "orlando",
        label: "Orlando",
      },
      {
        country: "us",
        city: "cleveland",
        label: "Cleveland",
      },
      {
        country: "us",
        city: "pittsburgh",
        label: "Pittsburgh",
      },
      {
        country: "us",
        city: "kansas-city",
        label: "Kansas City",
      },
      {
        country: "us",
        city: "st-louis",
        label: "St Louis",
      },
      {
        country: "us",
        city: "sacramento",
        label: "Sacramento",
      },
      {
        country: "us",
        city: "salt-lake-city",
        label: "Salt Lake City",
      },
      {
        country: "us",
        city: "honolulu",
        label: "Honolulu",
      },
      {
        country: "us",
        city: "new-orleans",
        label: "New Orleans",
      },
      {
        country: "us",
        city: "raleigh",
        label: "Raleigh",
      },
      {
        country: "us",
        city: "columbus",
        label: "Columbus",
      },
      {
        country: "us",
        city: "indianapolis",
        label: "Indianapolis",
      },
      {
        country: "us",
        city: "cincinnati",
        label: "Cincinnati",
      },
      {
        country: "us",
        city: "milwaukee",
        label: "Milwaukee",
      },
    ],
  },
  {
    code: "ca",
    iso: "CA",
    label: "Canada",
    cities: [
      {
        country: "ca",
        city: "toronto",
        label: "Toronto",
      },
      {
        country: "ca",
        city: "vancouver",
        label: "Vancouver",
      },
      {
        country: "ca",
        city: "montreal",
        label: "Montreal",
      },
      {
        country: "ca",
        city: "calgary",
        label: "Calgary",
      },
      {
        country: "ca",
        city: "ottawa",
        label: "Ottawa",
      },
      {
        country: "ca",
        city: "edmonton",
        label: "Edmonton",
      },
      {
        country: "ca",
        city: "winnipeg",
        label: "Winnipeg",
      },
      {
        country: "ca",
        city: "quebec-city",
        label: "Quebec City",
      },
      {
        country: "ca",
        city: "hamilton",
        label: "Hamilton",
      },
      {
        country: "ca",
        city: "halifax",
        label: "Halifax",
      },
      {
        country: "ca",
        city: "victoria",
        label: "Victoria",
      },
      {
        country: "ca",
        city: "saskatoon",
        label: "Saskatoon",
      },
      {
        country: "ca",
        city: "regina",
        label: "Regina",
      },
      {
        country: "ca",
        city: "london",
        label: "London",
      },
      {
        country: "ca",
        city: "kitchener",
        label: "Kitchener",
      },
      {
        country: "ca",
        city: "mississauga",
        label: "Mississauga",
      },
      {
        country: "ca",
        city: "brampton",
        label: "Brampton",
      },
      {
        country: "ca",
        city: "surrey",
        label: "Surrey",
      },
    ],
  },
  {
    code: "au",
    iso: "AU",
    label: "Australia",
    cities: [
      {
        country: "au",
        city: "sydney",
        label: "Sydney",
      },
      {
        country: "au",
        city: "melbourne",
        label: "Melbourne",
      },
      {
        country: "au",
        city: "brisbane",
        label: "Brisbane",
      },
      {
        country: "au",
        city: "perth",
        label: "Perth",
      },
      {
        country: "au",
        city: "adelaide",
        label: "Adelaide",
      },
      {
        country: "au",
        city: "canberra",
        label: "Canberra",
      },
      {
        country: "au",
        city: "hobart",
        label: "Hobart",
      },
      {
        country: "au",
        city: "gold-coast",
        label: "Gold Coast",
      },
      {
        country: "au",
        city: "newcastle",
        label: "Newcastle",
      },
      {
        country: "au",
        city: "wollongong",
        label: "Wollongong",
      },
      {
        country: "au",
        city: "geelong",
        label: "Geelong",
      },
      {
        country: "au",
        city: "cairns",
        label: "Cairns",
      },
      {
        country: "au",
        city: "darwin",
        label: "Darwin",
      },
      {
        country: "au",
        city: "townsville",
        label: "Townsville",
      },
      {
        country: "au",
        city: "sunshine-coast",
        label: "Sunshine Coast",
      },
    ],
  },
  {
    code: "ie",
    iso: "IE",
    label: "Ireland",
    cities: [
      {
        country: "ie",
        city: "dublin",
        label: "Dublin",
      },
      {
        country: "ie",
        city: "cork",
        label: "Cork",
      },
      {
        country: "ie",
        city: "galway",
        label: "Galway",
      },
      {
        country: "ie",
        city: "limerick",
        label: "Limerick",
      },
      {
        country: "ie",
        city: "waterford",
        label: "Waterford",
      },
      {
        country: "ie",
        city: "kilkenny",
        label: "Kilkenny",
      },
      {
        country: "ie",
        city: "sligo",
        label: "Sligo",
      },
      {
        country: "ie",
        city: "drogheda",
        label: "Drogheda",
      },
      {
        country: "ie",
        city: "dundalk",
        label: "Dundalk",
      },
      {
        country: "ie",
        city: "wexford",
        label: "Wexford",
      },
    ],
  },
  {
    code: "nz",
    iso: "NZ",
    label: "New Zealand",
    cities: [
      {
        country: "nz",
        city: "auckland",
        label: "Auckland",
      },
      {
        country: "nz",
        city: "wellington",
        label: "Wellington",
      },
      {
        country: "nz",
        city: "christchurch",
        label: "Christchurch",
      },
      {
        country: "nz",
        city: "hamilton",
        label: "Hamilton",
      },
      {
        country: "nz",
        city: "tauranga",
        label: "Tauranga",
      },
      {
        country: "nz",
        city: "dunedin",
        label: "Dunedin",
      },
      {
        country: "nz",
        city: "queenstown",
        label: "Queenstown",
      },
      {
        country: "nz",
        city: "palmerston-north",
        label: "Palmerston North",
      },
      {
        country: "nz",
        city: "napier",
        label: "Napier",
      },
      {
        country: "nz",
        city: "nelson",
        label: "Nelson",
      },
    ],
  },
  {
    code: "ph",
    iso: "PH",
    label: "Philippines",
    cities: [
      {
        country: "ph",
        city: "manila",
        label: "Manila",
      },
      {
        country: "ph",
        city: "quezon-city",
        label: "Quezon City",
      },
      {
        country: "ph",
        city: "cebu",
        label: "Cebu",
      },
      {
        country: "ph",
        city: "davao",
        label: "Davao",
      },
      {
        country: "ph",
        city: "makati",
        label: "Makati",
      },
      {
        country: "ph",
        city: "pasig",
        label: "Pasig",
      },
      {
        country: "ph",
        city: "taguig",
        label: "Taguig",
      },
      {
        country: "ph",
        city: "iloilo",
        label: "Iloilo",
      },
      {
        country: "ph",
        city: "cagayan-de-oro",
        label: "Cagayan De Oro",
      },
      {
        country: "ph",
        city: "bacolod",
        label: "Bacolod",
      },
      {
        country: "ph",
        city: "baguio",
        label: "Baguio",
      },
      {
        country: "ph",
        city: "angeles",
        label: "Angeles",
      },
    ],
  },
  {
    code: "th",
    iso: "TH",
    label: "Thailand",
    cities: [
      {
        country: "th",
        city: "bangkok",
        label: "Bangkok",
      },
      {
        country: "th",
        city: "chiang-mai",
        label: "Chiang Mai",
      },
      {
        country: "th",
        city: "phuket",
        label: "Phuket",
      },
      {
        country: "th",
        city: "pattaya",
        label: "Pattaya",
      },
      {
        country: "th",
        city: "chiang-rai",
        label: "Chiang Rai",
      },
      {
        country: "th",
        city: "hat-yai",
        label: "Hat Yai",
      },
      {
        country: "th",
        city: "khon-kaen",
        label: "Khon Kaen",
      },
      {
        country: "th",
        city: "hua-hin",
        label: "Hua Hin",
      },
      {
        country: "th",
        city: "krabi",
        label: "Krabi",
      },
      {
        country: "th",
        city: "udon-thani",
        label: "Udon Thani",
      },
    ],
  },
  {
    code: "nl",
    iso: "NL",
    label: "Netherlands",
    cities: [
      {
        country: "nl",
        city: "amsterdam",
        label: "Amsterdam",
      },
      {
        country: "nl",
        city: "rotterdam",
        label: "Rotterdam",
      },
      {
        country: "nl",
        city: "the-hague",
        label: "The Hague",
      },
      {
        country: "nl",
        city: "utrecht",
        label: "Utrecht",
      },
      {
        country: "nl",
        city: "eindhoven",
        label: "Eindhoven",
      },
      {
        country: "nl",
        city: "groningen",
        label: "Groningen",
      },
      {
        country: "nl",
        city: "maastricht",
        label: "Maastricht",
      },
      {
        country: "nl",
        city: "haarlem",
        label: "Haarlem",
      },
      {
        country: "nl",
        city: "tilburg",
        label: "Tilburg",
      },
      {
        country: "nl",
        city: "leiden",
        label: "Leiden",
      },
    ],
  },
  {
    code: "bs",
    iso: "BS",
    label: "Bahamas",
    cities: [
      {
        country: "bs",
        city: "nassau",
        label: "Nassau",
      },
      {
        country: "bs",
        city: "freeport",
        label: "Freeport",
      },
      {
        country: "bs",
        city: "marsh-harbour",
        label: "Marsh Harbour",
      },
    ],
  },
  {
    code: "jm",
    iso: "JM",
    label: "Jamaica",
    cities: [
      {
        country: "jm",
        city: "kingston",
        label: "Kingston",
      },
      {
        country: "jm",
        city: "montego-bay",
        label: "Montego Bay",
      },
      {
        country: "jm",
        city: "ocho-rios",
        label: "Ocho Rios",
      },
      {
        country: "jm",
        city: "spanish-town",
        label: "Spanish Town",
      },
      {
        country: "jm",
        city: "negril",
        label: "Negril",
      },
    ],
  },
  {
    code: "ae",
    iso: "AE",
    label: "United Arab Emirates",
    cities: [
      {
        country: "ae",
        city: "dubai",
        label: "Dubai",
      },
      {
        country: "ae",
        city: "abu-dhabi",
        label: "Abu Dhabi",
      },
      {
        country: "ae",
        city: "sharjah",
        label: "Sharjah",
      },
    ],
  },
  {
    code: "ag",
    iso: "AG",
    label: "Antigua and Barbuda",
    cities: [
      {
        country: "ag",
        city: "st-johns",
        label: "St Johns",
      },
    ],
  },
  {
    code: "ar",
    iso: "AR",
    label: "Argentina",
    cities: [
      {
        country: "ar",
        city: "buenos-aires",
        label: "Buenos Aires",
      },
      {
        country: "ar",
        city: "cordoba",
        label: "Cordoba",
      },
      {
        country: "ar",
        city: "mendoza",
        label: "Mendoza",
      },
      {
        country: "ar",
        city: "rosario",
        label: "Rosario",
      },
    ],
  },
  {
    code: "at",
    iso: "AT",
    label: "Austria",
    cities: [
      {
        country: "at",
        city: "vienna",
        label: "Vienna",
      },
      {
        country: "at",
        city: "salzburg",
        label: "Salzburg",
      },
      {
        country: "at",
        city: "innsbruck",
        label: "Innsbruck",
      },
    ],
  },
  {
    code: "bb",
    iso: "BB",
    label: "Barbados",
    cities: [
      {
        country: "bb",
        city: "bridgetown",
        label: "Bridgetown",
      },
      {
        country: "bb",
        city: "speightstown",
        label: "Speightstown",
      },
    ],
  },
  {
    code: "be",
    iso: "BE",
    label: "Belgium",
    cities: [
      {
        country: "be",
        city: "brussels",
        label: "Brussels",
      },
      {
        country: "be",
        city: "antwerp",
        label: "Antwerp",
      },
      {
        country: "be",
        city: "ghent",
        label: "Ghent",
      },
    ],
  },
  {
    code: "br",
    iso: "BR",
    label: "Brazil",
    cities: [
      {
        country: "br",
        city: "sao-paulo",
        label: "Sao Paulo",
      },
      {
        country: "br",
        city: "rio-de-janeiro",
        label: "Rio De Janeiro",
      },
      {
        country: "br",
        city: "brasilia",
        label: "Brasilia",
      },
      {
        country: "br",
        city: "salvador",
        label: "Salvador",
      },
      {
        country: "br",
        city: "belo-horizonte",
        label: "Belo Horizonte",
      },
    ],
  },
  {
    code: "bw",
    iso: "BW",
    label: "Botswana",
    cities: [
      {
        country: "bw",
        city: "gaborone",
        label: "Gaborone",
      },
      {
        country: "bw",
        city: "francistown",
        label: "Francistown",
      },
    ],
  },
  {
    code: "bz",
    iso: "BZ",
    label: "Belize",
    cities: [
      {
        country: "bz",
        city: "belize-city",
        label: "Belize City",
      },
      {
        country: "bz",
        city: "belmopan",
        label: "Belmopan",
      },
      {
        country: "bz",
        city: "san-ignacio",
        label: "San Ignacio",
      },
    ],
  },
  {
    code: "ch",
    iso: "CH",
    label: "Switzerland",
    cities: [
      {
        country: "ch",
        city: "zurich",
        label: "Zurich",
      },
      {
        country: "ch",
        city: "geneva",
        label: "Geneva",
      },
      {
        country: "ch",
        city: "bern",
        label: "Bern",
      },
    ],
  },
  {
    code: "cl",
    iso: "CL",
    label: "Chile",
    cities: [
      {
        country: "cl",
        city: "santiago",
        label: "Santiago",
      },
      {
        country: "cl",
        city: "valparaiso",
        label: "Valparaiso",
      },
      {
        country: "cl",
        city: "concepcion",
        label: "Concepcion",
      },
    ],
  },
  {
    code: "cm",
    iso: "CM",
    label: "Cameroon",
    cities: [
      {
        country: "cm",
        city: "douala",
        label: "Douala",
      },
      {
        country: "cm",
        city: "yaounde",
        label: "Yaounde",
      },
    ],
  },
  {
    code: "cn",
    iso: "CN",
    label: "China",
    cities: [
      {
        country: "cn",
        city: "shanghai",
        label: "Shanghai",
      },
      {
        country: "cn",
        city: "beijing",
        label: "Beijing",
      },
      {
        country: "cn",
        city: "guangzhou",
        label: "Guangzhou",
      },
      {
        country: "cn",
        city: "shenzhen",
        label: "Shenzhen",
      },
      {
        country: "cn",
        city: "chengdu",
        label: "Chengdu",
      },
    ],
  },
  {
    code: "co",
    iso: "CO",
    label: "Colombia",
    cities: [
      {
        country: "co",
        city: "bogota",
        label: "Bogota",
      },
      {
        country: "co",
        city: "medellin",
        label: "Medellin",
      },
      {
        country: "co",
        city: "cali",
        label: "Cali",
      },
      {
        country: "co",
        city: "cartagena",
        label: "Cartagena",
      },
    ],
  },
  {
    code: "cz",
    iso: "CZ",
    label: "Czechia",
    cities: [
      {
        country: "cz",
        city: "prague",
        label: "Prague",
      },
      {
        country: "cz",
        city: "brno",
        label: "Brno",
      },
      {
        country: "cz",
        city: "ostrava",
        label: "Ostrava",
      },
    ],
  },
  {
    code: "de",
    iso: "DE",
    label: "Germany",
    cities: [
      {
        country: "de",
        city: "berlin",
        label: "Berlin",
      },
      {
        country: "de",
        city: "munich",
        label: "Munich",
      },
      {
        country: "de",
        city: "hamburg",
        label: "Hamburg",
      },
      {
        country: "de",
        city: "cologne",
        label: "Cologne",
      },
      {
        country: "de",
        city: "frankfurt",
        label: "Frankfurt",
      },
    ],
  },
  {
    code: "dk",
    iso: "DK",
    label: "Denmark",
    cities: [
      {
        country: "dk",
        city: "copenhagen",
        label: "Copenhagen",
      },
      {
        country: "dk",
        city: "aarhus",
        label: "Aarhus",
      },
      {
        country: "dk",
        city: "odense",
        label: "Odense",
      },
    ],
  },
  {
    code: "eg",
    iso: "EG",
    label: "Egypt",
    cities: [
      {
        country: "eg",
        city: "cairo",
        label: "Cairo",
      },
      {
        country: "eg",
        city: "alexandria",
        label: "Alexandria",
      },
      {
        country: "eg",
        city: "giza",
        label: "Giza",
      },
    ],
  },
  {
    code: "es",
    iso: "ES",
    label: "Spain",
    cities: [
      {
        country: "es",
        city: "madrid",
        label: "Madrid",
      },
      {
        country: "es",
        city: "barcelona",
        label: "Barcelona",
      },
      {
        country: "es",
        city: "valencia",
        label: "Valencia",
      },
      {
        country: "es",
        city: "seville",
        label: "Seville",
      },
      {
        country: "es",
        city: "bilbao",
        label: "Bilbao",
      },
    ],
  },
  {
    code: "fi",
    iso: "FI",
    label: "Finland",
    cities: [
      {
        country: "fi",
        city: "helsinki",
        label: "Helsinki",
      },
      {
        country: "fi",
        city: "tampere",
        label: "Tampere",
      },
      {
        country: "fi",
        city: "turku",
        label: "Turku",
      },
    ],
  },
  {
    code: "fj",
    iso: "FJ",
    label: "Fiji",
    cities: [
      {
        country: "fj",
        city: "suva",
        label: "Suva",
      },
      {
        country: "fj",
        city: "nadi",
        label: "Nadi",
      },
      {
        country: "fj",
        city: "lautoka",
        label: "Lautoka",
      },
    ],
  },
  {
    code: "fm",
    iso: "FM",
    label: "Micronesia",
    cities: [
      {
        country: "fm",
        city: "palikir",
        label: "Palikir",
      },
      {
        country: "fm",
        city: "kolonia",
        label: "Kolonia",
      },
    ],
  },
  {
    code: "fr",
    iso: "FR",
    label: "France",
    cities: [
      {
        country: "fr",
        city: "paris",
        label: "Paris",
      },
      {
        country: "fr",
        city: "lyon",
        label: "Lyon",
      },
      {
        country: "fr",
        city: "marseille",
        label: "Marseille",
      },
      {
        country: "fr",
        city: "nice",
        label: "Nice",
      },
      {
        country: "fr",
        city: "bordeaux",
        label: "Bordeaux",
      },
    ],
  },
  {
    code: "gd",
    iso: "GD",
    label: "Grenada",
    cities: [
      {
        country: "gd",
        city: "st-georges",
        label: "St Georges",
      },
    ],
  },
  {
    code: "gh",
    iso: "GH",
    label: "Ghana",
    cities: [
      {
        country: "gh",
        city: "accra",
        label: "Accra",
      },
      {
        country: "gh",
        city: "kumasi",
        label: "Kumasi",
      },
      {
        country: "gh",
        city: "tamale",
        label: "Tamale",
      },
    ],
  },
  {
    code: "gm",
    iso: "GM",
    label: "Gambia",
    cities: [
      {
        country: "gm",
        city: "banjul",
        label: "Banjul",
      },
      {
        country: "gm",
        city: "serekunda",
        label: "Serekunda",
      },
    ],
  },
  {
    code: "gr",
    iso: "GR",
    label: "Greece",
    cities: [
      {
        country: "gr",
        city: "athens",
        label: "Athens",
      },
      {
        country: "gr",
        city: "thessaloniki",
        label: "Thessaloniki",
      },
      {
        country: "gr",
        city: "heraklion",
        label: "Heraklion",
      },
    ],
  },
  {
    code: "gy",
    iso: "GY",
    label: "Guyana",
    cities: [
      {
        country: "gy",
        city: "georgetown",
        label: "Georgetown",
      },
      {
        country: "gy",
        city: "linden",
        label: "Linden",
      },
    ],
  },
  {
    code: "hr",
    iso: "HR",
    label: "Croatia",
    cities: [
      {
        country: "hr",
        city: "zagreb",
        label: "Zagreb",
      },
      {
        country: "hr",
        city: "split",
        label: "Split",
      },
      {
        country: "hr",
        city: "dubrovnik",
        label: "Dubrovnik",
      },
    ],
  },
  {
    code: "id",
    iso: "ID",
    label: "Indonesia",
    cities: [
      {
        country: "id",
        city: "jakarta",
        label: "Jakarta",
      },
      {
        country: "id",
        city: "surabaya",
        label: "Surabaya",
      },
      {
        country: "id",
        city: "bandung",
        label: "Bandung",
      },
      {
        country: "id",
        city: "bali",
        label: "Bali",
      },
      {
        country: "id",
        city: "medan",
        label: "Medan",
      },
    ],
  },
  {
    code: "il",
    iso: "IL",
    label: "Israel",
    cities: [
      {
        country: "il",
        city: "tel-aviv",
        label: "Tel Aviv",
      },
      {
        country: "il",
        city: "jerusalem",
        label: "Jerusalem",
      },
      {
        country: "il",
        city: "haifa",
        label: "Haifa",
      },
    ],
  },
  {
    code: "in",
    iso: "IN",
    label: "India",
    cities: [
      {
        country: "in",
        city: "mumbai",
        label: "Mumbai",
      },
      {
        country: "in",
        city: "delhi",
        label: "Delhi",
      },
      {
        country: "in",
        city: "bangalore",
        label: "Bangalore",
      },
      {
        country: "in",
        city: "hyderabad",
        label: "Hyderabad",
      },
      {
        country: "in",
        city: "chennai",
        label: "Chennai",
      },
      {
        country: "in",
        city: "kolkata",
        label: "Kolkata",
      },
      {
        country: "in",
        city: "pune",
        label: "Pune",
      },
    ],
  },
  {
    code: "is",
    iso: "IS",
    label: "Iceland",
    cities: [
      {
        country: "is",
        city: "reykjavik",
        label: "Reykjavik",
      },
      {
        country: "is",
        city: "akureyri",
        label: "Akureyri",
      },
    ],
  },
  {
    code: "it",
    iso: "IT",
    label: "Italy",
    cities: [
      {
        country: "it",
        city: "rome",
        label: "Rome",
      },
      {
        country: "it",
        city: "milan",
        label: "Milan",
      },
      {
        country: "it",
        city: "naples",
        label: "Naples",
      },
      {
        country: "it",
        city: "florence",
        label: "Florence",
      },
      {
        country: "it",
        city: "turin",
        label: "Turin",
      },
    ],
  },
  {
    code: "jo",
    iso: "JO",
    label: "Jordan",
    cities: [
      {
        country: "jo",
        city: "amman",
        label: "Amman",
      },
      {
        country: "jo",
        city: "irbid",
        label: "Irbid",
      },
      {
        country: "jo",
        city: "aqaba",
        label: "Aqaba",
      },
    ],
  },
  {
    code: "jp",
    iso: "JP",
    label: "Japan",
    cities: [
      {
        country: "jp",
        city: "tokyo",
        label: "Tokyo",
      },
      {
        country: "jp",
        city: "osaka",
        label: "Osaka",
      },
      {
        country: "jp",
        city: "kyoto",
        label: "Kyoto",
      },
      {
        country: "jp",
        city: "yokohama",
        label: "Yokohama",
      },
      {
        country: "jp",
        city: "nagoya",
        label: "Nagoya",
      },
    ],
  },
  {
    code: "ke",
    iso: "KE",
    label: "Kenya",
    cities: [
      {
        country: "ke",
        city: "nairobi",
        label: "Nairobi",
      },
      {
        country: "ke",
        city: "mombasa",
        label: "Mombasa",
      },
      {
        country: "ke",
        city: "kisumu",
        label: "Kisumu",
      },
      {
        country: "ke",
        city: "nakuru",
        label: "Nakuru",
      },
    ],
  },
  {
    code: "ki",
    iso: "KI",
    label: "Kiribati",
    cities: [
      {
        country: "ki",
        city: "tarawa",
        label: "Tarawa",
      },
    ],
  },
  {
    code: "kn",
    iso: "KN",
    label: "Saint Kitts and Nevis",
    cities: [
      {
        country: "kn",
        city: "basseterre",
        label: "Basseterre",
      },
    ],
  },
  {
    code: "kr",
    iso: "KR",
    label: "South Korea",
    cities: [
      {
        country: "kr",
        city: "seoul",
        label: "Seoul",
      },
      {
        country: "kr",
        city: "busan",
        label: "Busan",
      },
      {
        country: "kr",
        city: "incheon",
        label: "Incheon",
      },
      {
        country: "kr",
        city: "daegu",
        label: "Daegu",
      },
    ],
  },
  {
    code: "lr",
    iso: "LR",
    label: "Liberia",
    cities: [
      {
        country: "lr",
        city: "monrovia",
        label: "Monrovia",
      },
    ],
  },
  {
    code: "ls",
    iso: "LS",
    label: "Lesotho",
    cities: [
      {
        country: "ls",
        city: "maseru",
        label: "Maseru",
      },
    ],
  },
  {
    code: "ma",
    iso: "MA",
    label: "Morocco",
    cities: [
      {
        country: "ma",
        city: "casablanca",
        label: "Casablanca",
      },
      {
        country: "ma",
        city: "rabat",
        label: "Rabat",
      },
      {
        country: "ma",
        city: "marrakesh",
        label: "Marrakesh",
      },
      {
        country: "ma",
        city: "tangier",
        label: "Tangier",
      },
    ],
  },
  {
    code: "mh",
    iso: "MH",
    label: "Marshall Islands",
    cities: [
      {
        country: "mh",
        city: "majuro",
        label: "Majuro",
      },
    ],
  },
  {
    code: "mt",
    iso: "MT",
    label: "Malta",
    cities: [
      {
        country: "mt",
        city: "valletta",
        label: "Valletta",
      },
      {
        country: "mt",
        city: "sliema",
        label: "Sliema",
      },
      {
        country: "mt",
        city: "st-julians",
        label: "St Julians",
      },
    ],
  },
  {
    code: "mw",
    iso: "MW",
    label: "Malawi",
    cities: [
      {
        country: "mw",
        city: "lilongwe",
        label: "Lilongwe",
      },
      {
        country: "mw",
        city: "blantyre",
        label: "Blantyre",
      },
    ],
  },
  {
    code: "mx",
    iso: "MX",
    label: "Mexico",
    cities: [
      {
        country: "mx",
        city: "mexico-city",
        label: "Mexico City",
      },
      {
        country: "mx",
        city: "guadalajara",
        label: "Guadalajara",
      },
      {
        country: "mx",
        city: "monterrey",
        label: "Monterrey",
      },
      {
        country: "mx",
        city: "cancun",
        label: "Cancun",
      },
      {
        country: "mx",
        city: "tijuana",
        label: "Tijuana",
      },
    ],
  },
  {
    code: "my",
    iso: "MY",
    label: "Malaysia",
    cities: [
      {
        country: "my",
        city: "kuala-lumpur",
        label: "Kuala Lumpur",
      },
      {
        country: "my",
        city: "penang",
        label: "Penang",
      },
      {
        country: "my",
        city: "johor-bahru",
        label: "Johor Bahru",
      },
      {
        country: "my",
        city: "kota-kinabalu",
        label: "Kota Kinabalu",
      },
    ],
  },
  {
    code: "na",
    iso: "NA",
    label: "Namibia",
    cities: [
      {
        country: "na",
        city: "windhoek",
        label: "Windhoek",
      },
      {
        country: "na",
        city: "swakopmund",
        label: "Swakopmund",
      },
    ],
  },
  {
    code: "ng",
    iso: "NG",
    label: "Nigeria",
    cities: [
      {
        country: "ng",
        city: "lagos",
        label: "Lagos",
      },
      {
        country: "ng",
        city: "abuja",
        label: "Abuja",
      },
      {
        country: "ng",
        city: "port-harcourt",
        label: "Port Harcourt",
      },
      {
        country: "ng",
        city: "ibadan",
        label: "Ibadan",
      },
      {
        country: "ng",
        city: "kano",
        label: "Kano",
      },
    ],
  },
  {
    code: "no",
    iso: "NO",
    label: "Norway",
    cities: [
      {
        country: "no",
        city: "oslo",
        label: "Oslo",
      },
      {
        country: "no",
        city: "bergen",
        label: "Bergen",
      },
      {
        country: "no",
        city: "trondheim",
        label: "Trondheim",
      },
    ],
  },
  {
    code: "nr",
    iso: "NR",
    label: "Nauru",
    cities: [
      {
        country: "nr",
        city: "yaren",
        label: "Yaren",
      },
    ],
  },
  {
    code: "pg",
    iso: "PG",
    label: "Papua New Guinea",
    cities: [
      {
        country: "pg",
        city: "port-moresby",
        label: "Port Moresby",
      },
      {
        country: "pg",
        city: "lae",
        label: "Lae",
      },
    ],
  },
  {
    code: "pk",
    iso: "PK",
    label: "Pakistan",
    cities: [
      {
        country: "pk",
        city: "karachi",
        label: "Karachi",
      },
      {
        country: "pk",
        city: "lahore",
        label: "Lahore",
      },
      {
        country: "pk",
        city: "islamabad",
        label: "Islamabad",
      },
      {
        country: "pk",
        city: "rawalpindi",
        label: "Rawalpindi",
      },
    ],
  },
  {
    code: "pl",
    iso: "PL",
    label: "Poland",
    cities: [
      {
        country: "pl",
        city: "warsaw",
        label: "Warsaw",
      },
      {
        country: "pl",
        city: "krakow",
        label: "Krakow",
      },
      {
        country: "pl",
        city: "gdansk",
        label: "Gdansk",
      },
      {
        country: "pl",
        city: "wroclaw",
        label: "Wroclaw",
      },
    ],
  },
  {
    code: "pt",
    iso: "PT",
    label: "Portugal",
    cities: [
      {
        country: "pt",
        city: "lisbon",
        label: "Lisbon",
      },
      {
        country: "pt",
        city: "porto",
        label: "Porto",
      },
      {
        country: "pt",
        city: "faro",
        label: "Faro",
      },
    ],
  },
  {
    code: "pw",
    iso: "PW",
    label: "Palau",
    cities: [
      {
        country: "pw",
        city: "ngerulmud",
        label: "Ngerulmud",
      },
      {
        country: "pw",
        city: "koror",
        label: "Koror",
      },
    ],
  },
  {
    code: "qa",
    iso: "QA",
    label: "Qatar",
    cities: [
      {
        country: "qa",
        city: "doha",
        label: "Doha",
      },
      {
        country: "qa",
        city: "al-rayyan",
        label: "Al Rayyan",
      },
    ],
  },
  {
    code: "rw",
    iso: "RW",
    label: "Rwanda",
    cities: [
      {
        country: "rw",
        city: "kigali",
        label: "Kigali",
      },
      {
        country: "rw",
        city: "butare",
        label: "Butare",
      },
    ],
  },
  {
    code: "sb",
    iso: "SB",
    label: "Solomon Islands",
    cities: [
      {
        country: "sb",
        city: "honiara",
        label: "Honiara",
      },
    ],
  },
  {
    code: "se",
    iso: "SE",
    label: "Sweden",
    cities: [
      {
        country: "se",
        city: "stockholm",
        label: "Stockholm",
      },
      {
        country: "se",
        city: "gothenburg",
        label: "Gothenburg",
      },
      {
        country: "se",
        city: "malmo",
        label: "Malmo",
      },
    ],
  },
  {
    code: "sg",
    iso: "SG",
    label: "Singapore",
    cities: [
      {
        country: "sg",
        city: "singapore",
        label: "Singapore",
      },
    ],
  },
  {
    code: "si",
    iso: "SI",
    label: "Slovenia",
    cities: [
      {
        country: "si",
        city: "ljubljana",
        label: "Ljubljana",
      },
      {
        country: "si",
        city: "maribor",
        label: "Maribor",
      },
    ],
  },
  {
    code: "sk",
    iso: "SK",
    label: "Slovakia",
    cities: [
      {
        country: "sk",
        city: "bratislava",
        label: "Bratislava",
      },
      {
        country: "sk",
        city: "kosice",
        label: "Kosice",
      },
    ],
  },
  {
    code: "sl",
    iso: "SL",
    label: "Sierra Leone",
    cities: [
      {
        country: "sl",
        city: "freetown",
        label: "Freetown",
      },
    ],
  },
  {
    code: "ss",
    iso: "SS",
    label: "South Sudan",
    cities: [
      {
        country: "ss",
        city: "juba",
        label: "Juba",
      },
    ],
  },
  {
    code: "sz",
    iso: "SZ",
    label: "Eswatini",
    cities: [
      {
        country: "sz",
        city: "mbabane",
        label: "Mbabane",
      },
      {
        country: "sz",
        city: "manzini",
        label: "Manzini",
      },
    ],
  },
  {
    code: "tn",
    iso: "TN",
    label: "Tunisia",
    cities: [
      {
        country: "tn",
        city: "tunis",
        label: "Tunis",
      },
      {
        country: "tn",
        city: "sfax",
        label: "Sfax",
      },
      {
        country: "tn",
        city: "sousse",
        label: "Sousse",
      },
    ],
  },
  {
    code: "to",
    iso: "TO",
    label: "Tonga",
    cities: [
      {
        country: "to",
        city: "nukualofa",
        label: "Nukualofa",
      },
    ],
  },
  {
    code: "tr",
    iso: "TR",
    label: "Turkey",
    cities: [
      {
        country: "tr",
        city: "istanbul",
        label: "Istanbul",
      },
      {
        country: "tr",
        city: "ankara",
        label: "Ankara",
      },
      {
        country: "tr",
        city: "izmir",
        label: "Izmir",
      },
      {
        country: "tr",
        city: "antalya",
        label: "Antalya",
      },
    ],
  },
  {
    code: "tt",
    iso: "TT",
    label: "Trinidad and Tobago",
    cities: [
      {
        country: "tt",
        city: "port-of-spain",
        label: "Port Of Spain",
      },
      {
        country: "tt",
        city: "san-fernando",
        label: "San Fernando",
      },
      {
        country: "tt",
        city: "chaguanas",
        label: "Chaguanas",
      },
    ],
  },
  {
    code: "tv",
    iso: "TV",
    label: "Tuvalu",
    cities: [
      {
        country: "tv",
        city: "funafuti",
        label: "Funafuti",
      },
    ],
  },
  {
    code: "ug",
    iso: "UG",
    label: "Uganda",
    cities: [
      {
        country: "ug",
        city: "kampala",
        label: "Kampala",
      },
      {
        country: "ug",
        city: "entebbe",
        label: "Entebbe",
      },
      {
        country: "ug",
        city: "jinja",
        label: "Jinja",
      },
    ],
  },
  {
    code: "vc",
    iso: "VC",
    label: "Saint Vincent and the Grenadines",
    cities: [
      {
        country: "vc",
        city: "kingstown",
        label: "Kingstown",
      },
    ],
  },
  {
    code: "vn",
    iso: "VN",
    label: "Vietnam",
    cities: [
      {
        country: "vn",
        city: "ho-chi-minh-city",
        label: "Ho Chi Minh City",
      },
      {
        country: "vn",
        city: "hanoi",
        label: "Hanoi",
      },
      {
        country: "vn",
        city: "da-nang",
        label: "Da Nang",
      },
      {
        country: "vn",
        city: "nha-trang",
        label: "Nha Trang",
      },
    ],
  },
  {
    code: "vu",
    iso: "VU",
    label: "Vanuatu",
    cities: [
      {
        country: "vu",
        city: "port-vila",
        label: "Port Vila",
      },
    ],
  },
  {
    code: "ws",
    iso: "WS",
    label: "Samoa",
    cities: [
      {
        country: "ws",
        city: "apia",
        label: "Apia",
      },
    ],
  },
  {
    code: "za",
    iso: "ZA",
    label: "South Africa",
    cities: [
      {
        country: "za",
        city: "cape-town",
        label: "Cape Town",
      },
      {
        country: "za",
        city: "johannesburg",
        label: "Johannesburg",
      },
      {
        country: "za",
        city: "durban",
        label: "Durban",
      },
      {
        country: "za",
        city: "pretoria",
        label: "Pretoria",
      },
      {
        country: "za",
        city: "port-elizabeth",
        label: "Port Elizabeth",
      },
    ],
  },
  {
    code: "zm",
    iso: "ZM",
    label: "Zambia",
    cities: [
      {
        country: "zm",
        city: "lusaka",
        label: "Lusaka",
      },
      {
        country: "zm",
        city: "ndola",
        label: "Ndola",
      },
      {
        country: "zm",
        city: "kitwe",
        label: "Kitwe",
      },
    ],
  },
  {
    code: "zw",
    iso: "ZW",
    label: "Zimbabwe",
    cities: [
      {
        country: "zw",
        city: "harare",
        label: "Harare",
      },
      {
        country: "zw",
        city: "bulawayo",
        label: "Bulawayo",
      },
    ],
  },
];

export const MARKET_COUNT = 91;

