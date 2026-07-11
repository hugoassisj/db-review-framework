#!/usr/bin/env python3
"""Optional LOCAL end-to-end runner for the Argus eval harness.

Unlike scripts/validate.py (which runs in CI and only checks structure), this script
actually drives the review over each golden fixture by shelling out to the Claude Code
CLI in headless mode, and writes each transcript to skills/review/evals/out/ for you to
grade against that fixture's expected_behavior in evals/evals.json.

It is NOT run in CI: it needs the `claude` CLI on PATH and a model, and it costs tokens.
For automated grading and with-vs-without benchmarking, prefer the official skill-creator
plugin (`/plugin install skill-creator@claude-plugins-official`, then ask it to evaluate
the review skill).

Usage:
  python3 scripts/run_evals.py            # run every eval entry
  python3 scripts/run_evals.py --list     # list entry names, run nothing
  python3 scripts/run_evals.py --only gp03-schema-approve-with-conditions
Exit code 0 if all attempted runs completed, 1 otherwise (or if the CLI is missing).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "skills" / "review" / "evals" / "evals.json"
OUT = ROOT / "skills" / "review" / "evals" / "out"


def load_entries() -> list[dict]:
    data = json.loads(EVALS.read_text(encoding="utf-8"))
    entries = data.get("evals") if isinstance(data, dict) else data
    if not isinstance(entries, list) or not entries:
        print(f"error: {EVALS} has no 'evals' list", file=sys.stderr)
        sys.exit(1)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Argus evals locally via the Claude CLI.")
    parser.add_argument("--only", help="run only the entry with this name")
    parser.add_argument("--list", action="store_true", help="list entry names and exit")
    args = parser.parse_args()

    entries = load_entries()

    if args.list:
        for e in entries:
            print(e.get("name", "<unnamed>"))
        return 0

    claude = shutil.which("claude")
    if not claude:
        print(
            "error: the `claude` CLI is not on PATH. This runner is a local-only, "
            "end-to-end check; install Claude Code or use the skill-creator plugin.",
            file=sys.stderr,
        )
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    selected = [e for e in entries if not args.only or e.get("name") == args.only]
    if not selected:
        print(f"error: no eval named {args.only!r}", file=sys.stderr)
        return 1

    failures = 0
    for e in selected:
        name = e.get("name", "unnamed")
        query = e["query"]
        print(f"==> {name}: {query}")
        try:
            result = subprocess.run(
                [claude, "--plugin-dir", str(ROOT), "-p", query],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT after 600s", file=sys.stderr)
            failures += 1
            continue
        out_file = OUT / f"{name}.md"
        out_file.write_text(result.stdout or "", encoding="utf-8")
        if result.returncode != 0:
            print(f"    exited {result.returncode}: {result.stderr.strip()[:200]}", file=sys.stderr)
            failures += 1
        else:
            print(f"    wrote {out_file.relative_to(ROOT)} — grade it against expected_behavior")

    if failures:
        print(f"\n{failures} of {len(selected)} run(s) did not complete cleanly.")
        return 1
    print(f"\nAll {len(selected)} run(s) completed. Grade the transcripts in {OUT.relative_to(ROOT)}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
