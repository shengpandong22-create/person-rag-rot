from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """The minimum user aggregate required by the Phase 0 database foundation."""

    id: UUID
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime
