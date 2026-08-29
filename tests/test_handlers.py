from swarnim_agent.cli.handlers import should_exit


def test_should_exit_recognizes_command() -> None:
    assert should_exit(" /EXIT ") is True


def test_should_exit_rejects_regular_text() -> None:
    assert should_exit("exit") is False
