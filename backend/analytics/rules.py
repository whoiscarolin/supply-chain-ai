"""
rules.py — Rule Engine.

Читает метрики из таблицы metrics,
применяет правила и генерирует алерты в таблицу alerts.

Правила:
  DEFICIT          — days_of_stock < 3  → CRITICAL
  DELAY            — delivery_delay > 3 → HIGH
  UNSTABLE_SUPPLIER — 2+ задержки у поставщика → MEDIUM

Запуск:
  python -m backend.analytics.rules
"""

import logging
import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models import SupplyEvent, Metric, Alert

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rules")

# ---------------------------------------------------------------------------
# БД
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Пороговые значения (легко менять)
# ---------------------------------------------------------------------------

DEFICIT_THRESHOLD = 3.0       # дней запаса — ниже этого CRITICAL
DELAY_THRESHOLD = 3.0         # дней задержки — выше этого HIGH
UNSTABLE_SUPPLIER_COUNT = 2   # кол-во задержек у поставщика → MEDIUM

# ---------------------------------------------------------------------------
# Правила
# ---------------------------------------------------------------------------

def rule_deficit(metric: Metric, event: SupplyEvent) -> Alert | None:
    """
    Правило 1: Дефицит запаса.
    days_of_stock < 3 → CRITICAL
    """
    if metric.days_of_stock < DEFICIT_THRESHOLD:
        return Alert(
            event_id=event.id,
            warehouse_id=event.warehouse_id,
            product=event.product,
            alert_type="DEFICIT",
            severity="CRITICAL",
            message=(
                f"Критический дефицит на складе {event.warehouse_id}: "
                f"товар '{event.product}' закончится через "
                f"{metric.days_of_stock} дн. "
                f"(остаток={event.stock}, потребление={event.daily_usage}/день)"
            ),
        )
    return None


def rule_delay(metric: Metric, event: SupplyEvent) -> Alert | None:
    """
    Правило 2: Задержка поставки.
    delivery_delay > 3 → HIGH
    """
    if event.delivery_delay > DELAY_THRESHOLD:
        return Alert(
            event_id=event.id,
            warehouse_id=event.warehouse_id,
            product=event.product,
            alert_type="DELAY",
            severity="HIGH",
            message=(
                f"Задержка поставки на складе {event.warehouse_id}: "
                f"товар '{event.product}' задержан на {event.delivery_delay} дн. "
                f"(поставщик: {event.supplier})"
            ),
        )
    return None


def rule_unstable_supplier(events: list[SupplyEvent]) -> list[Alert]:
    """
    Правило 3: Нестабильный поставщик.
    Если у одного поставщика 2+ событий с задержкой > 0 → MEDIUM
    """
    alerts = []

    # Считаем задержки по каждому поставщику
    supplier_delays = defaultdict(list)
    for event in events:
        if event.delivery_delay > 0:
            supplier_delays[event.supplier].append(event)

    for supplier, delayed_events in supplier_delays.items():
        if len(delayed_events) >= UNSTABLE_SUPPLIER_COUNT:
            # Берём последнее событие для алерта
            last_event = delayed_events[-1]
            avg_delay = round(
                sum(e.delivery_delay for e in delayed_events) / len(delayed_events), 1
            )
            alerts.append(Alert(
                event_id=last_event.id,
                warehouse_id=last_event.warehouse_id,
                product=last_event.product,
                alert_type="UNSTABLE_SUPPLIER",
                severity="MEDIUM",
                message=(
                    f"Нестабильный поставщик '{supplier}': "
                    f"{len(delayed_events)} задержек, "
                    f"средняя задержка {avg_delay} дн."
                ),
            ))

    return alerts


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def run(only_new: bool = True):
    """
    Применяем все правила и сохраняем алерты в БД.
    only_new=True → только события без алертов
    """
    db = SessionLocal()
    created = 0

    try:
        # Получаем метрики вместе с событиями
        metrics = db.query(Metric).all()
        events_by_id = {e.id: e for e in db.query(SupplyEvent).all()}

        if only_new:
            existing_event_ids = {a.event_id for a in db.query(Alert).all()}
            metrics = [m for m in metrics if m.event_id not in existing_event_ids]

        log.info(f"Обрабатываем {len(metrics)} метрик...")

        new_alerts = []

        # Правила 1 и 2 — на каждое событие отдельно
        for metric in metrics:
            event = events_by_id.get(metric.event_id)
            if not event:
                continue

            for rule_fn in [rule_deficit, rule_delay]:
                alert = rule_fn(metric, event)
                if alert:
                    new_alerts.append(alert)
                    log.info(
                        f"🚨 [{alert.severity}] {alert.alert_type} | "
                        f"{alert.warehouse_id}/{alert.product} | "
                        f"{alert.message}"
                    )

        # Правило 3 — по всем событиям сразу
        all_events = list(events_by_id.values())
        unstable_alerts = rule_unstable_supplier(all_events)
        for alert in unstable_alerts:
            new_alerts.append(alert)
            log.info(
                f"⚠️  [{alert.severity}] {alert.alert_type} | "
                f"{alert.message}"
            )

        # Сохраняем все алерты
        for alert in new_alerts:
            db.add(alert)
            created += 1

        db.commit()
        log.info(f"📋 Готово | Создано алертов: {created}")

    except Exception as e:
        db.rollback()
        log.error(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()

    return {"created": created}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rule Engine")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Применить правила ко всем событиям (не только новым)"
    )
    args = parser.parse_args()

    log.info("=" * 50)
    log.info("⚙️  Rule Engine запущен")
    log.info("=" * 50)

    run(only_new=not args.all)
