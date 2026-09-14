#!/usr/bin/env python3
"""Build a concise human-review scorecard from a Gemini evaluation report."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


REVIEW_QUERY_INDEXES = (0, 1, 2, 3, 4, 5, 6, 8, 9, 12, 14, 15)


def clean(value: object) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def render(report: dict) -> str:
    evaluations = report["evaluations"]
    selected = [evaluations[index] for index in REVIEW_QUERY_INDEXES]
    lines = [
        "# PaperMast AI Librarian — human recommendation review",
        "",
        "This review uses the finalized constraint-aware retrieval strategy and a fresh Gemini run.",
        "It is deliberately subjective: judge whether each set feels useful and appealing to a real reader.",
        "",
        "## How to review",
        "",
        "For each prompt, mark **Good**, **Mixed**, or **Bad**. Add a short note only when something feels wrong.",
        "A set is **Good** if you would be comfortable showing it to a visitor, even if it is not perfect.",
        "",
    ]
    for review_number, item in enumerate(selected, 1):
        lines.extend([
            f"## {review_number}. {clean(item['query'])}",
            "",
            "**Overall:** [ ] Good  [ ] Mixed  [ ] Bad",
            "",
        ])
        for rank, recommendation in enumerate(item["recommendations"], 1):
            title = clean(recommendation["title"])
            authors = "; ".join(clean(author) for author in recommendation.get("authors") or [])
            reason = clean(recommendation["reason"])
            url = f"https://openlibrary.org{recommendation['work_key']}"
            lines.extend([
                f"{rank}. [{title}]({url}) — {authors or 'Unknown author'}",
                f"   - {reason}",
                "",
            ])
        lines.extend(["**Concern or replacement:**", "", "---", ""])
    lines.extend([
        "## Final questions",
        "",
        "1. Did any set feel too literal, repetitive, childish, obscure, or misleading?",
        "2. Were any explanations unconvincing or unsupported by the book shown?",
        "3. Would you be comfortable moving this retrieval strategy into backend integration?",
        "",
        "**Overall decision:** [ ] Proceed  [ ] Adjust first",
        "",
        "**Final notes:**",
        "",
        "## Run metadata",
        "",
        f"- Gemini model: `{report['gemini_model']}`",
        f"- Fresh evaluation queries: {report['query_count']}",
        f"- Review sets shown: {len(selected)}",
        f"- Input tokens: {report['total_input_tokens']:,}",
        f"- Output tokens: {report['total_output_tokens']:,}",
        f"- Paid-tier equivalent estimate: ${report['total_estimated_cost_usd']:.4f}",
        "- Actual free-tier charge: $0",
        "",
    ])
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=Path(".data/openlibrary/reports/gemini-reranking-evaluation.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(".data/openlibrary/reports/recommendation-human-review.md"),
    )
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    if report.get("status") != "complete" or report.get("query_count", 0) < 16:
        raise RuntimeError("a complete 16-query evaluation report is required")
    atomic_write(args.output, render(report))
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
