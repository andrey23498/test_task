from typing import Any

from faststream.rabbit import RabbitBroker

from src.config import settings
from src.domain.enums import EventType
from src.infra.broker.topology import (
    payments_dlx,
    payments_exchange,
    payments_retry_exchange,
)


class PaymentEventPublisher:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish_payment_created(
        self,
        payload: dict[str, Any],
    ) -> None:
        await self.publish(payload, EventType.PAYMENT_CREATED)

    async def publish(
        self,
        payload: dict[str, Any],
        event_type: str,
        message_id: str | None = None,
    ) -> None:
        event_type = EventType(event_type)
        if event_type == EventType.PAYMENT_CREATED:
            exchange = payments_exchange
        elif event_type == EventType.DEAD_LETTER:
            exchange = payments_dlx
        else:
            exchange = payments_retry_exchange
        await self._broker.publish(
            payload,
            exchange=exchange,
            routing_key=event_type.value,
            message_id=message_id,
            persist=True,
            mandatory=True,
            timeout=settings.broker_publish_timeout,
        )
