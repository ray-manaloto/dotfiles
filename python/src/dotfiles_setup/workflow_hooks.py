# Copyright (c) 2026 Raymond Manaloto
"""ADR-0001 enforcement: a CI job that writes to git must skip hk's hooks.

``mise.toml``'s ``[hooks] postinstall = "mise reshim && hk install --mise"``
runs on **every** ``mise install``, including on GitHub Actions runners, and
``hk install`` writes the ``commit-msg``/``pre-commit``/``pre-push`` git hooks.
Any job that then commits or pushes fires them, and two hk steps CANNOT pass on
a runner (``ghcr_publish_prereqs`` needs a logged-in gh; ``test`` needs
``claude`` on the login-shell PATH). That is how the daily lock refresh failed
for six days having never once opened a PR — see
``docs/adr/0001-hk-hooks-do-not-run-in-ci.md``.

The accepted decision is ``HK_SKIP_HOOKS: pre-commit,pre-push`` at job level in
every workflow that commits or pushes. Its Consequences section NAMED the gap
this module closes — quoted here in its **pre-amendment** wording, because the
same change that added this module struck those two sentences and recorded the
gap closed, so the ADR no longer carries this text:

    Any **new** workflow that commits or pushes must set ``HK_SKIP_HOOKS`` too.
    There is no global guard — the two known cases are fixed by name.
    Correctness now depends on remembering. A contract asserting "every
    workflow that commits sets ``HK_SKIP_HOOKS``" would give this teeth; not
    written yet.

So this check must catch a **new** job, not re-assert the two known ones. A
contract that pinned ``refresh.yml`` and ``gcc-sha-repair.yml`` by name would
inherit exactly the weakness the ADR is complaining about.

**Why the warning that prompted this is NOT the bug.** A job with
``install_args: "python uv"`` logs ``sh: 1: hk: not found`` and a warn-only
postinstall failure. That is benign — ``mise reshim`` (the part CI needs) still
runs, and no hook is written, which is the state the ADR *wants*. The hazard is
that this safety is **incidental**: widen one ``install_args`` and hk appears,
the postinstall succeeds, and the hooks land. This check does not depend on
that accident holding.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``workflow-hooks`` CLI subcommand and
the ``workflow_hk_skip_hooks`` hk step are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import re
import shlex
import sys
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

from dotfiles_setup.heredoc import redact_heredoc_bodies

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOW_DIR = ".github/workflows"

# The env var is hk's NATIVE skip mechanism (`HK_SKIP_HOOKS` / `hk.skipHook`:
# "Hook names to skip entirely. Values from all sources are unioned together"),
# so this needs no custom code — .claude/rules/use-tool-builtins.md. hk has no
# CI self-detection (grepped every release v0.7.0→v1.51.0: zero hits), so the
# skip must be explicit.
SKIP_ENV = "HK_SKIP_HOOKS"

# `commit-msg` is deliberately NOT required: `check_conventional_commit` passes
# on the bots' messages and is cheap. The ADR says to add it if that changes.
REQUIRED_SKIPS: tuple[str, ...] = ("pre-commit", "pre-push")


@dataclass(frozen=True)
class Job:
    """One workflow job, flattened to what the predicate below needs.

    ``run_text`` and ``uses`` are kept separate on purpose: a git write can
    arrive either as a shell command in a ``run:`` block or as a third-party
    action (``peter-evans/create-pull-request`` is how ``refresh.yml`` does it,
    and it pushes as well as commits — the detail #274 missed, which is why it
    shipped green and was still broken).
    """

    workflow: str
    """Repo-relative path, e.g. `.github/workflows/refresh.yml`."""

    name: str
    """The job's key, e.g. `lock-refresh`."""

    run_text: str
    """Every `run:` block in the job, newline-joined."""

    uses: tuple[str, ...]
    """Every `uses:` value in the job, in step order."""

    env: dict[str, str]
    """Workflow-level env merged with job-level env (job wins)."""

    opaque_actions: tuple[str, ...] = ()
    """Local `./.github/actions/*` this job reaches whose body cannot be read.

    A first-party action declaring `runs.using: node20`/`docker` has no
    `steps:`, so :func:`_expand_local` contributes nothing for it — and
    :func:`action_id` returns `""` for a `./` reference, so
    :func:`unclassified_actions` skips it too. Without this field that is the
    ONE route in the module where an unrecognised writer produces silence
    rather than a reported hole; :func:`classification_gaps` turns it into a
    gap instead.
    """


