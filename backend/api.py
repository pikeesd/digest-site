from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rss_collector import (
    load_sources,
    collect_all,
    group_articles,
    build_digest,
)
from fastapi.middleware.cors import CORSMiddleware

import time
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "API is running"}


@app.get("/api/news")
def get_news():
    return news_cache


def update_news():
    global news_cache, last_update

    print("🔄 Updating news...")

    sources_path = Path(__file__).resolve().parent / "sources.json"
    sources = load_sources(sources_path)

    articles = collect_all(sources)
    print("ARTICLES COUNT:", len(articles))
    grouped = group_articles(articles)
    print("GROUPED COUNT:", len(grouped))
    digest = build_digest(grouped)

    news_cache = digest
    last_update = time.time()

    print("✅ News updated")


def scheduler():
    while True:
        update_news()
        time.sleep(600)  # каждые 10 минут


@app.on_event("startup")
def start_scheduler():
    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на старте ок, потом ограничим
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
