"""
decision.py — Decision Engine.

Читает алерты из таблицы alerts,
выбирает решения из playbook и сохраняет в recommendations.

Playbook — это словарь готовых действий для каждого типа алерта:
  DEFICIT + CRITICAL → срочный заказ
  DELAY   + HIGH     → связаться с поставщиком
  UNSTABLE_SUPPLIER  → рассмотреть замену

Запуск:
  python -m backend.decision
"""

import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models import Alert, Recommendation

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("decision")

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
# Playbook — готовые решения для каждого типа проблемы
# ---------------------------------------------------------------------------

PLAYBOOK = {
    ("DEFICIT", "CRITICAL"): {
        "priority": 1,
        "action": (
            "🚨 СРОЧНО: Оформить экстренный заказ у резервного поставщика. "
            "Запас заканчивается менее чем через 3 дня. "
            "Рассмотреть временную переброску товара с соседних складов."
        ),
    },
    ("DEFICIT", "HIGH"): {
        "priority": 2,
        "action": (
            "⚠️ Ускорить оформление заказа у текущего поставщика. "
            "Проверить возможность частичной поставки в ближайшие 1-2 дня."
        ),
    },
    ("DELAY", "HIGH"): {
        "priority": 2,
        "action": (
            "📞 Связаться с поставщиком и запросить актуальный статус поставки. "
            "Если задержка подтверждается — активировать резервного поставщика. "
            "Уведомить смежные склады о возможной нехватке товара."
        ),
    },
    ("DELAY", "MEDIUM"): {
        "priority": 3,
        "action": (
            "📋 Зафиксировать задержку в системе мониторинга поставщика. "
            "Запросить объяснение причин задержки и новые сроки поставки."
        ),
    },
    ("UNSTABLE_SUPPLIER", "MEDIUM"): {
        "priority": 3,
        "action": (
            "🔍 Провести анализ надёжности поставщика за последние 30 дней. "
            "Рассмотреть диверсификацию: подключить второго поставщика для этой категории. "
            "Инициировать переговоры об SLA и штрафных санкциях за задержки."
        ),
    },
    ("UNSTABLE_SUPPLIER", "HIGH"): {
        "priority": 2,
        "action": (
            "⚠️ Немедленно начать поиск альтернативного поставщика. "
            "Текущий поставщик систематически нарушает сроки — риск для всей цепи поставок."
        ),
    },
}

# Действие по умолчанию если тип алерта не найден в playbook
DEFAULT_ACTION = {
    "priority": 4,
    "action": "📌 Взять ситуацию на контроль. Проанализировать данные и принять решение вручную.",
}


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def get_recommendation_for_alert(alert: Alert) -> dict:
    """
    Находим подходящее решение из playbook по типу и severity алерта.
    """
    key = (alert.alert_type, alert.severity)
    return PLAYBOOK.get(key, DEFAULT_ACTION)


def run(only_new: bool = True):
    """
    Обрабатываем алерты и создаём рекомендации.
    only_new=True → только алерты без рекомендаций
    """
    db = SessionLocal()
    created = 0

    try:
        alerts = db.query(Alert).all()

        if only_new:
            existing_event_ids = {r.event_id for r in db.query(Recommendation).all()}
            alerts = [a for a in alerts if a.event_id not in existing_event_ids]

        log.info(f"Обрабатываем {len(alerts)} алертов...")

        for alert in alerts:
            playbook_entry = get_recommendation_for_alert(alert)

            rec = Recommendation(
                event_id=alert.event_id,
                warehouse_id=alert.warehouse_id,
                product=alert.product,
                priority=playbook_entry["priority"],
                action=playbook_entry["action"],
                reason=f"Алерт: {alert.alert_type} [{alert.severity}] — {alert.message}",
                source="rules",
            )
            db.add(rec)

            log.info(
                f"✅ Рекомендация | приоритет={rec.priority} | "
                f"{rec.warehouse_id}/{rec.product} | "
                f"{rec.action[:60]}..."
            )
            created += 1

        db.commit()
        log.info(f"📋 Готово | Создано рекомендаций: {created}")

    except Exception as e:
        db.rollback()
        log.error(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()

    return {"created": created}


def get_summary() -> list[dict]:
    """
    Возвращает сводку рекомендаций отсортированную по приоритету.
    Используется Dashboard и AI Layer.
    """
    db = SessionLocal()
    try:
        recs = (
            db.query(Recommendation)
            .order_by(Recommendation.priority.asc())
            .all()
        )
        return [
            {
                "id": r.id,
                "priority": r.priority,
                "warehouse_id": r.warehouse_id,
                "product": r.product,
                "action": r.action,
                "reason": r.reason,
                "source": r.source,
                "created_at": str(r.created_at),
            }
            for r in recs
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Decision Engine")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Пересоздать рекомендации для всех алертов"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Показать текущие рекомендации без создания новых"
    )
    args = parser.parse_args()

    log.info("=" * 50)
    log.info("🧠 Decision Engine запущен")
    log.info("=" * 50)

    if args.summary:
        recs = get_summary()
        if not recs:
            log.info("Рекомендаций пока нет")
        for r in recs:
            log.info(f"[P{r['priority']}] {r['warehouse_id']}/{r['product']} → {r['action'][:80]}...")
    else:
        run(only_new=not args.all)