def _as_str_map(raw: object) -> dict[str, str]:
    """Coerce a YAML `env:` mapping to str→str, dropping anything malformed."""
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def _steps_of(body: object) -> list[dict[Any, Any]]:
    """The `steps:`/`runs.steps:` list of a job or composite action."""
    if not isinstance(body, dict):
        return []
    steps: object = body.get("steps")
    if steps is None:
        runs: object = body.get("runs")
        if isinstance(runs, dict):
            steps = runs.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _expand_local(
    uses: str, root: Path, seen: set[str], opaque: set[str]
) -> tuple[str, list[str]]:
    """Inline a LOCAL composite action's own run/uses, recursively.

    Load-bearing, not a nicety. ``refresh.yml``'s ``lock-refresh`` job — the
    workflow ADR-0001 was actually written about — contains no ``git`` command
    and no third-party action of its own. It reaches
    ``peter-evans/create-pull-request`` through TWO hops:

        refresh.yml → uses: ./.github/actions/open-refresh-pr
                    → uses: peter-evans/create-pull-request

    A check that reads only a job's own steps therefore returns "this job does
    not write to git" for the single most important case in the repo. That is a
    bad-bound probe (`.claude/rules/probes-need-a-control-arm.md`): the answer
    is "not at this depth", not "not present".

    Only ``./``-prefixed uses are followed — a third-party action's source is
    not in this tree, so its behaviour has to be recognised by name in the
    predicate. ``seen`` makes a cyclic or diamond include terminate.

    An action whose ``runs.using`` is NOT ``composite`` (``node20``, ``docker``)
    has no readable steps. It is recorded in ``opaque`` rather than silently
    contributing nothing, because a ``./`` reference also gets no
    :func:`action_id`, so it would otherwise be the module's only silent False.
    """
    if not uses.startswith("./") or uses in seen:
        return "", []
    seen.add(uses)
    action_dir = root / uses[2:]
    candidates = [action_dir / "action.yml", action_dir / "action.yaml"]
    action_file = next((c for c in candidates if c.is_file()), None)
    if action_file is None:
        opaque.add(uses)
        return "", []
    try:
        doc = yaml.safe_load(action_file.read_text(encoding="utf-8"))
    except yaml.YAMLError, OSError, UnicodeDecodeError:
        opaque.add(uses)
        return "", []

    runs_block = doc.get("runs") if isinstance(doc, dict) else None
    using = runs_block.get("using") if isinstance(runs_block, dict) else None
    if str(using).lower() != "composite":
        opaque.add(uses)
        return "", []

    runs: list[str] = []
    all_uses: list[str] = []
    for step in _steps_of(doc):
        if isinstance(step.get("run"), str):
            runs.append(step["run"])
        nested = step.get("uses")
        if isinstance(nested, str):
            all_uses.append(nested)
            sub_run, sub_uses = _expand_local(nested, root, seen, opaque)
            if sub_run:
                runs.append(sub_run)
            all_uses.extend(sub_uses)
    return "\n".join(runs), all_uses


def parse_jobs(workflow_path: Path, repo_relative: str, root: Path) -> list[Job]:
    """Every job in one workflow file, flattened into :class:`Job` records.

    Parsed with ``yaml.safe_load`` rather than grepped: a job's ``env:`` block
    and its steps are structurally nested, and hand-rolling that indentation
    walk is precisely the homegrown parser
    ``.claude/rules/use-tool-builtins.md`` rejects (the same call that added
    ``python-debian`` instead of hand-rolling deb822).

    A file that does not parse, or that carries no ``jobs:`` mapping, yields no
    jobs. That is a deliberate fail-OPEN on malformed YAML: ``actionlint``
    already gates workflow syntax in both CI and hk, so a parse error here would
    be a duplicate failure with a worse message.
    """
    try:
        doc = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    except yaml.YAMLError, OSError, UnicodeDecodeError:
        return []
    if not isinstance(doc, dict):
        return []

    workflow_env = _as_str_map(doc.get("env"))
    jobs_raw = doc.get("jobs")
    if not isinstance(jobs_raw, dict):
        return []

    jobs: list[Job] = []
    for job_name, job_body in jobs_raw.items():
        if not isinstance(job_body, dict):
            continue
        runs: list[str] = []
        uses: list[str] = []
        seen: set[str] = set()
        opaque: set[str] = set()
        for step in _steps_of(job_body):
            if isinstance(step.get("run"), str):
                runs.append(step["run"])
            step_uses = step.get("uses")
            if isinstance(step_uses, str):
                uses.append(step_uses)
                sub_run, sub_uses = _expand_local(step_uses, root, seen, opaque)
                if sub_run:
                    runs.append(sub_run)
                uses.extend(sub_uses)
        jobs.append(
            Job(
                workflow=repo_relative,
                name=str(job_name),
                run_text="\n".join(runs),
                uses=tuple(uses),
                env={**workflow_env, **_as_str_map(job_body.get("env"))},
                opaque_actions=tuple(sorted(opaque)),
            )
        )
    return jobs


# ---------------------------------------------------------------------------
# The predicate — the one judgement call in this module.
#
# The causal rule everything below is derived from: hk's hooks are FILES in
# `.git/hooks/`, and exactly one thing executes them — the local `git` binary,
# running a hook-firing subcommand, in the runner's checkout. Not the REST or
# GraphQL API, not `gh`, not a vendor that pushes from its own infrastructure.
# So "must this job set HK_SKIP_HOOKS?" reduces to a question with no GitHub in
# it: does this job run `git commit` or `git push` HERE?
#
# Three routes reach a local git, and all three are needed — each of the two
# writing jobs in this tree is visible on exactly one of the first two, and the
# third is the route this repo's own rules push new code onto:
#
#   1. the job's own shell           (`gcc-sha-repair.yml` / repair)
#   2. a third-party action          (`refresh.yml` / lock-refresh)
#   3. a first-party entrypoint      (`mise run ship` -> pr.py's `git push`)
#
# Local composite actions are not a fourth route: `_expand_local` has already
# inlined them into `run_text`/`uses`.
# ---------------------------------------------------------------------------

