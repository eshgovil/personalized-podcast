import logging
from datetime import date

import typer

app = typer.Typer(help="PodForge — personalized podcast generator")


STAGE_NAMES = [
    "fetch",
    "summarize",
    "script",
    "synthesize",
    "deliver",
]


@app.command()
def generate(
    config: str = typer.Option(
        "config.yaml", "--config", "-c", help="Path to config file"
    ),
    target_date: str | None = typer.Option(
        None, "--date", "-d", help="Target date (YYYY-MM-DD), defaults to today"
    ),
    from_stage: str | None = typer.Option(
        None,
        "--from-stage",
        "-s",
        help="Re-run from this stage: fetch, summarize, script, synthesize, deliver",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Generate a podcast episode from configured sources."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from podforge.domain.value_objects.episode_status import (
        EpisodeStatus,
    )
    from podforge.main import build_and_run

    # Map CLI stage names to the status the episode should be rewound to
    stage_to_status: dict[str, EpisodeStatus] = {
        "fetch": EpisodeStatus.CREATED,
        "summarize": EpisodeStatus.ARTICLES_FETCHED,
        "script": EpisodeStatus.SUMMARIZED,
        "synthesize": EpisodeStatus.SCRIPTED,
        "deliver": EpisodeStatus.SYNTHESIZED,
    }

    rewind_status = None
    if from_stage:
        if from_stage not in stage_to_status:
            typer.echo(
                f"Unknown stage '{from_stage}'. Choose from: {', '.join(STAGE_NAMES)}"
            )
            raise typer.Exit(1)
        rewind_status = stage_to_status[from_stage]

    d = date.fromisoformat(target_date) if target_date else date.today()
    episode = build_and_run(config, d, from_stage=rewind_status)
    typer.echo(f"Episode delivered: {episode.audio_path}")
