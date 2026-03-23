from podforge.infrastructure.prompts import (
    build_script_writer_system,
    build_script_writer_user,
    build_summarizer_system,
    build_summarizer_user,
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

    def test_show_prompt_with_curly_braces(self) -> None:
        prompt = build_summarizer_system("Output as {json} format")
        assert "{json}" in prompt


class TestSummarizerUserPrompt:
    def test_includes_articles_text(self) -> None:
        prompt = build_summarizer_user("Article about AI breakthroughs.")
        assert "Article about AI breakthroughs." in prompt

    def test_curly_braces_in_article_text(self) -> None:
        prompt = build_summarizer_user('const x = {key: "value"}')
        assert '{key: "value"}' in prompt


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

    def test_show_prompt_separated_from_output_instructions(self) -> None:
        prompt = build_script_writer_system(
            target_length_minutes=5,
            host_descriptions="- Host: Friendly",
            show_prompt="Be fast-paced.",
        )
        # Show direction and output instructions should not run together
        assert "Be fast-paced.\nOutput ONLY" not in prompt


class TestScriptWriterUserPrompt:
    def test_includes_summary(self) -> None:
        prompt = build_script_writer_user("Today's top stories include...")
        assert "Today's top stories include..." in prompt

    def test_curly_braces_in_summary(self) -> None:
        prompt = build_script_writer_user("The API returns {data: [...]}")
        assert "{data: [...]}" in prompt