# Which git subcommand fires which hook, per githooks(5). `pre-commit` is
# "invoked by git-commit(1)" and nothing else; `pre-push` by git-push(1).
# `merge` is listed only under `commit-msg` (githooks(5): "invoked by
# git-commit and git-merge") — `git merge` fires `pre-merge-commit`, which hk
# does not install, so it is NOT a `pre-commit` trigger.
_HOOK_TRIGGER_SUBCOMMANDS: dict[str, frozenset[str]] = {
    "pre-commit": frozenset({"commit"}),
    "commit-msg": frozenset({"commit", "merge"}),
    "pre-push": frozenset({"push"}),
}

# DERIVED from the ADR's decision rather than guessed. With
# `REQUIRED_SKIPS = (pre-commit, pre-push)` this is exactly `{commit, push}`:
# nothing else can fire those two hooks, so adding `am`/`rebase`/`tag` would buy
# zero recall and pure false-positive surface. If the ADR's "add `commit-msg` if
# that changes" ever happens, its verbs arrive here with no second edit.
#
# The lookup is direct, NOT `.get(hook, frozenset())`: an unmapped hook must be
# a loud `KeyError` at import. A silently-empty verb set would disable route 1
# entirely while the check still exited 0 — a green, vacuous gate is the exact
# #274 failure this module exists to prevent.
GIT_WRITE_SUBCOMMANDS: frozenset[str] = frozenset().union(
    *(_HOOK_TRIGGER_SUBCOMMANDS[hook] for hook in REQUIRED_SKIPS)
)

# git's own options that consume the NEXT token, so the subcommand scan does not
# read their value as the subcommand: `git -C sub commit` must yield `commit`.
_GIT_OPTIONS_WITH_VALUE: frozenset[str] = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
)

# Third-party actions, each classified by the ONE question that matters: does it
# run git in the runner's checkout (True), or does it only talk to a remote
# service (False)? A remote writer produces a commit on GitHub without any local
# git running, so no hook can fire.
#
# Deliberately holding EXACTLY the actions this tree reaches — no speculative
# entries. :func:`classification_gaps` fails on an unclassified action AND on a
# stale one, mirroring `bash_budget.py`'s `"unlisted"`/`"stale"` contract ("so
# the map can't rot"). Pre-registering a verdict for an action nobody uses would
# spend the gate's only hard stop in advance, on a source read no control arm
# ever exercised — and a stale `False` degrades to a MISS, not to a harmless
# extra env line.
ACTION_RUNS_GIT_LOCALLY: dict[str, bool] = {
    # LOCAL. `src/create-pull-request.ts` calls `createOrUpdateBranch` (a local
    # `git commit`) and `git.push(['--force-with-lease', …])` via @actions/exec,
    # and passes `--no-verify` nowhere. Proven from the world, not just the
    # source: ADR-0001's live re-run logged `hk WARN pre-commit: skipping hook
    # due to HK_SKIP_HOOK` / `hk WARN pre-push: …` from inside this action.
    # (Conditional: with `sign-commits: true` the COMMIT is made through the
    # API — it still pushes locally, and we do not set the flag.)
    "peter-evans/create-pull-request": True,
    # REMOTE — THE TRAP. `autofix.yml`/autofix is the only job that installs the
    # FULL toolchain, so hk IS present, the postinstall SUCCEEDS and the git
    # hooks ARE written; it also sets a `git config` identity and runs
    # `hk run pre-commit --all` twice on purpose. Every surface signal says
    # "writes to git". It does not: this action uploads a DIFF to autofix.ci and
    # THEIR GitHub App makes the commit off-runner — the vendor's own action.yml
    # output `autofix_started` reads "changes have been sent to the autofix
    # server and a fix commit is coming up". Any predicate keyed on "configures
    # git identity", "has hk installed", or "touches GitHub" gets this wrong.
    "autofix-ci/action": False,
    # Runs a LOT of local git (init/fetch/checkout) and is still False: none of
    # it is `commit` or `push`, so no hk hook can fire.
    "actions/checkout": False,
    "actions/create-github-app-token": False,  # mints a token; no git
    "actions/upload-artifact": False,  # uploads to the Actions artifact store
    "aquasecurity/trivy-action": False,  # scans a filesystem/image
    "astral-sh/setup-uv": False,  # tool install
    "docker/bake-action": False,  # buildkit; pushes an IMAGE, not a git ref
    "docker/login-action": False,  # registry auth
    "docker/metadata-action": False,  # computes tags/labels
    "docker/setup-buildx-action": False,  # builder setup
    "dorny/paths-filter": False,  # diff classification; reads refs only
    "github/codeql-action": False,  # uploads SARIF to the code-scanning API
    "jdx/mise-action": False,  # tool install (reached via ./setup-mise)
    "jlumbroso/free-disk-space": False,  # deletes runner files
}

