from typing import Any

from swarnim_agent.transports.errors import ProviderResponseError
from swarnim_agent.transports.types import (
    ChatMessage,
    NormalizedChunk,
    ProviderRequest,
    Usage,
)


# Reuses one Chat Completions wire format across compatible providers.
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
        """Build a streaming Chat Completions request."""
        return ProviderRequest(
            api_mode=self.api_mode,
            parameters={
                "model": model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
                "max_tokens": max_tokens,
                "stream": True,
            },
        )

    # Accepts content, finish, and usage-only events without leaking SDK shapes.
    def normalize_chunk(self, raw_chunk: object) -> NormalizedChunk:
        missing = object()
        choices = getattr(raw_chunk, "choices", missing)
        if choices is missing or choices is None:
            raise ProviderResponseError("Provider stream chunk has no choices field")

        usage = self._normalize_usage(getattr(raw_chunk, "usage", None))
        if not choices:
            return NormalizedChunk(usage=usage)

        first_choice = choices[0]
        delta = getattr(first_choice, "delta", None)
        content = getattr(delta, "content", None)
        if content is not None and not isinstance(content, str):
            raise ProviderResponseError(
                "Provider stream chunk contains non-text content"
            )

        finish_reason = getattr(first_choice, "finish_reason", None)
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise ProviderResponseError(
                "Provider stream chunk has an invalid finish reason"
            )

        return NormalizedChunk(
            text=content or "",
            finish_reason=finish_reason,
            usage=usage,
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
