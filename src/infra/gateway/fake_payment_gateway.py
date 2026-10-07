import asyncio
import random

from src.domain.enums import PaymentResult


class FakePaymentGateway:
    async def process(self) -> PaymentResult:
        await asyncio.sleep(
            random.uniform(2, 5),
        )

        return PaymentResult.SUCCEEDED if random.random() < 0.9 else PaymentResult.FAILED
