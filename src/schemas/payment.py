from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, JsonValue

from src.domain.enums import Currency, PaymentStatus
from src.schemas.events import PaymentEvent

__all__ = ["PaymentCreate", "PaymentAccepted", "PaymentRead", "PaymentEvent"]

Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    amount: Amount
    currency: Currency
    description: str = Field(default="", max_length=1000)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    webhook_url: HttpUrl = Field(max_length=2048)


class PaymentAccepted(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_id: UUID = Field(validation_alias="id")
    status: PaymentStatus
    created_at: datetime


class PaymentRead(PaymentAccepted):
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, JsonValue] = Field(validation_alias="metadata_")
    idempotency_key: str
    webhook_url: str
    processed_at: datetime | None
    webhook_delivered_at: datetime | None
    delivery_failed_at: datetime | None
    processing_attempts: int
    last_error: str | None
