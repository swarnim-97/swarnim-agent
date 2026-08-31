from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSettings:
    """Describe the model selected for the application."""

    provider: str
    name: str
    max_tokens: int


@dataclass(frozen=True)
class ProviderSettings:
    """Describe one provider without including its secret value."""

    api_mode: str
    base_url: str
    api_key_env: str


# Keeps validated settings explicit instead of passing nested dictionaries.
@dataclass(frozen=True)
class AppSettings:
    """Contain all non-secret settings needed to resolve a model runtime."""

    model: ModelSettings
    providers: dict[str, ProviderSettings]
