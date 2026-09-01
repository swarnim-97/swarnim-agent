from swarnim_agent.agents.line_buffer import LineBuffer


def test_line_buffer_returns_complete_line() -> None:
    buffer = LineBuffer()

    assert buffer.push("Hello\n") == ["Hello"]
    assert buffer.finish() == []


def test_line_buffer_combines_partial_chunks() -> None:
    buffer = LineBuffer()

    assert buffer.push("Hello wor") == []
    assert buffer.push("ld\nSecond") == ["Hello world"]
    assert buffer.finish() == ["Second"]


def test_line_buffer_returns_multiple_lines_and_preserves_blanks() -> None:
    buffer = LineBuffer()

    assert buffer.push("First\n\nSecond\n") == ["First", "", "Second"]


def test_line_buffer_supports_split_crlf() -> None:
    buffer = LineBuffer()

    assert buffer.push("First\r") == []
    assert buffer.push("\nSecond\r\n") == ["First", "Second"]


def test_line_buffer_ignores_empty_chunks() -> None:
    buffer = LineBuffer()

    assert buffer.push("") == []
    assert buffer.finish() == []


def test_line_buffer_can_be_reused_after_finish() -> None:
    buffer = LineBuffer()

    assert buffer.push("First") == []
    assert buffer.finish() == ["First"]
    assert buffer.push("Second\n") == ["Second"]
