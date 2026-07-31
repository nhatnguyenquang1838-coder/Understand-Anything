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
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "sync-and-publish.yml"
README_PATH = ROOT / "distribution" / "README.md"

SKILLS = [
    "understand",
    "understand-chat",
    "understand-explain",
    "understand-diff",
    "understand-dashboard",
    "understand-domain",
    "understand-onboard",
    "understand-knowledge",
    "understand-figma",
]


class UAPowerDistributionTests(unittest.TestCase):
    def test_source_policy_is_fork_authoritative(self) -> None:
        lock = json.loads((ROOT / "SOURCE.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(2, lock["schemaVersion"])
        self.assertEqual("nhatnguyenquang1838-coder/Understand-Anything", lock["controlledRepository"])
        self.assertEqual("Egonex-AI/Understand-Anything", lock["upstreamRepository"])
        self.assertEqual(LOCK_SHA, lock["controlledSha"])
        self.assertEqual(LOCK_SHA, lock["upstreamSha"])
        self.assertEqual("fork-authoritative-upstream-advisory", lock["lockPolicy"])
        self.assertIn("never blocks", lock["notes"])

    def test_recipe_packages_core_and_companion_skills(self) -> None:
        recipe = yaml.safe_load((ROOT / "distribution/power-package.yaml").read_text(encoding="utf-8"))
        self.assertEqual("ua", recipe["metadata"]["id"])
        self.assertEqual(".ua", recipe["spec"]["runtime"]["dataRoot"])
        self.assertTrue(recipe["spec"]["capabilities"]["dashboard"])
        self.assertTrue(recipe["spec"]["capabilities"]["companionSkills"])

        expected_entrypoints = [
            f"understand-anything-plugin/skills/{skill}/SKILL.md" for skill in SKILLS
        ] + ["scripts/power_help.py"]
        self.assertEqual(expected_entrypoints, recipe["spec"]["package"]["entrypoints"])

        include = "\n".join(recipe["spec"]["include"])
        managed = "\n".join(recipe["spec"]["package"]["managedPaths"])
        for skill in SKILLS:
            self.assertIn(f"skills/{skill}/**", include)
            self.assertIn(f"skills/{skill}", managed)
        self.assertIn("packages/core/**", include)
        self.assertIn("packages/dashboard/**", include)

        forbidden = "\n".join(recipe["spec"]["forbidden"]["paths"]).lower()
        self.assertIn("vscode-extension", forbidden)
        self.assertIn("understand-anything-plugin/apps", forbidden)

    def test_skill_runtime_dependencies_exist(self) -> None:
        required = [
            *(f"understand-anything-plugin/skills/{skill}/SKILL.md" for skill in SKILLS),
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
            "understand-anything-plugin/packages/dashboard/package.json",
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

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/check-upstream.py"), *args, "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_status_is_current_for_baseline_shas(self) -> None:
        result = self.run_checker("--controlled-sha", LOCK_SHA, "--upstream-sha", LOCK_SHA)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("CURRENT", report["status"])
        self.assertEqual(
            "nhatnguyenquang1838-coder/Understand-Anything",
            report["publicationAuthority"]["repository"],
        )
        self.assertFalse(report["publicationBlocked"])

    def test_controlled_fork_advance_is_non_blocking(self) -> None:
        result = self.run_checker("--controlled-sha", "1" * 40, "--upstream-sha", LOCK_SHA)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("FORK_ADVANCED", report["status"])
        self.assertTrue(report["controlled"]["drift"])
        self.assertFalse(report["controlled"]["blocking"])
        self.assertFalse(report["publicationBlocked"])

    def test_vendor_drift_is_advisory(self) -> None:
        result = self.run_checker("--controlled-sha", "1" * 40, "--upstream-sha", "2" * 40)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("UPSTREAM_UPDATE_AVAILABLE", report["status"])
        self.assertTrue(report["upstream"]["drift"])
        self.assertFalse(report["upstream"]["blocking"])
        self.assertTrue(report["vendorUpdateAvailable"])
        self.assertFalse(report["publicationBlocked"])
        self.assertFalse(report["lockMovementAuthorized"])

    def test_workflow_decouples_vendor_status_from_publication(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        publish_condition = (
            "${{ github.event_name == 'push' || "
            "(github.event_name == 'workflow_dispatch' && inputs.publish) }}"
        )
        self.assertIn("name: Publish UA Power from controlled fork", text)
        self.assertIn("vendor_status:", text)
        self.assertIn("Report vendor drift (advisory only)", text)
        self.assertIn("continue-on-error: true", text)
        self.assertNotIn("needs: vendor_status", text)
        self.assertIn(f"if: {publish_condition}", text)
        self.assertIn("distribution_branch: power-dist", text)
        self.assertIn("publish_distribution_branch: true", text)

    def test_distribution_readme_states_vendor_is_non_blocking(self) -> None:
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("publication source of truth", text)
        self.assertIn("vendor drift", text)
        self.assertIn("never blocks", text)
        for skill in SKILLS[1:]:
            self.assertIn(f"`{skill}`", text)


if __name__ == "__main__":
    unittest.main()
