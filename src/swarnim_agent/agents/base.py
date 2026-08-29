from collections.abc import Iterable
from typing import Protocol


class Agent(Protocol):
    """Define the streaming contract for processing one user input."""

    def run(self, text: str) -> Iterable[str]:
        """Produce complete output lines for the submitted text."""
        ...
