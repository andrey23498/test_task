from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import EventType, PaymentStatus
from src.domain.payment import CreatePayment, IdempotencyConflict, PaymentNotFound
from src.infra.db.models import OutboxEvent, Payment
from src.infra.db.repositories import OutboxRepository, PaymentRepository
from src.schemas.events import PaymentEvent


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._outbox = OutboxRepository(session)

    async def create(self, command: CreatePayment) -> Payment:
        try:
            async with self._session.begin():
                existing = await self._payments.get_by_idempotency_key(command.idempotency_key)
                if existing is not None:
                    return self._check_idempotency(existing, command)

                payment = Payment(
                    id=uuid4(),
                    amount=command.amount,
                    currency=command.currency,
                    description=command.description,
                    metadata_=command.metadata,
                    webhook_url=command.webhook_url,
                    idempotency_key=command.idempotency_key,
                    status=PaymentStatus.PENDING,
                )
                event = PaymentEvent(event_id=uuid4(), payment_id=payment.id)
                self._payments.add(payment)
                self._outbox.add(
                    OutboxEvent(
                        id=event.event_id,
                        event_type=EventType.PAYMENT_CREATED,
                        aggregate_id=payment.id,
                        payload=event.model_dump(mode="json"),
                    )
                )
                await self._session.flush()
                return payment
        except IntegrityError:
            # The unique constraint also protects simultaneous requests; the
            # losing transaction rolls back both the payment and its event.
            async with self._session.begin():
                existing = await self._payments.get_by_idempotency_key(command.idempotency_key)
                if existing is None:
                    raise
                return self._check_idempotency(existing, command)

    async def get(self, payment_id: UUID) -> Payment:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFound(str(payment_id))
        return payment

    @staticmethod
    def _check_idempotency(payment: Payment, command: CreatePayment) -> Payment:
        if not command.matches(payment):
            raise IdempotencyConflict(command.idempotency_key)
        return payment
