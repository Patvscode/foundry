"""Tests for PDF and YouTube ingestion handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPDFHandler:
    """Tests for the PDF handler."""

    @pytest.mark.asyncio
    async def test_can_handle_pdf_url(self) -> None:
        from foundry.ingestion.handlers.pdf import PDFHandler
        handler = PDFHandler()
        assert await handler.can_handle("https://arxiv.org/pdf/2301.00001.pdf") is True
        assert await handler.can_handle("https://example.com/doc.PDF") is True

    @pytest.mark.asyncio
    async def test_cannot_handle_non_pdf(self) -> None:
        from foundry.ingestion.handlers.pdf import PDFHandler
        handler = PDFHandler()
        assert await handler.can_handle("https://example.com/article") is False
        assert await handler.can_handle("https://youtube.com/watch?v=abc") is False

    @pytest.mark.asyncio
    async def test_can_handle_local_pdf(self, tmp_path: Path) -> None:
        from foundry.ingestion.handlers.pdf import PDFHandler
        handler = PDFHandler()
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        assert await handler.can_handle(str(pdf_file)) is True

    @pytest.mark.asyncio
    async def test_extract_from_local_pdf(self, tmp_path: Path) -> None:
        """Test extraction from a real (minimal) PDF using pypdfium2."""
        import pypdfium2 as pdfium

        # Create a minimal PDF
        doc = pdfium.PdfDocument.new()
        page = doc.new_page(200, 200)
        page.close()
        pdf_path = tmp_path / "test.pdf"
        doc.save(str(pdf_path))
        doc.close()

        from foundry.ingestion.handlers.pdf import PDFHandler
        handler = PDFHandler()
        cache_dir = tmp_path / "cache"

        # pypdfium2 new pages have no text, so expect ExtractionError
        from foundry.ingestion.handlers.base import ExtractionError
        with pytest.raises(ExtractionError, match="no extractable text"):
            await handler.extract(str(pdf_path), cache_dir)

    @pytest.mark.asyncio
    async def test_extract_uses_cache(self, tmp_path: Path) -> None:
        """Cached results are returned without re-parsing."""
        from foundry.ingestion.handlers.pdf import PDFHandler
        import hashlib

        handler = PDFHandler()
        url = "https://example.com/paper.pdf"
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        cache_dir = tmp_path / "cache"
        cache_path = cache_dir / url_hash
        cache_path.mkdir(parents=True)
        (cache_path / "raw.txt").write_text("Cached PDF text", encoding="utf-8")
        (cache_path / "metadata.json").write_text(
            json.dumps({"url": url, "title": "paper"}),
            encoding="utf-8",
        )

        result = await handler.extract(url, cache_dir)
        assert result.text == "Cached PDF text"
        assert result.metadata["title"] == "paper"


class TestYouTubeHandler:
    """Tests for the YouTube handler."""

    @pytest.mark.asyncio
    async def test_can_handle_youtube(self) -> None:
        from foundry.ingestion.handlers.youtube import YouTubeHandler
        handler = YouTubeHandler()
        assert await handler.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert await handler.can_handle("https://youtu.be/dQw4w9WgXcQ") is True
        assert await handler.can_handle("https://youtube.com/shorts/abc123") is True

    @pytest.mark.asyncio
    async def test_cannot_handle_non_youtube(self) -> None:
        from foundry.ingestion.handlers.youtube import YouTubeHandler
        handler = YouTubeHandler()
        assert await handler.can_handle("https://example.com/video") is False
        assert await handler.can_handle("https://vimeo.com/12345") is False

    @pytest.mark.asyncio
    async def test_extract_uses_cache(self, tmp_path: Path) -> None:
        """Cached results are returned without calling yt-dlp."""
        from foundry.ingestion.handlers.youtube import YouTubeHandler
        import hashlib

        handler = YouTubeHandler()
        url = "https://www.youtube.com/watch?v=test123"
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        cache_dir = tmp_path / "cache"
        cache_path = cache_dir / url_hash
        cache_path.mkdir(parents=True)
        (cache_path / "raw.txt").write_text("Cached YT text", encoding="utf-8")
        (cache_path / "metadata.json").write_text(
            json.dumps({"url": url, "title": "Test Video", "handler": "youtube"}),
            encoding="utf-8",
        )

        result = await handler.extract(url, cache_dir)
        assert result.text == "Cached YT text"
        assert result.metadata["title"] == "Test Video"

    def test_vtt_parser(self, tmp_path: Path) -> None:
        """VTT parser strips timestamps and deduplicates lines."""
        from foundry.ingestion.handlers.youtube import _parse_vtt

        vtt_content = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:10.000
Hello world

00:00:10.000 --> 00:00:15.000
This is a test
"""
        vtt_path = tmp_path / "test.vtt"
        vtt_path.write_text(vtt_content)

        result = _parse_vtt(vtt_path)
        assert "Hello world" in result
        assert "This is a test" in result
        # Should deduplicate
        assert result.count("Hello world") == 1


class TestDispatch:
    """Tests for the handler dispatch logic."""

    @pytest.mark.asyncio
    async def test_youtube_dispatches_first(self) -> None:
        from foundry.ingestion.pipeline import dispatch
        name, handler = await dispatch("https://www.youtube.com/watch?v=abc123")
        assert name == "youtube"

    @pytest.mark.asyncio
    async def test_pdf_dispatches_for_pdf_url(self) -> None:
        from foundry.ingestion.pipeline import dispatch
        name, handler = await dispatch("https://arxiv.org/pdf/2301.00001.pdf")
        assert name == "pdf"

    @pytest.mark.asyncio
    async def test_webpage_dispatches_for_generic_url(self) -> None:
        from foundry.ingestion.pipeline import dispatch
        name, handler = await dispatch("https://example.com/article")
        assert name == "webpage"

    @pytest.mark.asyncio
    async def test_no_handler_raises(self) -> None:
        from foundry.ingestion.handlers.base import ExtractionError
        from foundry.ingestion.pipeline import dispatch
        with pytest.raises(ExtractionError):
            await dispatch("not-a-url-at-all")


class TestResourceTypeDetection:
    """Tests for the API resource type detection."""

    def test_detects_youtube(self) -> None:
        from foundry.api.resources import _detect_resource_type
        assert _detect_resource_type("https://www.youtube.com/watch?v=abc") == "youtube"
        assert _detect_resource_type("https://youtu.be/abc") == "youtube"

    def test_detects_pdf(self) -> None:
        from foundry.api.resources import _detect_resource_type
        assert _detect_resource_type("https://example.com/paper.pdf") == "pdf"
        assert _detect_resource_type("https://arxiv.org/pdf/2301.00001.pdf") == "pdf"

    def test_defaults_to_webpage(self) -> None:
        from foundry.api.resources import _detect_resource_type
        assert _detect_resource_type("https://example.com/article") == "webpage"
