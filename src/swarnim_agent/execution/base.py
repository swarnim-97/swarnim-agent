from collections.abc import Iterable
from typing import Protocol

from swarnim_agent.transports.types import ProviderRequest


# Keeps network execution replaceable in agent and unit tests.
class ProviderExecutor(Protocol):
    """Execute a provider-ready request and return its raw response."""

    def execute(self, request: ProviderRequest) -> Iterable[object]:
        """Perform one provider call and return its raw stream iterator."""
        ...
