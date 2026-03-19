"""Base classes for resource ingestion handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedContent:
    """Output of a resource handler's extract() method."""
    text: str
    metadata: dict = field(default_factory=dict)
    content_hash: str = ""
    raw_content_path: Path | None = None


class ExtractionError(Exception):
    """Raised when a handler fails to extract content."""

    def __init__(self, message: str, recoverable: bool = True, suggestion: str = "") -> None:
        super().__init__(message)
        self.recoverable = recoverable
        self.suggestion = suggestion


class ResourceHandler(ABC):
    """Abstract base class for resource type handlers."""

    name: str
    url_patterns: list[str] = []

    @abstractmethod
    async def can_handle(self, input_str: str) -> bool:
        """Return True if this handler can process the given input."""

    @abstractmethod
    async def extract(self, input_str: str, cache_dir: Path) -> ExtractedContent:
        """Extract content from the resource. Must be idempotent. Caches results."""
