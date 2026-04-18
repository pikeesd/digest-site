import time
import hashlib
import os
import feedparser
import requests
from rss_collector import run_full_collector

# Файл, где храним отпечаток последней важной новости
HASH_FILE = "top_story_hash.txt"


def get_current_top_story():
    """Заглядывает в самый жирный источник (например, CoinDesk), чтобы увидеть заголовок"""
    try:
        # Берем один надежный источник для проверки "пульса"
        url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        resp = requests.get(url, timeout=10)
        feed = feedparser.parse(resp.content)
        if feed.entries:
            # Возвращаем заголовок самой первой новости
            return feed.entries[0].title
    except:
        return None
    return None


def start_monitoring():
    print("👀 News Monitor active. Checking every 15 mins...")

    while True:
        current_story = get_current_top_story()
        if not current_story:
            time.sleep(60)
            continue

        current_hash = hashlib.md5(current_story.encode()).hexdigest()

        # Читаем старый хеш
        last_hash = ""
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, "r") as f:
                last_hash = f.read().strip()

        # СРАВНЕНИЕ
        if current_hash != last_hash:
            print(f"🔥 NEW TOP STORY: {current_story}")
            print("🚀 Triggering AI Digest update...")

            # Запускаем твой основной код
            run_full_collector()

            # Сохраняем новый хеш
            with open(HASH_FILE, "w") as f:
                f.write(current_hash)
        else:
            print("😴 No major changes in top news.")

        # Ждем 15 минут перед следующей проверкой
        time.sleep(900)


if __name__ == "__main__":
    start_monitoring()
