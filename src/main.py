from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.dependencies import require_api_key
from src.api.payments import router
from src.domain.payment import IdempotencyConflict, PaymentNotFound
from src.infra.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asynchronous payments",
        version="1.0.0",
        lifespan=lifespan,
        dependencies=[Depends(require_api_key)],
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(router)

    @app.exception_handler(PaymentNotFound)
    async def payment_not_found(request: Request, exc: PaymentNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Payment not found"})

    @app.exception_handler(IdempotencyConflict)
    async def idempotency_conflict(request: Request, exc: IdempotencyConflict) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "Idempotency-Key was already used with a different request"},
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_schema() -> JSONResponse:
        return JSONResponse(app.openapi())

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url="/openapi.json", title="Payments API")

    return app


app = create_app()
