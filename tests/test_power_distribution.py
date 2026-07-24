from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
LOCK_SHA = "6ae71878beb50226a1e4b7e2f52ac6468c86f74b"


class UAPowerDistributionTests(unittest.TestCase):
    def test_source_lock_is_exact_and_manual(self) -> None:
        lock = json.loads((ROOT / "SOURCE.lock.json").read_text(encoding="utf-8"))
        self.assertEqual("nhatnguyenquang1838-coder/Understand-Anything", lock["controlledRepository"])
        self.assertEqual("Egonex-AI/Understand-Anything", lock["upstreamRepository"])
        self.assertEqual(LOCK_SHA, lock["controlledSha"])
        self.assertEqual(LOCK_SHA, lock["upstreamSha"])
        self.assertEqual("manual-review-required", lock["lockPolicy"])

    def test_recipe_is_headless_and_allowlist_only(self) -> None:
        recipe = yaml.safe_load((ROOT / "distribution/power-package.yaml").read_text(encoding="utf-8"))
        self.assertEqual("ua", recipe["metadata"]["id"])
        self.assertEqual(".ua", recipe["spec"]["runtime"]["dataRoot"])
        self.assertEqual(
            ["understand-anything-plugin/skills/understand/SKILL.md"],
            recipe["spec"]["package"]["entrypoints"],
        )
        include = "\n".join(recipe["spec"]["include"])
        self.assertIn("skills/understand/**", include)
        self.assertIn("packages/core/**", include)
        self.assertNotIn("dashboard", include.lower())
        forbidden = "\n".join(recipe["spec"]["forbidden"]["paths"]).lower()
        self.assertIn("dashboard", forbidden)
        self.assertIn("vscode-extension", forbidden)

    def test_skill_runtime_dependencies_exist(self) -> None:
        required = [
            "understand-anything-plugin/skills/understand/SKILL.md",
            "understand-anything-plugin/skills/understand/generate-ignore.mjs",
            "understand-anything-plugin/skills/understand/scan-project.mjs",
            "understand-anything-plugin/skills/understand/compute-batches.mjs",
            "understand-anything-plugin/skills/understand/merge-batch-graphs.py",
            "understand-anything-plugin/skills/understand/merge-subdomain-graphs.py",
            "understand-anything-plugin/skills/understand/build-fingerprints.mjs",
            "understand-anything-plugin/agents/project-scanner.md",
            "understand-anything-plugin/agents/file-analyzer.md",
            "understand-anything-plugin/agents/assemble-reviewer.md",
            "understand-anything-plugin/agents/architecture-analyzer.md",
            "understand-anything-plugin/agents/tour-builder.md",
            "understand-anything-plugin/agents/graph-reviewer.md",
            "understand-anything-plugin/packages/core/package.json",
            "understand-anything-plugin/packages/tree-sitter-dart-wasm/package.json",
            "understand-anything-plugin/packages/tree-sitter-swift-wasm/package.json",
        ]
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual([], missing)

    def test_default_config_matches_schema(self) -> None:
        config = yaml.safe_load((ROOT / "distribution/config/understand.defaults.yaml").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "distribution/contracts/understand-config.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(config))
        self.assertEqual([], [error.message for error in errors])

    def test_upstream_checker_is_current_for_locked_shas(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check-upstream.py"),
                "--controlled-sha",
                LOCK_SHA,
                "--upstream-sha",
                LOCK_SHA,
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("CURRENT", json.loads(result.stdout)["status"])

    def test_upstream_checker_fails_closed_on_drift(self) -> None:
        drift = "0" * 40
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check-upstream.py"),
                "--controlled-sha",
                LOCK_SHA,
                "--upstream-sha",
                drift,
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(3, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual("DRIFT_DETECTED", report["status"])
        self.assertFalse(report["lockMovementAuthorized"])


if __name__ == "__main__":
    unittest.main()
