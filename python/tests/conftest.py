"""Run every test outside any git hook that started it."""

import os

# hk runs these tests from git's pre-commit hook, and git exports GIT_INDEX_FILE, GIT_DIR, GIT_AUTHOR_* and more
# to its hooks. A test's own `git init`, `add`, `commit` or `tag` in a scratch folder then acts on the real
# checkout: on 2026-11-12 test_herdr_app.py committed the staged change as "t" and tagged it v0.1.20. Each test
# that needs a git variable sets it itself, as test_work_approval.py does.
for name in [name for name in os.environ if name.startswith("GIT_")]:
    del os.environ[name]
