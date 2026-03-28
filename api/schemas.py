"""
schemas.py — Pydantic модели для валидации входящих данных.

Режим: СТРОГИЙ — при любой ошибке возвращаем 422 Unprocessable Entity.
Все поля обязательны, типы проверяются жёстко.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime


class SupplyEventCreate(BaseModel):
    """
    Схема для POST /data — приём данных от узла (склада).
    Соответствует полям sample_data.json.
    """

    model_config = ConfigDict(strict=True)  # строгий режим Pydantic v2

    warehouse_id: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="ID склада, например: MSK, SPB"
    )
    product: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название продукта"
    )
    stock: float = Field(
        ...,
        ge=0,
        description="Текущий остаток на складе (>= 0)"
    )
    daily_usage: float = Field(
        ...,
        gt=0,
        description="Среднесуточное потребление (> 0, иначе деление на ноль)"
    )
    delivery_delay: float = Field(
        ...,
        ge=0,
        description="Задержка поставки в днях (>= 0)"
    )
    supplier: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Код или название поставщика"
    )

    @field_validator("warehouse_id")
    @classmethod
    def warehouse_id_uppercase(cls, v: str) -> str:
        """Приводим ID склада к верхнему регистру: msk → MSK"""
        return v.strip().upper()

    @field_validator("product", "supplier")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Убираем лишние пробелы по краям"""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Поле не может быть пустым или состоять из пробелов")
        return stripped


class SupplyEventResponse(BaseModel):
    """Ответ после успешного сохранения события"""
    id: int
    warehouse_id: str
    product: str
    stock: float
    daily_usage: float
    delivery_delay: float
    supplier: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricResponse(BaseModel):
    """Метрика по событию — возвращается в GET /metrics"""
    id: int
    event_id: int
    warehouse_id: str
    product: str
    days_of_stock: float
    risk_score: float
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    """Алерт — возвращается в GET /alerts"""
    id: int
    event_id: int
    warehouse_id: str
    product: str
    alert_type: str       # DEFICIT, DELAY, UNSTABLE_SUPPLIER
    severity: str         # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Ответ на GET /health"""
    status: str
    version: str
    db_connected: bool
