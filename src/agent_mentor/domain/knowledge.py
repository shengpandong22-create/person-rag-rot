from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class IngestionJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TrustLevel(StrEnum):
    OFFICIAL = "official"
    CURATED = "curated"
    COMMUNITY = "community"
    UNKNOWN = "unknown"
