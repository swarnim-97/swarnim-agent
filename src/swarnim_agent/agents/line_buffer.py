# Assembles arbitrary text deltas while preserving complete-line formatting.
class LineBuffer:
    """Convert partial text chunks into complete terminal lines."""

    def __init__(self) -> None:
        self._pending = ""

    # Holds the unfinished suffix and returns every line completed by this chunk.
    def push(self, text: str) -> list[str]:
        if not text:
            return []

        parts = (self._pending + text).split("\n")
        self._pending = parts.pop()
        return [self._remove_carriage_return(line) for line in parts]

    def finish(self) -> list[str]:
        """Return the final unterminated line and clear buffered state."""
        if not self._pending:
            return []

        line = self._remove_carriage_return(self._pending)
        self._pending = ""
        return [line]

    @staticmethod
    def _remove_carriage_return(line: str) -> str:
        return line[:-1] if line.endswith("\r") else line
