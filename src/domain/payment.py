from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.domain.enums import Currency

MAX_PROCESSING_ATTEMPTS = 3


class PaymentNotFound(Exception):
    pass


class IdempotencyConflict(Exception):
    pass


class GatewayError(Exception):
    """A transient gateway failure; a declined payment is a normal result."""


@dataclass(frozen=True, slots=True)
class CreatePayment:
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    webhook_url: str
    idempotency_key: str

    def matches(self, payment: Any) -> bool:
        return (
            payment.amount == self.amount
            and payment.currency == self.currency
            and payment.description == self.description
            and payment.metadata_ == self.metadata
            and payment.webhook_url == self.webhook_url
        )
