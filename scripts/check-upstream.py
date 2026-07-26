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
SUPPORTED_POLICY = "fork-authoritative-upstream-advisory"


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
    if data["lockPolicy"] != SUPPORTED_POLICY:
        raise DriftError(f"lockPolicy must be {SUPPORTED_POLICY}")
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
    parser = argparse.ArgumentParser(
        description=(
            "Report controlled-fork and vendor drift. The controlled fork is the publication "
            "authority; vendor drift is advisory and never blocks publication."
        )
    )
    parser.add_argument("--lock", default="SOURCE.lock.json")
    parser.add_argument("--controlled-sha", help="offline/test override for the observed controlled branch SHA")
    parser.add_argument("--upstream-sha", help="offline/test override for the observed vendor branch SHA")
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

        status = "CURRENT"
        if upstream_drift:
            status = "UPSTREAM_UPDATE_AVAILABLE"
        elif controlled_drift:
            status = "FORK_ADVANCED"

        report = {
            "status": status,
            "lockPolicy": lock["lockPolicy"],
            "publicationAuthority": {
                "repository": lock["controlledRepository"],
                "ref": lock["controlledRef"],
                "observedSha": controlled,
            },
            "controlled": {
                "repository": lock["controlledRepository"],
                "ref": lock["controlledRef"],
                "baselineSha": lock["controlledSha"],
                "observedSha": controlled,
                "drift": controlled_drift,
                "blocking": False,
            },
            "upstream": {
                "repository": lock["upstreamRepository"],
                "ref": lock["upstreamRef"],
                "baselineSha": lock["upstreamSha"],
                "observedSha": upstream,
                "drift": upstream_drift,
                "blocking": False,
            },
            "vendorUpdateAvailable": upstream_drift,
            "publicationBlocked": False,
            "lockMovementAuthorized": False,
        }

        output = json.dumps(report, indent=2, sort_keys=True)
        print(output if args.json else output)
        return 0
    except (OSError, json.JSONDecodeError, DriftError) as exc:
        print(f"upstream-check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
