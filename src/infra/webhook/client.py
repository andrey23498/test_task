from typing import Any

import httpx


class WebhookClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
    ) -> None:
        self._client = client

    async def send(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> None:
        response = await self._client.post(
            url,
            json=payload,
            headers={"Idempotency-Key": str(payload["payment_id"])},
            follow_redirects=False,
        )

        response.raise_for_status()
