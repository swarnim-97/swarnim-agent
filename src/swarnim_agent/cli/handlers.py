EXIT_COMMAND = "/exit"


def should_exit(text: str) -> bool:
    """Return whether the submitted text asks the CLI to close."""
    return text.strip().lower() == EXIT_COMMAND


def echo_text(text: str):
    """Return submitted text unchanged."""
    return len(text)
