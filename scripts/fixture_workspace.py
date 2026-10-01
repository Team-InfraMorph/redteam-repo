"""Materialize inert corpus input in disposable workspaces; never execute it."""
from contextlib import contextmanager
from pathlib import Path
import json
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "REDTEAM_DUMMY_SENTINEL_ONLY\n"


def manifest(root=ROOT):
    return json.loads((root / "fixtures/manifest.json").read_text())


def corpus_path(relative, root=ROOT):
    path = (root / relative).resolve()
    if not path.is_relative_to((root / "fixtures").resolve()):
        raise ValueError("Corpus asset must stay under fixtures/")
    return path


@contextmanager
def workspace(root=ROOT):
    """Yield (snapshot, outside_sentinel); do not alter real host files."""
    with tempfile.TemporaryDirectory(prefix="inframorph-redteam-") as temporary:
        temporary_root = Path(temporary).resolve()
        snapshot = temporary_root / "snapshot"
        shutil.copytree(corpus_path(manifest(root)["baseline"], root), snapshot, symlinks=True)
        outside = temporary_root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text(SENTINEL)
        yield snapshot, sentinel


def apply_overlay(snapshot, case, root=ROOT):
    """Copy text only. A production Agent must handle it as untrusted input."""
    if not case.get("overlay"):
        return
    target = (snapshot / case["replaces"]).resolve()
    if not target.is_relative_to(snapshot.resolve()):
        raise ValueError("Overlay target must stay inside snapshot")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(corpus_path(case["overlay"], root), target)


def path_request(snapshot, sentinel, case):
    """Prepare a request string, including hostile paths; do not read it."""
    if case["id"] == "path-symlink":
        (snapshot / "escape-link").symlink_to(sentinel)
    return case["request"].replace("{outside_sentinel}", str(sentinel))
