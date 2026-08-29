from swarnim_agent.agents.character_count import CharacterCountAgent


def test_character_count_agent_streams_lines_in_order() -> None:
    agent = CharacterCountAgent()

    assert list(agent.run("hello")) == [
        "Calculating character count...",
        "5",
    ]


def test_character_count_agent_counts_whitespace() -> None:
    agent = CharacterCountAgent()

    assert list(agent.run(" a ")) == [
        "Calculating character count...",
        "3",
    ]


def test_character_count_agent_creates_independent_streams() -> None:
    agent = CharacterCountAgent()

    first_stream = agent.run("a")
    second_stream = agent.run("hello")

    assert first_stream is not second_stream
    assert list(first_stream) == ["Calculating character count...", "1"]
    assert list(second_stream) == ["Calculating character count...", "5"]
