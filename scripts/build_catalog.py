"""Normalize the pasted SHL product catalog into retrieval-ready JSON.

The raw file is kept as the source of truth. This script adds stable fields
that the API can consume without scraping or guessing at request time.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TYPE_CODE_BY_CATEGORY = {
    "Ability & Aptitude": "A",
    "Assessment Exercises": "E",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}

STOP_ALIAS_WORDS = {"NEW", "AND", "THE", "FOR", "WITH", "PLUS", "REPORT", "SHL"}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_duration_minutes(duration: str) -> int | None:
    match = re.search(r"\d+", duration or "")
    return int(match.group(0)) if match else None


def normalize_bool(value: Any) -> bool | None:
    text = clean_text(value).lower()
    if text in {"yes", "true", "1"}:
        return True
    if text in {"no", "false", "0"}:
        return False
    return None


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[-1] if parts else ""


def acronym(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    letters = [word[0].upper() for word in words if word.upper() not in STOP_ALIAS_WORDS]
    return "".join(letters)


def extract_aliases(name: str, description: str, slug: str) -> list[str]:
    aliases: set[str] = set()

    for value in re.findall(r"\(([^)]+)\)", name):
        cleaned = clean_text(value)
        if cleaned and cleaned.lower() != "new":
            aliases.add(cleaned)

    generated = acronym(name)
    if 2 <= len(generated) <= 8:
        aliases.add(generated)

    for token in re.findall(r"\b[A-Z][A-Z0-9]{1,7}r?\b", f"{name} {description}"):
        if token.upper() not in STOP_ALIAS_WORDS:
            aliases.add(token)

    compact_name = re.sub(r"[^A-Za-z0-9]+", "", name)
    if 2 <= len(compact_name) <= 20 and any(char.isdigit() for char in compact_name):
        aliases.add(compact_name)

    if slug:
        aliases.add(slug.replace("-", " "))

    aliases.discard(name)
    return sorted(aliases, key=lambda item: (len(item), item.lower()))


def normalize_item(raw: dict[str, Any], index: int) -> dict[str, Any]:
    name = clean_text(raw.get("name"))
    url = clean_text(raw.get("link"))
    description = clean_text(raw.get("description"))
    categories = [clean_text(item) for item in raw.get("keys", []) if clean_text(item)]
    type_codes = [TYPE_CODE_BY_CATEGORY[item] for item in categories if item in TYPE_CODE_BY_CATEGORY]
    slug = slug_from_url(url)
    job_levels = [clean_text(item) for item in raw.get("job_levels", []) if clean_text(item)]
    languages = [clean_text(item) for item in raw.get("languages", []) if clean_text(item)]
    duration_text = clean_text(raw.get("duration"))
    aliases = extract_aliases(name, description, slug)

    search_parts = [
        name,
        description,
        " ".join(aliases),
        " ".join(categories),
        " ".join(job_levels),
        " ".join(languages),
        duration_text,
        slug.replace("-", " "),
    ]

    return {
        "id": clean_text(raw.get("entity_id")) or f"generated-{index}",
        "name": name,
        "url": url,
        "description": description,
        "job_levels": job_levels,
        "languages": languages,
        "duration_text": duration_text,
        "duration_minutes": parse_duration_minutes(duration_text),
        "remote_testing": normalize_bool(raw.get("remote")),
        "adaptive": normalize_bool(raw.get("adaptive")),
        "categories": categories,
        "test_type": type_codes[0] if type_codes else "",
        "test_type_codes": type_codes,
        "aliases": aliases,
        "search_text": clean_text(" ".join(search_parts)).lower(),
        "source": {
            "entity_id": clean_text(raw.get("entity_id")),
            "status": clean_text(raw.get("status")),
            "scraped_at": clean_text(raw.get("scraped_at")),
        },
    }


def validate_catalog(items: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_names: set[str] = set()
    seen_urls: set[str] = set()

    for item in items:
        if not item["name"]:
            errors.append(f"Missing name for id={item['id']}")
        if not item["url"]:
            errors.append(f"Missing URL for {item['name']}")
        if item["url"] and "shl.com/products/product-catalog/view/" not in item["url"]:
            errors.append(f"Unexpected URL for {item['name']}: {item['url']}")
        if item["name"] in seen_names:
            errors.append(f"Duplicate name: {item['name']}")
        if item["url"] in seen_urls:
            errors.append(f"Duplicate URL: {item['url']}")
        if item["categories"] and not item["test_type_codes"]:
            errors.append(f"Unmapped category for {item['name']}: {item['categories']}")
        seen_names.add(item["name"])
        seen_urls.add(item["url"])

    return errors


def build(raw_path: Path, catalog_path: Path, meta_path: Path) -> None:
    raw_items = json.loads(raw_path.read_text(encoding="utf-8"), strict=False)
    if not isinstance(raw_items, list):
        raise ValueError("Raw catalog must be a JSON array.")

    normalized = [
        normalize_item(item, index)
        for index, item in enumerate(raw_items, start=1)
        if clean_text(item.get("status")).lower() == "ok"
    ]
    normalized.sort(key=lambda item: item["name"].lower())

    errors = validate_catalog(normalized)
    if errors:
        raise ValueError("Catalog validation failed:\n" + "\n".join(errors[:25]))

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    category_counts = Counter(category for item in normalized for category in item["categories"])
    type_counts = Counter(code for item in normalized for code in item["test_type_codes"])
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(raw_path),
        "source_count": len(raw_items),
        "catalog_count": len(normalized),
        "category_counts": dict(sorted(category_counts.items())),
        "test_type_counts": dict(sorted(type_counts.items())),
        "duration_known_count": sum(1 for item in normalized if item["duration_minutes"] is not None),
        "remote_testing_known_count": sum(1 for item in normalized if item["remote_testing"] is not None),
        "adaptive_known_count": sum(1 for item in normalized if item["adaptive"] is not None),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized SHL catalog JSON.")
    parser.add_argument("--raw", type=Path, default=Path("shl_product_catalog.json"))
    parser.add_argument("--out", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--meta", type=Path, default=Path("data/catalog_meta.json"))
    args = parser.parse_args()
    build(args.raw, args.out, args.meta)


if __name__ == "__main__":
    main()
