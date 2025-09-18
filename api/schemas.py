from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertIn(BaseModel):
    """Incoming alert payload (client-provided fields only)."""

    source: str = Field(..., description="Integration/source name")
    type: str = Field(..., description="Category: security, uptime, game, system, etc.")
    message: str = Field(..., description="Human-readable summary of the alert")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional extra details as a JSON object"
    )


class Alert(AlertIn):
    """Full alert as stored/published by the server."""

    id: UUID = Field(..., description="Server-generated UUID")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp with trailing Z")

