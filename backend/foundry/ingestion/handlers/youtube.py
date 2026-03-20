"""YouTube handler. Extracts transcript, metadata, and description from YouTube videos via yt-dlp."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path

from foundry.ingestion.handlers.base import ExtractedContent, ExtractionError, ResourceHandler

logger = logging.getLogger(__name__)

_YT_PATTERN = re.compile(
    r"^https?://(www\.)?(youtube\.com/(watch|shorts|live)|youtu\.be/)",
    re.IGNORECASE,
)


def _find_yt_dlp() -> str:
    """Find yt-dlp binary. Prefer the venv copy, fall back to system."""
    import shutil
    for candidate in [
        shutil.which("yt-dlp"),
        "/home/linuxbrew/.linuxbrew/bin/yt-dlp",
    ]:
        if candidate and Path(candidate).exists():
            return candidate
    raise ExtractionError(
        "yt-dlp is not installed. Install with: pip install yt-dlp",
        recoverable=False,
    )


class YouTubeHandler(ResourceHandler):
    name = "youtube"

    async def can_handle(self, input_str: str) -> bool:
        return bool(_YT_PATTERN.match(input_str.strip()))

    async def extract(self, input_str: str, cache_dir: Path) -> ExtractedContent:
        url = input_str.strip()
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_path = cache_dir / url_hash
        cached_text = cache_path / "raw.txt"
        cached_meta = cache_path / "metadata.json"

        if cached_text.exists():
            logger.info("Cache hit for YouTube %s", url)
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

        yt_dlp = _find_yt_dlp()

        # Step 1: Get video metadata (no download)
        logger.info("Fetching YouTube metadata for %s", url)
        try:
            result = subprocess.run(
                [yt_dlp, "--dump-json", "--no-download", url],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise ExtractionError(
                    f"yt-dlp metadata failed: {result.stderr[:500]}",
                    recoverable=True,
                    suggestion="Check the URL. Video may be private or region-locked.",
                )
            info = json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise ExtractionError("yt-dlp timed out fetching metadata", recoverable=True)
        except json.JSONDecodeError:
            raise ExtractionError("yt-dlp returned invalid JSON", recoverable=True)

        title = info.get("title", "Unknown Video")
        description = info.get("description", "")
        channel = info.get("channel", info.get("uploader", ""))
        duration = info.get("duration", 0)
        upload_date = info.get("upload_date", "")
        categories = info.get("categories", [])
        tags = info.get("tags", [])

        # Step 2: Get subtitles/transcript
        transcript = ""
        cache_path.mkdir(parents=True, exist_ok=True)
        sub_path = cache_path / "subs"
        sub_path.mkdir(exist_ok=True)

        try:
            sub_result = subprocess.run(
                [
                    yt_dlp,
                    "--write-auto-subs",
                    "--write-subs",
                    "--sub-lang", "en",
                    "--sub-format", "vtt",
                    "--skip-download",
                    "-o", str(sub_path / "%(id)s.%(ext)s"),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Parse any VTT file found
            for vtt_file in sub_path.glob("*.vtt"):
                transcript = _parse_vtt(vtt_file)
                break
        except subprocess.TimeoutExpired:
            logger.warning("Subtitle download timed out for %s", url)
        except Exception as e:
            logger.warning("Subtitle extraction failed for %s: %s", url, e)

        # Build the text document
        sections: list[str] = []
        sections.append(f"# {title}")
        sections.append(f"Channel: {channel}")
        if upload_date:
            sections.append(f"Uploaded: {upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}")
        if duration:
            mins = duration // 60
            secs = duration % 60
            sections.append(f"Duration: {mins}m {secs}s")
        if categories:
            sections.append(f"Categories: {', '.join(categories)}")
        if tags:
            sections.append(f"Tags: {', '.join(tags[:20])}")

        sections.append("\n## Description\n")
        sections.append(description or "(No description)")

        if transcript:
            sections.append("\n## Transcript\n")
            sections.append(transcript)
        else:
            sections.append(
                "\n## Transcript\n(No transcript available — video may lack subtitles)"
            )

        text = "\n".join(sections)
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        meta = {
            "url": url,
            "title": title,
            "channel": channel,
            "duration": duration,
            "upload_date": upload_date,
            "has_transcript": bool(transcript),
            "handler": "youtube",
        }

        # Cache
        cached_text.write_text(text, encoding="utf-8")
        cached_meta.write_text(json.dumps(meta), encoding="utf-8")

        logger.info(
            "Extracted %d chars from YouTube video '%s' (transcript: %s)",
            len(text), title, "yes" if transcript else "no",
        )
        return ExtractedContent(
            text=text,
            metadata=meta,
            content_hash=content_hash,
            raw_content_path=cached_text,
        )


def _parse_vtt(path: Path) -> str:
    """Parse WebVTT file into clean transcript text, removing timestamps and duplicates."""
    lines: list[str] = []
    seen: set[str] = set()

    raw = path.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        line = line.strip()
        # Skip VTT headers, timestamps, blank lines
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}", line):
            continue
        if line.startswith("NOTE"):
            continue
        # Strip VTT tags like <c>, </c>, <00:00:01.000>
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)

    return " ".join(lines)
