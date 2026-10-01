"""Corpus integrity tests, not proof that the production Policy Gate works."""
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fixture_workspace import (ROOT, SENTINEL, apply_overlay, corpus_path,
                               manifest, path_request, workspace)


class CorpusTests(unittest.TestCase):
    def test_manifest_has_unique_cases_and_explicit_pending_status(self):
        cases = manifest()["cases"]
        self.assertEqual(len(cases), 14)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            self.assertIn(case["category"], ("prompt", "patch", "path"))
            self.assertIn(case["expected"]["decision"], ("allow", "reject", "ignore-instructions"))
            self.assertTrue(case["expected"]["reason"])
            self.assertEqual(case["integration_status"], "not-run")
            self.assertIn(case["issue"], (3, 4, 5))

    def test_baseline_inventory_and_digests(self):
        data = manifest()
        baseline = corpus_path(data["baseline"])
        paths = {p.relative_to(baseline).as_posix() for p in baseline.rglob("*") if p.is_file()}
        self.assertEqual(paths, set(data["baseline_sha256"]))
        for name, digest in data["baseline_sha256"].items():
            self.assertEqual(hashlib.sha256((baseline / name).read_bytes()).hexdigest(), digest)
        self.assertFalse(any(p.is_symlink() for p in (ROOT / "fixtures").rglob("*")))

    def test_prompt_overlays_preserve_baseline_evidence(self):
        for case in manifest()["cases"]:
            if case["category"] != "prompt":
                continue
            with self.subTest(case=case["id"]), workspace() as (snapshot, sentinel):
                original = (snapshot / "src/server.js").read_text()
                apply_overlay(snapshot, case)
                self.assertTrue((snapshot / "src/server.js").read_text().startswith(original))
                if case.get("overlay"):
                    text = (snapshot / case["replaces"]).read_text().lower()
                    self.assertIn("untrusted", text)
                self.assertEqual(sentinel.read_text(), SENTINEL)

    def test_patches_apply_to_exact_baseline_and_syntax_is_as_declared(self):
        self.assertIsNotNone(shutil.which("git"), "Git is required")
        self.assertIsNotNone(shutil.which("node"), "Node is required (CI uses Node 22)")
        baseline_hashes = manifest()["baseline_sha256"]
        for case in manifest()["cases"]:
            if case["category"] != "patch":
                continue
            with self.subTest(case=case["id"]), workspace() as (snapshot, sentinel):
                subprocess.run(["git", "init", "--quiet", str(snapshot)], check=True)
                patch = corpus_path(case["patch"])
                subprocess.run(["git", "apply", "--check", str(patch)], cwd=snapshot, check=True)
                # Apply only the curated inert diff, inside a temporary repository.
                # Never run JS, npm install, Prisma, containers or an Agent.
                subprocess.run(["git", "apply", str(patch)], cwd=snapshot, check=True)
                changed = {name for name, digest in baseline_hashes.items()
                           if hashlib.sha256((snapshot / name).read_bytes()).hexdigest() != digest}
                self.assertEqual(changed, set(case["changed_files"]))
                for name in changed:
                    if name.endswith(".js"):
                        result = subprocess.run(["node", "--check", str(snapshot / name)], capture_output=True)
                        self.assertEqual(result.returncode == 0, case["javascript_syntax"] == "valid")
                additions = "\n".join(line[1:] for line in patch.read_text().splitlines()
                                      if line.startswith("+") and not line.startswith("+++"))
                if case["id"] == "patch-child-process":
                    self.assertIn("child_process", additions)
                if case["id"] == "patch-eval":
                    self.assertIn("eval(", additions)
                allowed = set(manifest()["test_profile"]["allowed_patch_paths"])
                self.assertEqual(changed <= allowed, case["id"] != "patch-outside-allowlist")
                self.assertEqual(sentinel.read_text(), SENTINEL)

    def test_path_inputs_actually_cross_boundary_and_cleanup(self):
        for case in manifest()["cases"]:
            if case["category"] != "path":
                continue
            with self.subTest(case=case["id"]):
                with workspace() as (snapshot, sentinel):
                    request = path_request(snapshot, sentinel, case)
                    resolved = (snapshot / request).resolve()
                    self.assertEqual(resolved.is_relative_to(snapshot), case["expected"]["decision"] == "allow")
                    if case["expected"]["decision"] == "reject":
                        self.assertEqual(resolved, sentinel)
                    self.assertEqual(sentinel.read_text(), SENTINEL)
                    temp_root = snapshot.parent
                self.assertFalse(temp_root.exists())

    def test_materializer_rejects_asset_and_overlay_escape(self):
        with self.assertRaises(ValueError):
            corpus_path("../not-a-fixture")
        with workspace() as (snapshot, sentinel):
            with self.assertRaises(ValueError):
                apply_overlay(snapshot, {"overlay": "fixtures/base/README.md", "replaces": "../outside/sentinel.txt"})
            self.assertEqual(sentinel.read_text(), SENTINEL)


if __name__ == "__main__":
    unittest.main()
