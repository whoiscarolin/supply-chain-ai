-- ============================================================
-- AI Decision Support System — Supply Chain
-- schema.sql | Этап 1
-- Путь: distributed-scm-ai/database/schema.sql
-- ============================================================

-- Таблица 1: Входящие события от узлов (склады, поставщики)
CREATE TABLE IF NOT EXISTS supply_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id    TEXT NOT NULL,          -- ID склада: MSK, SPB, ...
    product         TEXT NOT NULL,          -- название продукта
    stock           REAL NOT NULL,          -- остаток на складе (шт)
    daily_usage     REAL NOT NULL,          -- суточное потребление (шт)
    delivery_delay  REAL NOT NULL,          -- задержка поставки (дни)
    supplier        TEXT NOT NULL,          -- код поставщика: A, B, ...
    timestamp       TEXT NOT NULL           -- ISO 8601
);

-- Таблица 2: Рассчитанные метрики по каждому событию
CREATE TABLE IF NOT EXISTS metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        INTEGER NOT NULL REFERENCES supply_events(id),
    days_of_stock   REAL NOT NULL,          -- stock / daily_usage
    delay_score     REAL NOT NULL,          -- нормализованная задержка
    risk_score      REAL NOT NULL,          -- итоговый риск 0.0–1.0
    timestamp       TEXT NOT NULL
);

-- Таблица 3: Алерты — выявленные проблемы
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id    TEXT NOT NULL,
    product         TEXT NOT NULL,
    problem_type    TEXT NOT NULL,          -- DEFICIT | DELAY | SUPPLIER_RISK
    severity        TEXT NOT NULL,          -- CRITICAL | HIGH | MEDIUM | LOW
    description     TEXT NOT NULL,          -- человекочитаемое описание
    status          TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN | RESOLVED
    created_at      TEXT NOT NULL
);

-- Таблица 4: Рекомендации и решения
CREATE TABLE IF NOT EXISTS recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id        INTEGER NOT NULL REFERENCES alerts(id),
    action          TEXT NOT NULL,          -- что делать
    priority        INTEGER NOT NULL,       -- 1 = срочно, 2 = важно, 3 = плановое
    ai_explanation  TEXT,                   -- объяснение от Claude (Этап 8)
    created_at      TEXT NOT NULL
);

-- Индексы для быстрых запросов
CREATE INDEX IF NOT EXISTS idx_events_warehouse  ON supply_events(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp  ON supply_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_status     ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity   ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_metrics_event     ON metrics(event_id);
