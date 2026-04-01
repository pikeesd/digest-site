import json
import time
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем только главную функцию из коллектора
from rss_collector import main as run_collector

app = FastAPI()

# 1. Настраиваем CORS ОДИН раз
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIGEST_FILE = Path(__file__).resolve().parent / "digest.json"


@app.get("/")
def root():
    return {"status": "API is running"}


@app.get("/api/news")
def get_news():
    """Отдает готовые новости фронтенду из файла"""
    if DIGEST_FILE.exists():
        with open(DIGEST_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                return {"error": "File is currently being updated", "news": []}
    else:
        return {"error": "News digest is being generated. Please wait.", "news": []}


def scheduler():
    """Фоновый воркер, который раз в 10 минут обновляет файл"""
    sources_path = Path(__file__).resolve().parent / "sources.json"

    while True:
        print("🔄 Запуск сбора новостей...")
        try:
            run_collector([str(sources_path)])
            print("✅ Сбор новостей завершен")
        except Exception as e:
            print(f"❌ Ошибка в фоновом процессе: {e}")

        # Спим 10 минут
        time.sleep(600)


@app.on_event("startup")
def start_scheduler():
    """Запускает фоновый процесс при старте FastAPI"""
    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()
