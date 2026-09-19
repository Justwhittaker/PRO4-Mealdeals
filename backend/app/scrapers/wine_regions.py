"""Global wine-region catchment hubs — scraped in addition to country metro cities."""

from __future__ import annotations

# (hub display name, lat, lon, winery venue cap)
WineRegion = tuple[str, float, float, int]

WINE_REGIONS: dict[str, list[WineRegion]] = {
    # ── Africa ──
    "ZA": [
        ("Stellenbosch", -33.9321, 18.8602, 20),
        ("Franschhoek", -33.9143, 19.1239, 18),
        ("Paarl", -33.7364, 18.9708, 16),
        ("Constantia", -34.0108, 18.4080, 14),
        ("Robertson", -33.8023, 19.8847, 14),
        ("Swartland", -33.4500, 18.7333, 12),
        ("Elgin", -34.2500, 19.0833, 12),
        ("Hemel En Aarde", -34.4167, 19.2500, 12),
    ],
    # ── Oceania ──
    "AU": [
        ("Barossa Valley", -34.5244, 138.9636, 20),
        ("Hunter Valley", -32.7633, 151.2840, 18),
        ("Margaret River", -33.9550, 115.0750, 16),
        ("Mclaren Vale", -35.2167, 138.5500, 16),
        ("Yarra Valley", -37.6500, 145.5167, 16),
        ("Mornington Peninsula", -38.3500, 145.0167, 14),
        ("Tamar Valley", -41.2833, 146.9167, 14),
        ("Coonawarra", -37.2833, 140.8333, 14),
        ("Clare Valley", -33.8333, 138.6167, 14),
        ("Granite Belt", -28.6667, 152.0167, 12),
        ("Mudgee", -32.5833, 149.5833, 12),
    ],
    "NZ": [
        ("Marlborough", -41.5134, 173.9612, 18),
        ("Central Otago", -45.0312, 168.6626, 16),
        ("Hawkes Bay", -39.4928, 176.9120, 16),
        ("Martinborough", -41.2167, 175.4667, 14),
        ("Waiheke Island", -36.7883, 175.0553, 14),
        ("Gibbston Valley", -45.0167, 168.8833, 12),
        ("North Canterbury", -43.3167, 172.6833, 12),
    ],
    # ── Americas ──
    "US": [
        ("Napa Valley", 38.5025, -122.2654, 20),
        ("Sonoma", 38.2919, -122.4580, 18),
        ("Santa Barbara Wine Country", 34.6405, -120.0799, 16),
        ("Willamette Valley", 45.2132, -123.1970, 16),
        ("Walla Walla Valley", 46.0646, -118.3430, 14),
        ("Finger Lakes", 42.4400, -76.9500, 14),
        ("Virginia Wine Country", 38.0293, -78.4767, 14),
        ("Paso Robles", 35.6266, -120.6910, 14),
        ("Texas Hill Country Wine", 30.2752, -98.8719, 12),
        ("Monterey Wine Country", 36.6002, -121.8947, 12),
    ],
    "CA": [
        ("Okanagan Valley", 49.8844, -119.4962, 18),
        ("Niagara Wine Region", 43.2557, -79.0719, 16),
        ("Prince Edward County Wine", 44.0197, -77.6703, 12),
        ("Similkameen Valley", 49.1500, -119.7500, 12),
    ],
    "AR": [
        ("Mendoza Wine Country", -33.0800, -68.8700, 18),
        ("Uco Valley", -33.5833, -69.1333, 16),
        ("Salta Wine Country", -24.7859, -65.4117, 14),
        ("Patagonia Wine Country", -38.9516, -68.0591, 12),
        ("San Juan Wine Country", -31.5375, -68.5364, 12),
    ],
    "CL": [
        ("Casablanca Valley", -33.3833, -71.4167, 16),
        ("Colchagua Valley", -34.3833, -71.0833, 16),
        ("Maipo Valley", -33.6833, -70.9167, 14),
        ("Aconcagua Valley", -32.9167, -70.7167, 12),
        ("Limari Valley", -30.5833, -71.2167, 12),
    ],
    "BR": [
        ("Vale Dos Vinhedos", -29.1667, -51.5167, 14),
        ("Serra Gaucha Wine", -29.1686, -51.1794, 14),
    ],
    "MX": [
        ("Valle De Guadalupe", 32.0342, -116.6316, 16),
    ],
    # ── Western Europe ──
    "FR": [
        ("Bordeaux Wine Country", 44.8378, -0.5792, 18),
        ("Burgundy Wine Country", 47.0253, 4.8387, 18),
        ("Champagne Wine Country", 49.0436, 3.9594, 16),
        ("Loire Valley Wine Country", 47.3941, 0.6848, 16),
        ("Rhone Valley Wine Country", 43.9493, 4.8055, 16),
        ("Alsace Wine Country", 48.0794, 7.3585, 14),
        ("Provence Wine Country", 43.5297, 5.4474, 14),
        ("Languedoc Wine Country", 43.6108, 3.8767, 14),
    ],
    "IT": [
        ("Tuscany Wine Country", 43.7696, 11.2558, 18),
        ("Piedmont Wine Country", 44.6998, 8.0355, 18),
        ("Prosecco Wine Country", 45.9033, 11.9978, 16),
        ("Sicily Wine Country", 37.7989, 12.4371, 14),
        ("Umbria Wine Country", 42.7184, 12.1107, 12),
        ("Alto Adige Wine Country", 46.4983, 11.3548, 14),
        ("Puglia Wine Country", 40.4000, 17.6333, 12),
    ],
    "DE": [
        ("Mosel Wine Country", 49.9150, 7.0733, 16),
        ("Rheingau Wine Country", 49.9786, 7.9197, 16),
        ("Pfalz Wine Country", 49.4614, 8.1722, 14),
        ("Baden Wine Country", 47.9936, 7.8519, 14),
        ("Franconia Wine Country", 49.7913, 9.9534, 12),
    ],
    "ES": [
        ("Rioja Wine Country", 42.4650, -2.4456, 18),
        ("Ribera Del Duero Wine Country", 41.6704, -3.6896, 16),
        ("Priorat Wine Country", 41.1444, 0.8278, 14),
        ("Penedes Wine Country", 41.3467, 1.7000, 14),
        ("Rias Baixas Wine Country", 42.4336, -8.6486, 14),
        ("Jerez Sherry Country", 36.6866, -6.1365, 12),
    ],
    "PT": [
        ("Douro Wine Country", 41.1611, -7.7867, 18),
        ("Alentejo Wine Country", 38.5714, -7.9135, 14),
        ("Vinho Verde Wine Country", 41.4444, -8.2962, 14),
    ],
    "CH": [
        ("Lavaux Wine Country", 46.4984, 6.7328, 14),
        ("Valais Wine Country", 46.2333, 7.3667, 12),
    ],
    "AT": [
        ("Wachau Wine Country", 48.3967, 15.5206, 16),
        ("Burgenland Wine Country", 47.8011, 16.9250, 14),
    ],
    "GR": [
        ("Santorini Wine Country", 36.3932, 25.4615, 14),
        ("Nemea Wine Country", 37.8167, 22.7167, 12),
        ("Crete Wine Country", 35.3387, 25.1442, 12),
    ],
    "HR": [
        ("Istria Wine Country", 45.3367, 13.8286, 12),
    ],
    "SI": [
        ("Podravje Wine Country", 46.5547, 15.6467, 12),
    ],
    "MT": [
        ("Malta Wine Country", 35.8997, 14.4367, 10),
    ],
    # ── Central / Eastern Europe ──
    "CZ": [
        ("Moravia Wine Country", 48.7544, 16.8554, 12),
    ],
    # ── Asia ──
    "CN": [
        ("Ningxia Wine Country", 38.4872, 106.2309, 12),
    ],
    "JP": [
        ("Yamanashi Wine Country", 35.6642, 138.5686, 12),
    ],
    "IN": [
        ("Nashik Wine Country", 19.9975, 73.7898, 12),
    ],
}

# Countries not yet in TARGET_MARKETS (add here when markets expand):
# HU Tokaj, RO Transylvania, GE Kakheti, MD Moldova, LB Bekaa Valley


def wine_region_hubs(country_code: str) -> list[str]:
    code = country_code.strip().upper()
    return [row[0] for row in WINE_REGIONS.get(code, [])]


def wine_region_coords() -> dict[tuple[str, str], tuple[float, float]]:
    out: dict[tuple[str, str], tuple[float, float]] = {}
    for code, regions in WINE_REGIONS.items():
        for name, lat, lon, _cap in regions:
            out[(code, name.strip().title())] = (lat, lon)
    return out


def wine_region_winery_caps() -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for code, regions in WINE_REGIONS.items():
        for name, _lat, _lon, cap in regions:
            out[(code, name.strip().title())] = cap
    return out


def is_wine_region_hub(country_code: str, hub_city: str) -> bool:
    key = (country_code.strip().upper(), hub_city.strip().title())
    return key in wine_region_coords()
