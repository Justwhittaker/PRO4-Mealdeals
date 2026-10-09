/**
 * City and state labels for newsletter signup.
 * The API city map is the source of truth when the city is known.
 * This copy lets the signup form prefill "Salt Lake City, Utah" and
 * keep an IP region code (x-vercel-ip-country-region / cf-region-code)
 * for towns that are not in the city list.
 */

export interface SubscriberRegion {
  regionCode: string;
  regionLabel: string;
}

const REGION_LABELS: Record<string, Record<string, string>> = {
  us: {
    AL: "Alabama",
    AK: "Alaska",
    AZ: "Arizona",
    AR: "Arkansas",
    CA: "California",
    CO: "Colorado",
    CT: "Connecticut",
    DE: "Delaware",
    DC: "District of Columbia",
    FL: "Florida",
    GA: "Georgia",
    HI: "Hawaii",
    ID: "Idaho",
    IL: "Illinois",
    IN: "Indiana",
    IA: "Iowa",
    KS: "Kansas",
    KY: "Kentucky",
    LA: "Louisiana",
    ME: "Maine",
    MD: "Maryland",
    MA: "Massachusetts",
    MI: "Michigan",
    MN: "Minnesota",
    MS: "Mississippi",
    MO: "Missouri",
    MT: "Montana",
    NE: "Nebraska",
    NV: "Nevada",
    NH: "New Hampshire",
    NJ: "New Jersey",
    NM: "New Mexico",
    NY: "New York",
    NC: "North Carolina",
    ND: "North Dakota",
    OH: "Ohio",
    OK: "Oklahoma",
    OR: "Oregon",
    PA: "Pennsylvania",
    RI: "Rhode Island",
    SC: "South Carolina",
    SD: "South Dakota",
    TN: "Tennessee",
    TX: "Texas",
    UT: "Utah",
    VT: "Vermont",
    VA: "Virginia",
    WA: "Washington",
    WV: "West Virginia",
    WI: "Wisconsin",
    WY: "Wyoming",
  },
  ca: {
    AB: "Alberta",
    BC: "British Columbia",
    MB: "Manitoba",
    NB: "New Brunswick",
    NL: "Newfoundland and Labrador",
    NS: "Nova Scotia",
    NT: "Northwest Territories",
    NU: "Nunavut",
    ON: "Ontario",
    PE: "Prince Edward Island",
    QC: "Quebec",
    SK: "Saskatchewan",
    YT: "Yukon",
  },
  au: {
    ACT: "Australian Capital Territory",
    NSW: "New South Wales",
    NT: "Northern Territory",
    QLD: "Queensland",
    SA: "South Australia",
    TAS: "Tasmania",
    VIC: "Victoria",
    WA: "Western Australia",
  },
};

const CITY_REGION: Record<string, string> = {
  "us/newyork": "NY",
  "us/new-york": "NY",
  "us/losangeles": "CA",
  "us/los-angeles": "CA",
  "us/chicago": "IL",
  "us/miami": "FL",
  "us/saltlakecity": "UT",
  "us/salt-lake-city": "UT",
  "us/provo": "UT",
  "us/stgeorge": "UT",
  "us/st-george": "UT",
  "us/parkcity": "UT",
  "us/park-city": "UT",
  "us/denver": "CO",
  "us/seattle": "WA",
  "us/houston": "TX",
  "us/phoenix": "AZ",
  "us/philadelphia": "PA",
  "us/dallas": "TX",
  "us/austin": "TX",
  "us/sanfrancisco": "CA",
  "us/san-francisco": "CA",
  "us/boston": "MA",
  "us/atlanta": "GA",
  "us/washington": "DC",
  "ca/toronto": "ON",
  "ca/vancouver": "BC",
  "ca/montreal": "QC",
  "ca/calgary": "AB",
  "ca/ottawa": "ON",
  "au/sydney": "NSW",
  "au/melbourne": "VIC",
  "au/brisbane": "QLD",
  "au/perth": "WA",
  "au/adelaide": "SA",
  "au/canberra": "ACT",
  "au/hobart": "TAS",
};

function countryKey(country: string): string {
  const key = country.trim().toLowerCase();
  if (key === "gb") return "uk";
  return key;
}

function cityKey(city: string): string {
  return city.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

export function regionLabel(
  country: string,
  code: string | null | undefined,
): string | null {
  const compact = (code ?? "").trim().toUpperCase();
  if (!compact) return null;
  return REGION_LABELS[countryKey(country)]?.[compact] ?? null;
}

export function regionForCity(
  country: string,
  city: string,
): SubscriberRegion | null {
  const countrySlug = countryKey(country);
  const labels = REGION_LABELS[countrySlug];
  if (!labels) return null;
  const code =
    CITY_REGION[`${countrySlug}/${cityKey(city)}`] ??
    CITY_REGION[`${countrySlug}/${city.trim().toLowerCase()}`];
  if (!code) return null;
  const label = labels[code];
  if (!label) return null;
  return { regionCode: code, regionLabel: label };
}

export function regionFromCode(
  country: string,
  code: string | null | undefined,
): SubscriberRegion | null {
  const label = regionLabel(country, code);
  const compact = (code ?? "").trim().toUpperCase();
  if (!label || !compact) return null;
  return { regionCode: compact, regionLabel: label };
}
