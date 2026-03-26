#!/usr/bin/env python3
"""Simple RSS collector for crypto news feeds."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import feedparser


def load_sources(path: Path) -> List[Dict[str, str]]:
    """Load RSS sources from a JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"sources file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in sources file: {path}") from exc

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("'sources' must be a list")

    normalized: List[Dict[str, str]] = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if name and url:
            normalized.append({"name": name, "url": url})
    return normalized


def _extract_entry_text(entry: Any, key: str) -> str:
    value = entry.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _extract_published(entry: Any) -> str:
    for key in ("published", "updated", "pubDate"):
        text = _extract_entry_text(entry, key)
        if text:
            return text
    return ""


def normalize_entry(entry: Any, source_name: str) -> Dict[str, str]:
    """Normalize a feedparser entry into a consistent structure."""
    return {
        "title": _extract_entry_text(entry, "title"),
        "link": _extract_entry_text(entry, "link"),
        "summary": _extract_entry_text(entry, "summary") or _extract_entry_text(entry, "description"),
        "published": _extract_published(entry),
        "source": source_name,
    }


def collect_from_source(name: str, url: str) -> List[Dict[str, str]]:
    """Collect and normalize entries from a single RSS source."""
    feed = feedparser.parse(url)
    if getattr(feed, "bozo", False):
        # Skip malformed feeds but keep the collector running.
        return []

    entries = getattr(feed, "entries", []) or []
    return [normalize_entry(entry, name) for entry in entries]


def collect_all(sources: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Collect and normalize articles from all sources."""
    all_articles: List[Dict[str, str]] = []
    for src in sources:
        name = src.get("name", "").strip()
        url = src.get("url", "").strip()
        if not name or not url:
            continue
        try:
            all_articles.extend(collect_from_source(name, url))
        except Exception:
            # Skip broken feeds and continue.
            continue
    return all_articles


def main(argv: Optional[List[str]] = None) -> int:
    args = argv or sys.argv[1:]
    sources_path = Path(args[0]) if args else Path("sources.json")

    try:
        sources = load_sources(sources_path)
    except Exception as exc:
        print(f"error: {exc}")
        return 1

    articles = collect_all(sources)

    print(f"Collected {len(articles)} articles")
    for item in articles[:5]:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