# First-party entrypoints that reach a local `git commit`/`git push` through
# THIS repo's own python, matched as a token prefix at a shell command position.
#
# Route 3 exists because `.claude/rules/zero-bash-logic.md` and
# `.claude/rules/mise-tasks-only.md` actively push git-writing logic OFF the
# shell and INTO `python/` behind a mise task — and `gcc-sha-repair.yml`'s own
# header already describes its remaining `git commit`/`git push` block as "a
# thin trigger + commit seam" over `dotfiles-setup gcc-sha`. Finishing that
# stated migration would, without this route, silently convert one of the two
# true positives in the tree into a false negative: the gate would go green
# while the hazard was unchanged.
#
# `dotfiles-setup pr` covers `pr ship` and `pr land`. The exact
# `session_gate` entry covers only the credential-launcher mutation sentinel,
# whose hostile payload restores ship's historical uncredentialed push. Its
# sibling mutation and normal gate do not carry that payload and must remain
# outside this registry. These are SEEDS only: the mise half is DERIVED from
# `mise.toml` by :func:`mise_task_git_writers`, never listed.
#
# Listing the tasks was the reviewed defect, and it reproduced ADR-0001's own
# complaint one level up: `mise run ship` is literally
# `uv run --project python dotfiles-setup pr ship`, so a NEW task that wraps
# the same entrypoint (`mise run release`) was a silent false negative with no
# classification gap — `pr` is already registered, so nothing could fire.
# "Fixed by name" is exactly what this module exists to stop.
#
# :func:`classification_gaps` keeps the python half honest the same way — a NEW
# git write inside `python/` fails the check until its entrypoint is registered
# here.
FIRST_PARTY_GIT_WRITERS: tuple[tuple[str, ...], ...] = (
    ("dotfiles-setup", "pr"),
    (
        "-m",
        "dotfiles_setup.session_gate",
        "--repo-root",
        "$MISE_PROJECT_ROOT",
        "mutation-sentinel",
        "--prevention-id",
        "credential-launcher",
    ),
)

# Where mise tasks are declared. `.config/mise/conf.d/*.toml` is the fragment
# both host and image merge (root AGENTS.md), so a task can arrive from either.
MISE_CONFIGS: tuple[str, ...] = ("mise.toml", ".config/mise/conf.d/*.toml")

# Modules under `python/src/dotfiles_setup/` that invoke a git write verb, and
# whose entrypoint is therefore registered in :data:`FIRST_PARTY_GIT_WRITERS`.
# Today: `pr.py` performs ship's credential-scoped push, while `session_gate.py`
# carries the exact historical uncredentialed call as the credential mutation.
# (Deliberately paraphrased rather than quoted: the argv literal is what
# :data:`_ARGV_GIT_WRITE` looks for, and quoting it here would make this module
# match its own detector. Caught by running the check against the real tree —
# the derivation reported `workflow_hooks` as an unregistered git writer, which
# is exactly the FAIL direction working.)
# Every other module's git usage is a read (`ls-files`, `rev-parse`,
# `merge-base`, `diff`, `status`, `ls-remote`, `pull --ff-only`).
GIT_WRITING_MODULES: frozenset[str] = frozenset({"pr", "session_gate"})

_PYTHON_PACKAGE_DIR = "python/src/dotfiles_setup"

# A git write expressed as an argv list literal: a `git` element followed,
# inside the same list, by a write verb element.
# `[^]]` keeps the match inside one list literal, so a `merge-base` read cannot
# borrow a verb from the next statement (and `merge-base` is not `merge`: the
# alternation is quote-delimited, never a prefix). The
# verb alternation is built from :data:`GIT_WRITE_SUBCOMMANDS` plus the verbs
# that fire the hooks hk installs but REQUIRED_SKIPS does not currently name —
# the derivation is deliberately a superset, because over-detecting here only
# forces a registration, while under-detecting reopens the gap.
_ARGV_GIT_WRITE = re.compile(
    r"""\[\s*["']git["']\s*,[^]]{0,200}?["'](?:"""
    + "|".join(sorted({*GIT_WRITE_SUBCOMMANDS, "merge", "rebase", "am", "revert"}))
    + r""")["']"""
)

# Words that may precede the real command without being it.
_COMMAND_PREFIX_WORDS: frozenset[str] = frozenset(
    {
        "!",
        "command",
        "do",
        "elif",
        "else",
        "exec",
        "if",
        "nice",
        "nohup",
        "sudo",
        "then",
        "time",
        "until",
        "while",
        "xargs",
    }
)

# `FOO=bar git push` — a leading assignment is not the command.
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Tokens `shlex` emits as punctuation. A newline is included deliberately: it is
# a command separator, and without it `git push` on the line after
# `git commit -m x` would not be at a command position and would be MISSED —
# which is precisely `gcc-sha-repair.yml`'s shape.
_PUNCTUATION_CHARS = "();<>|&\n"
_SEPARATOR_TOKENS: frozenset[str] = frozenset(
    {";", "&", "&&", "|", "||", "(", ")", "\n", "<", ">", ">>", "<<"}
)


