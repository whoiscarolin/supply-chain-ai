"""
explainer.py — AI Layer на Claude API.

Генерирует объяснения проблем и рекомендации на естественном языке.
Поддерживает чат с системой (Q&A по цепи поставок).

Использование:
  from backend.explainer import explain_alert, chat

Запуск (демо):
  python -m backend.explainer
"""

import os
import sys
import logging
from dotenv import load_dotenv
import anthropic

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("explainer")

# ---------------------------------------------------------------------------
# Claude клиент
# ---------------------------------------------------------------------------

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Системный промпт
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — AI-аналитик системы управления цепями поставок.

Твоя задача:
- Объяснять проблемы в цепи поставок простым и чётким языком
- Давать конкретные actionable рекомендации
- Отвечать на вопросы менеджеров по логистике

Контекст системы:
- Система отслеживает склады, остатки товаров и задержки поставок
- Метрики: days_of_stock (дней запаса), risk_score (риск 0.0-1.0)
- Алерты: DEFICIT (дефицит), DELAY (задержка), UNSTABLE_SUPPLIER (нестабильный поставщик)
- Severity: CRITICAL > HIGH > MEDIUM > LOW

Правила ответа:
- Отвечай на русском языке
- Будь конкретным — называй склад, товар, цифры
- Давай 2-3 чётких шага что делать прямо сейчас
- Не используй общие фразы — только конкретика
- Ответ максимум 200 слов
"""

# ---------------------------------------------------------------------------
# Функции
# ---------------------------------------------------------------------------

def explain_alert(alert: dict, metric: dict = None) -> str:
    """
    Генерирует объяснение для конкретного алерта.

    alert  — словарь с полями: warehouse_id, product, alert_type, severity, message
    metric — опционально: days_of_stock, risk_score

    Возвращает текст объяснения от Claude.
    """
    # Формируем контекст
    context_parts = [
        f"Склад: {alert.get('warehouse_id')}",
        f"Товар: {alert.get('product')}",
        f"Тип проблемы: {alert.get('alert_type')}",
        f"Уровень: {alert.get('severity')}",
        f"Описание: {alert.get('message')}",
    ]

    if metric:
        context_parts += [
            f"Дней запаса: {metric.get('days_of_stock')}",
            f"Risk score: {metric.get('risk_score')}",
        ]

    context = "\n".join(context_parts)

    prompt = f"""Проанализируй следующую проблему в цепи поставок и объясни:
1. Что именно происходит и почему это критично
2. Какие последствия если не действовать прямо сейчас
3. Три конкретных шага которые нужно сделать сегодня

Данные проблемы:
{context}"""

    log.info(f"Запрос к Claude API для {alert.get('warehouse_id')}/{alert.get('product')}...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def explain_summary(alerts: list[dict], metrics: list[dict]) -> str:
    """
    Генерирует общую сводку по всем проблемам в системе.
    Используется для ежедневного отчёта.
    """
    if not alerts:
        return "Критических проблем в цепи поставок не обнаружено. Система работает в штатном режиме."

    # Берём только критичные и высокие алерты
    important = [a for a in alerts if a.get("severity") in ("CRITICAL", "HIGH")][:5]

    alerts_text = "\n".join([
        f"- [{a['severity']}] {a['warehouse_id']}/{a['product']}: {a['message']}"
        for a in important
    ])

    metrics_text = "\n".join([
        f"- {m['warehouse_id']}/{m['product']}: {m['days_of_stock']} дн. запаса, risk={m['risk_score']}"
        for m in metrics[:5]
    ]) if metrics else "Нет данных"

    prompt = f"""Сформируй краткий ежедневный отчёт по состоянию цепи поставок.

Активные алерты:
{alerts_text}

Метрики складов:
{metrics_text}

Отчёт должен содержать:
1. Общая оценка ситуации (1-2 предложения)
2. Топ-3 приоритетных проблемы которые требуют внимания сегодня
3. Общая рекомендация на день"""

    log.info("Генерация ежедневного отчёта...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def chat(question: str, context: dict = None) -> str:
    """
    Чат с системой — отвечает на вопросы по цепи поставок.

    question — вопрос менеджера
    context  — опционально: текущие алерты и метрики для контекста

    Пример:
        chat("Почему SPB в критическом состоянии?")
        chat("Что делать с поставщиком B?")
        chat("Какие склады под наибольшим риском?")
    """
    messages = []

    # Добавляем контекст системы если есть
    if context:
        alerts = context.get("alerts", [])
        metrics = context.get("metrics", [])

        context_text = "Текущее состояние системы:\n"

        if alerts:
            context_text += "\nАктивные алерты:\n"
            for a in alerts[:5]:
                context_text += f"  - [{a['severity']}] {a['warehouse_id']}/{a['product']}: {a['message']}\n"

        if metrics:
            context_text += "\nМетрики складов:\n"
            for m in metrics[:5]:
                context_text += f"  - {m['warehouse_id']}/{m['product']}: {m['days_of_stock']} дн., risk={m['risk_score']}\n"

        messages.append({
            "role": "user",
            "content": f"Вот текущее состояние системы:\n{context_text}\n\nТеперь ответь на мой вопрос: {question}"
        })
    else:
        messages.append({
            "role": "user",
            "content": question
        })

    log.info(f"Чат запрос: {question[:60]}...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return message.content[0].text


# ---------------------------------------------------------------------------
# Демо
# ---------------------------------------------------------------------------

def run_demo():
    """Демонстрация всех возможностей AI Layer."""

    print("\n" + "=" * 60)
    print("  AI LAYER — демонстрация")
    print("=" * 60)

    # Тестовые данные
    test_alert = {
        "warehouse_id": "SPB",
        "product": "router",
        "alert_type": "DEFICIT",
        "severity": "CRITICAL",
        "message": "Критический дефицит на складе SPB: товар 'router' закончится через 2.5 дн."
    }
    test_metric = {
        "days_of_stock": 2.5,
        "risk_score": 0.78
    }

    # Тест 1: объяснение алерта
    print("\n📍 Тест 1 — Объяснение алерта CRITICAL")
    print("-" * 60)
    explanation = explain_alert(test_alert, test_metric)
    print(explanation)

    # Тест 2: чат
    print("\n📍 Тест 2 — Чат с системой")
    print("-" * 60)
    answer = chat(
        question="Что делать с поставщиком B у которого постоянные задержки?",
        context={
            "alerts": [test_alert],
            "metrics": [{"warehouse_id": "SPB", "product": "router", **test_metric}]
        }
    )
    print(answer)

    # Тест 3: ежедневный отчёт
    print("\n📍 Тест 3 — Ежедневный отчёт")
    print("-" * 60)
    report = explain_summary(
        alerts=[test_alert],
        metrics=[{"warehouse_id": "SPB", "product": "router", **test_metric}]
    )
    print(report)

    print("\n" + "=" * 60)
    print("  ✅ AI Layer работает!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_demo()
