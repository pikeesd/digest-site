#!/usr/bin/env python3
"""Simple RSS collector for crypto news feeds."""

from __future__ import annotations

import json
import sys
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import feedparser

STOPWORDS = {
    "the",
    "a",
    "of",
    "to",
    "as",
    "in",
    "on",
    "for",
    "with",
    "and",
    "is",
    "are",
    "after",
    "amid",
    "over",
    "under",
}

CATEGORIES = {
    "markets": ["bitcoin", "btc", "price", "etf", "market"],
    "defi": ["defi", "protocol", "staking", "yield"],
    "ai": ["ai", "agent", "model"],
    "regulation": ["sec", "law", "regulation", "tax"],
    "security": ["hack", "exploit", "phishing"],
}


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
        "summary": clean_html(
            _extract_entry_text(entry, "summary")
            or _extract_entry_text(entry, "description")
        ),
        "published": _extract_published(entry),
        "source": source_name,
    }


def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text)


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


def normalize_title(title: str) -> str:
    title = title.lower()

    #  нормализация крипто-терминов
    title = title.replace("btc", "bitcoin")
    title = title.replace("eth", "ethereum")

    #  нормализация чисел (70k → 70000)
    title = re.sub(r"(\d+)k", lambda m: str(int(m.group(1)) * 1000), title)

    #  убираем символы
    title = re.sub(r"[^a-z0-9 ]", "", title)

    words = title.split()

    #  убираем стоп-слова
    words = [w for w in words if w not in STOPWORDS]

    return " ".join(words)


def detect_category(title: str) -> str:
    title = title.lower()

    for category, keywords in CATEGORIES.items():
        if any(word in title for word in keywords):
            return category

    return "other"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def word_overlap(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())

    if not set_a or not set_b:
        return 0.0

    return len(set_a & set_b) / len(set_a | set_b)


def extract_keywords(title: str) -> set:
    title = normalize_title(title)
    words = set(title.split())

    # убираем короткие слова (шум)
    return {w for w in words if len(w) > 3}


def extract_entities(title: str) -> set:
    words = set(normalize_title(title).split())

    important = {
        "bitcoin",
        "ethereum",
        "sec",
        "etf",
        "fed",
        "coinbase",
        "binance",
        "crypto",
        "ai",
        "nasdaq",
        "ftx",
    }

    return words & important


def is_similar(title1: str, title2: str) -> bool:
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)

    words1 = set(t1.split())
    words2 = set(t2.split())

    # базовые метрики
    seq_score = similarity(t1, t2)
    overlap = len(words1 & words2)

    # 🔥 сущности
    ent1 = extract_entities(title1)
    ent2 = extract_entities(title2)

    entity_match = len(ent1 & ent2) > 0

    return seq_score > 0.65 or overlap >= 3 or entity_match and overlap >= 2


def deduplicate_articles(articles: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique = []
    seen = set()

    for article in articles:
        title = normalize_title(article["title"])

        # только почти точные дубли
        if title in seen:
            continue

        seen.add(title)
        unique.append(article)

    return unique


def group_articles(articles: List[Dict[str, str]]):
    groups = []

    for article in articles:
        title = article["title"]
        added = False

        for group in groups:
            group_title = group["main"]["title"]  # ← ОБЯЗАТЕЛЬНО

            if is_similar(title, group_title):
                group["items"].append(article)
                added = True
                break

        if not added:
            groups.append({"main": article, "items": [article]})

    return groups


def build_structured_summary(group):
    texts = []

    for item in group["items"]:
        if item.get("summary"):
            texts.append(item["summary"])

    full_text = " ".join(texts).lower()

    # очень простая логика (MVP)
    main = full_text[:200] if full_text else ""

    impact = ""
    if "price" in full_text or "market" in full_text:
        impact = "Affects market"

    consequences = ""
    if "risk" in full_text or "drop" in full_text:
        consequences = "May lead to volatility"

    return {"main": main, "impact": impact, "consequences": consequences}


def build_digest(groups):
    digest = []

    for group in groups:
        main = group["main"]
        sources = list(set(item["source"] for item in group["items"]))

        summary = build_structured_summary(group) or {
            "main": "",
            "impact": "",
            "consequences": "",
        }

        digest.append(
            {
                "title": main["title"],
                "summary": summary,
                "sources": sources,
                "count": len(group["items"]),
                "link": group["main"]["link"],
            }
        )

    return digest


def format_for_output(digest):
    lines = []

    for item in digest:
        title = item["title"]
        count = item["count"]

        lines.append(f"• {title} — {count} sources")
        lines.append(f"  ↳ {item['link']}")
        lines.append("")  # пустая строка для отступа

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    args = argv or sys.argv[1:]
    sources_path = Path(args[0]) if args else Path("sources.json")

    try:
        sources = load_sources(sources_path)
    except Exception as exc:
        print(f"error: {exc}")
        return 1

    articles = collect_all(sources)  # ← ВАЖНО

    raw_count = len(articles)

    articles = deduplicate_articles(articles)
    dedup_count = len(articles)

    groups = group_articles(articles)

    from collections import defaultdict

    grouped_by_category = defaultdict(list)

    for g in groups:
        title = g["main"]["title"]
        category = detect_category(title)

        grouped_by_category[category].append(g)

    groups = [g for g in groups if g["main"]["title"]]

    group_count = len(groups)

    print(f"Raw: {raw_count}")
    print(f"After dedup: {dedup_count}")
    print(f"Grouped: {group_count}")

    for category, items in grouped_by_category.items():
        digest = build_digest(items)
        digest = [d for d in digest if d["count"] >= 2]
        digest = sorted(digest, key=lambda x: x["count"], reverse=True)

        print(f"\n=== {category.upper()} ===")
        print(format_for_output(digest[:5]))

    # print(f"Final digest: {len(digest)} news")
    # print(f"Removed duplicates: {raw_count - dedup_count}")
    # print("Top news:")
    # print(digest[0]["title"])
    # print("\nTop 3 news:")
    # for item in digest[:3]:
    # print(f"- {item['title']} ({item['count']} sources)")

    # with open("digest.json", "w", encoding="utf-8") as f:
    # json.dump(digest, f, indent=2, ensure_ascii=False)

    # formatted = format_for_output(digest)

    # print("\n=== DIGEST ===\n")
    # print(formatted)


if __name__ == "__main__":
    raise SystemExit(main())
