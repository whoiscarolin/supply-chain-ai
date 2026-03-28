"""
models.py — SQLAlchemy ORM модели.

Каждый класс = таблица в БД.
Связи: SupplyEvent → Metric, Alert, Recommendation (один ко многим).
"""

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class SupplyEvent(Base):
    """
    supply_events — сырые данные от узлов.
    Каждый POST /data создаёт одну запись.
    """
    __tablename__ = "supply_events"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String(10), nullable=False, index=True)
    product = Column(String(100), nullable=False)
    stock = Column(Float, nullable=False)
    daily_usage = Column(Float, nullable=False)
    delivery_delay = Column(Float, nullable=False)
    supplier = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Связи — один ивент может породить много метрик/алертов/рекомендаций
    metrics = relationship("Metric", back_populates="event", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="event", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="event", cascade="all, delete-orphan")


class Metric(Base):
    """
    metrics — рассчитанные показатели на основе события.
    Заполняется Metrics Engine (Этап 4).
    """
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("supply_events.id"), nullable=False, index=True)
    warehouse_id = Column(String(10), nullable=False)
    product = Column(String(100), nullable=False)
    days_of_stock = Column(Float, nullable=False)   # stock / daily_usage
    risk_score = Column(Float, nullable=False)       # 0.0 — 1.0
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    event = relationship("SupplyEvent", back_populates="metrics")


class Alert(Base):
    """
    alerts — проблемы, выявленные Rule Engine (Этап 5).
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("supply_events.id"), nullable=False, index=True)
    warehouse_id = Column(String(10), nullable=False)
    product = Column(String(100), nullable=False)
    alert_type = Column(String(30), nullable=False)   # DEFICIT / DELAY / UNSTABLE_SUPPLIER
    severity = Column(String(10), nullable=False)     # CRITICAL / HIGH / MEDIUM / LOW
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    event = relationship("SupplyEvent", back_populates="alerts")


class Recommendation(Base):
    """
    recommendations — решения от Decision Engine (Этап 6) и AI Layer (Этап 8).
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("supply_events.id"), nullable=False, index=True)
    warehouse_id = Column(String(10), nullable=False)
    product = Column(String(100), nullable=False)
    priority = Column(Integer, nullable=False)        # 1 = самый важный
    action = Column(Text, nullable=False)             # что делать
    reason = Column(Text, nullable=True)              # почему (AI объяснение)
    source = Column(String(20), default="rules")      # "rules" или "ai"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    event = relationship("SupplyEvent", back_populates="recommendations")
