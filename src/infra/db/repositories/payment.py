from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.payments import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        payment_id: UUID,
    ) -> Payment | None:
        return await self._session.get(Payment, payment_id)

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.idempotency_key == idempotency_key,
        )

        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    def add(
        self,
        payment: Payment,
    ) -> None:
        self._session.add(payment)

    async def get_for_update(self, payment_id: UUID) -> Payment | None:
        result = await self._session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()
