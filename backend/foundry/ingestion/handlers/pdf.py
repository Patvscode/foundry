"""PDF handler. Extracts text from local or remote PDF files using pypdfium2."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import httpx
import pypdfium2 as pdfium

from foundry.ingestion.handlers.base import ExtractedContent, ExtractionError, ResourceHandler

logger = logging.getLogger(__name__)

_PDF_URL = re.compile(r"^https?://.*\.pdf(\?.*)?$", re.IGNORECASE)
_PDF_CONTENT_TYPE = re.compile(r"application/pdf", re.IGNORECASE)


class PDFHandler(ResourceHandler):
    name = "pdf"

    async def can_handle(self, input_str: str) -> bool:
        s = input_str.strip()
        if _PDF_URL.match(s):
            return True
        # Check if it's a local file
        if Path(s).suffix.lower() == ".pdf" and Path(s).exists():
            return True
        # For ambiguous URLs, do a HEAD check
        if s.startswith(("http://", "https://")) and not _PDF_URL.match(s):
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.head(s)
                    ct = resp.headers.get("content-type", "")
                    if _PDF_CONTENT_TYPE.search(ct):
                        return True
            except Exception:
                pass
        return False

    async def extract(self, input_str: str, cache_dir: Path) -> ExtractedContent:
        s = input_str.strip()
        url_hash = hashlib.sha256(s.encode()).hexdigest()[:16]
        cache_path = cache_dir / url_hash
        cached_text = cache_path / "raw.txt"
        cached_meta = cache_path / "metadata.json"

        if cached_text.exists():
            logger.info("Cache hit for PDF %s", s)
            text = cached_text.read_text(encoding="utf-8")
            meta = {}
            if cached_meta.exists():
                meta = json.loads(cached_meta.read_text(encoding="utf-8"))
            return ExtractedContent(
                text=text,
                metadata=meta,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                raw_content_path=cached_text,
            )

        # Get the PDF bytes
        pdf_path: Path | None = None
        if Path(s).exists():
            pdf_bytes = Path(s).read_bytes()
            pdf_path = Path(s)
        else:
            logger.info("Downloading PDF from %s", s)
            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.get(s)
                    resp.raise_for_status()
                    pdf_bytes = resp.content
            except httpx.HTTPError as e:
                raise ExtractionError(
                    f"Could not download PDF: {s} ({e})",
                    recoverable=True,
                    suggestion="Check the URL is accessible.",
                ) from e

        # Extract text with pypdfium2
        try:
            doc = pdfium.PdfDocument(pdf_bytes)
            pages_text: list[str] = []
            page_count = len(doc)
            for i in range(page_count):
                page = doc[i]
                textpage = page.get_textpage()
                page_text = textpage.get_text_range()
                if page_text.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{page_text}")
                textpage.close()
                page.close()
            doc.close()
        except Exception as e:
            raise ExtractionError(
                f"Could not parse PDF: {e}",
                recoverable=False,
                suggestion="The PDF may be image-only or corrupted.",
            ) from e

        if not pages_text:
            raise ExtractionError(
                "PDF contained no extractable text (image-only PDF?)",
                recoverable=False,
                suggestion="This PDF may need OCR, which is not yet supported.",
            )

        text = "\n\n".join(pages_text)
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        title = Path(s).stem if pdf_path else s.split("/")[-1].split("?")[0]
        meta = {"url": s, "title": title, "page_count": page_count, "handler": "pdf"}

        # Cache
        cache_path.mkdir(parents=True, exist_ok=True)
        cached_text.write_text(text, encoding="utf-8")
        cached_meta.write_text(json.dumps(meta), encoding="utf-8")

        # Save raw PDF for future reference
        raw_pdf_path = cache_path / "raw.pdf"
        if not raw_pdf_path.exists():
            raw_pdf_path.write_bytes(pdf_bytes)

        logger.info("Extracted %d chars from %d pages of %s", len(text), page_count, s)
        return ExtractedContent(
            text=text,
            metadata=meta,
            content_hash=content_hash,
            raw_content_path=cached_text,
        )