def shell_tokens(run_text: str) -> list[str]:
    """Tokenize a ``run:`` block the way a shell would, separators included.

    Uses :mod:`shlex` — the stdlib's shell lexer — rather than a homegrown
    scanner (`.claude/rules/use-tool-builtins.md`), configured so quoting AND
    command position both survive:

    - ``posix=True`` means a quoted span is ONE token, so
      ``echo "remember to git push (x)"`` cannot be misread as a command. That
      is the false-positive class `hook_guard._inert_masked` had to fix by hand
      in #265 — a separator inside quoted CONTENT read as a shell separator.
    - ``punctuation_chars`` emits ``;``/``&&``/``|``/``(`` … as their own
      tokens, so the caller can tell a command position from an argument.
    - a newline is added to that set (and removed from ``whitespace``) because
      it separates commands too, while a newline INSIDE a quoted span still
      stays inside its token.

    Quoting is not enough on its own: a heredoc body is UNQUOTED stdin data
    whose newlines are real newlines, so ``gh issue create --body-file - <<'EOF'
    … git push … EOF`` — remediation prose in an issue body — tokenizes exactly
    like two commands and was a false positive. :func:`redact_heredoc_bodies`
    blanks those bodies first, EXCEPT when a shell owns the redirect
    (``bash <<'SH' … git push … SH`` really does run them); that is the same
    class ``hook_guard._inert_masked`` fixed in #265, and the pattern is now
    shared rather than copied.

    An unbalanced quote makes ``shlex`` raise; the fallback is a whitespace
    split with newlines preserved as separators, which errs toward DETECTING a
    write. That direction is deliberate: the result is a loud, one-line-fixable
    violation instead of a silent miss.
    """
    run_text = redact_heredoc_bodies(run_text)
    lexer = shlex.shlex(run_text, posix=True, punctuation_chars=_PUNCTUATION_CHARS)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return run_text.replace("\n", " \n ").split(" ")


def _command_starts(tokens: list[str]) -> list[int]:
    """Indices at which a new command word begins.

    A command starts at the beginning of the text and after every separator
    token, then skips leading env assignments and wrapper words so
    ``if ! sudo git push`` presents ``git`` as the command.
    """
    starts: list[int] = []
    index = 0
    at_start = True
    while index < len(tokens):
        token = tokens[index]
        if token in _SEPARATOR_TOKENS:
            at_start = True
            index += 1
            continue
        if at_start and (_ASSIGNMENT.match(token) or token in _COMMAND_PREFIX_WORDS):
            index += 1
            continue
        if at_start:
            starts.append(index)
            at_start = False
        index += 1
    return starts


def _git_subcommand(tokens: list[str], start: int) -> str | None:
    """The subcommand of the git invocation whose command word is ``start``.

    ``None`` when the command is not git, or is git with nothing but options.
    Skipping :data:`_GIT_OPTIONS_WITH_VALUE` and their values is what makes
    ``git -C sub commit`` yield ``commit`` rather than ``sub``.
    """
    head = tokens[start]
    if head != "git" and not head.endswith("/git"):
        return None
    index = start + 1
    while index < len(tokens) and tokens[index] not in _SEPARATOR_TOKENS:
        token = tokens[index]
        if not token.startswith("-"):
            return token
        index += 2 if token in _GIT_OPTIONS_WITH_VALUE else 1
    return None


def _invocation_tokens(tokens: list[str], start: int) -> list[str]:
    """Tokens of one command, from its command word up to the next separator."""
    end = start
    while end < len(tokens) and tokens[end] not in _SEPARATOR_TOKENS:
        end += 1
    return tokens[start:end]


def git_write_subcommands(run_text: str) -> set[str]:
    """Every hook-firing git verb invoked at a command position in ``run_text``.

    Returns the verbs, not a bool, so a caller can name what it saw and a test
    can assert WHY a job was flagged — a bare bool cannot distinguish "found
    ``git push``" from "found nothing because the probe is broken".

    Parsing the subcommand rather than grepping for ``git commit`` is what keeps
    ``git config``, ``git diff --quiet``, ``git add``, ``git status`` and
    ``git merge-base`` (exact-token equality, never a prefix — this repo really
    runs ``merge-base``) out of the answer. Both jobs that DO write also run
    ``git config``, and so do two that do not, so a `"git" in run_text` check
    would flag every hk-identity step in the repo.

    ``--no-verify`` is git's own documented hook bypass, so an invocation
    carrying it genuinely cannot fire a hook. Only the long form is honoured:
    ``-n`` means ``--no-verify`` for ``git commit`` but ``--dry-run`` for
    ``git push``, and treating it as "still fires" merely over-flags.
    """
    tokens = shell_tokens(run_text)
    found: set[str] = set()
    for start in _command_starts(tokens):
        subcommand = _git_subcommand(tokens, start)
        if subcommand not in GIT_WRITE_SUBCOMMANDS:
            continue
        if "--no-verify" in _invocation_tokens(tokens, start):
            continue
        found.add(subcommand)
    return found


