from collections.abc import Iterator

from swarnim_agent.execution.base import ProviderExecutor
from swarnim_agent.transports.base import ProviderTransport
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

    # Keeps the worker's line iterator contract while the API call is non-streaming.
    def run(self, text: str) -> Iterator[str]:
        yield "Waiting for model response..."
        request = self._transport.build_request(
            model=self._model,
            messages=[ChatMessage(role="user", content=text)],
            max_tokens=self._max_tokens,
        )
        raw_response = self._executor.execute(request)
        response = self._transport.normalize_response(raw_response)

        for line in response.content.splitlines():
            if line.strip():
                yield line
