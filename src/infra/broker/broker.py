from faststream.rabbit import Channel, RabbitBroker

from src.config import settings


def create_broker() -> RabbitBroker:
    return RabbitBroker(
        settings.rabbitmq_url,
        default_channel=Channel(prefetch_count=1, publisher_confirms=True, on_return_raises=True),
    )
