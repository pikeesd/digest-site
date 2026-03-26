from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rss_collector import (
    load_sources,
    collect_all,
    group_articles,
    build_digest
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "API is running"}


@app.get("/api/news")
def get_news():
    sources_path = Path(__file__).resolve().parent / "sources.json"
    sources = load_sources(sources_path)
    articles = collect_all(sources)
    grouped = group_articles(articles)
    digest = build_digest(grouped)
    return digest
