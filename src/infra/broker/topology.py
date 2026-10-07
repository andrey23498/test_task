from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

payments_exchange = RabbitExchange(
    "payments",
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_retry_exchange = RabbitExchange(
    "payments.retry",
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_dlx = RabbitExchange(
    "payments.dlx",
    type=ExchangeType.DIRECT,
    durable=True,
)


payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-queue-type": "quorum",
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.dlq",
        "x-dead-letter-strategy": "at-least-once",
        "x-overflow": "reject-publish",
    },
)


payments_retry_1_queue = RabbitQueue(
    "payments.retry.1",
    durable=True,
    routing_key="payments.retry.1",
    arguments={
        "x-queue-type": "quorum",
        "x-dead-letter-strategy": "at-least-once",
        "x-overflow": "reject-publish",
        "x-message-ttl": 1_000,
        "x-dead-letter-exchange": "payments",
        "x-dead-letter-routing-key": "payments.new",
    },
)

payments_retry_2_queue = RabbitQueue(
    "payments.retry.2",
    durable=True,
    routing_key="payments.retry.2",
    arguments={
        "x-queue-type": "quorum",
        "x-dead-letter-strategy": "at-least-once",
        "x-overflow": "reject-publish",
        "x-message-ttl": 2_000,
        "x-dead-letter-exchange": "payments",
        "x-dead-letter-routing-key": "payments.new",
    },
)

payments_dlq = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key="payments.dlq",
    arguments={"x-queue-type": "quorum"},
)


async def declare_topology(broker: RabbitBroker) -> None:
    for exchange, queues in (
        (payments_exchange, (payments_new_queue,)),
        (payments_retry_exchange, (payments_retry_1_queue, payments_retry_2_queue)),
        (payments_dlx, (payments_dlq,)),
    ):
        declared_exchange = await broker.declare_exchange(exchange)
        for queue in queues:
            declared_queue = await broker.declare_queue(queue)
            await declared_queue.bind(declared_exchange, routing_key=queue.routing_key)
