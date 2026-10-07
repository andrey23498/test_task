from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import Currency, PaymentStatus
from src.domain.payment import MAX_PROCESSING_ATTEMPTS


class PaymentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    payment_id: UUID
    attempt: int = Field(default=1, ge=1, le=MAX_PROCESSING_ATTEMPTS)


class WebhookPayload(BaseModel):
    event_id: UUID
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    processed_at: datetime
