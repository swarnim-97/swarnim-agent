from swarnim_agent.cli.handlers import should_exit, text_length


def test_text_length_returns_character_count_as_text() -> None:
    assert text_length("hello") == "5"


def test_text_length_counts_whitespace() -> None:
    assert text_length(" a ") == "3"


def test_should_exit_recognizes_command() -> None:
    assert should_exit(" /EXIT ") is True


def test_should_exit_rejects_regular_text() -> None:
    assert should_exit("exit") is False
