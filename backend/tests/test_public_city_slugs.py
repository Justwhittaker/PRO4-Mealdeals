"""Public city URLs must match scrape catchment hubs, and reject sentinel names."""

from __future__ import annotations

import re
from pathlib import Path

from app.scrapers.catchment_hubs import CATCHMENT_HUBS, catchment_cities_for
from app.services.geo_names import is_placeholder_city
from app.services.scrape_runner import scrape_and_ingest_area

ROOT = Path(__file__).resolve().parents[2]
CATCHMENT_TS = ROOT / "frontend" / "lib" / "catchment-hubs.ts"

# Search Console "Not found (404)" hubs from the 4 Oct 2026 report, excluding
# /us/null (sentinel) and the removed Waiheke deal URL.
SEARCH_CONSOLE_HUBS = {
    "ar/san-juan-wine-country",
    "it/puglia-wine-country",
    "it/sicily-wine-country",
    "it/piedmont-wine-country",
    "au/barossa-valley",
    "de/pfalz-wine-country",
    "au/granite-belt",
    "it/umbria-wine-country",
    "au/mornington-peninsula",
    "pt/douro-wine-country",
    "it/tuscany-wine-country",
    "za/franschhoek",
    "mx/valle-de-guadalupe",
    "za/stellenbosch",
    "au/margaret-river",
    "au/mclaren-vale",
    "ca/niagara-wine-region",
    "cl/aconcagua-valley",
    "fr/champagne-wine-country",
    "ar/uco-valley",
    "fr/bordeaux-wine-country",
    "nz/hawkes-bay",
    "nz/north-canterbury",
    "fr/alsace-wine-country",
    "at/burgenland-wine-country",
    "au/mudgee",
    "cl/casablanca-valley",
    "ie/killarney",
    "it/alto-adige-wine-country",
    "si/podravje-wine-country",
    "pt/alentejo-wine-country",
    "au/coonawarra",
    "au/tamar-valley",
    "it/prosecco-wine-country",
}


def _slug(name: str) -> str:
    return "-".join(name.strip().lower().split())


def _country_slug(iso: str) -> str:
    return "uk" if iso == "GB" else iso.lower()


def _python_hub_paths() -> set[str]:
    return {
        f"{_country_slug(iso)}/{_slug(name)}"
        for iso, names in CATCHMENT_HUBS.items()
        for name in names
    }


def _typescript_hub_paths() -> set[str]:
    text = CATCHMENT_TS.read_text(encoding="utf-8")
    countries = re.findall(r'country: "([a-z]{2})"', text)
    cities = re.findall(r'city: "([a-z0-9-]+)"', text)
    assert len(countries) == len(cities)
    return {f"{country}/{city}" for country, city in zip(countries, cities)}


def test_search_console_404_hubs_are_catchment_hubs() -> None:
    paths = _python_hub_paths()
    missing = SEARCH_CONSOLE_HUBS - paths
    assert not missing
    assert "us/null" not in paths
    assert "ie/killarney" in paths
    assert "nz/waiheke-island" in paths


def test_frontend_catchment_catalog_matches_backend() -> None:
    assert _typescript_hub_paths() == _python_hub_paths()


def test_catchment_cities_are_added_once() -> None:
    extras = catchment_cities_for("AU", ["Sydney"])
    assert "Barossa Valley" in extras
    again = catchment_cities_for("AU", ["Sydney", "Barossa Valley"])
    assert "Barossa Valley" not in again


def test_placeholder_city_names() -> None:
    assert is_placeholder_city(None)
    assert is_placeholder_city("")
    assert is_placeholder_city("null")
    assert is_placeholder_city("Null")
    assert is_placeholder_city("NONE")
    assert is_placeholder_city("undefined")
    assert is_placeholder_city("Unknown")
    assert not is_placeholder_city("Douro Wine Country")
    assert not is_placeholder_city("Napa Valley")
    assert not is_placeholder_city("Killarney")


def test_placeholder_city_is_not_scraped() -> None:
    result = scrape_and_ingest_area("US", "null")
    assert result["skipped"] == "placeholder_city"
    assert result["ingested"] == 0
    assert result["discovered"] == 0
    assert result["city"] == "Null"
