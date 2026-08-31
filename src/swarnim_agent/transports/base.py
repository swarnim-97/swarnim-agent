from typing import Protocol

from swarnim_agent.transports.types import (
    ChatMessage,
    NormalizedResponse,
    ProviderRequest,
)


# Defines provider-format responsibilities without requiring inheritance.
class ProviderTransport(Protocol):
    """Build provider requests and normalize provider responses."""

    @property
    def api_mode(self) -> str:
        """Return the wire protocol handled by this transport."""
        ...

    def build_request(
        self,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
    ) -> ProviderRequest:
        """Convert internal messages into a provider-ready request."""
        ...

    def normalize_response(self, raw_response: object) -> NormalizedResponse:
        """Convert a raw provider result into the shared response shape."""
        ...
