#!/usr/bin/env python3
"""Measure an already-running librarian process during one HTTP recommendation."""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from pathlib import Path

import psutil

from embedding_contract import utc_now
from gemini_librarian import atomic_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--url", default="http://127.0.0.1:8091/recommend")
    parser.add_argument("--query", default="Something funny and weird.")
    parser.add_argument("--concurrency", type=int, default=1, choices=(1, 2))
    parser.add_argument(
        "--output", type=Path,
        default=Path(".data/openlibrary/reports/librarian-runtime-memory.json"),
    )
    args = parser.parse_args()
    process = psutil.Process(args.pid)
    samples = []
    stop = threading.Event()

    def sample() -> None:
        while not stop.wait(0.05):
            memory = process.memory_info()
            samples.append({
                "elapsed_seconds": time.monotonic() - started,
                "rss_bytes": memory.rss,
                "cpu_percent": process.cpu_percent(interval=None),
            })

    responses = []
    errors = []

    def make_request() -> None:
        body = json.dumps({"query": args.query, "result_count": 5}).encode("utf-8")
        request = urllib.request.Request(
            args.url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                responses.append(json.load(response))
        except Exception as error:
            errors.append(repr(error))

    idle_rss = process.memory_info().rss
    started = time.monotonic()
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        request_threads = [threading.Thread(target=make_request) for _ in range(args.concurrency)]
        for request_thread in request_threads:
            request_thread.start()
        for request_thread in request_threads:
            request_thread.join()
    finally:
        stop.set()
        thread.join()
    if errors:
        raise RuntimeError(f"recommendation requests failed: {errors}")
    final_rss = process.memory_info().rss
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "pid": args.pid,
        "query": args.query,
        "concurrency": args.concurrency,
        "elapsed_seconds": time.monotonic() - started,
        "idle_rss_bytes": idle_rss,
        "peak_rss_bytes": max([idle_rss, *(item["rss_bytes"] for item in samples)]),
        "final_rss_bytes": final_rss,
        "sample_count": len(samples),
        "recommendation_count": sum(len(item.get("recommendations", [])) for item in responses),
        "service_elapsed_ms": [item.get("elapsed_ms") for item in responses],
        "samples": samples,
    }
    atomic_json(args.output, report)
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
