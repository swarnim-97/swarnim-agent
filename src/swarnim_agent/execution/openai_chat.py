from collections.abc import Iterable
from typing import Any

from openai import OpenAI

from swarnim_agent.transports.types import ProviderRequest


# Owns the OpenAI-compatible client while leaving request shape to the transport.
class OpenAIChatExecutor:
    """Execute Chat Completions requests through an OpenAI-compatible client."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        client: Any | None = None,
    ) -> None:
        self._client = (
            client
            if client is not None
            else OpenAI(base_url=base_url, api_key=api_key)
        )

    def execute(self, request: ProviderRequest) -> Iterable[object]:
        """Send one request and return the raw Chat Completions stream."""
        if request.api_mode != "chat_completions":
            raise ValueError(
                f"OpenAIChatExecutor cannot execute API mode '{request.api_mode}'"
            )
        return self._client.chat.completions.create(**dict(request.parameters))
