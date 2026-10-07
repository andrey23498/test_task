import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
from faststream import AckPolicy, FastStream
from faststream.rabbit import RabbitMessage
from pydantic import ValidationError

from src.app.outbox_worker import OutboxWorker
from src.app.payment_processor import PaymentProcessor
from src.config import settings
from src.infra.broker.broker import create_broker
from src.infra.broker.publisher import PaymentEventPublisher
from src.infra.broker.topology import (
    declare_topology,
    payments_exchange,
    payments_new_queue,
)
from src.infra.db.session import async_session_factory, engine
from src.infra.gateway.fake_payment_gateway import FakePaymentGateway
from src.infra.webhook.client import WebhookClient
from src.schemas.events import PaymentEvent

logger = logging.getLogger(__name__)


def create_consumer() -> FastStream:
    broker = create_broker()
    processor: PaymentProcessor | None = None
    outbox_task: asyncio.Task[None] | None = None

    @asynccontextmanager
    async def lifespan() -> AsyncIterator[None]:
        nonlocal processor
        async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
            processor = PaymentProcessor(
                async_session_factory, FakePaymentGateway(), WebhookClient(client)
            )
            try:
                yield
            finally:
                if outbox_task is not None:
                    outbox_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await outbox_task
                processor = None
                await engine.dispose()

    app = FastStream(broker, lifespan=lifespan)

    @broker.subscriber(
        payments_new_queue,
        payments_exchange,
        ack_policy=AckPolicy.NACK_ON_ERROR,
        decoder=lambda message: message.body,
    )
    async def handle_payment(message: RabbitMessage) -> None:
        if processor is None:
            raise RuntimeError("Payment processor has not started")
        try:
            event = PaymentEvent.model_validate_json(message.body)
        except ValidationError:
            logger.warning("Invalid payment message; saving it for DLQ delivery")
            await processor.quarantine(message.body, "Invalid payment event")
            return
        await processor.process(event)

    @app.after_startup
    async def start_outbox() -> None:
        nonlocal outbox_task
        await declare_topology(broker)
        outbox_task = asyncio.create_task(
            OutboxWorker(async_session_factory, PaymentEventPublisher(broker)).run(),
            name="outbox-publisher",
        )

    return app


app = create_consumer()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(app.run())
