#!/usr/bin/env python3
"""Download, profile, and merge Open Library dumps locally."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import heapq
import json
import os
import platform
import random
import re
import resource
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import orjson

from catalog_builder import (
    catalog_status,
    classify_fiction,
    ingest_dataset,
    prepare_retrieval_documents,
    rebuild_catalog,
)


PROFILER_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = 1
DEFAULT_DUMP_URL = "https://openlibrary.org/data/ol_dump_works_latest.txt.gz"
DUMP_URLS = {
    "works": DEFAULT_DUMP_URL,
    "editions": "https://openlibrary.org/data/ol_dump_editions_latest.txt.gz",
    "authors": "https://openlibrary.org/data/ol_dump_authors_latest.txt.gz",
}
CHUNK_SIZE = 1024 * 1024
PROGRESS_BYTES = 64 * 1024 * 1024


class BoundedCounter:
    """Space-Saving heavy-hitter counter with a fixed upper memory bound."""

    def __init__(self, capacity: int = 10_000) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.counts: Dict[str, Tuple[int, int]] = {}
        self.heap: List[Tuple[int, str]] = []

    def add(self, value: str) -> None:
        if value in self.counts:
            count, error = self.counts[value]
            self.counts[value] = (count + 1, error)
            heapq.heappush(self.heap, (count + 1, value))
            self._compact_heap_if_needed()
            return
        if len(self.counts) < self.capacity:
            self.counts[value] = (1, 0)
            heapq.heappush(self.heap, (1, value))
            return
        minimum, replaced = heapq.heappop(self.heap)
        while replaced not in self.counts or self.counts[replaced][0] != minimum:
            minimum, replaced = heapq.heappop(self.heap)
        del self.counts[replaced]
        self.counts[value] = (minimum + 1, minimum)
        heapq.heappush(self.heap, (minimum + 1, value))
        self._compact_heap_if_needed()

    def _compact_heap_if_needed(self) -> None:
        if len(self.heap) > self.capacity * 4:
            self.heap = [(count, key) for key, (count, _) in self.counts.items()]
            heapq.heapify(self.heap)

    def top(self, count: int) -> List[Dict[str, Any]]:
        return [
            {"subject": subject, "approximate_count": value[0], "maximum_error": value[1]}
            for subject, value in sorted(
                self.counts.items(), key=lambda item: (-item[1][0], item[0])
            )[:count]
        ]


class ReservoirSampler:
    def __init__(self, size: int, seed: int) -> None:
        self.size = size
        self.seen = 0
        self.items: List[Dict[str, Any]] = []
        self.random = random.Random(seed)

    def add(self, item: Dict[str, Any]) -> None:
        self.seen += 1
        if len(self.items) < self.size:
            self.items.append(item)
            return
        replacement = self.random.randrange(self.seen)
        if replacement < self.size:
            self.items[replacement] = item


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def file_hashes(path: Path, algorithms: Iterable[str]) -> Dict[str, str]:
    digests = {algorithm: hashlib.new(algorithm) for algorithm in algorithms}
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                return {name: digest.hexdigest() for name, digest in digests.items()}
            for digest in digests.values():
                digest.update(chunk)


def archive_identifier(resolved_url: str) -> Optional[str]:
    match = re.search(r"archive\.org/download/([^/]+)/", resolved_url)
    if not match:
        match = re.search(r"\.archive\.org/(?:\d+/)?items/([^/]+)/", resolved_url)
    return match.group(1) if match else None


def archive_md5(resolved_url: str, filename: str) -> Optional[str]:
    identifier = archive_identifier(resolved_url)
    if not identifier:
        return None
    metadata_url = f"https://archive.org/metadata/{identifier}"
    try:
        with urllib.request.urlopen(metadata_url, timeout=60) as response:
            metadata = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return None
    for item in metadata.get("files", []):
        if item.get("name") == filename:
            return item.get("md5")
    return None


def resolved_filename(response: Any) -> str:
    name = unquote(Path(urlparse(response.geturl()).path).name)
    if not name.endswith(".txt.gz"):
        raise ValueError(f"resolved URL does not name an Open Library dump: {name}")
    return name


def resolve_dump_url(url: str) -> Tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperMast-OpenLibrary-Profiler/1.0"},
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.geturl(), resolved_filename(response)
    except urllib.error.URLError as error:
        raise RuntimeError(f"could not resolve latest dump URL: {error.reason}") from error


def write_download_metadata(
    final_path: Path,
    source_url: str,
    resolved_url: str,
    hashes: Dict[str, str],
    expected_md5: Optional[str],
    downloaded_at_utc: Optional[str],
) -> None:
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", final_path.name)
    metadata = {
        "schema_version": 1,
        "source_url": source_url,
        "resolved_url": resolved_url,
        "filename": final_path.name,
        "dump_date": date_match.group(1) if date_match else None,
        "downloaded_at_utc": downloaded_at_utc,
        "verified_at_utc": utc_now(),
        "size_bytes": final_path.stat().st_size,
        "sha256": hashes["sha256"],
        "archive_md5": expected_md5,
        "archive_md5_verified": expected_md5 is not None and hashes["md5"] == expected_md5,
    }
    atomic_write_text(
        final_path.with_suffix(final_path.suffix + ".metadata.json"),
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )


def download_dump(url: str, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    resolved_url, filename = resolve_dump_url(url)
    final_path = output / filename
    partial = output / f"{filename}.part"
    if final_path.is_file():
        expected_md5 = archive_md5(resolved_url, filename)
        hashes = file_hashes(final_path, ["sha256", "md5"])
        if expected_md5 and hashes["md5"] != expected_md5:
            raise RuntimeError(f"existing dump failed archive checksum verification: {final_path}")
        write_download_metadata(final_path, url, resolved_url, hashes, expected_md5, None)
        print(f"Already downloaded and verified: {final_path}")
        return final_path
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "PaperMast-OpenLibrary-Profiler/1.0"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(resolved_url, headers=headers)

    try:
        response = urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as error:
        if error.code == 416 and partial.exists():
            partial.unlink()
            return download_dump(url, output)
        raise RuntimeError(f"download failed with HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"download failed: {error.reason}") from error

    with response:
        resumed = existing > 0 and getattr(response, "status", None) == 206
        mode = "ab" if resumed else "wb"
        if existing and not resumed:
            existing = 0
        downloaded = existing
        next_progress = ((downloaded // PROGRESS_BYTES) + 1) * PROGRESS_BYTES
        with partial.open(mode) as handle:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_progress:
                    print(f"Downloaded {downloaded / (1024 ** 3):.2f} GiB...", flush=True)
                    next_progress += PROGRESS_BYTES
            handle.flush()
            os.fsync(handle.fileno())

        expected_total = response.headers.get("Content-Range")
        if expected_total and "/" in expected_total:
            total_text = expected_total.rsplit("/", 1)[1]
        else:
            content_length = response.headers.get("Content-Length")
            total_text = str(existing + int(content_length)) if content_length else None
        if total_text and total_text != "*" and partial.stat().st_size != int(total_text):
            raise RuntimeError(
                f"download is incomplete: expected {total_text} bytes, found {partial.stat().st_size}"
            )
        resolved_url = response.geturl()

    os.replace(partial, final_path)
    print("Calculating checksums...", flush=True)
    expected_md5 = archive_md5(resolved_url, filename)
    hashes = file_hashes(final_path, ["sha256", "md5"])
    if expected_md5 and hashes["md5"] != expected_md5:
        raise RuntimeError("downloaded file failed checksum verification")
    write_download_metadata(final_path, url, resolved_url, hashes, expected_md5, utc_now())
    print(f"Saved {final_path} ({final_path.stat().st_size} bytes)")
    return final_path


def open_library_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict) and isinstance(value.get("value"), str):
        return value["value"].strip()
    return ""


def nonempty_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def parse_dump_line(line: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    columns = line.rstrip(b"\r\n").split(b"\t", 4)
    if len(columns) != 5:
        return None, "malformed_tsv"
    try:
        record = orjson.loads(columns[4])
    except orjson.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(record, dict):
        return None, "invalid_json"
    return {
        "type": columns[0].decode("utf-8", errors="replace"),
        "key": columns[1].decode("utf-8", errors="replace"),
        "revision": columns[2].decode("ascii", errors="replace"),
        "last_modified": columns[3].decode("ascii", errors="replace"),
        "record": record,
    }, None


def parse_year(value: Any) -> Optional[int]:
    text = open_library_text(value)
    match = re.search(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)", text)
    if not match:
        return None
    year = int(match.group(1))
    current_year = dt.datetime.now().year + 2
    return year if 1000 <= year <= current_year else None


def bucket(value: int, boundaries: Iterable[Tuple[int, str]], fallback: str) -> str:
    for upper, label in boundaries:
        if value <= upper:
            return label
    return fallback


def author_keys(authors: List[Any]) -> List[str]:
    keys = []
    for item in authors:
        if not isinstance(item, dict):
            continue
        author = item.get("author", item)
        if isinstance(author, dict) and isinstance(author.get("key"), str):
            keys.append(author["key"])
    return keys


def rejection_reasons(record: Dict[str, Any]) -> List[str]:
    title = open_library_text(record.get("title"))
    authors = author_keys(nonempty_list(record.get("authors")))
    description = open_library_text(record.get("description"))
    subjects = [item for item in nonempty_list(record.get("subjects")) if isinstance(item, str) and item.strip()]
    covers = nonempty_list(record.get("covers"))
    year = parse_year(record.get("first_publish_date"))
    reasons = []
    if not title:
        reasons.append("missing_title")
    if not authors:
        reasons.append("missing_author")
    if not description and len(subjects) < 3:
        reasons.append("insufficient_descriptive_metadata")
    if not covers:
        reasons.append("missing_cover")
    if year is None:
        reasons.append("missing_or_invalid_publication_year")
    return reasons


def sample_record(key: str, record: Dict[str, Any], reasons: List[str]) -> Dict[str, Any]:
    subjects = [item.strip() for item in nonempty_list(record.get("subjects")) if isinstance(item, str) and item.strip()]
    return {
        "key": key,
        "title": open_library_text(record.get("title")),
        "author_keys": author_keys(nonempty_list(record.get("authors")))[:10],
        "description_length": len(open_library_text(record.get("description"))),
        "subjects": subjects[:10],
        "covers": nonempty_list(record.get("covers"))[:3],
        "first_publish_date": open_library_text(record.get("first_publish_date")),
        "rejection_reasons": reasons,
    }


def peak_memory_bytes() -> Optional[int]:
    try:
        maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(maximum if platform.system() == "Darwin" else maximum * 1024)
    except (AttributeError, ValueError):
        return None


def percentage(value: int, total: int) -> float:
    return round((value / total * 100) if total else 0.0, 4)


def profile_dump(input_path: Path, output: Path, seed: int, sample_size: int, subject_capacity: int) -> Tuple[Path, Path]:
    if not input_path.is_file():
        raise FileNotFoundError(f"input dump does not exist: {input_path}")
    started = time.monotonic()
    generated_at = utc_now()
    totals = Counter()
    coverage = Counter()
    description_lengths = Counter()
    author_counts = Counter()
    subject_counts = Counter()
    publication_years = Counter()
    funnel = Counter()
    subjects = BoundedCounter(subject_capacity)
    qualifying_samples = ReservoirSampler(sample_size, seed)
    rejected_samples = ReservoirSampler(sample_size, seed + 1)
    error_samples = ReservoirSampler(sample_size, seed + 2)

    try:
        with gzip.open(input_path, "rb") as handle:
            for line_number, line in enumerate(handle, 1):
                totals["total_rows"] += 1
                parsed, error = parse_dump_line(line)
                if error:
                    totals[error] += 1
                    error_samples.add({
                        "line": line_number,
                        "error": error,
                        "preview": line[:200].decode("utf-8", errors="replace"),
                    })
                    continue
                assert parsed is not None
                totals["valid_records"] += 1
                record = parsed["record"]
                title = open_library_text(record.get("title"))
                subtitle = open_library_text(record.get("subtitle"))
                authors = author_keys(nonempty_list(record.get("authors")))
                description = open_library_text(record.get("description"))
                record_subjects = [item.strip() for item in nonempty_list(record.get("subjects")) if isinstance(item, str) and item.strip()]
                covers = nonempty_list(record.get("covers"))
                publish_text = open_library_text(record.get("first_publish_date"))
                languages = nonempty_list(record.get("original_languages"))
                year = parse_year(record.get("first_publish_date"))

                values = {
                    "title": bool(title), "subtitle": bool(subtitle), "authors": bool(authors),
                    "description": bool(description), "subjects": bool(record_subjects), "covers": bool(covers),
                    "first_publish_date": bool(publish_text), "original_languages": bool(languages),
                }
                coverage.update(key for key, present in values.items() if present)
                description_lengths[bucket(len(description), [(0, "0"), (99, "1-99"), (499, "100-499"), (1999, "500-1999")], "2000+")] += 1
                author_counts[bucket(len(authors), [(0, "0"), (1, "1"), (2, "2")], "3+")] += 1
                subject_counts[bucket(len(record_subjects), [(0, "0"), (4, "1-4"), (19, "5-19")], "20+")] += 1
                if year is None:
                    publication_years["missing_or_invalid"] += 1
                elif year < 1800:
                    publication_years["before_1800"] += 1
                elif year < 1900:
                    publication_years["1800-1899"] += 1
                elif year < 1950:
                    publication_years["1900-1949"] += 1
                elif year < 2000:
                    publication_years["1950-1999"] += 1
                else:
                    publication_years["2000+"] += 1
                for subject in record_subjects:
                    subjects.add(subject.casefold())

                if title:
                    funnel["has_title"] += 1
                    if authors:
                        funnel["plus_author"] += 1
                        if description or len(record_subjects) >= 3:
                            funnel["plus_descriptive_metadata"] += 1
                            if covers:
                                funnel["plus_cover"] += 1
                                if year is not None:
                                    funnel["plus_publication_year"] += 1

                reasons = rejection_reasons(record)
                sampled = sample_record(parsed["key"], record, reasons)
                if reasons:
                    rejected_samples.add(sampled)
                else:
                    qualifying_samples.add(sampled)

                if line_number % 100_000 == 0:
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(f"Profiled {line_number:,} rows ({line_number / elapsed:,.0f} rows/s)...", flush=True)
    except (gzip.BadGzipFile, EOFError, OSError) as error:
        raise RuntimeError(f"unable to read gzip dump: {error}") from error

    elapsed = time.monotonic() - started
    valid = totals["valid_records"]
    source_stat = input_path.stat()
    download_metadata_path = input_path.with_suffix(input_path.suffix + ".metadata.json")
    download_metadata = None
    if download_metadata_path.is_file():
        try:
            download_metadata = json.loads(download_metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            download_metadata = {"warning": "Download metadata exists but could not be read."}
    for key in ("total_rows", "valid_records", "malformed_tsv", "invalid_json"):
        totals[key] += 0
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "profiler_version": PROFILER_VERSION,
        "generated_at_utc": generated_at,
        "source": {
            "filename": input_path.name,
            "path": str(input_path.resolve()),
            "compressed_size_bytes": source_stat.st_size,
            "modified_at_utc": dt.datetime.fromtimestamp(source_stat.st_mtime, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "download_metadata": download_metadata,
        },
        "command_options": {"seed": seed, "sample_size": sample_size, "subject_capacity": subject_capacity},
        "totals": dict(totals),
        "coverage": {key: {"count": coverage[key], "percent_of_valid": percentage(coverage[key], valid)} for key in (
            "title", "subtitle", "authors", "description", "subjects", "covers", "first_publish_date", "original_languages"
        )},
        "distributions": {
            "description_length": dict(description_lengths),
            "author_count": dict(author_counts),
            "subject_count": dict(subject_counts),
            "publication_year": dict(publication_years),
        },
        "qualification_funnel": {key: {"count": funnel[key], "percent_of_valid": percentage(funnel[key], valid)} for key in (
            "has_title", "plus_author", "plus_descriptive_metadata", "plus_cover", "plus_publication_year"
        )},
        "top_subjects_approximate": subjects.top(50),
        "samples": {
            "qualifying": qualifying_samples.items,
            "rejected": rejected_samples.items,
            "errors": error_samples.items,
        },
        "performance": {
            "elapsed_seconds": round(elapsed, 3),
            "rows_per_second": round(totals["total_rows"] / elapsed, 2) if elapsed else None,
            "peak_process_memory_bytes": peak_memory_bytes(),
        },
        "limitations": [
            "Top-subject counts are approximate; maximum_error records the Space-Saving counter's error bound.",
            "English-edition eligibility cannot be determined reliably from the works dump and requires the editions phase.",
            "The qualification funnel is observational and does not define the final catalog inclusion policy.",
        ],
    }
    base_name = input_path.name.removesuffix(".txt.gz")
    json_path = output / f"{base_name}-profile.json"
    markdown_path = output / f"{base_name}-profile.md"
    atomic_write_text(json_path, json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    atomic_write_text(markdown_path, render_markdown(report))
    return json_path, markdown_path


def markdown_table(headers: List[str], rows: Iterable[Iterable[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows)
    return "\n".join(output)


def render_markdown(report: Dict[str, Any]) -> str:
    totals = report["totals"]
    coverage_rows = [(name, values["count"], f'{values["percent_of_valid"]:.2f}%') for name, values in report["coverage"].items()]
    funnel_rows = [(name, values["count"], f'{values["percent_of_valid"]:.2f}%') for name, values in report["qualification_funnel"].items()]
    subject_rows = [(item["subject"], item["approximate_count"], item["maximum_error"]) for item in report["top_subjects_approximate"]]
    lines = [
        "# Open Library Works Dump Profile", "",
        f'- Source: `{report["source"]["filename"]}`',
        f'- Compressed size: {report["source"]["compressed_size_bytes"]:,} bytes',
        f'- Generated: {report["generated_at_utc"]}',
        f'- Profiler version: {report["profiler_version"]}', "",
        "## Totals", "",
        markdown_table(["Metric", "Count"], [(key, value) for key, value in totals.items()]), "",
        "## Field coverage", "", markdown_table(["Field", "Count", "% of valid"], coverage_rows), "",
        "## Qualification funnel", "", markdown_table(["Stage", "Count", "% of valid"], funnel_rows), "",
        "## Distributions", "",
    ]
    for name, values in report["distributions"].items():
        lines.extend([f"### {name.replace('_', ' ').title()}", "", markdown_table(["Bucket", "Count"], values.items()), ""])
    lines.extend(["## Approximate top subjects", "", markdown_table(["Subject", "Approximate count", "Maximum error"], subject_rows), ""])
    lines.extend(["## Samples", ""])
    for group in ("qualifying", "rejected", "errors"):
        lines.extend([f"### {group.title()}", ""])
        samples = report["samples"][group]
        if not samples:
            lines.extend(["_None sampled._", ""])
            continue
        for item in samples:
            compact = json.dumps(item, ensure_ascii=False, sort_keys=True)
            escaped = compact.replace("`", "\\`")
            lines.append(f"- `{escaped}`")
        lines.append("")
    lines.extend(["## Performance", "", markdown_table(["Metric", "Value"], report["performance"].items()), "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="download a current Open Library dump")
    download.add_argument("--output", type=Path, required=True)
    download.add_argument("--dump", choices=sorted(DUMP_URLS), default="works")
    download.add_argument("--url", help="override the selected dump URL")
    profile = subparsers.add_parser("profile", help="profile a works dump")
    profile.add_argument("--input", type=Path, required=True)
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--seed", type=int, default=20260826)
    profile.add_argument("--sample-size", type=int, default=25)
    profile.add_argument("--subject-capacity", type=int, default=10_000)
    ingest = subparsers.add_parser("ingest", help="ingest one dump into the local DuckDB warehouse")
    ingest.add_argument("--dataset", choices=sorted(DUMP_URLS), required=True)
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--database", type=Path, required=True)
    ingest.add_argument("--temp-directory", type=Path, default=Path(".data/openlibrary/tmp"))
    ingest.add_argument("--memory-limit", default="12GB")
    ingest.add_argument("--threads", type=int, default=8)
    merge = subparsers.add_parser("merge", help="materialize work/author/edition joins")
    merge.add_argument("--database", type=Path, required=True)
    merge.add_argument("--temp-directory", type=Path, default=Path(".data/openlibrary/tmp"))
    merge.add_argument("--memory-limit", default="16GB")
    merge.add_argument("--threads", type=int, default=4)
    classify = subparsers.add_parser("classify", help="materialize and audit the fiction catalog")
    classify.add_argument("--database", type=Path, required=True)
    classify.add_argument("--output", type=Path, required=True)
    classify.add_argument("--seed", type=int, default=20260826)
    classify.add_argument("--sample-size", type=int, default=50)
    classify.add_argument("--temp-directory", type=Path, default=Path(".data/openlibrary/tmp"))
    classify.add_argument("--memory-limit", default="16GB")
    classify.add_argument("--threads", type=int, default=4)
    prepare = subparsers.add_parser("prepare-documents", help="construct model-ready retrieval text")
    prepare.add_argument("--database", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--seed", type=int, default=20260826)
    prepare.add_argument("--sample-size", type=int, default=50)
    prepare.add_argument("--temp-directory", type=Path, default=Path(".data/openlibrary/tmp"))
    prepare.add_argument("--memory-limit", default="16GB")
    prepare.add_argument("--threads", type=int, default=4)
    status = subparsers.add_parser("status", help="show local catalog warehouse state")
    status.add_argument("--database", type=Path, required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "download":
            download_dump(args.url or DUMP_URLS[args.dump], args.output)
        elif args.command == "profile":
            if args.sample_size < 1 or args.subject_capacity < 1:
                raise ValueError("sample size and subject capacity must be positive")
            json_path, markdown_path = profile_dump(args.input, args.output, args.seed, args.sample_size, args.subject_capacity)
            print(f"Wrote {json_path}")
            print(f"Wrote {markdown_path}")
        elif args.command == "ingest":
            result = ingest_dataset(args.database, args.dataset, args.input, args.temp_directory, args.memory_limit, args.threads)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "merge":
            result = rebuild_catalog(args.database, args.temp_directory, args.memory_limit, args.threads)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "classify":
            report = classify_fiction(
                args.database, args.temp_directory, args.memory_limit, args.threads,
                args.seed, args.sample_size,
            )
            args.output.mkdir(parents=True, exist_ok=True)
            json_path = args.output / "fiction-classification-audit.json"
            markdown_path = args.output / "fiction-classification-audit.md"
            atomic_write_text(json_path, json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
            lines = [
                "# Open Library fiction classification audit", "",
                f"Generated: {report['generated_at_utc']}", "",
                "## Totals", "",
                markdown_table(["Metric", "Count"], report["totals"].items()), "",
                "## Genre counts", "",
                markdown_table(["Genre", "Count"], report["genre_counts"].items()), "",
                "Genre counts overlap because works may have multiple genres.", "",
                "## Deterministic audit samples", "",
            ]
            for group, records in report["samples"].items():
                lines.extend([f"### {group.replace('_', ' ').title()}", ""])
                for record in records:
                    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str).replace("`", "\\`")
                    lines.append(f"- `{serialized}`")
                if not records:
                    lines.append("_No records._")
                lines.append("")
            lines.extend(["## Limitations", ""] + [f"- {item}" for item in report["limitations"]] + [""])
            atomic_write_text(markdown_path, "\n".join(lines))
            print(f"Wrote {json_path}")
            print(f"Wrote {markdown_path}")
        elif args.command == "prepare-documents":
            report = prepare_retrieval_documents(
                args.database, args.temp_directory, args.memory_limit, args.threads,
                args.seed, args.sample_size,
            )
            args.output.mkdir(parents=True, exist_ok=True)
            json_path = args.output / "retrieval-documents-report.json"
            markdown_path = args.output / "retrieval-documents-report.md"
            atomic_write_text(json_path, json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
            lines = [
                "# Open Library retrieval documents", "",
                f"Generated: {report['generated_at_utc']}", "",
                "No embeddings were generated by this command.", "",
                "## Totals", "",
                markdown_table(["Metric", "Value"], report["totals"].items()), "",
                "## Text length distribution", "",
                markdown_table(["Characters", "Documents"], report["text_length_distribution"].items()), "",
                "## Subject count distribution", "",
                markdown_table(["Cleaned subjects", "Documents"], report["subject_count_distribution"].items()), "",
                "## Deterministic samples", "",
            ]
            for group, records in report["samples"].items():
                lines.extend([f"### {group.replace('_', ' ').title()}", ""])
                for record in records:
                    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str).replace("`", "\\`")
                    lines.append(f"- `{serialized}`")
                if not records:
                    lines.append("_No records._")
                lines.append("")
            lines.extend(["## Limitations", ""] + [f"- {item}" for item in report["limitations"]] + [""])
            atomic_write_text(markdown_path, "\n".join(lines))
            print(f"Wrote {json_path}")
            print(f"Wrote {markdown_path}")
        else:
            print(json.dumps(catalog_status(args.database), indent=2, sort_keys=True, default=str))
        return 0
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
