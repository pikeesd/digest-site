#!/usr/bin/env python3
"""Hybrid RSS collector for crypto news feeds with AI Classification & SQLite Cache."""

from __future__ import annotations
from datetime import datetime, timedelta

import email.utils
import json
import sys
import os
import re
import requests
import sqlite3
import hashlib
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import feedparser

# --- ИНИЦИАЛИЗАЦИЯ OPENAI И КЭША ---
try:
    from openai import OpenAI

    # Теперь скрипт автоматически подтянет ключ из .env
    API_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=API_KEY) if API_KEY else None
except ImportError:
    client = None
    print(
        "⚠️ Библиотека openai не установлена. Будет использован старый метод классификации."
    )

DB_FILE = "news_cache.db"


def init_db():
    """Создает базу данных для кэширования ответов AI."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS category_cache (
            hash_id TEXT PRIMARY KEY,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


def get_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_from_cache(text_hash: str) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT category FROM category_cache WHERE hash_id = ?", (text_hash,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def save_to_cache(text_hash: str, category: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO category_cache (hash_id, category) VALUES (?, ?)",
        (text_hash, category),
    )
    conn.commit()
    conn.close()


# --- СТАРЫЕ КОНСТАНТЫ И ФУНКЦИИ (без изменений) ---

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


def parse_date(date_str):
    try:
        return datetime(*email.utils.parsedate(date_str)[:6])
    except:
        return None


def load_sources(path: Path) -> List[Dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Ошибка загрузки sources: {exc}")

    return [
        {"name": s.get("name", "").strip(), "url": s.get("url", "").strip()}
        for s in data.get("sources", [])
        if isinstance(s, dict)
    ]


def _extract_entry_text(entry: Any, key: str) -> str:
    return str(entry.get(key, "")).strip() if entry.get(key) is not None else ""


def _extract_published(entry: Any) -> str:
    for key in ("published", "updated", "pubDate"):
        text = _extract_entry_text(entry, key)
        if text:
            return text
    return ""


def clean_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def normalize_entry(entry: Any, source_name: str) -> Dict[str, str]:
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


def collect_from_source(name: str, url: str) -> List[Dict[str, str]]:
    try:
        response = requests.get(url, timeout=5)
        feed = feedparser.parse(response.content)
        if getattr(feed, "bozo", False):
            return []
        return [normalize_entry(entry, name) for entry in getattr(feed, "entries", [])]
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []


def collect_all(sources: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    all_articles = []
    for src in sources:
        if src.get("name") and src.get("url"):
            all_articles.extend(collect_from_source(src["name"], src["url"]))
    return all_articles


def filter_recent(articles, hours=24):
    """Фильтрует новости за последние X часов."""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=hours)
    filtered = []
    for a in articles:
        dt = parse_date(a.get("published", ""))
        if not dt or dt >= cutoff:
            filtered.append(a)
    return filtered


def normalize_title(title: str) -> str:
    title = title.lower()
    title = title.replace("btc", "bitcoin").replace("eth", "ethereum")
    title = re.sub(r"(\d+)k", lambda m: str(int(m.group(1)) * 1000), title)
    title = re.sub(r"[^a-z0-9 ]", "", title)
    return " ".join([w for w in title.split() if w not in STOPWORDS])


def is_aggregate(title: str) -> bool:
    title = title.lower()
    if len(title) > 140 or title.count(",") >= 3:
        return True
    separators = sum(title.count(sep) for sep in ["|", " - ", " — ", ":"])
    if separators >= 3:
        return True
    patterns = [
        "morning report",
        "crypto news",
        "roundup",
        "heres what happened",
        "what happened",
        "daily",
        "weekly",
        "recap",
        "top stories",
    ]
    if any(p in title for p in patterns):
        return True
    return False


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


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
    t1, t2 = normalize_title(article1["title"]), normalize_title(article2["title"])
    overlap = len(set(t1.split()) & set(t2.split()))
    ent_match = (
        len(extract_entities(article1["title"]) & extract_entities(article2["title"]))
        > 0
    )

    if similarity(t1, t2) > 0.75 or overlap >= 4 or (ent_match and overlap >= 3):
        return True
    return False


def deduplicate_articles(articles: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique, seen = [], set()
    for article in articles:
        title = normalize_title(article["title"])
        if title not in seen:
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
                group["items"].sort(
                    key=lambda x: (
                        x.get("is_aggregate", False),
                        -len(x.get("summary", "")),
                    )
                )
                group["main"] = group["items"][0]
                added = True
                break
        if not added:
            groups.append({"main": article, "items": [article]})
    return groups


def shorten(text, max_len=200):
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len].rsplit(" ", 1)[0] + "..."


# --- НОВЫЙ БЛОК: ГИБРИДНАЯ КЛАССИФИКАЦИЯ ---


def detect_category_fallback(text: str) -> str:
    """Старая логика на правилах (запасной вариант)."""
    text = text.lower()
    if any(w in text for w in ["hack", "exploit", "breach", "attack"]):
        return "Security"
    if any(w in text for w in ["sec", "law", "regulation", "government"]):
        return "Regulation"
    if any(w in text for w in ["ai", "artificial intelligence", "openai"]):
        return "AI"
    if any(w in text for w in ["defi", "staking", "yield", "protocol"]):
        return "DeFi"
    if any(w in text for w in ["bitcoin", "btc", "price", "market", "eth"]):
        return "Markets"
    return "Other"


def get_category_hybrid(title: str, summary: str) -> str:
    """Гибридная классификация: Кэш -> AI -> Fallback."""
    combined_text = f"Title: {title}\nSummary: {summary}"
    text_hash = get_hash(title)  # Хешируем только тайтл, он обычно уникален для группы

    # 1. Проверяем кэш
    cached = get_from_cache(text_hash)
    if cached:
        return cached

    # 2. Если нет OpenAI, используем Fallback
    if not client:
        cat = detect_category_fallback(combined_text)
        save_to_cache(text_hash, cat)
        return cat

    # 3. Запрос к OpenAI
    system_prompt = """
    Identify and classify crypto news into EXACTLY ONE category. 
    Strictly follow these definitions and priorities:

    1. SECURITY: Critical focus on hacks, exploits, rug pulls, smart contract vulnerabilities, or stolen funds. 
       - EXCLUDE: General risk warnings or legal cases (those go to Regulation).

    2. REGULATION: Any interaction with government, law, or authority. SEC, CFTC, lawsuits (e.g., Ripple vs SEC), ETF approvals, taxes, and policy changes.
       - PRIORITY: If a news piece is about a court case involving a DeFi protocol, it MUST be 'Regulation', not 'DeFi'.

    3. AI (Artificial Intelligence): Strictly technology-centric. LLMs, NVIDIA/AI chips in crypto, decentralized compute (Render, Akash), AI agents, or Machine Learning.
       - STRICT RULE: DO NOT classify general market analysis or price pumps as 'AI' just because they mention 'algorithmic trading'. If it's about Bitcoin's price drop, it is 'Markets'.

    4. DEFI: Focus on yield farming, DEXs (Uniswap, PancakeSwap), lending (Aave, Compound), and liquid staking (Lido). 
       - EXCLUDE: If it's a hack of a DeFi protocol, it's 'Security'. If it's a lawsuit against a DeFi dev, it's 'Regulation'.

    5. MARKETS: Price action (BTC/ETH pumps/dumps), market sentiment, institutional adoption, exchange listings, and macro-financial trends.
       - RULE: This is the catch-all for price-related news that isn't a legal or security issue.

    6. OTHER: General partnerships, rebranding, community events, or non-crypto tech.

    OUTPUT RULES:
    - Return ONLY valid JSON: {"category": "CategoryName"}
    - Do not explain your choice.
    - If a news piece fits two categories, pick the one with the LOWER number in the priority list above.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text},
            ],
            response_format={"type": "json_object"},
            timeout=10,
        )

        result = json.loads(response.choices[0].message.content)
        category = result.get("category", "Other")

        # Валидация
        valid_categories = ["Security", "Regulation", "AI", "DeFi", "Markets", "Other"]
        if category not in valid_categories:
            category = "Other"

        # Сохраняем в кэш
        save_to_cache(text_hash, category)
        return category

    except Exception as e:
        print(f"⚠️ Ошибка OpenAI: {e}. Используем fallback.")
        cat = detect_category_fallback(combined_text)
        return cat


