from podforge.infrastructure.prompts import (
    build_script_writer_system,
    build_summarizer_system,
)


class TestSummarizerPrompt:
    def test_without_show_prompt(self) -> None:
        prompt = build_summarizer_system()
        assert "news editor" in prompt
        assert "Show direction" not in prompt

    def test_with_show_prompt(self) -> None:
        prompt = build_summarizer_system("Keep it spicy and opinionated.")
        assert "Show direction" in prompt
        assert "Keep it spicy and opinionated." in prompt

    def test_blank_show_prompt_is_omitted(self) -> None:
        prompt = build_summarizer_system("   ")
        assert "Show direction" not in prompt


class TestScriptWriterPrompt:
    def test_includes_host_descriptions(self) -> None:
        prompt = build_script_writer_system(
            target_length_minutes=5,
            host_descriptions="- Alice: Curious\n- Bob: Skeptical",
        )
        assert "Alice: Curious" in prompt
        assert "Bob: Skeptical" in prompt

    def test_calculates_target_words(self) -> None:
        prompt = build_script_writer_system(
            target_length_minutes=10,
            host_descriptions="- Host: Friendly",
        )
        assert "1500 words" in prompt
        assert "10 minutes" in prompt

    def test_with_show_prompt(self) -> None:
        prompt = build_script_writer_system(
            target_length_minutes=5,
            host_descriptions="- Host: Friendly",
            show_prompt="Be sarcastic and irreverent.",
        )
        assert "Show direction" in prompt
        assert "Be sarcastic and irreverent." in prompt

    def test_without_show_prompt(self) -> None:
        prompt = build_script_writer_system(
            target_length_minutes=5,
            host_descriptions="- Host: Friendly",
        )
        assert "Show direction" not in prompt
