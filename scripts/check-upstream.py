#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class DriftError(RuntimeError):
    pass


def load_lock(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "controlledRepository",
        "controlledRef",
        "controlledSha",
        "upstreamRepository",
        "upstreamRef",
        "upstreamSha",
        "lockPolicy",
    }
    missing = sorted(required - set(data))
    if missing:
        raise DriftError(f"lock missing fields: {', '.join(missing)}")
    for field in ("controlledSha", "upstreamSha"):
        if not SHA_RE.fullmatch(str(data[field])):
            raise DriftError(f"{field} must be a full lowercase commit SHA")
    if data["lockPolicy"] != "manual-review-required":
        raise DriftError("lockPolicy must be manual-review-required")
    return data


def ls_remote(repository: str, ref: str) -> str:
    url = f"https://github.com/{repository}.git"
    result = subprocess.run(
        ["git", "ls-remote", url, f"refs/heads/{ref}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise DriftError(result.stderr.strip() or f"git ls-remote failed for {repository}")
    line = result.stdout.strip()
    if not line:
        raise DriftError(f"branch not found: {repository}@{ref}")
    sha = line.split()[0]
    if not SHA_RE.fullmatch(sha):
        raise DriftError(f"unexpected ls-remote output for {repository}@{ref}")
    return sha


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect controlled-fork and upstream drift without moving SOURCE.lock.json.")
    parser.add_argument("--lock", default="SOURCE.lock.json")
    parser.add_argument("--controlled-sha", help="offline/test override for the observed controlled branch SHA")
    parser.add_argument("--upstream-sha", help="offline/test override for the observed upstream branch SHA")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        lock = load_lock(Path(args.lock))
        controlled = args.controlled_sha or ls_remote(lock["controlledRepository"], lock["controlledRef"])
        upstream = args.upstream_sha or ls_remote(lock["upstreamRepository"], lock["upstreamRef"])
        for label, value in (("controlled", controlled), ("upstream", upstream)):
            if not SHA_RE.fullmatch(value):
                raise DriftError(f"{label} observed SHA must be a full lowercase commit SHA")
        report = {
            "status": "CURRENT",
            "lockPolicy": lock["lockPolicy"],
            "controlled": {
                "repository": lock["controlledRepository"],
                "ref": lock["controlledRef"],
                "lockedSha": lock["controlledSha"],
                "observedSha": controlled,
                "drift": controlled != lock["controlledSha"],
            },
            "upstream": {
                "repository": lock["upstreamRepository"],
                "ref": lock["upstreamRef"],
                "lockedSha": lock["upstreamSha"],
                "observedSha": upstream,
                "drift": upstream != lock["upstreamSha"],
            },
            "lockMovementAuthorized": False,
        }
        if report["controlled"]["drift"] or report["upstream"]["drift"]:
            report["status"] = "DRIFT_DETECTED"
        output = json.dumps(report, indent=2, sort_keys=True)
        print(output if args.json else output)
        return 3 if report["status"] == "DRIFT_DETECTED" else 0
    except (OSError, json.JSONDecodeError, DriftError) as exc:
        print(f"upstream-check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
