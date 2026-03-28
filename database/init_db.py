"""
init_db.py — инициализация базы данных
Этап 1: создаёт supply_chain.db из schema.sql

Путь: distributed-scm-ai/database/init_db.py

Запуск из корня проекта:
    python database/init_db.py
"""

import sqlite3
import os

# Пути — всё относительно этого файла
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DB_PATH     = os.path.join(BASE_DIR, "supply_chain.db")


def init_db():
    print(f"📦 Инициализация БД...")
    print(f"   schema : {SCHEMA_PATH}")
    print(f"   db     : {DB_PATH}")

    # Читаем схему
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    # Создаём / подключаемся к БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Применяем схему
    cursor.executescript(schema)
    conn.commit()

    # Проверяем результат
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\n✅ Таблицы созданы:")
    for t in tables:
        print(f"   • {t}")
    print(f"\n🚀 БД готова: database/supply_chain.db")


def get_connection():
    """
    Возвращает соединение с БД.
    Используется всеми модулями: api, analytics, dashboard.
    
    Пример:
        from database.init_db import get_connection
        conn = get_connection()
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False)


if __name__ == "__main__":
    init_db()
