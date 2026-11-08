"""Worldwide Overpass tiles. Europe first, then the rest of the planet.

Each static tile is a country or a slice of one. A weekly run walks that list
from a checkpoint. When a query returns a full page or times out, the tile is
split into four sub-tiles and the checkpoint stores those, so a later week
resumes mid-country. Europe stays first.

Default pace (see ``TILES_PER_RUN_DEFAULT``): 60 Overpass queries a week. The
static tile count is ``len(TILES)``. Runtime splits add more queries on dense cells.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Static grid. About 2.5 degrees keeps a query polite. Countries larger than
# MAX_TILES_PER_COUNTRY cells are coarser and then split at runtime when a
# query fills the place cap or times out.
MAX_SPAN_DEGREES = 2.5
# Prefer this many cells, but do not coarsen a cell past MAX_CELL_DEGREES.
# A 40-cell cap left the US and Russia as multi-degree blocks that time out.
MAX_TILES_PER_COUNTRY = 80
MAX_CELL_DEGREES = 4.0
# Do not recurse forever on a dense city block.
MIN_SUBTILE_SPAN = 0.5
MAX_SPLIT_DEPTH = 6
# Give a dead mirror a few Sundays, then move on so one bbox cannot stall the planet.
MAX_TILE_RETRIES = 3
# Stop the week here even when the yield clock is still open, so Sunday
# morning zone scrapes are not walking into a hot Overpass.
TILES_PER_RUN_DEFAULT = 60
# Homepage plus one contact page and one about page.
FETCHES_PER_PLACE = 3

# code, name, south, west, north, east, europe, zone
# zone "" means pick from the country (US east/west uses the tile centre).
_REGIONS: tuple[tuple[str, str, float, float, float, float, bool, str], ...] = (
    # Europe first. Order is the first-pass order.
    ("IE", "Ireland", 51.4, -10.6, 55.5, -5.4, True, "british_isles"),
    ("GB", "United Kingdom", 49.8, -8.7, 60.9, 1.8, True, "british_isles"),
    ("IM", "Isle of Man", 54.0, -4.9, 54.4, -4.3, True, "british_isles"),
    ("FR", "France", 41.3, -5.2, 51.1, 8.3, True, "france_benelux"),
    ("BE", "Belgium", 49.5, 2.5, 51.5, 6.4, True, "france_benelux"),
    ("NL", "Netherlands", 50.7, 3.3, 53.6, 7.2, True, "france_benelux"),
    ("LU", "Luxembourg", 49.4, 5.7, 50.2, 6.5, True, "france_benelux"),
    ("MC", "Monaco", 43.7, 7.4, 43.8, 7.5, True, "france_benelux"),
    ("DE", "Germany", 47.2, 5.8, 55.1, 15.0, True, "dach_nordics"),
    ("CH", "Switzerland", 45.8, 5.9, 47.8, 10.5, True, "dach_nordics"),
    ("AT", "Austria", 46.3, 9.5, 49.0, 17.2, True, "dach_nordics"),
    ("LI", "Liechtenstein", 47.0, 9.5, 47.3, 9.6, True, "dach_nordics"),
    ("ES", "Spain", 36.0, -9.4, 43.8, 3.4, True, "iberia"),
    ("ES", "Canary Islands", 27.6, -18.2, 29.5, -13.4, True, "iberia"),
    ("PT", "Portugal", 36.9, -9.5, 42.2, -6.2, True, "iberia"),
    ("PT", "Azores", 36.9, -31.3, 39.8, -25.0, True, "iberia"),
    ("PT", "Madeira", 32.6, -17.3, 32.9, -16.2, True, "iberia"),
    ("AD", "Andorra", 42.4, 1.4, 42.7, 1.8, True, "iberia"),
    ("IT", "Italy", 36.6, 6.6, 47.1, 18.5, True, "italy_adriatic"),
    ("SM", "San Marino", 43.9, 12.4, 44.0, 12.5, True, "italy_adriatic"),
    ("MT", "Malta", 35.8, 14.2, 36.1, 14.6, True, "italy_adriatic"),
    ("GR", "Greece", 34.8, 19.3, 41.8, 28.3, True, "italy_adriatic"),
    ("SI", "Slovenia", 45.4, 13.4, 46.9, 16.6, True, "italy_adriatic"),
    ("HR", "Croatia", 42.4, 13.5, 46.6, 19.4, True, "italy_adriatic"),
    ("BA", "Bosnia and Herzegovina", 42.5, 15.7, 45.3, 19.6, True, "italy_adriatic"),
    ("ME", "Montenegro", 41.8, 18.4, 43.6, 20.4, True, "italy_adriatic"),
    ("AL", "Albania", 39.6, 19.3, 42.7, 21.1, True, "italy_adriatic"),
    ("DK", "Denmark", 54.5, 8.0, 57.8, 12.7, True, "dach_nordics"),
    ("NO", "Norway", 57.9, 4.5, 71.2, 31.2, True, "dach_nordics"),
    ("SE", "Sweden", 55.3, 11.0, 69.1, 24.2, True, "dach_nordics"),
    ("FI", "Finland", 59.7, 20.5, 70.1, 31.6, True, "dach_nordics"),
    ("IS", "Iceland", 63.3, -24.6, 66.6, -13.5, True, "dach_nordics"),
    ("PL", "Poland", 49.0, 14.1, 54.9, 24.2, True, "eastern_europe"),
    ("CZ", "Czechia", 48.5, 12.1, 51.1, 18.9, True, "eastern_europe"),
    ("SK", "Slovakia", 47.7, 16.8, 49.6, 22.6, True, "eastern_europe"),
    ("HU", "Hungary", 45.7, 16.1, 48.6, 22.9, True, "eastern_europe"),
    ("RO", "Romania", 43.6, 20.2, 48.3, 29.7, True, "eastern_europe"),
    ("BG", "Bulgaria", 41.2, 22.4, 44.2, 28.6, True, "eastern_europe"),
    ("RS", "Serbia", 42.2, 18.8, 46.2, 23.0, True, "eastern_europe"),
    ("MK", "North Macedonia", 40.8, 20.4, 42.4, 23.0, True, "eastern_europe"),
    ("XK", "Kosovo", 41.8, 20.0, 43.3, 21.8, True, "eastern_europe"),
    ("MD", "Moldova", 45.4, 26.6, 48.5, 30.2, True, "eastern_europe"),
    ("UA", "Ukraine", 44.3, 22.1, 52.4, 40.2, True, "eastern_europe"),
    ("BY", "Belarus", 51.3, 23.2, 56.2, 32.8, True, "eastern_europe"),
    ("EE", "Estonia", 57.5, 21.8, 59.7, 28.2, True, "eastern_europe"),
    ("LV", "Latvia", 55.6, 20.9, 58.1, 28.2, True, "eastern_europe"),
    ("LT", "Lithuania", 53.9, 20.9, 56.5, 26.9, True, "eastern_europe"),
    ("CY", "Cyprus", 34.5, 32.2, 35.7, 34.6, True, "eastern_europe"),
    ("RU", "European Russia", 44.0, 28.0, 69.5, 60.0, True, "eastern_europe"),
    # Rest of the planet, roughly west to east after Europe.
    ("US", "United States", 24.4, -125.0, 49.4, -66.9, False, ""),
    ("US", "Alaska", 51.2, -179.0, 71.4, -129.9, False, "us_west"),
    ("US", "Hawaii", 18.9, -160.3, 22.3, -154.8, False, "us_west"),
    ("CA", "Canada", 41.7, -141.0, 70.0, -52.6, False, "canada"),
    ("MX", "Mexico", 14.5, -118.4, 32.7, -86.7, False, "mexico_caribbean"),
    ("GT", "Guatemala", 13.7, -92.3, 17.8, -88.2, False, "mexico_caribbean"),
    ("BZ", "Belize", 15.9, -89.3, 18.5, -87.4, False, "mexico_caribbean"),
    ("HN", "Honduras", 13.0, -89.4, 16.5, -83.1, False, "mexico_caribbean"),
    ("SV", "El Salvador", 13.1, -90.1, 14.5, -87.7, False, "mexico_caribbean"),
    ("NI", "Nicaragua", 10.7, -87.7, 15.0, -82.6, False, "mexico_caribbean"),
    ("CR", "Costa Rica", 8.0, -85.9, 11.2, -82.5, False, "mexico_caribbean"),
    ("PA", "Panama", 7.2, -83.0, 9.6, -77.2, False, "mexico_caribbean"),
    ("CU", "Cuba", 19.8, -84.9, 23.3, -74.1, False, "mexico_caribbean"),
    ("HT", "Haiti", 18.0, -74.5, 20.1, -71.6, False, "mexico_caribbean"),
    ("DO", "Dominican Republic", 17.5, -72.0, 19.9, -68.3, False, "mexico_caribbean"),
    ("JM", "Jamaica", 17.7, -78.4, 18.5, -76.2, False, "mexico_caribbean"),
    ("TT", "Trinidad and Tobago", 10.0, -61.9, 11.4, -60.5, False, "mexico_caribbean"),
    ("BS", "Bahamas", 20.9, -79.3, 27.3, -72.7, False, "mexico_caribbean"),
    ("BB", "Barbados", 13.0, -59.7, 13.3, -59.4, False, "mexico_caribbean"),
    ("PR", "Puerto Rico", 17.9, -67.3, 18.5, -65.2, False, "mexico_caribbean"),
    ("BR", "Brazil", -33.8, -73.9, 5.3, -34.7, False, "latin_america"),
    ("AR", "Argentina", -55.1, -73.6, -21.8, -53.6, False, "latin_america"),
    ("CL", "Chile", -55.9, -75.7, -17.5, -66.4, False, "latin_america"),
    ("CO", "Colombia", -4.2, -79.0, 12.5, -66.8, False, "latin_america"),
    ("PE", "Peru", -18.4, -81.4, -0.0, -68.7, False, "latin_america"),
    ("VE", "Venezuela", 0.6, -73.4, 12.2, -59.8, False, "latin_america"),
    ("EC", "Ecuador", -5.0, -81.1, 1.5, -75.2, False, "latin_america"),
    ("BO", "Bolivia", -22.9, -69.6, -9.7, -57.5, False, "latin_america"),
    ("PY", "Paraguay", -27.6, -62.6, -19.3, -54.2, False, "latin_america"),
    ("UY", "Uruguay", -35.0, -58.4, -30.1, -53.1, False, "latin_america"),
    ("GY", "Guyana", 1.2, -61.4, 8.4, -56.5, False, "latin_america"),
    ("SR", "Suriname", 1.8, -58.1, 6.0, -53.9, False, "latin_america"),
    ("MA", "Morocco", 27.6, -13.2, 35.9, -1.0, False, "mena"),
    ("DZ", "Algeria", 18.9, -8.7, 37.1, 12.0, False, "mena"),
    ("TN", "Tunisia", 30.2, 7.5, 37.5, 11.6, False, "mena"),
    ("LY", "Libya", 19.5, 9.3, 33.2, 25.2, False, "mena"),
    ("EG", "Egypt", 22.0, 24.7, 31.7, 36.9, False, "mena"),
    ("TR", "Turkey", 35.8, 26.0, 42.1, 44.8, False, "mena"),
    ("IL", "Israel", 29.5, 34.2, 33.3, 35.9, False, "mena"),
    ("PS", "Palestine", 31.2, 34.2, 32.6, 35.6, False, "mena"),
    ("JO", "Jordan", 29.2, 34.9, 33.4, 39.3, False, "mena"),
    ("LB", "Lebanon", 33.0, 35.1, 34.7, 36.6, False, "mena"),
    ("SY", "Syria", 32.3, 35.7, 37.3, 42.4, False, "mena"),
    ("IQ", "Iraq", 29.1, 38.8, 37.4, 48.6, False, "mena"),
    ("IR", "Iran", 25.0, 44.0, 39.8, 63.3, False, "mena"),
    ("SA", "Saudi Arabia", 16.3, 34.5, 32.2, 55.7, False, "mena"),
    ("YE", "Yemen", 12.1, 42.5, 19.0, 54.5, False, "mena"),
    ("OM", "Oman", 16.6, 52.0, 26.4, 59.8, False, "mena"),
    ("AE", "United Arab Emirates", 22.6, 51.5, 26.1, 56.4, False, "mena"),
    ("QA", "Qatar", 24.5, 50.7, 26.2, 51.6, False, "mena"),
    ("KW", "Kuwait", 28.5, 46.5, 30.1, 48.5, False, "mena"),
    ("BH", "Bahrain", 25.8, 50.4, 26.3, 50.7, False, "mena"),
    ("SD", "Sudan", 8.7, 21.8, 22.2, 38.6, False, "west_east_africa"),
    ("SS", "South Sudan", 3.5, 24.1, 12.2, 35.9, False, "west_east_africa"),
    ("SN", "Senegal", 12.3, -17.5, 16.7, -11.3, False, "west_east_africa"),
    ("GM", "Gambia", 13.1, -16.8, 13.8, -13.8, False, "west_east_africa"),
    ("GN", "Guinea", 7.2, -15.1, 12.7, -7.6, False, "west_east_africa"),
    ("SL", "Sierra Leone", 6.9, -13.3, 10.0, -10.3, False, "west_east_africa"),
    ("LR", "Liberia", 4.3, -11.5, 8.6, -7.4, False, "west_east_africa"),
    ("CI", "Cote d'Ivoire", 4.3, -8.6, 10.7, -2.5, False, "west_east_africa"),
    ("GH", "Ghana", 4.7, -3.3, 11.2, 1.2, False, "west_east_africa"),
    ("TG", "Togo", 6.1, -0.1, 11.1, 1.8, False, "west_east_africa"),
    ("BJ", "Benin", 6.2, 0.8, 12.4, 3.8, False, "west_east_africa"),
    ("NG", "Nigeria", 4.2, 2.7, 13.9, 14.7, False, "west_east_africa"),
    ("CM", "Cameroon", 1.7, 8.5, 13.1, 16.2, False, "west_east_africa"),
    ("KE", "Kenya", -4.7, 33.9, 5.0, 41.9, False, "west_east_africa"),
    ("TZ", "Tanzania", -11.7, 29.3, -0.9, 40.4, False, "west_east_africa"),
    ("UG", "Uganda", -1.5, 29.6, 4.2, 35.0, False, "west_east_africa"),
    ("RW", "Rwanda", -2.8, 28.8, -1.0, 30.9, False, "west_east_africa"),
    ("ET", "Ethiopia", 3.4, 33.0, 14.9, 48.0, False, "west_east_africa"),
    ("SO", "Somalia", -1.7, 40.9, 12.0, 51.4, False, "west_east_africa"),
    ("ZA", "South Africa", -34.8, 16.4, -22.1, 32.9, False, "southern_africa"),
    ("NA", "Namibia", -28.9, 11.7, -16.9, 25.3, False, "southern_africa"),
    ("BW", "Botswana", -26.9, 19.9, -17.8, 29.4, False, "southern_africa"),
    ("ZW", "Zimbabwe", -22.4, 25.2, -15.6, 33.1, False, "southern_africa"),
    ("ZM", "Zambia", -18.1, 22.0, -8.2, 33.7, False, "southern_africa"),
    ("MW", "Malawi", -17.1, 32.7, -9.4, 35.9, False, "southern_africa"),
    ("MZ", "Mozambique", -26.9, 30.2, -10.5, 40.8, False, "southern_africa"),
    ("LS", "Lesotho", -30.7, 27.0, -28.6, 29.5, False, "southern_africa"),
    ("SZ", "Eswatini", -27.3, 30.8, -25.7, 32.1, False, "southern_africa"),
    ("MG", "Madagascar", -25.6, 43.2, -11.9, 50.5, False, "southern_africa"),
    ("MU", "Mauritius", -20.5, 57.3, -19.9, 57.8, False, "southern_africa"),
    ("PK", "Pakistan", 23.7, 60.9, 37.1, 77.1, False, "east_south_asia"),
    ("IN", "India", 6.7, 68.1, 35.5, 97.4, False, "east_south_asia"),
    ("NP", "Nepal", 26.3, 80.0, 30.4, 88.2, False, "east_south_asia"),
    ("BD", "Bangladesh", 20.7, 88.0, 26.6, 92.7, False, "east_south_asia"),
    ("LK", "Sri Lanka", 5.9, 79.6, 9.8, 81.9, False, "east_south_asia"),
    ("CN", "China", 18.1, 73.5, 53.6, 134.8, False, "east_south_asia"),
    ("MN", "Mongolia", 41.6, 87.7, 52.1, 119.9, False, "east_south_asia"),
    ("JP", "Japan", 24.2, 122.9, 45.5, 145.8, False, "east_south_asia"),
    ("KR", "South Korea", 33.1, 124.6, 38.6, 129.6, False, "east_south_asia"),
    ("KP", "North Korea", 37.6, 124.2, 43.0, 130.7, False, "east_south_asia"),
    ("TW", "Taiwan", 21.9, 120.0, 25.3, 122.0, False, "east_south_asia"),
    ("HK", "Hong Kong", 22.1, 113.8, 22.6, 114.4, False, "east_south_asia"),
    ("KZ", "Kazakhstan", 40.6, 46.5, 55.4, 87.3, False, "east_south_asia"),
    ("UZ", "Uzbekistan", 37.2, 56.0, 45.6, 73.1, False, "east_south_asia"),
    ("KG", "Kyrgyzstan", 39.2, 69.2, 43.3, 80.3, False, "east_south_asia"),
    ("MM", "Myanmar", 9.6, 92.2, 28.5, 101.2, False, "se_asia"),
    ("TH", "Thailand", 5.6, 97.3, 20.5, 105.6, False, "se_asia"),
    ("LA", "Laos", 13.9, 100.1, 22.5, 107.7, False, "se_asia"),
    ("KH", "Cambodia", 10.4, 102.3, 14.7, 107.6, False, "se_asia"),
    ("VN", "Vietnam", 8.4, 102.1, 23.4, 109.5, False, "se_asia"),
    ("MY", "Malaysia", 0.8, 99.6, 7.4, 119.3, False, "se_asia"),
    ("SG", "Singapore", 1.2, 103.6, 1.5, 104.1, False, "se_asia"),
    ("ID", "Indonesia", -11.0, 95.0, 6.1, 141.0, False, "se_asia"),
    ("PH", "Philippines", 4.6, 116.9, 21.1, 126.6, False, "se_asia"),
    ("AU", "Australia", -43.6, 113.1, -10.7, 153.6, False, "australia"),
    ("NZ", "New Zealand", -47.3, 166.4, -34.4, 178.6, False, "pacific"),
    ("PG", "Papua New Guinea", -11.7, 140.8, -1.3, 156.0, False, "pacific"),
    ("FJ", "Fiji", -19.2, 176.9, -16.0, 180.0, False, "pacific"),
    ("SB", "Solomon Islands", -11.9, 155.5, -6.6, 167.0, False, "pacific"),
    ("VU", "Vanuatu", -20.3, 166.5, -13.0, 170.2, False, "pacific"),
    ("WS", "Samoa", -14.1, -172.8, -13.4, -171.4, False, "pacific"),
    ("TO", "Tonga", -21.5, -175.4, -15.6, -173.9, False, "pacific"),
    ("RU", "Asian Russia", 41.2, 60.0, 77.0, 180.0, False, "east_south_asia"),
    ("GL", "Greenland", 59.7, -73.0, 83.6, -12.2, False, "other"),
)


@dataclass(frozen=True)
class OutreachTile:
    """One Overpass bounding box the weekly job can finish on its own."""

    tile_id: str
    country_code: str
    name: str
    south: float
    west: float
    north: float
    east: float
    europe: bool
    lead_zone: str
    depth: int = 0
    retries: int = 0

    @property
    def label(self) -> str:
        return self.name

    @property
    def span(self) -> float:
        return max(self.north - self.south, self.east - self.west)


def _zone_for(country: str, fallback: str, west: float, east: float) -> str:
    if fallback:
        return fallback
    if country == "US":
        centre = (west + east) / 2.0
        return "us_west" if centre < -100 else "us_east"
    return "other"


def _split_bbox(
    south: float,
    west: float,
    north: float,
    east: float,
) -> list[tuple[float, float, float, float]]:
    lat_span = max(north - south, 0.1)
    lon_span = max(east - west, 0.1)
    lat_n = max(1, math.ceil(lat_span / MAX_SPAN_DEGREES - 1e-9))
    lon_n = max(1, math.ceil(lon_span / MAX_SPAN_DEGREES - 1e-9))
    while lat_n * lon_n > MAX_TILES_PER_COUNTRY:
        if lon_n >= lat_n and lon_n > 1:
            trial_lat, trial_lon = lat_n, lon_n - 1
        elif lat_n > 1:
            trial_lat, trial_lon = lat_n - 1, lon_n
        else:
            break
        if (
            lat_span / trial_lat > MAX_CELL_DEGREES
            or lon_span / trial_lon > MAX_CELL_DEGREES
        ):
            break
        lat_n, lon_n = trial_lat, trial_lon
    lat_step = lat_span / lat_n
    lon_step = lon_span / lon_n
    boxes: list[tuple[float, float, float, float]] = []
    for lat_index in range(lat_n):
        for lon_index in range(lon_n):
            boxes.append(
                (
                    south + lat_index * lat_step,
                    west + lon_index * lon_step,
                    south + (lat_index + 1) * lat_step,
                    west + (lon_index + 1) * lon_step,
                )
            )
    return boxes


def _build_tiles() -> tuple[OutreachTile, ...]:
    counts: dict[str, int] = {}
    tiles: list[OutreachTile] = []
    for code, name, south, west, north, east, europe, zone in _REGIONS:
        if south >= north or west >= east:
            raise RuntimeError(f"Bad bbox for {code} {name}")
        parts = _split_bbox(south, west, north, east)
        for part_south, part_west, part_north, part_east in parts:
            index = counts.get(code, 0)
            counts[code] = index + 1
            tile_name = name if len(parts) == 1 else f"{name} {index + 1}"
            tiles.append(
                OutreachTile(
                    tile_id=f"{code.lower()}-{index}",
                    country_code=code,
                    name=tile_name,
                    south=round(part_south, 4),
                    west=round(part_west, 4),
                    north=round(part_north, 4),
                    east=round(part_east, 4),
                    europe=europe,
                    lead_zone=_zone_for(code, zone, part_west, part_east),
                )
            )
    return tuple(tiles)


TILES: tuple[OutreachTile, ...] = _build_tiles()


def tiles_for_zone(zone_id: str) -> list[OutreachTile]:
    """Tiles whose coarse zone matches, used by the one-zone dry run."""
    key = zone_id.strip().lower()
    return [tile for tile in TILES if tile.lead_zone == key]


def tile_by_id(tile_id: str) -> OutreachTile | None:
    key = tile_id.strip().lower()
    for tile in TILES:
        if tile.tile_id == key:
            return tile
    return None


def slice_tiles(
    start: int,
    limit: int,
    tiles: tuple[OutreachTile, ...] | list[OutreachTile] | None = None,
) -> tuple[list[OutreachTile], int, bool]:
    """Take up to ``limit`` tiles from ``start``.

    Crossing the end finishes the cycle and stops. The next run begins at 0.
    Returns the batch, the next index, and whether the cycle wrapped.
    """
    sequence = list(TILES if tiles is None else tiles)
    if not sequence or limit <= 0:
        return [], 0, False
    count = len(sequence)
    index = start % count
    batch: list[OutreachTile] = []
    wrapped = False
    while len(batch) < limit:
        batch.append(sequence[index])
        index += 1
        if index >= count:
            index = 0
            wrapped = True
            break
    return batch, index, wrapped


def quadrants(tile: OutreachTile) -> list[OutreachTile]:
    """Four child bboxes. Empty when the tile cannot get smaller."""
    mid_lat = (tile.south + tile.north) / 2.0
    mid_lon = (tile.west + tile.east) / 2.0
    boxes = (
        (tile.south, tile.west, mid_lat, mid_lon, "sw"),
        (tile.south, mid_lon, mid_lat, tile.east, "se"),
        (mid_lat, tile.west, tile.north, mid_lon, "nw"),
        (mid_lat, mid_lon, tile.north, tile.east, "ne"),
    )
    children: list[OutreachTile] = []
    for south, west, north, east, suffix in boxes:
        if south >= north or west >= east:
            continue
        child_span = max(north - south, east - west)
        if child_span <= 0:
            continue
        children.append(
            OutreachTile(
                tile_id=f"{tile.tile_id}-{suffix}",
                country_code=tile.country_code,
                name=f"{tile.name} {suffix}",
                south=round(south, 4),
                west=round(west, 4),
                north=round(north, 4),
                east=round(east, 4),
                europe=tile.europe,
                lead_zone=tile.lead_zone,
                depth=tile.depth + 1,
            )
        )
    return children


def should_subdivide(
    tile: OutreachTile,
    *,
    result_count: int,
    timed_out: bool,
    max_places: int,
) -> bool:
    """Split when the bbox is still large and the query saturated or timed out.

    A full ``out tags N`` page means Overpass truncated the country. Those
    elements are not kept; the four children are queried instead.
    """
    if tile.depth >= MAX_SPLIT_DEPTH or tile.span <= MIN_SUBTILE_SPAN:
        return False
    if timed_out:
        return True
    return result_count >= max(int(max_places), 1)


def encode_pending(tiles: list[OutreachTile]) -> str:
    """One sub-tile per line. Small enough for the single checkpoint row."""
    lines: list[str] = []
    for tile in tiles:
        name = tile.name.replace("|", "/")
        lines.append(
            "|".join(
                (
                    tile.tile_id,
                    tile.country_code,
                    name,
                    f"{tile.south:.4f}",
                    f"{tile.west:.4f}",
                    f"{tile.north:.4f}",
                    f"{tile.east:.4f}",
                    "1" if tile.europe else "0",
                    tile.lead_zone,
                    str(tile.depth),
                    str(tile.retries),
                )
            )
        )
    return "\n".join(lines)


def decode_pending(raw: str | None) -> list[OutreachTile]:
    tiles: list[OutreachTile] = []
    for line in (raw or "").splitlines():
        parts = line.split("|")
        if len(parts) == 10:
            tile_id, country, name, south, west, north, east, europe, zone, depth = parts
            retries = "0"
        elif len(parts) == 11:
            tile_id, country, name, south, west, north, east, europe, zone, depth, retries = parts
        else:
            continue
        tiles.append(
            OutreachTile(
                tile_id=tile_id,
                country_code=country,
                name=name,
                south=float(south),
                west=float(west),
                north=float(north),
                east=float(east),
                europe=europe == "1",
                lead_zone=zone,
                depth=int(depth),
                retries=int(retries),
            )
        )
    return tiles


@dataclass(frozen=True)
class TileProgress:
    index: int
    pending: tuple[OutreachTile, ...]
    cycle: int
    advanced: bool
    retrying: bool
    dropped: bool


def record_tile_outcome(
    *,
    index: int,
    pending: list[OutreachTile],
    cycle: int,
    tile: OutreachTile,
    blocks_static: bool,
    success: bool,
    tile_count: int,
) -> TileProgress:
    """Move the checkpoint only past a tile that was queried successfully.

    A failure stays at the front of ``pending`` and does not move ``index``,
    so the next run retries it first. After ``MAX_TILE_RETRIES`` the tile is
    dropped and, if it was blocking the static cursor, the cursor moves on.
    """
    if success:
        if blocks_static and tile_count:
            nxt = (index + 1) % tile_count
            wrapped = nxt == 0 and not pending
            return TileProgress(
                nxt,
                tuple(pending),
                cycle + 1 if wrapped else cycle,
                True,
                False,
                False,
            )
        return TileProgress(index, tuple(pending), cycle, False, False, False)

    retries = tile.retries + 1
    if retries > MAX_TILE_RETRIES:
        rest = [item for item in pending if item.tile_id != tile.tile_id]
        if blocks_static and tile_count:
            nxt = (index + 1) % tile_count
            wrapped = nxt == 0 and not rest
            return TileProgress(
                nxt,
                tuple(rest),
                cycle + 1 if wrapped else cycle,
                True,
                False,
                True,
            )
        return TileProgress(index, tuple(rest), cycle, False, False, True)

    retried = replace_tile_retries(tile, retries)
    rest = [item for item in pending if item.tile_id != tile.tile_id]
    return TileProgress(index, (retried, *rest), cycle, False, True, False)


def replace_tile_retries(tile: OutreachTile, retries: int) -> OutreachTile:
    return OutreachTile(
        tile_id=tile.tile_id,
        country_code=tile.country_code,
        name=tile.name,
        south=tile.south,
        west=tile.west,
        north=tile.north,
        east=tile.east,
        europe=tile.europe,
        lead_zone=tile.lead_zone,
        depth=tile.depth,
        retries=retries,
    )


def venues_for_fetch(
    pending: int,
    remaining_fetches: int,
    *,
    fetches_per_place: int = FETCHES_PER_PLACE,
) -> tuple[int, int]:
    """How many website lookups to start, and how many wait for a later week.

    A place is started only when the whole homepage plus contact/about budget
    is still available, so a partial crawl is not thrown away.
    """
    cost = max(int(fetches_per_place), 1)
    slots = max(int(remaining_fetches), 0) // cost
    start = min(max(int(pending), 0), slots)
    return start, max(int(pending), 0) - start


def europe_prefix_length(tiles: tuple[OutreachTile, ...] | None = None) -> int:
    sequence = TILES if tiles is None else tiles
    for index, tile in enumerate(sequence):
        if not tile.europe:
            return index
    return len(sequence)
