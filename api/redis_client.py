import json
import os
from typing import Any, Dict, List
from datetime import datetime, timezone
from uuid import uuid4

import redis
from redis.exceptions import RedisError

STREAM_NAME = os.getenv("ALERTS_STREAM", "alerts")

_redis: redis.Redis | None = None


def _new_client() -> redis.Redis:
    """Create a new Redis client from environment variables."""
    url = os.getenv("REDIS_URL")
    if url:
        return redis.Redis.from_url(url, decode_responses=True)

    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


def get_client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = _new_client()
    return _redis


def utcnow_iso_z() -> str:
    """Return current UTC time in ISO 8601 format with trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_alert(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fill server-managed fields for an alert and return the full dict."""
    alert = dict(payload)
    alert["id"] = str(uuid4())
    alert["timestamp"] = utcnow_iso_z()
    return alert


def publish_alert(alert: Dict[str, Any]) -> str:
    """Publish a validated alert to the Redis stream. Returns stream ID."""
    client = get_client()
    # Store the alert as a single JSON field to keep schema intact
    data = {"alert": json.dumps(alert, separators=(",", ":"))}
    try:
        stream_id: str = client.xadd(STREAM_NAME, data)
        return stream_id
    except RedisError as exc:
        raise ConnectionError(str(exc))


def fetch_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch the most recent N alerts from the Redis stream (newest first)."""
    client = get_client()
    try:
        entries = client.xrevrange(STREAM_NAME, count=limit)
    except RedisError as exc:
        raise ConnectionError(str(exc))
    alerts: List[Dict[str, Any]] = []
    for _id, fields in entries:
        # fields keys/values are already str due to decode_responses=True
        raw = fields.get("alert")
        if not raw:
            continue
        try:
            alerts.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    # Return newest first as fetched by XREVRANGE; API may choose to reorder
    return alerts
