import json
import time
import threading
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем главную функцию из коллектора
# Убедись, что в rss_collector.py функция называется именно run_full_collector
from rss_collector import run_full_collector as run_collector

app = FastAPI(title="Peak Digest API")

# --- 1. НАСТРОЙКА CORS (Строгая версия для digestpeak.com) ---
origins = [
    "https://digestpeak.com",
    "http://digestpeak.com",
    "https://www.digestpeak.com",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Пути к файлам
BASE_DIR = Path(__file__).resolve().parent
DIGEST_FILE = BASE_DIR / "digest.json"
SOURCES_FILE = BASE_DIR / "sources.json"


@app.get("/")
def root():
    return {
        "status": "API is running",
        "timestamp": time.time(),
        "info": "Peak Digest Backend",
    }


@app.get("/api/news")
def get_news():
    """Отдает готовые новости фронтенду из файла digest.json"""
    if DIGEST_FILE.exists():
        try:
            with open(DIGEST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            return {"error": "File is currently being updated", "news": []}
        except Exception as e:
            return {"error": f"Internal error: {str(e)}", "news": []}
    else:
        return {
            "error": "News digest is being generated. Please wait.",
            "news": [],
            "metadata": {"briefing": "Initial generation in progress..."},
        }


# --- 2. ФОНОВЫЙ ВОРКЕР (ОБНОВЛЕНИЕ КАЖДЫЕ 4 ЧАСА) ---
def scheduler():
    """Фоновый поток, который раз в 4 часа запускает полную пересборку новостей и ИИ-брифинга"""
    # Ждем пару секунд после старта сервера, чтобы не нагружать систему сразу
    time.sleep(5)

    while True:
        print(
            f"🔄 [{time.strftime('%H:%M:%S')}] Запуск планового сбора новостей и AI рекапа..."
        )
        try:
            # Запускаем коллектор. Передаем путь к sources.json как аргумент
            run_collector([str(SOURCES_FILE)])
            print(f"✅ [{time.strftime('%H:%M:%S')}] Обновление успешно завершено")
        except Exception as e:
            print(f"❌ [{time.strftime('%H:%M:%S')}] Ошибка в фоновом процессе: {e}")

        # Интервал 4 часа (4 * 3600 секунд)
        print("😴 Спим 4 часа до следующего обновления...")
        time.sleep(14400)


@app.on_event("startup")
def start_scheduler():
    """Запускает фоновый процесс при старте FastAPI"""
    # daemon=True гарантирует, что поток закроется при остановке сервера
    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()
