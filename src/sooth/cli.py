"""CLI: sooth. File I/O, exit codes, --log writer."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sooth.claims import split_claims
from sooth.report import exit_code, log_record, render_markdown, render_plain, verdicts_from_record
from sooth.verify import DEFAULT_THRESHOLD, VerifyError, verify_claims

DEMO_RECORD = Path(__file__).with_name("demo.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="sooth",
        description="Verify AI-generated text against source material. "
                    "Each claim gets PASS / FAIL / REVIEW with calibrated probabilities.",
    )
    p.add_argument("command", nargs="?", choices=["demo"],
                   help="run the offline demo against a bundled recorded run (no API key)")
    p.add_argument("--source", action="append", metavar="FILE",
                   help="ground-truth source file (repeatable)")
    p.add_argument("--text", metavar="FILE", help="AI-generated draft to check")
    p.add_argument("--confidence", type=float, default=DEFAULT_THRESHOLD, metavar="T",
                   help=f"REVIEW below this confidence (default {DEFAULT_THRESHOLD})")
    p.add_argument("--format", choices=["md", "plain"], default="md", help="report format")
    p.add_argument("-o", "--output", metavar="FILE", help="write report to file instead of stdout")
    p.add_argument("--log", metavar="FILE", help="append full judgment trace as one JSONL line")
    return p.parse_args(argv)


def run_demo(fmt: str) -> int:
    """Replay a bundled judgment trace through the real report code. No network."""
    record = json.loads(DEMO_RECORD.read_text(encoding="utf-8"))
    print(
        "demo: replaying a recorded run "
        f"({record['draft']} vs {', '.join(record['sources'])}) — no API key needed",
        file=sys.stderr,
    )
    verdicts = verdicts_from_record(record)
    report = (render_markdown if fmt == "md" else render_plain)(
        verdicts, threshold=record["threshold"]
    )
    print(report, end="")
    return exit_code(verdicts)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "demo":
        return run_demo(args.format)
    if not args.source or not args.text:
        print("error: --source and --text are required (or try: sooth demo)", file=sys.stderr)
        return 3
    try:
        sources = [(path, Path(path).read_text(encoding="utf-8")) for path in args.source]
        draft = Path(args.text).read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    if not draft.strip():
        print("error: empty draft", file=sys.stderr)
        return 3
    if any(not text.strip() for _, text in sources):
        print("error: empty source file", file=sys.stderr)
        return 3

    claims = split_claims(draft)
    if not claims:
        print("error: no claims found in draft", file=sys.stderr)
        return 3

    try:
        result = verify_claims(claims, sources, threshold=args.confidence)
    except VerifyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3

    report = (render_markdown if args.format == "md" else render_plain)(
        result.verdicts, threshold=args.confidence
    )
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report, end="")

    if args.log:
        record = log_record(result, threshold=args.confidence,
                            sources=[path for path, _ in sources], draft=args.text)
        record["ts"] = datetime.now(UTC).isoformat(timespec="seconds")
        with Path(args.log).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    return exit_code(result.verdicts)


if __name__ == "__main__":
    raise SystemExit(main())
