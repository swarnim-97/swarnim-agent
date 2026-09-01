from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal


MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    """Represent one provider-independent conversation message."""

    role: MessageRole
    content: str


@dataclass(frozen=True)
class ProviderRequest:
    """Carry provider-ready parameters without performing the API call."""

    api_mode: str
    parameters: Mapping[str, object]


@dataclass(frozen=True)
class Usage:
    """Normalize token counts reported by a provider."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class NormalizedChunk:
    """Expose one provider-independent event from a streaming response."""

    text: str = ""
    finish_reason: str | None = None
    usage: Usage | None = None
