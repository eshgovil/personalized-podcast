"""Prompt templates for LLM adapters.

The public API is the four `build_*` functions. Templates are internal.
"""


def show_prompt_section(show_prompt: str) -> str:
    """Wrap show_prompt in a labeled section, or return empty string."""
    if not show_prompt.strip():
        return ""
    return f"\nShow direction:\n{show_prompt.strip()}\n"


# --- Summarizer -----------------------------------------------------------

_SUMMARIZER_SYSTEM = """\
You are a news editor preparing a briefing for a podcast.

Summarize the following articles into a concise briefing.
Group related stories together.
Highlight what is most interesting, surprising, or consequential.
Keep it factual but engaging.
Write in a way that gives podcast hosts enough material to have a natural \
conversation.
{show_prompt_section}"""


def build_summarizer_system(show_prompt: str = "") -> str:
    return _SUMMARIZER_SYSTEM.format(
        show_prompt_section=show_prompt_section(show_prompt),
    )


def build_summarizer_user(articles_text: str) -> str:
    return f"Summarize these articles for today's podcast:\n\n{articles_text}"


# --- Script Writer --------------------------------------------------------

_SCRIPT_WRITER_SYSTEM = """\
You are a podcast script writer. Write a natural, engaging conversation \
between podcast hosts discussing today's news.

The conversation should feel authentic — hosts can agree, disagree, ask \
follow-up questions, make jokes, and share opinions based on their \
personalities.

Target length: ~{target_words} words ({target_length_minutes} minutes of audio)

Hosts:
{host_descriptions}
{show_prompt_section}
Output ONLY a JSON array of objects with these fields:
- "host_name": the speaking host's name (must match exactly)
- "text": what they say (natural spoken language, not written prose)
- "segment_type": one of "intro", "discussion", "transition", "outro"

Start with an intro where hosts greet listeners, cover the main stories with \
natural back-and-forth discussion, use transitions between topics, and end \
with a brief outro. Keep the dialogue conversational — short turns, reactions, \
and follow-ups feel more natural than long monologues."""


def build_script_writer_system(
    target_length_minutes: int,
    host_descriptions: str,
    show_prompt: str = "",
) -> str:
    target_words = target_length_minutes * 150
    return _SCRIPT_WRITER_SYSTEM.format(
        target_words=target_words,
        target_length_minutes=target_length_minutes,
        host_descriptions=host_descriptions,
        show_prompt_section=show_prompt_section(show_prompt),
    )


def build_script_writer_user(summary: str) -> str:
    return f"Write a podcast script for this briefing:\n\n{summary}"
