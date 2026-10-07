# Async Payment Service

## Запуск

Запуск через Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

API: `http://localhost:8081`. Миграции и обработчик запускаются автоматически.

## Примеры API

Ключ из `.env.example`: `local-development-key`. В `webhook_url` укажите свой HTTP-приёмник; пример использует порт 9000.

Создать платёж:

```bash
curl -sS -X POST 'http://localhost:8081/api/v1/payments' \
  -H 'X-API-Key: local-development-key' \
  -H 'Idempotency-Key: order-1' \
  -H 'Content-Type: application/json' \
  -d '{"amount":"1500.00","currency":"RUB","webhook_url":"http://host.docker.internal:9000/webhook"}'
```

Ответ: `202 Accepted` с `payment_id`, `status` и `created_at`.

Получить платёж (подставьте `payment_id` из ответа):

```bash
curl -sS 'http://localhost:8081/api/v1/payments/<payment_id>' \
  -H 'X-API-Key: local-development-key'
```

Статусы: `pending`, `succeeded`, `failed`. Результат отправляется на `webhook_url`.

Повтор с тем же `Idempotency-Key` и теми же данными возвращает тот же платёж. Другие данные с этим ключом `409 Conflict`.
