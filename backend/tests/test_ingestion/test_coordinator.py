"""Tests for the ingestion coordinator (bounded swarm mode)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from foundry.ingestion.coordinator import (
    CoordinatedResult,
    CoordinatorConfig,
    _chunk_text,
    run_coordinated_analysis,
)
from foundry.ingestion.handlers.base import ExtractedContent


class TestChunking:
    def test_short_text_single_chunk(self) -> None:
        result = _chunk_text("short text", 1000)
        assert len(result) == 1
        assert result[0] == "short text"

    def test_long_text_splits(self) -> None:
        text = "\n\n".join([f"Paragraph {i}. " * 20 for i in range(10)])
        result = _chunk_text(text, 500)
        assert len(result) > 1
        for chunk in result:
            # Allow some overflow for paragraph boundaries
            assert len(chunk) < 1500

    def test_empty_text(self) -> None:
        result = _chunk_text("", 1000)
        assert len(result) == 1


class TestCoordinatorDisabled:
    @pytest.mark.asyncio
    async def test_returns_sequential_when_no_providers(self) -> None:
        config = CoordinatorConfig(enabled=True)  # No providers set
        extracted = ExtractedContent(text="test content")
        result = await run_coordinated_analysis(extracted, config)
        assert result.mode == "sequential"


class TestCoordinatedAnalysis:
    @pytest.mark.asyncio
    async def test_full_coordinated_run(self) -> None:
        """Coordinated analysis with mock providers produces structured output."""
        # Mock worker provider
        worker_provider = AsyncMock()
        worker_provider.analyze = AsyncMock(side_effect=lambda content, prompt: json.dumps({
            "concepts": ["test concept"],
            "entities": {"repos": ["test/repo"]},
            "components": [{"name": "Widget"}],
            "questions": ["How does it work?"],
        }))

        # Mock coordinator provider (for synthesis)
        coordinator_provider = AsyncMock()
        coordinator_provider.analyze = AsyncMock(return_value=json.dumps({
            "summary": "Synthesized summary of test content",
            "key_concepts": ["test concept"],
            "entities": {"repos": ["test/repo"], "models": [], "datasets": [], "tools": [], "papers": [], "people": []},
            "content_sections": [{"title": "Section 1", "summary": "Test"}],
            "open_questions": ["How does it work?"],
            "follow_up_suggestions": ["Read the docs"],
        }))

        config = CoordinatorConfig(
            enabled=True,
            max_parallel_workers=2,
            section_chunk_chars=5000,
            coordinator_provider=coordinator_provider,
            worker_provider=worker_provider,
        )
        extracted = ExtractedContent(text="This is test content about a machine learning project. " * 50)

        result = await run_coordinated_analysis(extracted, config)

        assert result.mode == "coordinated"
        assert result.synthesis  # Should have synthesis output
        assert len(result.section_analyses) > 0
        assert worker_provider.analyze.call_count >= 2  # section + entity + follow-up
        assert coordinator_provider.analyze.call_count >= 1  # synthesis

    @pytest.mark.asyncio
    async def test_critic_pass(self) -> None:
        """When use_critic is True, coordinator runs a critic pass."""
        provider = AsyncMock()
        provider.analyze = AsyncMock(return_value=json.dumps({
            "summary": "Test",
            "key_concepts": [],
            "entities": {},
            "content_sections": [],
            "open_questions": [],
            "follow_up_suggestions": [],
        }))

        config = CoordinatorConfig(
            enabled=True,
            max_parallel_workers=2,
            use_critic=True,
            coordinator_provider=provider,
            worker_provider=provider,
        )
        extracted = ExtractedContent(text="Short content")

        result = await run_coordinated_analysis(extracted, config)
        assert result.mode == "coordinated"
        # Coordinator should be called at least twice: synthesis + critic
        assert provider.analyze.call_count >= 2

    @pytest.mark.asyncio
    async def test_worker_failure_graceful(self) -> None:
        """Workers that fail don't crash the whole pipeline."""
        call_count = 0

        async def flaky_analyze(content, prompt):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise RuntimeError("Simulated failure")
            return json.dumps({"concepts": ["survived"]})

        worker = AsyncMock()
        worker.analyze = AsyncMock(side_effect=flaky_analyze)

        coordinator = AsyncMock()
        coordinator.analyze = AsyncMock(return_value=json.dumps({
            "summary": "Partial results",
        }))

        config = CoordinatorConfig(
            enabled=True,
            max_parallel_workers=2,
            coordinator_provider=coordinator,
            worker_provider=worker,
        )
        extracted = ExtractedContent(text="Content " * 500)

        result = await run_coordinated_analysis(extracted, config)
        assert result.mode == "coordinated"
        # Should still produce some results despite partial failures
