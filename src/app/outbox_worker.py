import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import settings
from src.infra.broker.broker import create_broker
from src.infra.broker.publisher import PaymentEventPublisher
from src.infra.broker.topology import declare_topology
from src.infra.db.repositories import OutboxRepository
from src.infra.db.session import async_session_factory, engine

logger = logging.getLogger(__name__)


class OutboxWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        publisher: PaymentEventPublisher,
        batch_size: int = settings.outbox_batch_size,
        poll_interval: float = settings.outbox_poll_interval,
    ) -> None:
        self._sessions = sessions
        self._publisher = publisher
        self._batch_size = batch_size
        self._poll_interval = poll_interval

    async def publish_once(self) -> int:
        async with self._sessions() as session, session.begin():
            repository = OutboxRepository(session)
            events = await repository.get_unpublished(self._batch_size)
            for event in events:
                # A database rollback can cause redelivery, but an event must
                # never be marked published before RabbitMQ confirms it.
                await self._publisher.publish(
                    event.payload, event.event_type, message_id=str(event.id)
                )
                event.published_at = datetime.now(UTC)
            return len(events)

    async def run(self) -> None:
        while True:
            try:
                count = await self.publish_once()
            except Exception:
                logger.exception("Outbox publication failed; events remain in the database")
                count = 0
            if count < self._batch_size:
                await asyncio.sleep(self._poll_interval)


async def main() -> None:
    broker = create_broker()
    try:
        async with broker:
            await declare_topology(broker)
            await OutboxWorker(async_session_factory, PaymentEventPublisher(broker)).run()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
