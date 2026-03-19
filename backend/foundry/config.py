from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8120


class AuthSettings(BaseModel):
    method: str = "none"
    pin: str = ""
    session_timeout: str = "24h"


class StorageSettings(BaseModel):
    data_dir: str = "~/.foundry"

    @field_validator("data_dir")
    @classmethod
    def _expand_data_dir(cls, value: str) -> str:
        return str(Path(value).expanduser())


class AgentInteractionSettings(BaseModel):
    style: str = "collaborative"


class AgentConfirmationSettings(BaseModel):
    on_delete: bool = True
    on_git_push: bool = True
    on_large_write: bool = True
    on_first_execute: bool = True
    large_write_kb: int = 50


class OllamaProviderSettings(BaseModel):
    base_url: str = "http://localhost:11434"


class OpenAIProviderSettings(BaseModel):
    api_key: str = ""


class AnthropicProviderSettings(BaseModel):
    api_key: str = ""


class OpenClawProviderSettings(BaseModel):
    gateway_url: str = "http://localhost:18789"


class AgentProviderSettings(BaseModel):
    ollama: OllamaProviderSettings = Field(default_factory=OllamaProviderSettings)
    openai: OpenAIProviderSettings = Field(default_factory=OpenAIProviderSettings)
    anthropic: AnthropicProviderSettings = Field(default_factory=AnthropicProviderSettings)
    openclaw: OpenClawProviderSettings = Field(default_factory=OpenClawProviderSettings)


class AgentSettings(BaseModel):
    default_provider: str = "ollama"
    default_model: str = ""
    can_read: bool = True
    can_search: bool = True
    can_explain: bool = True
    can_propose: bool = True
    can_write: bool = False
    can_execute: bool = False
    can_network: bool = False
    can_git: bool = False
    can_install: bool = False
    interaction: AgentInteractionSettings = Field(default_factory=AgentInteractionSettings)
    confirmations: AgentConfirmationSettings = Field(default_factory=AgentConfirmationSettings)
    providers: AgentProviderSettings = Field(default_factory=AgentProviderSettings)


class IngestionSettings(BaseModel):
    max_concurrent: int = 3
    cache_dir: str = "~/.foundry/cache"
    cache_ttl_days: int = 30
    transcript_method: str = "auto"

    @field_validator("cache_dir")
    @classmethod
    def _expand_cache_dir(cls, value: str) -> str:
        return str(Path(value).expanduser())


class ExecutionSettings(BaseModel):
    workspace_scope: str = "project"
    default_timeout: int = 600
    max_concurrent: int = 3
    show_output: bool = True


class WorkspaceSettings(BaseModel):
    auto_commit: bool = True
    reconcile_mode: str = "detect"


class SearchSettings(BaseModel):
    engine: str = "fts5"


class UISettings(BaseModel):
    theme: str = "dark"
    default_layout: str = "three-panel"


class BackupSettings(BaseModel):
    enabled: bool = True
    interval_hours: int = 24
    keep_count: int = 7


class LoggingSettings(BaseModel):
    level: str = "INFO"


class FoundrySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FOUNDRY_",
        env_nested_delimiter="__",
        extra="ignore",
        validate_assignment=True,
    )

    server: ServerSettings = Field(default_factory=ServerSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    workspace: WorkspaceSettings = Field(default_factory=WorkspaceSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    ui: UISettings = Field(default_factory=UISettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            env_settings,
            file_secret_settings,
        )

    @model_validator(mode="after")
    def _expand_and_prepare_paths(self) -> FoundrySettings:
        data_dir = Path(self.storage.data_dir).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(data_dir, 0o700)
        self.storage.data_dir = str(data_dir)

        ingestion_cache = Path(self.ingestion.cache_dir).expanduser()
        self.ingestion.cache_dir = str(ingestion_cache)
        return self


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)

    def _load_file_data(self) -> dict[str, Any]:
        config_path = Path("~/.foundry/config.toml").expanduser()
        if not config_path.exists():
            return {}
        with config_path.open("rb") as handle:
            return tomllib.load(handle)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        data = self._load_file_data()
        if field_name in data:
            return data[field_name], field_name, False
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._load_file_data()


def get_settings() -> FoundrySettings:
    return FoundrySettings()


def mask_secrets(data: dict[str, Any]) -> dict[str, Any]:
    def _mask(value: Any, key: str) -> Any:
        lowered = key.lower()
        if isinstance(value, dict):
            return {k: _mask(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [_mask(item, key) for item in value]
        if any(secret in lowered for secret in ("api_key", "token", "pin", "secret", "password")):
            if isinstance(value, str) and value:
                return "***"
        return value

    return {k: _mask(v, k) for k, v in data.items()}
