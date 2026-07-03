import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


def load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_exists_and_has_expected_size():
    catalog = load_catalog()
    assert len(catalog) >= 300


def test_recommendation_contract_fields_are_present():
    item = load_catalog()[0]
    assert {"name", "url", "test_type"}.issubset(item)
    assert item["name"]
    assert item["url"].startswith("https://www.shl.com/products/product-catalog/view/")
    assert item["test_type"]


def test_catalog_names_and_urls_are_unique():
    catalog = load_catalog()
    names = [item["name"] for item in catalog]
    urls = [item["url"] for item in catalog]
    assert len(names) == len(set(names))
    assert len(urls) == len(set(urls))


def test_java_and_opq_examples_are_findable():
    catalog = load_catalog()
    names = {item["name"] for item in catalog}
    assert "Java 8 (New)" in names
    assert "Occupational Personality Questionnaire OPQ32r" in names
