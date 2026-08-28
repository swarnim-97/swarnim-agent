EXIT_COMMAND = "/exit"


def should_exit(text: str) -> bool:
    """Return whether the submitted text asks the CLI to close."""
    return text.strip().lower() == EXIT_COMMAND


def text_length(text: str) -> str:
    """Return the number of submitted characters as text."""
    return str(len(text))
