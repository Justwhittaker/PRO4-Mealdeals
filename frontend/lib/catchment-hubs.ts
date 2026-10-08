/**
 * Regional hubs scraped in addition to metro cities.
 * Generated from backend CATCHMENT_HUBS (wine regions + extra catchments).
 * Slugs must match listingPath: lowercase, spaces to hyphens.
 */
export interface CatchmentHub {
  /** Frontend route country slug (`uk` for GB). */
  country: string;
  city: string;
  label: string;
}

export const CATCHMENT_HUBS: CatchmentHub[] = [
  {
    country: "ar",
    city: "mendoza-wine-country",
    label: "Mendoza Wine Country",
  },
  {
    country: "ar",
    city: "uco-valley",
    label: "Uco Valley",
  },
  {
    country: "ar",
    city: "salta-wine-country",
    label: "Salta Wine Country",
  },
  {
    country: "ar",
    city: "patagonia-wine-country",
    label: "Patagonia Wine Country",
  },
  {
    country: "ar",
    city: "san-juan-wine-country",
    label: "San Juan Wine Country",
  },
  {
    country: "at",
    city: "wachau-wine-country",
    label: "Wachau Wine Country",
  },
  {
    country: "at",
    city: "burgenland-wine-country",
    label: "Burgenland Wine Country",
  },
  {
    country: "au",
    city: "barossa-valley",
    label: "Barossa Valley",
  },
  {
    country: "au",
    city: "hunter-valley",
    label: "Hunter Valley",
  },
  {
    country: "au",
    city: "margaret-river",
    label: "Margaret River",
  },
  {
    country: "au",
    city: "mclaren-vale",
    label: "Mclaren Vale",
  },
  {
    country: "au",
    city: "yarra-valley",
    label: "Yarra Valley",
  },
  {
    country: "au",
    city: "mornington-peninsula",
    label: "Mornington Peninsula",
  },
  {
    country: "au",
    city: "tamar-valley",
    label: "Tamar Valley",
  },
  {
    country: "au",
    city: "coonawarra",
    label: "Coonawarra",
  },
  {
    country: "au",
    city: "clare-valley",
    label: "Clare Valley",
  },
  {
    country: "au",
    city: "granite-belt",
    label: "Granite Belt",
  },
  {
    country: "au",
    city: "mudgee",
    label: "Mudgee",
  },
  {
    country: "br",
    city: "vale-dos-vinhedos",
    label: "Vale Dos Vinhedos",
  },
  {
    country: "br",
    city: "serra-gaucha-wine",
    label: "Serra Gaucha Wine",
  },
  {
    country: "ca",
    city: "okanagan-valley",
    label: "Okanagan Valley",
  },
  {
    country: "ca",
    city: "niagara-wine-region",
    label: "Niagara Wine Region",
  },
  {
    country: "ca",
    city: "prince-edward-county-wine",
    label: "Prince Edward County Wine",
  },
  {
    country: "ca",
    city: "similkameen-valley",
    label: "Similkameen Valley",
  },
  {
    country: "ch",
    city: "lavaux-wine-country",
    label: "Lavaux Wine Country",
  },
  {
    country: "ch",
    city: "valais-wine-country",
    label: "Valais Wine Country",
  },
  {
    country: "cl",
    city: "casablanca-valley",
    label: "Casablanca Valley",
  },
  {
    country: "cl",
    city: "colchagua-valley",
    label: "Colchagua Valley",
  },
  {
    country: "cl",
    city: "maipo-valley",
    label: "Maipo Valley",
  },
  {
    country: "cl",
    city: "aconcagua-valley",
    label: "Aconcagua Valley",
  },
  {
    country: "cl",
    city: "limari-valley",
    label: "Limari Valley",
  },
  {
    country: "cn",
    city: "ningxia-wine-country",
    label: "Ningxia Wine Country",
  },
  {
    country: "cz",
    city: "moravia-wine-country",
    label: "Moravia Wine Country",
  },
  {
    country: "de",
    city: "mosel-wine-country",
    label: "Mosel Wine Country",
  },
  {
    country: "de",
    city: "rheingau-wine-country",
    label: "Rheingau Wine Country",
  },
  {
    country: "de",
    city: "pfalz-wine-country",
    label: "Pfalz Wine Country",
  },
  {
    country: "de",
    city: "baden-wine-country",
    label: "Baden Wine Country",
  },
  {
    country: "de",
    city: "franconia-wine-country",
    label: "Franconia Wine Country",
  },
  {
    country: "es",
    city: "rioja-wine-country",
    label: "Rioja Wine Country",
  },
  {
    country: "es",
    city: "ribera-del-duero-wine-country",
    label: "Ribera Del Duero Wine Country",
  },
  {
    country: "es",
    city: "priorat-wine-country",
    label: "Priorat Wine Country",
  },
  {
    country: "es",
    city: "penedes-wine-country",
    label: "Penedes Wine Country",
  },
  {
    country: "es",
    city: "rias-baixas-wine-country",
    label: "Rias Baixas Wine Country",
  },
  {
    country: "es",
    city: "jerez-sherry-country",
    label: "Jerez Sherry Country",
  },
  {
    country: "es",
    city: "mallorca-wine-country",
    label: "Mallorca Wine Country",
  },
  {
    country: "es",
    city: "lanzarote-wine-country",
    label: "Lanzarote Wine Country",
  },
  {
    country: "es",
    city: "tenerife-wine-country",
    label: "Tenerife Wine Country",
  },
  {
    country: "fr",
    city: "bordeaux-wine-country",
    label: "Bordeaux Wine Country",
  },
  {
    country: "fr",
    city: "burgundy-wine-country",
    label: "Burgundy Wine Country",
  },
  {
    country: "fr",
    city: "champagne-wine-country",
    label: "Champagne Wine Country",
  },
  {
    country: "fr",
    city: "loire-valley-wine-country",
    label: "Loire Valley Wine Country",
  },
  {
    country: "fr",
    city: "rhone-valley-wine-country",
    label: "Rhone Valley Wine Country",
  },
  {
    country: "fr",
    city: "alsace-wine-country",
    label: "Alsace Wine Country",
  },
  {
    country: "fr",
    city: "provence-wine-country",
    label: "Provence Wine Country",
  },
  {
    country: "fr",
    city: "languedoc-wine-country",
    label: "Languedoc Wine Country",
  },
  {
    country: "gr",
    city: "santorini-wine-country",
    label: "Santorini Wine Country",
  },
  {
    country: "gr",
    city: "nemea-wine-country",
    label: "Nemea Wine Country",
  },
  {
    country: "gr",
    city: "crete-wine-country",
    label: "Crete Wine Country",
  },
  {
    country: "hr",
    city: "istria-wine-country",
    label: "Istria Wine Country",
  },
  {
    country: "ie",
    city: "killarney",
    label: "Killarney",
  },
  {
    country: "ie",
    city: "westport",
    label: "Westport",
  },
  {
    country: "in",
    city: "nashik-wine-country",
    label: "Nashik Wine Country",
  },
  {
    country: "it",
    city: "tuscany-wine-country",
    label: "Tuscany Wine Country",
  },
  {
    country: "it",
    city: "piedmont-wine-country",
    label: "Piedmont Wine Country",
  },
  {
    country: "it",
    city: "prosecco-wine-country",
    label: "Prosecco Wine Country",
  },
  {
    country: "it",
    city: "sicily-wine-country",
    label: "Sicily Wine Country",
  },
  {
    country: "it",
    city: "umbria-wine-country",
    label: "Umbria Wine Country",
  },
  {
    country: "it",
    city: "alto-adige-wine-country",
    label: "Alto Adige Wine Country",
  },
  {
    country: "it",
    city: "puglia-wine-country",
    label: "Puglia Wine Country",
  },
  {
    country: "jp",
    city: "yamanashi-wine-country",
    label: "Yamanashi Wine Country",
  },
  {
    country: "mt",
    city: "malta-wine-country",
    label: "Malta Wine Country",
  },
  {
    country: "mx",
    city: "valle-de-guadalupe",
    label: "Valle De Guadalupe",
  },
  {
    country: "nz",
    city: "marlborough",
    label: "Marlborough",
  },
  {
    country: "nz",
    city: "central-otago",
    label: "Central Otago",
  },
  {
    country: "nz",
    city: "hawkes-bay",
    label: "Hawkes Bay",
  },
  {
    country: "nz",
    city: "martinborough",
    label: "Martinborough",
  },
  {
    country: "nz",
    city: "waiheke-island",
    label: "Waiheke Island",
  },
  {
    country: "nz",
    city: "gibbston-valley",
    label: "Gibbston Valley",
  },
  {
    country: "nz",
    city: "north-canterbury",
    label: "North Canterbury",
  },
  {
    country: "pt",
    city: "douro-wine-country",
    label: "Douro Wine Country",
  },
  {
    country: "pt",
    city: "alentejo-wine-country",
    label: "Alentejo Wine Country",
  },
  {
    country: "pt",
    city: "vinho-verde-wine-country",
    label: "Vinho Verde Wine Country",
  },
  {
    country: "si",
    city: "podravje-wine-country",
    label: "Podravje Wine Country",
  },
  {
    country: "us",
    city: "napa-valley",
    label: "Napa Valley",
  },
  {
    country: "us",
    city: "sonoma",
    label: "Sonoma",
  },
  {
    country: "us",
    city: "santa-barbara-wine-country",
    label: "Santa Barbara Wine Country",
  },
  {
    country: "us",
    city: "willamette-valley",
    label: "Willamette Valley",
  },
  {
    country: "us",
    city: "walla-walla-valley",
    label: "Walla Walla Valley",
  },
  {
    country: "us",
    city: "finger-lakes",
    label: "Finger Lakes",
  },
  {
    country: "us",
    city: "virginia-wine-country",
    label: "Virginia Wine Country",
  },
  {
    country: "us",
    city: "paso-robles",
    label: "Paso Robles",
  },
  {
    country: "us",
    city: "texas-hill-country-wine",
    label: "Texas Hill Country Wine",
  },
  {
    country: "us",
    city: "monterey-wine-country",
    label: "Monterey Wine Country",
  },
  {
    country: "us",
    city: "oakland",
    label: "Oakland",
  },
  {
    country: "us",
    city: "fresno",
    label: "Fresno",
  },
  {
    country: "us",
    city: "palm-springs",
    label: "Palm Springs",
  },
  {
    country: "us",
    city: "long-beach",
    label: "Long Beach",
  },
  {
    country: "za",
    city: "stellenbosch",
    label: "Stellenbosch",
  },
  {
    country: "za",
    city: "franschhoek",
    label: "Franschhoek",
  },
  {
    country: "za",
    city: "paarl",
    label: "Paarl",
  },
  {
    country: "za",
    city: "constantia",
    label: "Constantia",
  },
  {
    country: "za",
    city: "robertson",
    label: "Robertson",
  },
  {
    country: "za",
    city: "swartland",
    label: "Swartland",
  },
  {
    country: "za",
    city: "elgin",
    label: "Elgin",
  },
  {
    country: "za",
    city: "hemel-en-aarde",
    label: "Hemel En Aarde",
  },
];
