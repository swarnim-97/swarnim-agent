from typing import Any

from swarnim_agent.transports.errors import ProviderResponseError
from swarnim_agent.transports.types import (
    ChatMessage,
    NormalizedResponse,
    ProviderRequest,
    Usage,
)


# Reuses one OpenAI-compatible wire format across vendors such as NVIDIA.
class ChatCompletionsTransport:
    """Build and normalize OpenAI-compatible Chat Completions data."""

    @property
    def api_mode(self) -> str:
        """Return the API mode handled by this transport."""
        return "chat_completions"

    def build_request(
        self,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
    ) -> ProviderRequest:
        """Build a non-streaming Chat Completions request."""
        return ProviderRequest(
            api_mode=self.api_mode,
            parameters={
                "model": model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
                "max_tokens": max_tokens,
                "stream": False,
            },
        )

    # Defensively reduces an SDK-specific response to the fields our agent uses.
    def normalize_response(self, raw_response: object) -> NormalizedResponse:
        choices = getattr(raw_response, "choices", None)
        if not choices:
            raise ProviderResponseError("Provider response contains no choices")

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("Provider response contains no text content")

        finish_reason = getattr(first_choice, "finish_reason", None)
        if not isinstance(finish_reason, str) or not finish_reason:
            finish_reason = "unknown"

        return NormalizedResponse(
            content=content.strip(),
            finish_reason=finish_reason,
            usage=self._normalize_usage(getattr(raw_response, "usage", None)),
        )

    def _normalize_usage(self, raw_usage: Any) -> Usage | None:
        if raw_usage is None:
            return None

        input_tokens = getattr(raw_usage, "prompt_tokens", None)
        output_tokens = getattr(raw_usage, "completion_tokens", None)
        total_tokens = getattr(raw_usage, "total_tokens", None)
        if not all(
            isinstance(value, int)
            for value in (input_tokens, output_tokens, total_tokens)
        ):
            return None

        return Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
