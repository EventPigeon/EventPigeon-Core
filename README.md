# EventPigeon Core (v0.1)

EventPigeon Core is the backbone of an open-source alerting system. It provides a simple FastAPI REST API to publish alerts into a Redis Streams broker, and includes a minimal Python subscriber that prints incoming alerts.

This repository is the core service (publisher + broker integration). External integrations (producers and advanced subscribers) can build on top of this.

## Architecture

- API: FastAPI app that validates and publishes alerts to Redis Streams.
- Broker: Redis Streams (stream name: `alerts`).
- Subscriber: Example Python CLI that reads from `alerts` and prettifies events.

## Alert Schema

All alerts follow this JSON structure:

```json
{
  "id": "uuid",
  "timestamp": "2025-09-17T21:40:00Z",
  "source": "fail2ban",
  "type": "security",
  "message": "Blocked IP 185.234.22.11 after 6 attempts",
  "metadata": {
    "ip": "185.234.22.11",
    "service": "ssh",
    "geo": "RU"
  }
}
```

Rules:

- `id`: UUID generated server-side.
- `timestamp`: auto-generated in ISO 8601 UTC format (trailing `Z`).
- `source`: string (integration name).
- `type`: string (e.g., security, uptime, game, system).
- `message`: human-readable summary.
- `metadata`: optional object with extra details.

## Quick Start

Prerequisites: Docker + docker-compose.

1) Start the stack:

```bash
docker-compose up -d
```

This launches:

- `api` → FastAPI (Uvicorn) on `http://localhost:8000`
- `redis` → Redis 7
- `subscriber` (optional) → Only runs if you enable the `demo` profile

2) Publish an alert with curl (fields `id` and `timestamp` are added server-side):

```bash
curl -X POST http://localhost:8000/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "fail2ban",
    "type": "security",
    "message": "Blocked IP 185.234.22.11 after 6 attempts",
    "metadata": {"ip": "185.234.22.11", "service": "ssh", "geo": "RU"}
  }'
```

You should see the subscriber container print the new alert. View its logs with:

```bash
docker-compose logs -f subscriber
```

3) Fetch recent alerts (last N) via the API:

```bash
curl "http://localhost:8000/alerts/recent?limit=5"
```

## Project Structure

```
eventpigeon-core/
├── api/
│   ├── main.py              # FastAPI app with endpoints
│   ├── schemas.py           # Pydantic models for alert schema
│   └── redis_client.py      # Redis Streams publisher + helpers
├── subscriber/
│   └── subscriber.py        # Example subscriber client
├── docker-compose.yml       # Runs API + Redis (+ subscriber)
├── Dockerfile               # API container image
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Configuration

Environment variables (used by API and subscriber):

- `REDIS_URL` – (optional) Redis URL, e.g. `redis://redis:6379/0`
- `REDIS_HOST` – default `redis`
- `REDIS_PORT` – default `6379`
- `REDIS_DB` – default `0`
- `ALERTS_STREAM` – default `alerts`
- `FROM_START` (subscriber) – `true` to read from beginning, else only new

## API Endpoints

- `POST /alerts` → Validate body, add `id` + `timestamp`, publish to Redis stream `alerts`. Returns `201` with the stored alert JSON.
- `GET /alerts/recent?limit=N` → Fetch last N alerts from Redis stream and return as a JSON list.

OpenAPI docs available at `http://localhost:8000/docs` when the API is running.

## Run Subscriber Locally (API + Redis in Docker)

If you prefer to run the subscriber on your host while keeping API and Redis in Docker:

1) Start only API and Redis (subscriber is behind a compose profile):

```bash
docker-compose up -d
```

2) Install dependencies locally (Python 3.10+):

```bash
python -m venv .venv && source .venv/bin/activate
pip install redis
```

3) Point the subscriber to the Docker-exposed Redis and run it:

```bash
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export ALERTS_STREAM=alerts
export FROM_START=false   # set true to replay from beginning
python -u subscriber/subscriber.py
```

4) In another terminal, publish a test alert (via API in Docker):

```bash
curl -X POST http://localhost:8000/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "fail2ban",
    "type": "security",
    "message": "Blocked IP 185.234.22.11 after 6 attempts",
    "metadata": {"ip": "185.234.22.11", "service": "ssh", "geo": "RU"}
  }'
```

You should see the alert printed by the local subscriber.

Tip: You can use `REDIS_URL=redis://127.0.0.1:6379/0` instead of `REDIS_HOST`/`PORT`.

## Optional: Run Subscriber in Docker

To run the subscriber as a container, enable the `demo` profile:

```bash
docker-compose --profile demo up -d subscriber
docker-compose --profile demo logs -f subscriber
```

## Local Development (optional)

Run API locally (requires Python 3.11+):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export REDIS_HOST=localhost REDIS_PORT=6379
uvicorn api.main:app --reload
```

Run subscriber locally:

```bash
python subscriber/subscriber.py
```

## Notes

- Alerts are stored in the Redis stream as a single JSON field (`alert`) to preserve schema fidelity.
- The example subscriber reads only new messages by default. Set `FROM_START=true` to replay older alerts.
