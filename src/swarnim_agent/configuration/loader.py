from collections.abc import Iterable, Mapping
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
import yaml

from swarnim_agent.configuration.errors import (
    ConfigurationError,
    MissingConfigurationError,
)
from swarnim_agent.configuration.models import (
    AppSettings,
    ModelSettings,
    ProviderSettings,
)


# Derives the repository root from src/swarnim_agent/configuration/loader.py.
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]


# Reads project YAML once so downstream layers receive validated settings.
def load_settings(project_root: Path | None = None) -> AppSettings:
    """Load and validate non-secret settings from the project root."""
    root = project_root or DEFAULT_PROJECT_ROOT
    config_path = root / "config.yaml"

    if not config_path.is_file():
        raise MissingConfigurationError(
            f"Configuration file not found at {config_path}. "
            "Create config.yaml in the project root before starting the CLI."
        )

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(
            f"Could not read configuration from {config_path}: {error}"
        ) from error

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a YAML mapping")

    return _parse_settings(raw)


# Resolves only declared credential names instead of copying the whole environment.
def load_secrets(
    secret_names: Iterable[str],
    project_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load file secrets, then apply explicit process-environment overrides."""
    root = project_root or DEFAULT_PROJECT_ROOT
    file_values = dotenv_values(root / ".env")
    environment = os.environ if environ is None else environ
    secrets: dict[str, str] = {}
    for name in secret_names:
        file_value = file_values.get(name)
        if isinstance(file_value, str) and file_value:
            secrets[name] = file_value
        environment_value = environment.get(name)
        if environment_value:
            secrets[name] = environment_value

    return secrets


# Converts untrusted YAML into the small typed contract used by the runtime.
def _parse_settings(raw: dict[str, Any]) -> AppSettings:
    model_raw = raw.get("model")
    providers_raw = raw.get("providers")
    if not isinstance(model_raw, dict):
        raise ConfigurationError("Configuration requires a 'model' mapping")
    if not isinstance(providers_raw, dict) or not providers_raw:
        raise ConfigurationError("Configuration requires a non-empty 'providers' mapping")

    provider_name = _required_text(model_raw, "provider", "model.provider")
    model_name = _required_text(model_raw, "name", "model.name")
    max_tokens = model_raw.get("max_tokens", 1024)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
        raise ConfigurationError("model.max_tokens must be a positive integer")

    providers: dict[str, ProviderSettings] = {}
    for name, provider_raw in providers_raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("Provider names must be non-empty strings")
        if not isinstance(provider_raw, dict):
            raise ConfigurationError(f"providers.{name} must be a mapping")
        providers[name.strip()] = ProviderSettings(
            api_mode=_required_text(
                provider_raw,
                "api_mode",
                f"providers.{name}.api_mode",
            ),
            base_url=_required_text(
                provider_raw,
                "base_url",
                f"providers.{name}.base_url",
            ).rstrip("/"),
            api_key_env=_required_text(
                provider_raw,
                "api_key_env",
                f"providers.{name}.api_key_env",
            ),
        )

    return AppSettings(
        model=ModelSettings(
            provider=provider_name,
            name=model_name,
            max_tokens=max_tokens,
        ),
        providers=providers,
    )


def _required_text(values: dict[str, Any], key: str, path: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{path} must be a non-empty string")
    return value.strip()
