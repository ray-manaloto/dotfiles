"""copy_checkout against a real git repository: ignored build outputs stay behind."""

import subprocess
from pathlib import Path

from checkout import REPO, copy_checkout


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True)


def test_the_copy_leaves_ignored_files_behind(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "swift/.build/out").mkdir(parents=True)
    git(source, "init", "-q")
    (source / ".gitignore").write_text("/swift/.build/\n")
    (source / "swift/Package.swift").write_text("tracked\n")
    (source / "swift/.build/out/data.v1").write_bytes(b"cache")
    (source / "new.txt").write_text("untracked, not ignored\n")
    (source / "link").symlink_to("new.txt")
    git(source, "add", ".gitignore", "swift/Package.swift")
    (source / "gone.txt").write_text("staged, then deleted\n")
    git(source, "add", "gone.txt")
    (source / "gone.txt").unlink()
    copy = copy_checkout(tmp_path / "copy", source)
    found = sorted(str(p.relative_to(copy)) for p in copy.rglob("*") if not p.is_dir())
    assert found == [".gitignore", "link", "new.txt", "swift/Package.swift"]
    assert (copy / "link").is_symlink()


def test_the_real_checkout_copy_has_no_build_output(tmp_path: Path) -> None:
    copy = copy_checkout(tmp_path / "copy")
    assert (copy / "mise.toml").is_file()
    assert not (copy / ".git").exists()
    assert not any(copy.glob("swift/.build"))
    assert sum(1 for _ in copy.rglob("*")) < sum(1 for _ in REPO.rglob("*"))
