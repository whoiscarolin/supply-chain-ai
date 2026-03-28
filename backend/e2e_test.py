"""
e2e_test.py — End-to-end тест всей системы.

Прогоняет данные через всю цепочку:
  1. Отправляет данные через симулятор
  2. Считает метрики
  3. Применяет правила
  4. Генерирует рекомендации
  5. Печатает итоговый отчёт

Запуск:
  python -m backend.e2e_test
  
Важно: API должен быть запущен перед стартом теста.
  uvicorn api.main:app --reload --port 8000
"""

import httpx
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.analytics.metrics import run as run_metrics
from backend.analytics.rules import run as run_rules
from backend.decision import run as run_decision, get_summary

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("e2e")

API_URL = "http://127.0.0.1:8000"
DATA_FILE = Path(__file__).parent.parent / "data" / "sample_data.json"

# ---------------------------------------------------------------------------
# Шаги теста
# ---------------------------------------------------------------------------

def step_check_api() -> bool:
    """Шаг 0 — проверяем что API запущен."""
    log.info("🔍 Шаг 0: Проверка API...")
    try:
        r = httpx.get(f"{API_URL}/health", timeout=3.0)
        if r.status_code == 200:
            log.info("✅ API доступен")
            return True
    except Exception:
        pass
    log.error("❌ API недоступен! Запусти: uvicorn api.main:app --reload --port 8000")
    return False


def step_send_data() -> int:
    """Шаг 1 — отправляем данные через API."""
    log.info("📦 Шаг 1: Отправка данных...")

    if not DATA_FILE.exists():
        log.error(f"❌ Файл не найден: {DATA_FILE}")
        return 0

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sent = 0
    with httpx.Client() as client:
        for event in data:
            try:
                r = client.post(f"{API_URL}/data", json=event, timeout=5.0)
                if r.status_code == 201:
                    result = r.json()
                    log.info(f"   ✅ id={result['id']} | {result['warehouse_id']}/{result['product']}")
                    sent += 1
                else:
                    log.warning(f"   ⚠️ Статус {r.status_code} для {event}")
                time.sleep(0.1)
            except Exception as e:
                log.error(f"   ❌ Ошибка: {e}")

    log.info(f"✅ Отправлено событий: {sent}")
    return sent


def step_run_metrics() -> dict:
    """Шаг 2 — считаем метрики."""
    log.info("📐 Шаг 2: Расчёт метрик...")
    result = run_metrics(only_new=True)
    log.info(f"✅ Метрик рассчитано: {result['processed']}")
    return result


def step_run_rules() -> dict:
    """Шаг 3 — применяем правила."""
    log.info("⚙️  Шаг 3: Применение правил...")
    result = run_rules(only_new=True)
    log.info(f"✅ Алертов создано: {result['created']}")
    return result


def step_run_decision() -> dict:
    """Шаг 4 — генерируем рекомендации."""
    log.info("🧠 Шаг 4: Генерация рекомендаций...")
    result = run_decision(only_new=True)
    log.info(f"✅ Рекомендаций создано: {result['created']}")
    return result


def step_print_report():
    """Шаг 5 — итоговый отчёт."""
    log.info("📊 Шаг 5: Итоговый отчёт")
    print()
    print("=" * 60)
    print("  ИТОГОВЫЙ ОТЧЁТ — Supply Chain AI")
    print("=" * 60)

    recs = get_summary()

    if not recs:
        print("  Рекомендаций нет — система в норме ✅")
    else:
        print(f"  Всего рекомендаций: {len(recs)}")
        print()

        priority_labels = {1: "🚨 КРИТИЧНО", 2: "⚠️  ВЫСОКИЙ", 3: "📋 СРЕДНИЙ", 4: "📌 НИЗКИЙ"}

        for rec in recs:
            label = priority_labels.get(rec["priority"], "📌")
            print(f"  {label} | {rec['warehouse_id']} / {rec['product']}")
            print(f"  Действие: {rec['action']}")
            print(f"  Причина:  {rec['reason'][:100]}...")
            print("-" * 60)

    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def main():
    print()
    log.info("=" * 60)
    log.info("🚀 E2E тест запущен")
    log.info("=" * 60)
    print()

    # Шаг 0: проверка API
    if not step_check_api():
        sys.exit(1)
    print()

    # Шаг 1: отправка данных
    sent = step_send_data()
    if sent == 0:
        log.error("❌ Нет данных для обработки")
        sys.exit(1)
    print()

    # Шаг 2: метрики
    step_run_metrics()
    print()

    # Шаг 3: правила
    step_run_rules()
    print()

    # Шаг 4: решения
    step_run_decision()
    print()

    # Шаг 5: отчёт
    step_print_report()

    log.info("✅ E2E тест завершён успешно!")


if __name__ == "__main__":
    main()
