from collections.abc import Iterator


class CharacterCountAgent:
    """Produce deterministic character-count output for learning."""

    def run(self, text: str) -> Iterator[str]:
        """Yield a status line followed by the submitted character count."""
        yield "Calculating character count..."
        yield str(len(text))
