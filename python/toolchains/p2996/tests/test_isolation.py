"""The tests run inside a commit hook (hk step p2996): their git must not reach the outer repository."""

from .conftest import Upstream, git


def test_fixture_commits_touch_their_own_repository_only(upstream: Upstream) -> None:
    upstream.write("isolated.txt", "one\n")
    assert git(upstream.path, "rev-parse", "--show-toplevel") == str(upstream.path.resolve())