# --- СБОРКА ДАЙДЖЕСТА ---


def build_digest(groups):
    digest = []
    for group in groups:
        main = group["main"]
        sources = list(set(item["source"] for item in group["items"]))
        clean_summ = clean_html(main.get("summary", ""))
        short_summary = shorten(clean_summ)

        # Вызываем гибридную систему!
        category = get_category_hybrid(main.get("title", ""), clean_summ)

        item = {
            "title": main["title"],
            "category": category,
            "summary": {
                "main": short_summary if short_summary else main["title"],
            },
            "sources": sources,
            "count": len(group["items"]),
            "links": [
                {"source": i["source"], "link": i["link"]} for i in group["items"]
            ],
            "published": main.get("published", ""),
        }
        digest.append(item)
    return digest


def main(argv: Optional[List[str]] = None) -> int:
    init_db()  # Инициализируем кэш

    args = argv or sys.argv[1:]
    sources_path = Path(args[0]) if args else Path("sources.json")

    try:
        sources = load_sources(sources_path)
    except Exception as exc:
        print(f"error: {exc}")
        return 1

    print("Fetching feeds...")
    raw_articles = collect_all(sources)

    # 1. Фильтр по времени (оставляем только за последние 24 часа для свежести)
    articles = filter_recent(raw_articles, hours=24)
    raw_count = len(articles)

    # 2. Группировка
    groups = group_articles(articles)

    # 3. ОТСЕВ МУСОРА: Выбрасываем группы-агрегаторы до отправки в AI
    clean_groups = [
        g
        for g in groups
        if not g["main"].get("is_aggregate", False) and g["main"]["title"]
    ]

    print(f"Raw (last 24h): {raw_count}")
    print(f"Grouped & Cleaned (no aggregates): {len(clean_groups)}")

    # 4. Классификация и сборка дайджеста
    digest = build_digest(clean_groups)

    # Сортируем по важности (количеству источников)
    digest = sorted(digest, key=lambda x: x["count"], reverse=True)

    # 5. Формируем финальный JSON для сайта с метаданными
    final_output = {
        "metadata": {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_news": len(digest),
            "timeframe_hours": 24,
        },
        "news": digest,
    }

    # Сохраняем для фронтенда
    with open("digest.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print("\n✅ Успешно! Файл digest.json обновлен.")
    print(f"Время обновления (UTC): {final_output['metadata']['last_updated']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
