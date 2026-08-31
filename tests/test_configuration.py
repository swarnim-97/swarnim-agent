from pathlib import Path

import pytest

from swarnim_agent.configuration import loader
from swarnim_agent.configuration.errors import (
    ConfigurationError,
    MissingConfigurationError,
)
from swarnim_agent.configuration.loader import load_secrets, load_settings


VALID_CONFIG = """\
model:
  provider: nvidia
  name: openai/gpt-oss-20b
  max_tokens: 256
providers:
  nvidia:
    api_mode: chat_completions
    base_url: https://integrate.api.nvidia.com/v1/
    api_key_env: NVIDIA_API_KEY
"""


def test_load_settings_returns_typed_configuration(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(VALID_CONFIG, encoding="utf-8")

    settings = load_settings(tmp_path)

    assert settings.model.provider == "nvidia"
    assert settings.model.name == "openai/gpt-oss-20b"
    assert settings.model.max_tokens == 256
    assert settings.providers["nvidia"].base_url == (
        "https://integrate.api.nvidia.com/v1"
    )


def test_load_settings_uses_config_from_default_project_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "config.yaml").write_text(VALID_CONFIG, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_PROJECT_ROOT", tmp_path)

    settings = load_settings()

    assert settings.model.provider == "nvidia"


def test_load_settings_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MissingConfigurationError, match="config.yaml"):
        load_settings(tmp_path)


def test_load_settings_rejects_invalid_max_tokens(tmp_path: Path) -> None:
    invalid = VALID_CONFIG.replace("max_tokens: 256", "max_tokens: zero")
    (tmp_path / "config.yaml").write_text(invalid, encoding="utf-8")

    with pytest.raises(ConfigurationError, match="positive integer"):
        load_settings(tmp_path)


def test_load_secrets_prefers_process_environment(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "NVIDIA_API_KEY=file-key\nUNRELATED_SECRET=ignored\n",
        encoding="utf-8",
    )

    secrets = load_secrets(
        {"NVIDIA_API_KEY"},
        tmp_path,
        environ={"NVIDIA_API_KEY": "environment-key"},
    )

    assert secrets == {"NVIDIA_API_KEY": "environment-key"}


def test_load_secrets_uses_dotenv_when_environment_is_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "NVIDIA_API_KEY=file-key\n",
        encoding="utf-8",
    )

    secrets = load_secrets({"NVIDIA_API_KEY"}, tmp_path, environ={})

    assert secrets == {"NVIDIA_API_KEY": "file-key"}
