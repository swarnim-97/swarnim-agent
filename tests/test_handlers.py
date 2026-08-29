from swarnim_agent.cli.handlers import (
    should_exit,
    text_length,
    text_length_lines,
)


def test_text_length_returns_character_count_as_text() -> None:
    assert text_length("hello") == "5"


def test_text_length_counts_whitespace() -> None:
    assert text_length(" a ") == "3"


def test_text_length_lines_yields_processing_lines_in_order() -> None:
    assert list(text_length_lines("hello")) == [
        "Calculating character count...",
        "5",
    ]


def test_should_exit_recognizes_command() -> None:
    assert should_exit(" /EXIT ") is True


def test_should_exit_rejects_regular_text() -> None:
    assert should_exit("exit") is False
