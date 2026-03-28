"""
metrics.py — Metrics Engine.

Читает необработанные события из supply_events,
считает метрики и сохраняет в таблицу metrics.

Запуск:
  python -m analytics.metrics
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import Base, SupplyEvent, Metric

# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("metrics")

# ---------------------------------------------------------------------------
# Конфигурация БД
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Формулы расчёта метрик
# ---------------------------------------------------------------------------

def calc_days_of_stock(stock: float, daily_usage: float) -> float:
    """
    Сколько дней хватит текущего запаса.

    Примеры:
      stock=120, daily_usage=30 → 4.0 дня
      stock=50,  daily_usage=20 → 2.5 дня  ← тревожно
    """
    if daily_usage <= 0:
        return 0.0
    return round(stock / daily_usage, 2)


def calc_delivery_risk(delivery_delay: float) -> float:
    """
    Риск от задержки поставки. Шкала 0.0 — 1.0.

    0 дней  → 0.0  (нет задержки)
    3 дня   → 0.5  (умеренный риск)
    5+ дней → 1.0  (критично)
    """
    if delivery_delay <= 0:
        return 0.0
    elif delivery_delay >= 5:
        return 1.0
    else:
        return round(delivery_delay / 5, 2)


def calc_risk_score(days_of_stock: float, delivery_risk: float) -> float:
    """
    Итоговый риск-скор. Взвешенная сумма двух факторов.

    Веса:
      - запас (days_of_stock) — 60% влияния
      - задержка поставки     — 40% влияния

    Логика запаса:
      >= 7 дней  → риск 0.0  (всё хорошо)
      3-7 дней   → риск 0.0-0.5 (умеренно)
      < 3 дней   → риск 0.5-1.0 (опасно)
      0 дней     → риск 1.0  (дефицит)
    """
    # Риск по запасу: чем меньше дней — тем выше риск
    if days_of_stock >= 7:
        stock_risk = 0.0
    elif days_of_stock <= 0:
        stock_risk = 1.0
    else:
        stock_risk = round(1 - (days_of_stock / 7), 2)

    # Взвешенная сумма
    score = round(stock_risk * 0.6 + delivery_risk * 0.4, 2)
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def process_event(db, event: SupplyEvent) -> Metric:
    """
    Считает метрики для одного события и сохраняет в БД.
    """
    days = calc_days_of_stock(event.stock, event.daily_usage)
    d_risk = calc_delivery_risk(event.delivery_delay)
    score = calc_risk_score(days, d_risk)

    metric = Metric(
        event_id=event.id,
        warehouse_id=event.warehouse_id,
        product=event.product,
        days_of_stock=days,
        risk_score=score,
    )
    db.add(metric)
    return metric


def run(only_new: bool = True):
    """
    Обрабатываем события из supply_events.

    only_new=True  → только события без метрик (по умолчанию)
    only_new=False → пересчитываем все события
    """
    db = SessionLocal()
    processed = 0
    skipped = 0

    try:
        # Получаем события
        query = db.query(SupplyEvent)

        if only_new:
            # Только события у которых ещё нет метрик
            existing_event_ids = {m.event_id for m in db.query(Metric).all()}
            events = [e for e in query.all() if e.id not in existing_event_ids]
            log.info(f"Найдено {len(events)} новых событий для обработки")
        else:
            events = query.all()
            log.info(f"Пересчёт всех {len(events)} событий")

        for event in events:
            metric = process_event(db, event)
            log.info(
                f"✅ Метрики | id={event.id} | "
                f"{event.warehouse_id}/{event.product} | "
                f"days_of_stock={metric.days_of_stock} | "
                f"risk_score={metric.risk_score}"
            )
            processed += 1

        db.commit()
        log.info(f"📊 Готово | Обработано: {processed} | Пропущено: {skipped}")

    except Exception as e:
        db.rollback()
        log.error(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()

    return {"processed": processed, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Metrics Engine")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Пересчитать метрики для всех событий (не только новых)"
    )
    args = parser.parse_args()

    log.info("=" * 50)
    log.info("📐 Metrics Engine запущен")
    log.info("=" * 50)

    run(only_new=not args.all)
