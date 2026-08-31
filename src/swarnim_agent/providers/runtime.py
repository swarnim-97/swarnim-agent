from collections.abc import Mapping
from dataclasses import dataclass, field

from swarnim_agent.configuration.errors import (
    MissingCredentialError,
    UnsupportedProviderError,
)
from swarnim_agent.configuration.models import AppSettings


SUPPORTED_API_MODES = {"chat_completions"}


# Carries the fully resolved provider dependency without exposing its key in repr().
@dataclass(frozen=True)
class ProviderRuntime:
    """Contain the selected provider values required during execution."""

    provider: str
    model: str
    api_mode: str
    base_url: str
    api_key: str = field(repr=False)
    max_tokens: int = 1024


# Joins configuration and secrets at one boundary before client construction.
def resolve_provider_runtime(
    settings: AppSettings,
    secrets: Mapping[str, str],
) -> ProviderRuntime:
    """Combine selected non-secret settings with one resolved credential."""
    provider_name = settings.model.provider
    provider = settings.providers.get(provider_name)
    if provider is None:
        raise UnsupportedProviderError(
            f"Provider '{provider_name}' is not defined in config.yaml"
        )
    if provider.api_mode not in SUPPORTED_API_MODES:
        raise UnsupportedProviderError(
            f"API mode '{provider.api_mode}' is not supported"
        )

    api_key = secrets.get(provider.api_key_env, "").strip()
    if not api_key:
        raise MissingCredentialError(
            f"{provider.api_key_env} is not configured. "
            "Add it to the project .env or the process environment."
        )

    return ProviderRuntime(
        provider=provider_name,
        model=settings.model.name,
        api_mode=provider.api_mode,
        base_url=provider.base_url,
        api_key=api_key,
        max_tokens=settings.model.max_tokens,
    )
