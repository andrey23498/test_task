from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(
        self,
        event: OutboxEvent,
    ) -> None:
        self._session.add(event)

    async def get_unpublished(
        self,
        limit: int = 100,
    ) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self._session.execute(stmt)

        return list(result.scalars().all())

    async def mark_published(
        self,
        event_id: UUID,
        published_at: datetime,
    ) -> None:
        event = await self._session.get(
            OutboxEvent,
            event_id,
        )

        if event is None:
            return

        event.published_at = published_at