def _strip_runner_prefix(words: list[str]) -> list[str]:
    """Drop a ``uv run --project python``-style wrapper from a command.

    ``uv run --project python dotfiles-setup pr ship`` -> ``dotfiles-setup pr
    ship``. Written as a narrow unwrap of the ONE runner shape this repo
    mandates (`python/AGENTS.md`: always ``uv run --project python``), not as a
    general shell interpreter.
    """
    if words[:2] != ["uv", "run"]:
        return words
    index = 2
    while index < len(words):
        word = words[index]
        if word in {"--project", "--directory", "--with", "--python"}:
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        break
    remainder = words[index:]
    if remainder[:1] == ["python"]:
        remainder = remainder[1:]
    return remainder


def first_party_git_writers(
    run_text: str, writers: tuple[tuple[str, ...], ...] = FIRST_PARTY_GIT_WRITERS
) -> set[str]:
    """Every ``writers`` entrypoint invoked at a command position in ``run_text``.

    Matched at a command position, after unwrapping the ``uv run --project
    python`` runner, so a mention inside a quoted string or a comment cannot
    trigger it.

    ``writers`` defaults to the SEED tuple so the function is usable on its own;
    :func:`find_violations` passes the seeds unioned with
    :func:`mise_task_git_writers`'s derivation.
    """
    tokens = shell_tokens(run_text)
    found: set[str] = set()
    for start in _command_starts(tokens):
        words = _strip_runner_prefix(_invocation_tokens(tokens, start))
        for entrypoint in writers:
            if tuple(words[: len(entrypoint)]) == entrypoint:
                found.add(" ".join(entrypoint))
    return found


def _task_entry(body: object) -> tuple[str, tuple[str, ...]] | None:
    """One task's ``(run text, depends)``, or ``None`` when it is not a task.

    Both declared shapes are read: the inline string form
    (``[tasks] ship = "…"``) and the table form (``[tasks.ship] run = "…"``),
    where ``run`` and each depends key may be a string or a list of strings.
    """
    if isinstance(body, str):
        return body, ()
    if not isinstance(body, dict):
        return None
    run = body.get("run")
    if isinstance(run, list):
        run_text = "\n".join(str(item) for item in run)
    else:
        run_text = str(run or "")
    depends: list[str] = []
    for key in ("depends", "depends_post", "wait_for"):
        value = body.get(key)
        if isinstance(value, str):
            depends.append(value)
        elif isinstance(value, list):
            depends.extend(str(item) for item in value)
    return run_text, tuple(depends)


