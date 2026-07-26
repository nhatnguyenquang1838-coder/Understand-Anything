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
    parser.add_argument(
        "--allow-controlled-drift",
        action="store_true",
        help="Allow the controlled fork to advance while continuing to fail closed on upstream drift.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        lock = load_lock(Path(args.lock))
        controlled = args.controlled_sha or ls_remote(lock["controlledRepository"], lock["controlledRef"])
        upstream = args.upstream_sha or ls_remote(lock["upstreamRepository"], lock["upstreamRef"])
        for label, value in (("controlled", controlled), ("upstream", upstream)):
            if not SHA_RE.fullmatch(value):
                raise DriftError(f"{label} observed SHA must be a full lowercase commit SHA")

        controlled_drift = controlled != lock["controlledSha"]
        upstream_drift = upstream != lock["upstreamSha"]
        controlled_drift_allowed = bool(
            args.allow_controlled_drift and controlled_drift and not upstream_drift
        )

        report = {
            "status": "CURRENT",
            "lockPolicy": lock["lockPolicy"],
            "controlled": {
                "repository": lock["controlledRepository"],
                "ref": lock["controlledRef"],
                "lockedSha": lock["controlledSha"],
                "observedSha": controlled,
                "drift": controlled_drift,
            },
            "upstream": {
                "repository": lock["upstreamRepository"],
                "ref": lock["upstreamRef"],
                "lockedSha": lock["upstreamSha"],
                "observedSha": upstream,
                "drift": upstream_drift,
            },
            "controlledDriftAllowed": controlled_drift_allowed,
            "lockMovementAuthorized": False,
        }

        if upstream_drift or (controlled_drift and not args.allow_controlled_drift):
            report["status"] = "DRIFT_DETECTED"
        elif controlled_drift_allowed:
            report["status"] = "CONTROLLED_DRIFT_ALLOWED"

        output = json.dumps(report, indent=2, sort_keys=True)
        print(output if args.json else output)
        return 3 if report["status"] == "DRIFT_DETECTED" else 0
    except (OSError, json.JSONDecodeError, DriftError) as exc:
        print(f"upstream-check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
