"""Command-line interface for the manuscript reviewer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .pipeline import ReviewPipeline
from .rubrics import list_rubrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manuscript-reviewer",
        description="Multi-agent peer review (triage -> 2 reviewers -> judge).",
    )
    parser.add_argument("manuscript", nargs="?", help="Path to the manuscript (PDF/txt/md)")
    parser.add_argument("-c", "--config", help="Path to config.yaml")
    parser.add_argument(
        "-o", "--output", help="Write the Markdown report to this file"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit the report as JSON instead of Markdown"
    )
    parser.add_argument(
        "--list-rubrics", action="store_true", help="List available rubrics and exit"
    )
    args = parser.parse_args(argv)

    # Load .env for API keys if python-dotenv is available (optional).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    if args.list_rubrics:
        for rid in list_rubrics():
            print(rid)
        return 0

    if not args.manuscript:
        parser.error("a manuscript path is required (or use --list-rubrics)")

    if not Path(args.manuscript).exists():
        print(f"Error: file not found: {args.manuscript}", file=sys.stderr)
        return 2

    config = load_config(args.config)
    pipeline = ReviewPipeline(config)

    print("Reviewing manuscript… (this may take a while with real models)",
          file=sys.stderr)
    report = pipeline.run(args.manuscript)

    rendered = report.to_json() if args.json else report.to_markdown()

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
