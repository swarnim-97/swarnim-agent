from swarnim_agent.cli.handlers import echo_text, should_exit


def test_echo_text_returns_input_unchanged() -> None:
    assert echo_text("Hello, CLI!") == "Hello, CLI!"


def test_echo_text_preserves_whitespace() -> None:
    assert echo_text("  keep this spacing  ") == "  keep this spacing  "


def test_should_exit_recognizes_command() -> None:
    assert should_exit(" /EXIT ") is True


def test_should_exit_rejects_regular_text() -> None:
    assert should_exit("exit") is False
