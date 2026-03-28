"""
main.py — FastAPI приложение.

Эндпоинты:
  POST /data        — приём данных от узлов
  GET  /metrics     — получение метрик
  GET  /alerts      — получение алертов
  GET  /alerts/summary — сводка по severity
  GET  /health      — проверка состояния сервера

Запуск:
  uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Optional
from datetime import datetime, timezone
import os

from api.models import Base, SupplyEvent, Metric, Alert, Recommendation
from api.schemas import (
    SupplyEventCreate,
    SupplyEventResponse,
    MetricResponse,
    AlertResponse,
    HealthResponse,
)

# ---------------------------------------------------------------------------
# Конфигурация БД
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./supply_chain.db")

engine = create_engine(
    DATABASE_URL,
    # Нужно только для SQLite — разрешает использовать соединение в нескольких потоках
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаём таблицы при старте (если не существуют)
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# FastAPI приложение
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Supply Chain AI — API",
    description="API для приёма данных от узлов, расчёта метрик и выдачи алертов.",
    version="1.0.0",
)

# CORS — разрешаем Dashboard (Streamlit) обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить конкретными адресами
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dependency — сессия БД
# ---------------------------------------------------------------------------

def get_db():
    """Открывает сессию БД, гарантированно закрывает после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Эндпоинты
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """
    Проверка состояния сервера и подключения к БД.
    Используется симулятором и Dashboard для проверки доступности.
    """
    try:
        db.execute(func.now() if "postgresql" in DATABASE_URL else func.current_timestamp())
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version="1.0.0",
        db_connected=db_ok,
    )


@app.post(
    "/data",
    response_model=SupplyEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Data Ingestion"],
)
def ingest_supply_event(
    payload: SupplyEventCreate,
    db: Session = Depends(get_db),
):
    """
    Приём данных от узла (склада).

    - Валидирует данные через Pydantic (строгий режим)
    - Сохраняет событие в supply_events
    - Возвращает сохранённую запись с id и created_at

    При ошибке валидации автоматически возвращает 422 с описанием проблемы.
    """
    event = SupplyEvent(
        warehouse_id=payload.warehouse_id,
        product=payload.product,
        stock=payload.stock,
        daily_usage=payload.daily_usage,
        delivery_delay=payload.delivery_delay,
        supplier=payload.supplier,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/metrics", response_model=List[MetricResponse], tags=["Analytics"])
def get_metrics(
    warehouse_id: Optional[str] = Query(None, description="Фильтр по складу, например: MSK"),
    limit: int = Query(100, ge=1, le=1000, description="Максимум записей"),
    db: Session = Depends(get_db),
):
    """
    Получение рассчитанных метрик.

    Метрики заполняются Metrics Engine (Этап 4).
    До запуска аналитики таблица будет пустой.
    """
    query = db.query(Metric)
    if warehouse_id:
        query = query.filter(Metric.warehouse_id == warehouse_id.upper())
    metrics = query.order_by(Metric.calculated_at.desc()).limit(limit).all()
    return metrics


@app.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
def get_alerts(
    warehouse_id: Optional[str] = Query(None, description="Фильтр по складу"),
    severity: Optional[str] = Query(None, description="Фильтр по severity: CRITICAL, HIGH, MEDIUM, LOW"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Получение алертов о проблемах в цепи поставок.

    Алерты создаются Rule Engine (Этап 5).
    """
    query = db.query(Alert)
    if warehouse_id:
        query = query.filter(Alert.warehouse_id == warehouse_id.upper())
    if severity:
        severity_upper = severity.upper()
        if severity_upper not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            raise HTTPException(
                status_code=400,
                detail="severity должен быть одним из: CRITICAL, HIGH, MEDIUM, LOW"
            )
        query = query.filter(Alert.severity == severity_upper)

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    return alerts


@app.get("/alerts/summary", tags=["Alerts"])
def get_alerts_summary(db: Session = Depends(get_db)):
    """
    Сводка алертов по уровню severity.
    Используется Dashboard для отображения счётчиков.

    Пример ответа:
    {
      "total": 5,
      "CRITICAL": 1,
      "HIGH": 2,
      "MEDIUM": 2,
      "LOW": 0
    }
    """
    rows = (
        db.query(Alert.severity, func.count(Alert.id))
        .group_by(Alert.severity)
        .all()
    )
    summary = {"total": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for severity, count in rows:
        summary[severity] = count
        summary["total"] += count
    return summary


@app.get("/events", response_model=List[SupplyEventResponse], tags=["Data Ingestion"])
def get_events(
    warehouse_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Просмотр принятых событий. Удобно для отладки.
    """
    query = db.query(SupplyEvent)
    if warehouse_id:
        query = query.filter(SupplyEvent.warehouse_id == warehouse_id.upper())
    return query.order_by(SupplyEvent.created_at.desc()).limit(limit).all()
