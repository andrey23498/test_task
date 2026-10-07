import base64
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.enums import EventType, PaymentStatus
from src.domain.payment import MAX_PROCESSING_ATTEMPTS, GatewayError
from src.infra.db.models import OutboxEvent, Payment
from src.infra.db.repositories import PaymentRepository
from src.infra.gateway.fake_payment_gateway import FakePaymentGateway
from src.infra.webhook.client import WebhookClient
from src.schemas.events import PaymentEvent, WebhookPayload


class PaymentProcessor:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        gateway: FakePaymentGateway,
        webhooks: WebhookClient,
    ) -> None:
        self._sessions = sessions
        self._gateway = gateway
        self._webhooks = webhooks

    async def process(self, event: PaymentEvent) -> None:
        async with self._sessions() as session:
            async with session.begin():
                payment = await PaymentRepository(session).get_for_update(event.payment_id)
                if payment is None:
                    self._dead_letter(session, event, "Payment does not exist")
                    return
                if self._already_handled(payment, event):
                    return
                if event.attempt != payment.processing_attempts + 1:
                    self._dead_letter(session, event, "Unexpected attempt number")
                    return
                if payment.status == PaymentStatus.PENDING:
                    try:
                        result = await self._gateway.process()
                    except GatewayError as exc:
                        self._record_failure(session, payment, event, type(exc).__name__)
                        return
                    payment.status = PaymentStatus(result.value)
                    payment.processed_at = datetime.now(UTC)

            # Save the gateway result before HTTP delivery. Webhook retries
            # must never trigger another call to the payment gateway.
            async with session.begin():
                payment = await PaymentRepository(session).get_for_update(event.payment_id)
                if payment is None or self._already_handled(payment, event):
                    return
                payload = WebhookPayload(
                    event_id=event.event_id,
                    payment_id=payment.id,
                    status=payment.status,
                    amount=payment.amount,
                    currency=payment.currency,
                    processed_at=payment.processed_at,
                )
                try:
                    await self._webhooks.send(payment.webhook_url, payload.model_dump(mode="json"))
                except httpx.HTTPError as exc:
                    error = type(exc).__name__
                    if isinstance(exc, httpx.HTTPStatusError):
                        error += f": HTTP {exc.response.status_code}"
                    self._record_failure(session, payment, event, error)
                else:
                    payment.processing_attempts = event.attempt
                    payment.webhook_delivered_at = datetime.now(UTC)
                    payment.last_error = None

    async def quarantine(self, body: bytes, error: str) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                OutboxEvent(
                    event_type=EventType.DEAD_LETTER,
                    aggregate_id=uuid4(),
                    payload={
                        "raw_body_base64": base64.b64encode(body).decode("ascii"),
                        "error": error,
                        "failed_at": datetime.now(UTC).isoformat(),
                    },
                )
            )

    @staticmethod
    def _already_handled(payment: Payment, event: PaymentEvent) -> bool:
        return (
            payment.webhook_delivered_at is not None
            or payment.delivery_failed_at is not None
            or event.attempt <= payment.processing_attempts
        )

    @staticmethod
    def _dead_letter(session: AsyncSession, event: PaymentEvent, error: str) -> None:
        session.add(
            OutboxEvent(
                event_type=EventType.DEAD_LETTER,
                aggregate_id=event.payment_id,
                payload={
                    **event.model_dump(mode="json"),
                    "error": error,
                    "failed_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def _record_failure(
        self,
        session: AsyncSession,
        payment: Payment,
        event: PaymentEvent,
        error: str,
    ) -> None:
        payment.processing_attempts = event.attempt
        payment.last_error = error
        if event.attempt >= MAX_PROCESSING_ATTEMPTS:
            payment.delivery_failed_at = datetime.now(UTC)
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.FAILED
                payment.processed_at = payment.delivery_failed_at
            self._dead_letter(session, event, error)
            return

        retry_event = event.model_copy(update={"attempt": event.attempt + 1})
        session.add(
            OutboxEvent(
                event_type=EventType.RETRY_1 if event.attempt == 1 else EventType.RETRY_2,
                aggregate_id=payment.id,
                payload=retry_event.model_dump(mode="json"),
            )
        )
