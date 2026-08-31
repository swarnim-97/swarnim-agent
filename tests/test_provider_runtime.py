import pytest

from swarnim_agent.configuration.errors import (
    MissingCredentialError,
    UnsupportedProviderError,
)
from swarnim_agent.configuration.models import (
    AppSettings,
    ModelSettings,
    ProviderSettings,
)
from swarnim_agent.providers.runtime import resolve_provider_runtime


def create_settings(api_mode: str = "chat_completions") -> AppSettings:
    return AppSettings(
        model=ModelSettings(
            provider="nvidia",
            name="openai/gpt-oss-20b",
            max_tokens=256,
        ),
        providers={
            "nvidia": ProviderSettings(
                api_mode=api_mode,
                base_url="https://integrate.api.nvidia.com/v1",
                api_key_env="NVIDIA_API_KEY",
            )
        },
    )


def test_resolve_provider_runtime_combines_settings_and_secret() -> None:
    runtime = resolve_provider_runtime(
        create_settings(),
        {"NVIDIA_API_KEY": "secret-key"},
    )

    assert runtime.provider == "nvidia"
    assert runtime.model == "openai/gpt-oss-20b"
    assert runtime.api_mode == "chat_completions"
    assert runtime.api_key == "secret-key"
    assert runtime.max_tokens == 256
    assert "secret-key" not in repr(runtime)


def test_resolve_provider_runtime_reports_missing_credential() -> None:
    with pytest.raises(MissingCredentialError, match="NVIDIA_API_KEY"):
        resolve_provider_runtime(create_settings(), {})


def test_resolve_provider_runtime_rejects_unsupported_api_mode() -> None:
    with pytest.raises(UnsupportedProviderError, match="responses"):
        resolve_provider_runtime(
            create_settings(api_mode="responses"),
            {"NVIDIA_API_KEY": "secret-key"},
        )
