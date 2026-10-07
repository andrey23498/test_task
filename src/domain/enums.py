from enum import StrEnum


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PaymentResult(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EventType(StrEnum):
    PAYMENT_CREATED = "payments.new"
    RETRY_1 = "payments.retry.1"
    RETRY_2 = "payments.retry.2"
    DEAD_LETTER = "payments.dlq"
