from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from src.api.dependencies import get_payment_service
from src.app.payment_service import PaymentService
from src.domain.payment import CreatePayment
from src.schemas.payment import PaymentAccepted, PaymentCreate, PaymentRead

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    payload: PaymentCreate,
    response: Response,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255, pattern=r".*\S.*")
    ],
) -> PaymentAccepted:
    payment = await service.create(
        CreatePayment(
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            metadata=payload.metadata,
            webhook_url=str(payload.webhook_url),
            idempotency_key=idempotency_key,
        )
    )
    response.headers["Location"] = f"/api/v1/payments/{payment.id}"
    return PaymentAccepted.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: UUID,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentRead:
    return PaymentRead.model_validate(await service.get(payment_id))
