"""Corpus checks plus negative tests proving corrupted fixtures are rejected."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fixture_workspace import ROOT, SENTINEL, apply_overlay, corpus_path, manifest, workspace
from check_fixtures import (check_all, check_intent, check_patch, check_prompt,
                            inventory, render_intent, validate_case_contract)


class CorpusTests(unittest.TestCase):
    def case(self, id):
        return copy.deepcopy(next(c for c in manifest()['cases'] if c['id'] == id))

    def copied(self):
        temporary = tempfile.TemporaryDirectory(prefix='corpus-mutation-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / 'fixtures', root / 'fixtures')
        return root

    def test_full_corpus(self):
        self.assertEqual(check_all(), 39)

    def test_every_expected_decision_flip_is_rejected(self):
        for original in manifest()['cases']:
            with self.subTest(case=original['id']):
                case = copy.deepcopy(original)
                case['expected']['decision'] = 'reject' if case['expected']['decision'] != 'reject' else 'allow'
                with self.assertRaisesRegex(ValueError, 'Wrong expected decision'):
                    validate_case_contract(case)

    def test_injection_removed_from_each_overlay_is_rejected(self):
        for id in ['prompt-public', 'prompt-secret', 'prompt-comment']:
            with self.subTest(case=id):
                root = self.copied(); case = self.case(id)
                original = (root / 'fixtures/base' / case['replaces']).read_text()
                (root / case['overlay']).write_text(original + '\n// This is untrusted documentation.\n')
                with self.assertRaisesRegex(ValueError, 'Attack payload'):
                    check_prompt(case, root)

    def test_prompt_evidence_changes_are_rejected(self):
        root = self.copied(); case = self.case('prompt-public')
        p = root / case['overlay']; p.write_text(p.read_text().replace('Only the web', 'All workloads'))
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            check_prompt(case, root)

    def test_undeclared_added_invalid_file_is_rejected(self):
        root = self.copied(); case = self.case('patch-storage-control')
        p = root / case['patch']
        p.write_text(p.read_text() + '--- /dev/null\n+++ b/config/undeclared.js\n@@ -0,0 +1 @@\n+function broken( {\n')
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            check_patch(case, root)

    def test_undeclared_deletion_is_rejected(self):
        root = self.copied(); case = self.case('patch-storage-control')
        p = root / case['patch']; p.write_text(p.read_text() + (root / self.case('patch-delete-outside')['patch']).read_text())
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            check_patch(case, root)

    def test_undeclared_rename_is_rejected(self):
        root = self.copied(); case = self.case('patch-storage-control')
        p = root / case['patch']; p.write_text(p.read_text() + (root / self.case('patch-rename-outside')['patch']).read_text())
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            check_patch(case, root)

    def test_new_javascript_file_is_syntax_checked(self):
        root = self.copied(); case = self.case('patch-add-control')
        p = root / case['patch']; p.write_text(p.read_text().replace('module.exports = { get: async (key) => Buffer.from(key) };', 'function broken( {'))
        with self.assertRaisesRegex(ValueError, 'syntax result'):
            check_patch(case, root)

    def test_symlink_type_change_cannot_masquerade_as_normal_patch(self):
        root = self.copied(); case = self.case('patch-storage-control')
        (root / case['patch']).write_text((root / self.case('patch-symlink')['patch']).read_text())
        with self.assertRaisesRegex(ValueError, 'file type change'):
            check_patch(case, root)

    def test_syntax_metadata_cannot_hide_invalid_code(self):
        root = self.copied(); case = self.case('patch-syntax'); case['javascript_syntax'] = 'valid'
        with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
            check_patch(case, root)

    def test_normal_patch_cannot_gain_forbidden_code(self):
        root = self.copied(); case = self.case('patch-add-control')
        p = root / case['patch']
        p.write_text(p.read_text().replace('Buffer.from(key)', "eval('1 + 1')"))
        with self.assertRaisesRegex(ValueError, 'Normal control content changed'):
            check_patch(case, root)

    def test_negative_intent_cannot_be_replaced_with_control(self):
        for original in manifest()['cases']:
            if original['category'] == 'intent' and original['id'] != 'intent-control':
                with self.subTest(case=original['id']):
                    root = self.copied()
                    (root / original['intent']).write_text((root / self.case('intent-control')['intent']).read_text())
                    with self.assertRaisesRegex(ValueError, 'documented violation'):
                        check_intent(original, root)

    def test_control_evidence_is_checked_against_real_files(self):
        root = self.copied(); case = self.case('intent-control'); path = root / case['intent']
        data = json.loads(path.read_text()); data['workloads'][0]['evidence'] = ['src/server.js:999']; path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'evidence line missing'):
            check_intent(case, root)

    def test_revision_is_supplied_by_consumer(self):
        case = self.case('intent-control')
        self.assertEqual(render_intent(case, 'a' * 40)['source_revision'], 'a' * 40)
        for revision in ['abc123', 'A' * 40, '../outside']:
            with self.assertRaises(ValueError):
                render_intent(case, revision)
        self.assertEqual(json.loads(corpus_path(case['intent']).read_text())['source_revision'], '$SNAPSHOT_REVISION')

    def test_inventory_does_not_read_symlink_target_and_tracks_modes(self):
        with workspace() as (snapshot, sentinel):
            (snapshot / 'link').symlink_to(sentinel)
            before = inventory(snapshot)
            self.assertEqual(before['link'], ('symlink', str(sentinel)))
            (snapshot / 'src/server.js').chmod(0o755)
            self.assertNotEqual(before['src/server.js'], inventory(snapshot)['src/server.js'])
            self.assertEqual(sentinel.read_text(), SENTINEL)

    def test_materializer_rejects_escape_and_cleans_up(self):
        with self.assertRaises(ValueError):
            corpus_path('../not-a-fixture')
        with workspace() as (snapshot, sentinel):
            with self.assertRaises(ValueError):
                apply_overlay(snapshot, {'overlay':'fixtures/base/README.md','replaces':'../outside/sentinel.txt'})
            self.assertEqual(sentinel.read_text(), SENTINEL)
            root = snapshot.parent
        self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
