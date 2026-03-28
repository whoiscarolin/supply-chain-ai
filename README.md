# Supply Chain AI — Decision Support System

AI-система для анализа цепей поставок, выявления проблем и генерации рекомендаций на основе Claude API.

---

## Что умеет система

- Принимает данные от складских узлов через REST API
- Рассчитывает метрики: дней запаса, risk score
- Выявляет проблемы: дефицит, задержки, нестабильные поставщики
- Генерирует рекомендации из playbook
- Объясняет проблемы человеческим языком через Claude API
- Отвечает на вопросы менеджеров в реальном времени
- Отображает всё в интерактивном Dashboard

---

## Стек технологий

| Слой | Технология |
|------|-----------|
| База данных | SQLite, SQLAlchemy |
| API сервер | FastAPI, Pydantic, Uvicorn |
| Аналитика | Python, pandas |
| AI слой | Claude API (claude-sonnet-4) |
| Dashboard | Streamlit |

---

## Структура проекта

```
distributed scm ai/
├── api/                    # FastAPI сервер
│   ├── main.py             # Эндпоинты
│   ├── models.py           # ORM модели
│   └── schemas.py          # Pydantic схемы
├── backend/
│   ├── analytics/
│   │   ├── metrics.py      # Расчёт метрик
│   │   └── rules.py        # Rule Engine
│   ├── decision.py         # Decision Engine
│   ├── explainer.py        # AI Layer (Claude API)
│   └── e2e_test.py         # End-to-end тест
├── nodes/
│   └── simulator.py        # Симулятор складских узлов
├── dashboard/
│   └── app.py              # Streamlit Dashboard
├── data/
│   └── sample_data.json    # Тестовые данные
├── .env                    # API ключи (не коммитить!)
├── requirements.txt
└── supply_chain.db         # SQLite база данных
```

---

## Установка и запуск

### 1. Клонируй репозиторий

```bash
git clone <repo-url>
cd distributed-scm-ai
```

### 2. Установи зависимости

```bash
pip install -r requirements.txt
```

### 3. Создай `.env` файл

```
ANTHROPIC_API_KEY=sk-ant-api03-твой-ключ
```

### 4. Запусти систему

**Терминал 1 — API сервер:**
```bash
uvicorn api.main:app --reload --port 8000
```

**Терминал 2 — Dashboard:**
```bash
streamlit run dashboard/app.py
```

**Терминал 3 — Симулятор (опционально):**
```bash
python -m nodes.simulator --file data/sample_data.json
```

### 5. Открой Dashboard

```
http://localhost:8501
```

---

## Как работает система

```
data/sample_data.json
        ↓
nodes/simulator.py  →  POST /data  →  supply_chain.db
        ↓
backend/analytics/metrics.py  →  таблица metrics
        ↓
backend/analytics/rules.py  →  таблица alerts
        ↓
backend/decision.py  →  таблица recommendations
        ↓
backend/explainer.py  →  Claude API  →  объяснения на русском
        ↓
dashboard/app.py  →  Streamlit UI
```

---

## API эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/data` | Приём данных от узла |
| GET | `/alerts` | Список алертов |
| GET | `/alerts/summary` | Сводка по severity |
| GET | `/metrics` | Метрики складов |
| GET | `/events` | Сырые события |
| GET | `/health` | Статус сервера |

Документация API: `http://localhost:8000/docs`

---

## Правила выявления проблем

| Условие | Тип | Severity |
|---------|-----|----------|
| `days_of_stock < 3` | DEFICIT | CRITICAL |
| `delivery_delay > 3` | DELAY | HIGH |
| `2+ задержки у поставщика` | UNSTABLE_SUPPLIER | MEDIUM |

---

## Автор

Bogdan Safronov — [LinkedIn](https://linkedin.com)

Проект создан как демонстрация возможностей AI в логистике и управлении цепями поставок.
