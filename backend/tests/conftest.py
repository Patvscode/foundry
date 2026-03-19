from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "foundry-data"
    monkeypatch.setenv("FOUNDRY_STORAGE__DATA_DIR", str(data_dir))
    monkeypatch.setenv("FOUNDRY_AGENT__DEFAULT_PROVIDER", "none")
    return data_dir
