#!/usr/bin/env python3
"""Simple RSS collector for crypto news feeds."""

from __future__ import annotations
from datetime import datetime, timedelta

import email.utils
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


def parse_date(date_str):
    try:
        return datetime(*email.utils.parsedate(date_str)[:6])
    except:
        return None


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
    try:
        response = requests.get(url, timeout=5)
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []
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


def filter_recent(articles, hours=72):
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=hours)

    filtered = []

    for a in articles:
        dt = parse_date(a.get("published", ""))

        # если нет даты → можно оставить (или убрать позже)
        if not dt:
            filtered.append(a)
            continue

        if dt >= cutoff:
            filtered.append(a)

    return filtered


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


def is_aggregate(title: str) -> bool:
    title = title.lower()

    # 1. супер длинные заголовки
    if len(title) > 140:
        return True

    # 2. много частей → часто агрегаты
    separators = ["|", " - ", " — ", ":"]
    parts = sum(title.count(sep) for sep in separators)
    if parts >= 3:
        return True

    # 3. ключевые слова агрегатов
    patterns = [
        "morning report",
        "crypto news",
        "roundup",
        "here’s what happened",
        "heres what happened",
        "what happened",
        "daily",
        "weekly",
        "recap",
        "top stories",
    ]

    if any(p in title for p in patterns):
        return True

    # 4. слишком много разных тем (много запятых)
    if title.count(",") >= 3:
        return True

    return False


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


def is_similar(article1, article2):
    t1 = normalize_title(article1["title"])
    t2 = normalize_title(article2["title"])

    words1 = set(t1.split())
    words2 = set(t2.split())

    seq_score = similarity(t1, t2)
    overlap = len(words1 & words2)

    ent1 = extract_entities(article1["title"])
    ent2 = extract_entities(article2["title"])

    entity_match = len(ent1 & ent2) > 0

    # 🔥 НОВАЯ ЛОГИКА (строже)
    if seq_score > 0.75:
        return True

    if overlap >= 4:
        return True

    if entity_match and overlap >= 3:
        return True

    return False


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


def group_articles(articles):
    groups = []

    for article in articles:
        article["is_aggregate"] = is_aggregate(article["title"])

    for article in articles:
        added = False

        for group in groups:
            if is_similar(article, group["main"]):
                group["items"].append(article)

                # 🔥 СРАЗУ обновляем main
                group["items"].sort(
                    key=lambda x: (
                        x.get("is_aggregate", False),  # False лучше чем True
                        -len(x.get("summary", "")),  # потом по качеству
                    )
                )

                group["main"] = group["items"][0]

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

        raw_summary = main.get("summary", "")
        clean_summary = clean_html(raw_summary)
        short_summary = shorten(clean_summary)

        category = detect_category(main.get("title", "") + " " + clean_summary)

        item = {
            "title": main["title"],
            "summary": {
                "main": short_summary if short_summary else main["title"],
                "impact": "",
                "consequences": "",
            },
            "sources": sources,
            "count": len(set(item["source"] for item in group["items"])),
            "links": [
                {"source": item["source"], "link": item["link"]}
                for item in group["items"]
            ],
        }

        item["category"] = category

        digest.append(item)

    return digest


def format_for_output(digest):
    lines = []

    for item in digest:
        title = item["title"]
        count = item["count"]
        links = item.get("links", [])
        first_link = links[0]["link"] if links else ""

        lines.append(f"• {title} — {count} sources")
        if first_link:
            lines.append(f"  ↳ {first_link}")
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

    dedup_count = len(articles)

    groups = group_articles(articles)
    for g in groups:
        print("COLLECTOR LOADED")
        print("MAIN:", g["main"]["title"])
        print("COUNT:", len(g["items"]))
        print("---")

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


def clean_html(text):
    if not text:
        return ""

    # удалить HTML теги
    clean = re.sub(r"<.*?>", "", text)

    # убрать лишние пробелы
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean


def shorten(text, max_len=200):
    if not text:
        return ""

    if len(text) <= max_len:
        return text

    return text[:max_len].rsplit(" ", 1)[0] + "..."


def detect_category(text):
    text = text.lower()

    if any(word in text for word in ["bitcoin", "btc", "price", "market", "eth"]):
        return "Markets"
    if any(word in text for word in ["defi", "staking", "yield", "protocol"]):
        return "DeFi"
    if any(word in text for word in ["ai", "artificial intelligence", "openai"]):
        return "AI"
    if any(word in text for word in ["sec", "law", "regulation", "government"]):
        return "Regulation"
    if any(word in text for word in ["hack", "exploit", "breach", "attack"]):
        return "Security"

    return "Other"
