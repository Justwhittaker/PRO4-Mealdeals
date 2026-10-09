"""State and province lookup for countries that are too wide to email as one list.

Deals do not store a state. The newsletter derives one from the city, and
from a region code on the subscriber when the city is not in this map
(for example Park City, UT). Ireland and other countries without an entry
here stay city → nearby → country.
"""

from __future__ import annotations

import re

from app.services.geo_names import normalize_country

# ISO country → region code → display label.
REGIONS: dict[str, dict[str, str]] = {
    "US": {
        "AL": "Alabama",
        "AK": "Alaska",
        "AZ": "Arizona",
        "AR": "Arkansas",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "DC": "the District of Columbia",
        "FL": "Florida",
        "GA": "Georgia",
        "HI": "Hawaii",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "IA": "Iowa",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "ME": "Maine",
        "MD": "Maryland",
        "MA": "Massachusetts",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MS": "Mississippi",
        "MO": "Missouri",
        "MT": "Montana",
        "NE": "Nebraska",
        "NV": "Nevada",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NY": "New York",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PA": "Pennsylvania",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VT": "Vermont",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "WI": "Wisconsin",
        "WY": "Wyoming",
    },
    "CA": {
        "AB": "Alberta",
        "BC": "British Columbia",
        "MB": "Manitoba",
        "NB": "New Brunswick",
        "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia",
        "NT": "the Northwest Territories",
        "NU": "Nunavut",
        "ON": "Ontario",
        "PE": "Prince Edward Island",
        "QC": "Quebec",
        "SK": "Saskatchewan",
        "YT": "Yukon",
    },
    "AU": {
        "ACT": "the Australian Capital Territory",
        "NSW": "New South Wales",
        "NT": "the Northern Territory",
        "QLD": "Queensland",
        "SA": "South Australia",
        "TAS": "Tasmania",
        "VIC": "Victoria",
        "WA": "Western Australia",
    },
}

# (country, city key) → region code. City keys drop spaces and punctuation.
_CITY_REGION: dict[tuple[str, str], str] = {
    ("US", "newyork"): "NY",
    ("US", "losangeles"): "CA",
    ("US", "chicago"): "IL",
    ("US", "houston"): "TX",
    ("US", "phoenix"): "AZ",
    ("US", "philadelphia"): "PA",
    ("US", "sanantonio"): "TX",
    ("US", "sandiego"): "CA",
    ("US", "dallas"): "TX",
    ("US", "sanjose"): "CA",
    ("US", "austin"): "TX",
    ("US", "jacksonville"): "FL",
    ("US", "sanfrancisco"): "CA",
    ("US", "seattle"): "WA",
    ("US", "denver"): "CO",
    ("US", "boston"): "MA",
    ("US", "nashville"): "TN",
    ("US", "detroit"): "MI",
    ("US", "portland"): "OR",
    ("US", "lasvegas"): "NV",
    ("US", "miami"): "FL",
    ("US", "atlanta"): "GA",
    ("US", "washington"): "DC",
    ("US", "minneapolis"): "MN",
    ("US", "charlotte"): "NC",
    ("US", "tampa"): "FL",
    ("US", "orlando"): "FL",
    ("US", "cleveland"): "OH",
    ("US", "pittsburgh"): "PA",
    ("US", "kansascity"): "MO",
    ("US", "stlouis"): "MO",
    ("US", "sacramento"): "CA",
    ("US", "saltlakecity"): "UT",
    ("US", "provo"): "UT",
    ("US", "stgeorge"): "UT",
    ("US", "parkcity"): "UT",
    ("US", "ogden"): "UT",
    ("US", "orem"): "UT",
    ("US", "honolulu"): "HI",
    ("US", "neworleans"): "LA",
    ("US", "raleigh"): "NC",
    ("US", "columbus"): "OH",
    ("US", "indianapolis"): "IN",
    ("US", "cincinnati"): "OH",
    ("US", "milwaukee"): "WI",
    ("CA", "toronto"): "ON",
    ("CA", "vancouver"): "BC",
    ("CA", "montreal"): "QC",
    ("CA", "calgary"): "AB",
    ("CA", "ottawa"): "ON",
    ("CA", "edmonton"): "AB",
    ("CA", "winnipeg"): "MB",
    ("CA", "quebeccity"): "QC",
    ("CA", "hamilton"): "ON",
    ("CA", "halifax"): "NS",
    ("CA", "victoria"): "BC",
    ("CA", "saskatoon"): "SK",
    ("CA", "regina"): "SK",
    ("CA", "london"): "ON",
    ("CA", "kitchener"): "ON",
    ("CA", "mississauga"): "ON",
    ("CA", "brampton"): "ON",
    ("CA", "surrey"): "BC",
    ("AU", "sydney"): "NSW",
    ("AU", "melbourne"): "VIC",
    ("AU", "brisbane"): "QLD",
    ("AU", "perth"): "WA",
    ("AU", "adelaide"): "SA",
    ("AU", "canberra"): "ACT",
    ("AU", "hobart"): "TAS",
    ("AU", "goldcoast"): "QLD",
    ("AU", "newcastle"): "NSW",
    ("AU", "wollongong"): "NSW",
    ("AU", "geelong"): "VIC",
    ("AU", "cairns"): "QLD",
    ("AU", "darwin"): "NT",
    ("AU", "townsville"): "QLD",
    ("AU", "sunshinecoast"): "QLD",
}


def _city_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _name_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _name_index() -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    for country, regions in REGIONS.items():
        for code, label in regions.items():
            index[_name_key(label)] = (country, code)
            if label.lower().startswith("the "):
                index[_name_key(label[4:])] = (country, code)
            index[_name_key(code)] = (country, code)
    return index


_NAMES = _name_index()


def regions_with_code(code: str) -> list[tuple[str, str]]:
    """Every (country, label) that uses this region code. CA is California, not Canada."""
    compact = re.sub(r"[^A-Za-z0-9]", "", code).upper()
    if not compact:
        return []
    found: list[tuple[str, str]] = []
    for country, regions in REGIONS.items():
        label = regions.get(compact)
        if label:
            found.append((country, label))
    return found


def region_from_name(name: str) -> tuple[str, str] | None:
    """Map 'Utah' or 'New South Wales' to (country, region code)."""
    return _NAMES.get(_name_key(name))


def region_belongs(country: str | None, code: str | None) -> bool:
    if not country or not code:
        return False
    compact = re.sub(r"[^A-Za-z0-9]", "", code).upper()
    return compact in REGIONS.get(normalize_country(country), {})


def region_label(country: str | None, code: str | None) -> str | None:
    if not region_belongs(country, code):
        return None
    compact = re.sub(r"[^A-Za-z0-9]", "", code or "").upper()
    return REGIONS[normalize_country(country or "")][compact]


def region_for_city(country: str | None, city: str | None) -> tuple[str, str] | None:
    """Return (region code, label) when this city is in the state map."""
    if not country or not city:
        return None
    code = normalize_country(country)
    regions = REGIONS.get(code)
    if not regions:
        return None
    key = _city_key(city)
    region_code = _CITY_REGION.get((code, key))
    if region_code is None and key.endswith("city") and len(key) > 4:
        region_code = _CITY_REGION.get((code, key[:-4]))
    if not region_code:
        return None
    label = regions.get(region_code)
    if not label:
        return None
    return region_code, label