def _task_bodies(root: Path) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Every declared mise task, as ``name -> (run text, depends)``.

    Both task shapes are read: the table form (``[tasks.ship] run = "…"``) and
    the inline string form (``[tasks] ship = "…"``). ``run`` may be a string or
    a list of strings; ``depends``/``depends_post`` likewise.
    """
    bodies: dict[str, tuple[str, tuple[str, ...]]] = {}
    paths: list[Path] = []
    for pattern in MISE_CONFIGS:
        paths.extend(sorted(root.glob(pattern)))
    for path in paths:
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError, OSError, UnicodeDecodeError:
            continue
        tasks = document.get("tasks")
        if not isinstance(tasks, dict):
            continue
        for name, body in tasks.items():
            entry = _task_entry(body)
            if entry is not None:
                bodies[str(name)] = entry
    return bodies


def mise_task_git_writers(
    root: Path, seeds: tuple[tuple[str, ...], ...] = FIRST_PARTY_GIT_WRITERS
) -> tuple[tuple[str, ...], ...]:
    """``("mise", "run", <task>)`` for every task that TRANSITIVELY writes to git.

    Derived, not listed — that is the whole point. A task qualifies when its own
    body runs a hook-firing git verb, or invokes a ``seeds`` entrypoint, or
    depends on a task that already qualifies. Iterated to a fixed point so a
    chain (``release`` -> ``ship`` -> ``dotfiles-setup pr ship``) resolves
    regardless of declaration order.

    A task name is taken as its first word only (``mise run land -- 42``
    matches ``land``); the ``--`` payload is arguments, not another task.
    """
    bodies = _task_bodies(root)
    writers: set[str] = set()
    changed = True
    while changed:
        changed = False
        current = seeds + tuple(("mise", "run", name) for name in sorted(writers))
        for name, (run_text, depends) in bodies.items():
            if name in writers:
                continue
            reaches = (
                git_write_subcommands(run_text)
                or first_party_git_writers(run_text, current)
                or {dependency.split()[0] for dependency in depends if dependency}
                & writers
            )
            if reaches:
                writers.add(name)
                changed = True
    return tuple(("mise", "run", name) for name in sorted(writers))


def action_id(uses: str) -> str:
    """Normalise a ``uses:`` value to a case-folded ``owner/repo`` lookup key.

    ``github/codeql-action/upload-sarif@<sha> # v4`` -> ``github/codeql-action``.
    A local ``./`` composite or a reusable ``./.github/workflows/*.yml`` returns
    ``""``: composites are already INLINED by :func:`_expand_local`, and a
    reusable workflow's jobs are checked in their own file (job ``env`` does not
    cross ``workflow_call``). ``docker://`` likewise has no action to classify.
    """
    reference = uses.split("@", 1)[0].strip().strip("'\"").lower()
    if reference.startswith(("./", ".github/", "docker://")):
        return ""
    return "/".join([part for part in reference.split("/") if part][:2])


def committing_actions(job: Job) -> set[str]:
    """The third-party actions ``job`` reaches that write to git locally."""
    return {
        identifier
        for identifier in (action_id(uses) for uses in job.uses)
        if ACTION_RUNS_GIT_LOCALLY.get(identifier) is True
    }


def unclassified_actions(job: Job) -> set[str]:
    """Third-party actions ``job`` reaches that carry no recorded verdict.

    Exported so :func:`find_violations` can report them under a DIFFERENT
    message than the ``HK_SKIP_HOOKS`` one. That split is load-bearing rather
    than cosmetic: the only remediation this check can otherwise print is a free
    and harmless-looking env line, so a check that printed it for an
    unclassified action would train operators to set the skip unconditionally —
    after which a genuinely new git-writing job passes too. Worse, the env var
    also silences an EXPLICIT ``hk run <hook>``, so blanket-applying it to
    ``autofix.yml`` would turn its two deliberate ``hk run pre-commit`` steps
    into no-ops and leave a green, dead safety net.

    So an unknown action is NOT treated as a git writer by
    :func:`job_writes_to_git` — it is reported as a *classification* gap whose
    remedy is a one-line reviewable verdict, exactly the shape
    `bash_budget.py`'s ALLOWLIST already uses in this repo.
    """
    return {
        identifier
        for identifier in (action_id(uses) for uses in job.uses)
        if identifier and identifier not in ACTION_RUNS_GIT_LOCALLY
    }


def job_writes_to_git(
    job: Job, writers: tuple[tuple[str, ...], ...] = FIRST_PARTY_GIT_WRITERS
) -> bool:
    """True when ``job`` commits or pushes, and so must skip hk's git hooks.

    Three routes to a local git, unioned — see the banner comment above for why
    each is required and none is optional:

    1. a hook-firing git verb at a shell command position in ``run_text``
       (``gcc-sha-repair.yml`` / ``repair``);
    2. a third-party action classified as a local writer (``refresh.yml`` /
       ``lock-refresh``, which contains no ``git`` command of its own and
       reaches ``peter-evans/create-pull-request`` two composite hops down —
       missing this is exactly how #274 shipped green and was still broken);
    3. a first-party entrypoint that reaches a git write inside ``python/``
       (``mise run ship`` -> ``pr.py``), the route this repo's zero-bash-logic
       and mise-tasks-only rules actively steer new code onto.

    The negatives are as load-bearing as the positives, because each defeats an
    obvious cheaper predicate:

    - ``refresh.yml`` / ``tool-currency`` runs ``gh issue create/edit/close`` —
      the GitHub API, never the index or a remote. A predicate keyed on "writes
      to GitHub" or "holds a token" flags it wrongly. (``lock-refresh``
      declares job-level ``contents: read`` and writes anyway, while
      ``ci.yml`` / ``promote`` holds write scope and never touches git, so
      permissions discriminate nothing here.)
    - ``autofix.yml`` / ``autofix`` sets a ``git config`` identity, installs the
      FULL toolchain — hk present, postinstall successful, hooks written — and
      runs ``hk run pre-commit`` twice, yet the commit is made off-runner by
      autofix.ci's App. A predicate keyed on "configures git identity" or "hk is
      installed" flags it wrongly.

    An UNRECOGNISED third-party action returns False here by design; it surfaces
    through :func:`unclassified_actions` / :func:`classification_gaps` as a
    classification gap instead. See :func:`unclassified_actions` for why the
    remedy must not be "add the env var".
    """
    return bool(
        git_write_subcommands(job.run_text)
        or first_party_git_writers(job.run_text, writers)
        or committing_actions(job)
    )


def classification_gaps(root: Path) -> list[str]:
    """Gaps that make the predicate's data untrustworthy, in either direction.

    This is what actually closes ADR-0001's "correctness depends on
    remembering" for the two routes whose ground truth lives outside a ``run:``
    block. Each gap has a one-line reviewable remedy, and each is derived from
    the tree rather than from intuition:

    - **unclassified action** — a third-party ``uses:`` with no verdict. A new
      job written with a NEW action is otherwise invisible to route 2.
    - **stale action entry** — a verdict for an action the tree no longer
      reaches. Mirrors `bash_budget.py`'s ``"stale"`` kind ("so the map can't
      rot"); without it, entries only ever accumulate and a ``False`` verdict
      whose vendor changed behaviour is never re-asked.
    - **unregistered git write in python** — a module invoking a git write verb
      as an argv literal whose entrypoint is not in
      :data:`FIRST_PARTY_GIT_WRITERS`. This makes adding a ``git push`` inside
      ``python/`` a hard stop, exactly as adopting a new action is, so route 3
      cannot silently fall behind the code.
    - **opaque local action** — a first-party ``./.github/actions/*`` whose
      ``runs.using`` is not ``composite`` (``node20``/``docker``), or which
      cannot be read at all. Its body is invisible to :func:`_expand_local` AND
      it gets no :func:`action_id`, so without this it would be the module's
      only place where an unrecognised writer answers False in silence.
    """
    reachable: set[str] = set()
    unclassified: set[str] = set()
    opaque: set[str] = set()
    for path in sorted((root / WORKFLOW_DIR).glob("*.y*ml")):
        for job in parse_jobs(path, f"{WORKFLOW_DIR}/{path.name}", root):
            reachable.update(i for i in (action_id(u) for u in job.uses) if i)
            unclassified.update(unclassified_actions(job))
            opaque.update(job.opaque_actions)

    gaps = [
        f"local action `{reference}` has no readable composite `steps:` "
        f"(a node/docker action, or an unreadable file), so this check cannot "
        f"see whether it runs git in the checkout. Convert it to a composite, "
        f"or record its verdict at its call site."
        for reference in sorted(opaque)
    ]
    gaps += [
        f"third-party action `{identifier}` has no verdict in "
        f"ACTION_RUNS_GIT_LOCALLY. Read its source and record whether it runs "
        f"git in the runner's checkout (True) or only talks to a remote "
        f"service (False), with the evidence at the entry."
        for identifier in sorted(unclassified)
    ]
    gaps += [
        f"ACTION_RUNS_GIT_LOCALLY entry `{identifier}` is stale — no workflow "
        f"reaches that action any more. Prune it; a verdict nothing exercises "
        f"rots silently."
        for identifier in sorted(set(ACTION_RUNS_GIT_LOCALLY) - reachable)
    ]
    gaps += [
        f"{_PYTHON_PACKAGE_DIR}/{module}.py invokes a git write verb but "
        f"`{module}` is not in GIT_WRITING_MODULES. Register the mise task / "
        f"`dotfiles-setup` subcommand that reaches it in "
        f"FIRST_PARTY_GIT_WRITERS, or the check goes blind to any workflow "
        f"that calls it."
        for module in sorted(_python_git_write_modules(root) - GIT_WRITING_MODULES)
    ]
    return gaps


def _python_git_write_modules(root: Path) -> set[str]:
    """Module stems under ``python/src/dotfiles_setup`` that write to git."""
    package_dir = root / _PYTHON_PACKAGE_DIR
    modules: set[str] = set()
    for path in sorted(package_dir.glob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        if _ARGV_GIT_WRITE.search(source):
            modules.add(path.stem)
    return modules


def skips_required_hooks(job: Job) -> bool:
    """True when ``job``'s env skips every hook in :data:`REQUIRED_SKIPS`.

    hk's own semantics are a comma-separated union, so this parses rather than
    string-matches: ``pre-push,pre-commit`` and ``pre-commit,pre-push`` must be
    equivalent, and a partial value like #274's ``pre-commit`` alone must FAIL
    — that PR set exactly that, passed every gate, and was still broken because
    the failing steps were ``pre-push``'s.
    """
    declared = {
        part.strip() for part in job.env.get(SKIP_ENV, "").split(",") if part.strip()
    }
    return all(hook in declared for hook in REQUIRED_SKIPS)


def find_violations(root: Path) -> list[str]:
    """Human-readable violation lines; empty means the policy holds.

    Ordered by workflow then job so the output is stable across runs and a
    diff of two reports is readable.

    :func:`classification_gaps` is appended last and reported with its OWN
    remedy, never the ``HK_SKIP_HOOKS`` one: an unclassified action, a stale
    verdict, or an unregistered git write inside ``python/`` is a hole in the
    check's data, and telling an operator to "add the env var" would both
    misdirect and, applied habitually, dissolve the check.
    """
    workflow_dir = root / WORKFLOW_DIR
    writers = FIRST_PARTY_GIT_WRITERS + mise_task_git_writers(root)
    violations: list[str] = []
    for path in sorted(workflow_dir.glob("*.y*ml")):
        repo_relative = f"{WORKFLOW_DIR}/{path.name}"
        violations.extend(
            f"{repo_relative}: job `{job.name}` commits or pushes but "
            f"does not set {SKIP_ENV} covering "
            f"{','.join(REQUIRED_SKIPS)}. hk's git hooks would run on "
            f"the runner and fail (ADR-0001). Add to the job's env:\n"
            f"      {SKIP_ENV}: {','.join(REQUIRED_SKIPS)}"
            for job in parse_jobs(path, repo_relative, root)
            if job_writes_to_git(job, writers) and not skips_required_hooks(job)
        )
    return violations + classification_gaps(root)


def workflow_hooks_main(root: Path) -> int:
    """CLI entry: 0 when every git-writing job skips hk's hooks, else 1."""
    violations = find_violations(root)
    if not violations:
        sys.stdout.write(
            "workflow-hooks OK: every git-writing job skips hk's git hooks\n"
        )
        return 0
    sys.stdout.write("workflow-hooks: ADR-0001 violations\n\n")
    for line in violations:
        sys.stdout.write(f"  - {line}\n")
    sys.stdout.write(
        f"\n{len(violations)} violation(s). "
        f"See docs/adr/0001-hk-hooks-do-not-run-in-ci.md\n"
    )
    return 1
