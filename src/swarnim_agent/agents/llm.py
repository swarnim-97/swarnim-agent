from collections.abc import Iterator

from swarnim_agent.agents.line_buffer import LineBuffer
from swarnim_agent.execution.base import ProviderExecutor
from swarnim_agent.transports.base import ProviderTransport
from swarnim_agent.transports.errors import ProviderResponseError
from swarnim_agent.transports.types import ChatMessage


# Coordinates model execution without owning provider formatting or networking.
class LLMAgent:
    """Process one user input through an injected transport and executor."""

    def __init__(
        self,
        model: str,
        max_tokens: int,
        transport: ProviderTransport,
        executor: ProviderExecutor,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._transport = transport
        self._executor = executor

    # Converts provider deltas into complete lines without exposing SDK chunks.
    def run(self, text: str) -> Iterator[str]:
        yield "Waiting for model response..."
        request = self._transport.build_request(
            model=self._model,
            messages=[ChatMessage(role="user", content=text)],
            max_tokens=self._max_tokens,
        )
        raw_chunks = self._executor.execute(request)
        line_buffer = LineBuffer()
        received_text = False

        for raw_chunk in raw_chunks:
            chunk = self._transport.normalize_chunk(raw_chunk)
            if not chunk.text:
                continue

            received_text = True
            yield from line_buffer.push(chunk.text)

        if not received_text:
            raise ProviderResponseError(
                "Provider stream contains no text content"
            )

        yield from line_buffer.finish()
