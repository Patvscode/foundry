"""Webpage handler. Extracts readable text from web URLs using trafilatura."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from foundry.ingestion.handlers.base import ExtractedContent, ExtractionError, ResourceHandler

logger = logging.getLogger(__name__)

# Matches http/https URLs that aren't obviously YouTube or GitHub repos
_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


class WebpageHandler(ResourceHandler):
    name = "webpage"

    async def can_handle(self, input_str: str) -> bool:
        return bool(_URL_PATTERN.match(input_str.strip()))

    async def extract(self, input_str: str, cache_dir: Path) -> ExtractedContent:
        url = input_str.strip()

        # Check cache first
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_path = cache_dir / url_hash
        cached_text = cache_path / "raw.txt"
        cached_meta = cache_path / "metadata.json"

        if cached_text.exists():
            import json
            logger.info("Cache hit for %s", url)
            text = cached_text.read_text(encoding="utf-8")
            meta = {}
            if cached_meta.exists():
                meta = json.loads(cached_meta.read_text(encoding="utf-8"))
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            return ExtractedContent(
                text=text,
                metadata=meta,
                content_hash=content_hash,
                raw_content_path=cached_text,
            )

        # Fetch and extract
        try:
            import trafilatura
        except ImportError as e:
            raise ExtractionError(
                "trafilatura is not installed. Install with: pip install trafilatura",
                recoverable=False,
            ) from e

        logger.info("Fetching %s", url)
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            raise ExtractionError(
                f"Could not fetch URL: {url}",
                recoverable=True,
                suggestion="Check the URL is accessible and try again.",
            )

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
        )
        if not text:
            raise ExtractionError(
                f"Could not extract readable text from: {url}",
                recoverable=True,
                suggestion="The page may be JavaScript-rendered or empty.",
            )

        # Extract metadata
        metadata_obj = trafilatura.extract(
            downloaded,
            output_format="json",
            include_comments=False,
        )
        import json
        meta = {}
        if metadata_obj:
            try:
                meta = json.loads(metadata_obj) if isinstance(metadata_obj, str) else {}
            except (json.JSONDecodeError, TypeError):
                pass

        title = meta.get("title", url)
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Cache
        cache_path.mkdir(parents=True, exist_ok=True)
        cached_text.write_text(text, encoding="utf-8")
        cached_meta.write_text(
            json.dumps({"url": url, "title": title, "content_hash": content_hash}),
            encoding="utf-8",
        )

        logger.info("Extracted %d chars from %s", len(text), url)
        return ExtractedContent(
            text=text,
            metadata={"url": url, "title": title},
            content_hash=content_hash,
            raw_content_path=cached_text,
        )
