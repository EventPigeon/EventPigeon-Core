from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query

from .schemas import Alert, AlertIn
from .redis_client import (
    build_alert,
    fetch_recent_alerts,
    publish_alert,
)

app = FastAPI(title="EventPigeon Core", version="0.1.0")


@app.post("/alerts", response_model=Alert, status_code=201)
def create_alert(payload: AlertIn) -> Dict[str, Any]:
    """Validate, enrich, and publish an alert."""
    try:
        alert = build_alert(payload.model_dump())
        publish_alert(alert)
        # Validate output shape with Alert model before returning
        return Alert(**alert).model_dump()
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Broker unavailable")
    except Exception as exc:  # pragma: no cover - generic safety net
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/alerts/recent", response_model=List[Alert])
def recent_alerts(limit: int = Query(10, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Fetch the last N alerts from the Redis stream."""
    try:
        items = fetch_recent_alerts(limit=limit)
        # Ensure response conforms to schema
        return [Alert(**a).model_dump() for a in items]
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Broker unavailable")
    except Exception as exc:  # pragma: no cover - generic safety net
        raise HTTPException(status_code=500, detail=str(exc))

