# 🗺️ ROADMAP — AI Decision Support System for Supply Chains

> Итоговый план разработки. Согласован 18.03.2026.

---

## Цель проекта

Создать систему, которая анализирует цепи поставок, выявляет проблемы,
объясняет причины и предлагает решения — с AI-слоем на Claude API.

---

## Стек технологий

| Слой | Технология |
|------|-----------|
| База данных | SQLite → PostgreSQL, SQLAlchemy, Alembic |
| API сервер | FastAPI, Pydantic, Uvicorn |
| Аналитика | Python, pandas, scipy |
| AI слой | Claude API (claude-sonnet) |
| Dashboard | Streamlit |
| DevOps | venv, requirements.txt, Docker (опционально) |

---

## Этапы разработки

### Этап 1 — База данных
- [ ] Создать `schema.sql`
- [ ] Таблицы: `supply_events`, `metrics`, `alerts`, `recommendations`
- [ ] Инициализация БД скриптом

### Этап 2 — API сервер
- [ ] FastAPI приложение
- [ ] `POST /data` — приём данных от узлов
- [ ] `GET /metrics` — получение метрик
- [ ] `GET /alerts` — получение алертов
- [ ] Pydantic схемы валидации

### Этап 3 — Node Simulator
- [ ] Скрипт `simulator.py`
- [ ] Генерация и отправка данных на API
- [ ] Использование `sample_data.json` как seed
- [ ] Режим: разовый запуск + loop

### Этап 4 — Metrics Engine
- [ ] Расчёт `days_of_stock = stock / daily_usage`
- [ ] Расчёт `delivery_delay` score
- [ ] Расчёт `risk_score`
- [ ] Сохранение метрик в БД

### Этап 5 — Rule Engine 🔥
- [ ] Правило: дефицит (`days_of_stock < 3` → CRITICAL)
- [ ] Правило: задержка (`delivery_delay > 3` → HIGH)
- [ ] Правило: нестабильный поставщик (2+ задержки → MEDIUM)
- [ ] Генерация алертов в БД

### Этап 6 — Decision Engine
- [ ] Объединение: data + metrics + rules
- [ ] Классификация проблем по приоритету
- [ ] Выбор решений из playbook
- [ ] Формирование контекста для AI

### Этап 6.5 — End-to-end тест ✅
- [ ] Прогнать `sample_data.json` через всю цепочку
- [ ] Проверить: данные → метрики → алерты → решения
- [ ] Убедиться что Dashboard получит корректные данные

### Этап 7 — Dashboard
- [ ] Streamlit интерфейс
- [ ] Таблица алертов с severity
- [ ] Метрики по складам
- [ ] Карточки рекомендаций

### Этап 8 — AI Layer
- [ ] Подключение Claude API
- [ ] Генерация объяснений на естественном языке
- [ ] Чат с системой (Q&A по цепи поставок)
- [ ] Промпты: контекст + проблема → объяснение + решение

### Этап 9 — Финал
- [ ] Рефакторинг кода
- [ ] `README.md` с описанием и запуском
- [ ] Скриншоты Dashboard
- [ ] Подготовка для LinkedIn

---

## Структура проекта (целевая)

```
supply-chain-ai/
├── README.md
├── ROADMAP.md
├── AGENT_MANIFESTO.md
├── REQUIREMENTS.md
├── requirements.txt
├── sample_data.json
│
├── db/
│   ├── schema.sql          # Этап 1
│   └── init_db.py
│
├── api/
│   ├── main.py             # Этап 2
│   ├── models.py
│   └── schemas.py
│
├── simulator/
│   └── simulator.py        # Этап 3
│
├── analytics/
│   ├── metrics.py          # Этап 4
│   ├── rules.py            # Этап 5
│   └── decision.py         # Этап 6
│
├── ai/
│   └── explainer.py        # Этап 8
│
└── dashboard/
    └── app.py              # Этап 7
```

---

## Прогресс

| Этап | Статус |
|------|--------|
| 1 — База данных | ⬜ В работе |
| 2 — API сервер | ⬜ Не начат |
| 3 — Node Simulator | ⬜ Не начат |
| 4 — Metrics Engine | ⬜ Не начат |
| 5 — Rule Engine | ⬜ Не начат |
| 6 — Decision Engine | ⬜ Не начат |
| 6.5 — E2E тест | ⬜ Не начат |
| 7 — Dashboard | ⬜ Не начат |
| 8 — AI Layer | ⬜ Не начат |
| 9 — Финал | ⬜ Не начат |

---

*Обновляй статус этапов по мере выполнения.*
