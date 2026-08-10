# Copyright (c) 2026 Raymond Manaloto
"""The one module owning msgspec's encode and decode hooks (#675).

msgspec's conversion hooks are **per-call** — `enc_hook`/`dec_hook` are keyword
arguments to `encode`/`decode`, not global registrations. So a codebase that
calls msgspec directly grows one copy of the hook per call site, and they drift.
#669 chose to centralise from the outset for exactly that reason.

What makes the centralisation load-bearing rather than tidy: `pathlib.Path` is
unsupported in **both** directions. Measured against msgspec 0.21.1, control-armed
against three types it does support (datetime, uuid, decimal, all of which encode
natively):

    >>> msgspec.json.encode(pathlib.Path("/tmp/x"))
    TypeError: Encoding objects of type PosixPath is unsupported
    >>> msgspec.json.decode(b'"/tmp/x"', type=pathlib.Path)
    ValidationError: Expected `Path`, got `str`

The second one is the dangerous half. Encoding *raises*, so a missing hook is
found immediately; decoding raises only because the annotation is `Path`, and a
field annotated `str` would accept the value and hand the caller a string that
behaves like a path until something calls `.parent` on it.
"""

from __future__ import annotations

import datetime
import decimal
import importlib
import inspect
import pathlib
import pkgutil
import re
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import msgspec
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).parent.parent

#: A real msgspec IMPORT, not the bare word. The tree sweep below used to match
#: the substring "msgspec" anywhere in a file, so a module that merely
#: DOCUMENTED the ban would be reported as violating it — and `python/AGENTS.md`
#: now instructs every author to write exactly that sentence (review F5). It is
#: the same trap this file calls out for a docstring satisfying a wiring check,
#: met from the other side.
_IMPORTS_MSGSPEC_RE = re.compile(r"^\s*(?:import msgspec|from msgspec)", re.MULTILINE)


class _Sample(msgspec.Struct):
    """A generated-model stand-in: the shape #680 will emit."""

    workspace: Path
    label: str


# --------------------------------------------------------------------------- #
# AC2 — round-tripping a filesystem path works in both directions
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fmt", list(codec.Format))
def test_a_path_round_trips_through_both_formats(fmt: codec.Format) -> None:
    """The headline acceptance criterion, on every format the module offers.

    Parametrised over `Format` rather than spelled twice, so adding msgpack's
    successor cannot ship with only the JSON half covered.
    """
    original = Path("/workspaces/dotfiles/.devcontainer")

    restored = codec.decode(codec.encode(original, fmt=fmt), Path, fmt=fmt)

    assert restored == original
    assert isinstance(restored, pathlib.PurePath)


def test_a_path_inside_a_struct_round_trips() -> None:
    """A path is almost never the top-level value — it is a field.

    The top-level case can pass while a nested one fails, because msgspec walks
    into a Struct with different machinery than it uses for a bare value.
    """
    original = _Sample(workspace=Path("/workspaces/dotfiles"), label="dev")

    restored = codec.decode(codec.encode(original), _Sample)

    assert restored == original
    assert isinstance(restored.workspace, pathlib.PurePath)


def test_paths_nested_in_containers_round_trip() -> None:
    """Containers are a separate walk again — a list of paths, and a dict of them."""
    original = {"roots": [Path("/a"), Path("/b")]}

    restored = codec.decode(codec.encode(original), dict[str, list[Path]])

    assert restored == original


def test_encoding_a_path_produces_the_plain_string_a_reader_expects() -> None:
    """#669 wants records readable "with ordinary tools during an incident".

    Pinning the WIRE FORM, not just the round-trip: a hook that encoded a path
    as `{"__path__": "/a"}` would round-trip perfectly and be unreadable to
    `jq`, and no round-trip test can tell the difference.
    """
    assert codec.encode(Path("/workspaces/dotfiles")) == b'"/workspaces/dotfiles"'


def test_the_hooks_are_what_msgspec_itself_would_call() -> None:
    """Control arm for the whole module: bypass it and the SAME hooks work.

    If `encode`/`decode` did the conversion themselves rather than through the
    hooks, every test above would pass while the hooks — the thing #675 exists
    to provide, and what a generated model's own call would use — were dead.
    """
    raw = msgspec.json.encode(Path("/a/b"), enc_hook=codec.enc_hook)
    restored = msgspec.json.decode(raw, type=Path, dec_hook=codec.dec_hook)

    assert raw == b'"/a/b"'
    assert restored == Path("/a/b")


def test_msgspec_really_cannot_do_this_unaided() -> None:
    """The premise, armed. Without it every test above could be vacuous.

    If a future msgspec supports paths natively, this fails and the module's
    justification should be re-read rather than the test deleted.
    """
    with pytest.raises(TypeError, match="unsupported"):
        msgspec.json.encode(Path("/a"))

    with pytest.raises(msgspec.ValidationError):
        msgspec.json.decode(b'"/a"', type=Path)


# --------------------------------------------------------------------------- #
# AC3 — an unsupported type fails loudly rather than silently degrading
# --------------------------------------------------------------------------- #


class _Unregistered:
    """A type the codec was never taught — the realistic future mistake."""


def test_encoding_an_unregistered_type_raises_and_names_it() -> None:
    """Failing "loudly" means naming the offender, not just failing.

    A bare "unsupported type" sends the reader back to a stack trace to find out
    which of a struct's twenty fields it was.
    """
    with pytest.raises(codec.UnsupportedTypeError) as excinfo:
        codec.encode(_Unregistered())

    assert excinfo.value.offending_type is _Unregistered
    assert "_Unregistered" in str(excinfo.value)


def test_decoding_into_an_unregistered_type_raises_and_names_it() -> None:
    """The decode direction needs its own arm — it is a different hook.

    Covering only encode is the "both arms, one axis" trap: the two hooks share
    a module and nothing else.
    """
    with pytest.raises(codec.UnsupportedTypeError) as excinfo:
        codec.decode(b'"x"', _Unregistered)

    assert excinfo.value.offending_type is _Unregistered


def test_the_unsupported_error_is_what_msgspec_asks_hooks_to_raise() -> None:
    """Msgspec documents `NotImplementedError` as the hook's "I can't" signal.

    Subclassing it keeps a caller who catches the documented exception working,
    while `UnsupportedTypeError` gives one who wants the offending type a place to
    read it from. Raising something unrelated would be a silent behaviour change
    for anyone following msgspec's own docs.
    """
    assert issubclass(codec.UnsupportedTypeError, NotImplementedError)


def test_an_unregistered_type_never_degrades_to_its_repr() -> None:
    """The specific silent failure AC3 forbids.

    `str(obj)` is the tempting fallback and it always "works" — every object has
    one. It would encode `<_Unregistered object at 0x…>` as a happy JSON string,
    round-trip nothing, and surface as corrupt data far from here.
    """
    with pytest.raises(codec.UnsupportedTypeError):
        codec.encode({"field": _Unregistered()})


# --------------------------------------------------------------------------- #
# The registry — extensible by parameter, not by editing the hook
# --------------------------------------------------------------------------- #


def test_a_registered_type_round_trips_without_touching_the_hooks() -> None:
    """The next unsupported type must be a registration, not a hook edit.

    Otherwise the module becomes a growing `if isinstance(...)` chain and the
    "one place" property degrades into "one long function".
    """
    codec.register(
        _Unregistered,
        encode=lambda _: "sentinel",
        decode=lambda _target, _value: _Unregistered(),
    )
    try:
        assert codec.encode(_Unregistered()) == b'"sentinel"'
        assert isinstance(codec.decode(b'"sentinel"', _Unregistered), _Unregistered)
    finally:
        codec.unregister(_Unregistered)

    with pytest.raises(codec.UnsupportedTypeError):
        codec.encode(_Unregistered())


def test_a_path_subclass_resolves_through_its_base() -> None:
    """`Path()` instantiates `PosixPath`/`WindowsPath`, never `Path` itself.

    A registry keyed on exact type would therefore miss every real path — the
    encode hook receives `PosixPath`. Measured: msgspec's own error says
    "objects of type PosixPath".
    """
    assert codec.encode(PurePosixPath("/a/b")) == b'"/a/b"'


# --------------------------------------------------------------------------- #
# AC4 — every codec call in the project routes through this module
# --------------------------------------------------------------------------- #


def _run_ruff(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ruff's TID251 check, refusing to return a non-answer.

    The `returncode` assertion is the point (review F3). Every negative arm here
    reads `"TID251" not in proc.stdout`, and a ruff that never ran — broken
    venv, missing binary, bad config path — produces empty stdout and satisfies
    that for free. rc 0 means clean and rc 1 means findings; anything else is
    the tool failing, and a gate must not read that as "no violations".
    """
    proc = subprocess.run(
        [
            *("uv", "run", "--project", "python"),
            *("ruff", "check", "--no-cache", "--select", "TID251"),
            *argv,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert proc.returncode in (0, 1), (
        f"ruff did not run (rc={proc.returncode}); its verdict cannot be read. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    return proc


def _ruff(target: Path) -> subprocess.CompletedProcess[str]:
    """Check a file INSIDE the repo, exactly as the hk gate invokes ruff.

    No `--config`: ruff resolves config per-file by walking up, which is what
    makes `python/pyproject.toml`'s relative `per-file-ignores` globs land. An
    explicit `--config` re-anchors them to the invocation directory and the
    codec's own allowance stops matching — measured while fixing review F3, and
    the same re-anchoring hazard `ruff.toml`'s header documents.
    """
    return _run_ruff([str(target)])


def _ruff_external(target: Path) -> subprocess.CompletedProcess[str]:
    """Check a file OUTSIDE the repo (a `tmp_path` probe).

    Here `--config` is required rather than harmful: ruff walking up from a
    temp directory finds no config at all, so the banned-api table — which is
    the whole subject of these probes — would simply not be loaded, and every
    probe would come back clean for the most uninteresting possible reason.
    """
    return _run_ruff(
        [*("--config", str(REPO_ROOT / "python" / "pyproject.toml")), str(target)]
    )


def _hook_taking_apis() -> set[str]:
    """Every msgspec entry point that accepts a conversion hook, from msgspec.

    Derived at runtime from the installed library rather than transcribed, so a
    new entry point in a future msgspec makes the coverage test below fail
    instead of quietly widening the hole. Enumerating beat hand-listing here by
    a wide margin: the obvious four (`json`/`msgpack` x `encode`/`decode`) are
    under a third of what this finds.

    The SUBMODULE list is discovered too (review F7). It was originally
    transcribed — `msgspec`, `.json`, `.msgpack`, `.yaml`, `.toml` — which
    defeated the point: a new hook-taking submodule is the shape most likely to
    add a wire format, and a hand-written list is blind to precisely that. Half
    a derivation reads exactly like a whole one.
    """
    modules = {"msgspec": msgspec}
    for info in pkgutil.iter_modules(msgspec.__path__):
        # Private submodules are out of scope: `msgspec._core` re-exports the
        # same callables under different names (`json_encode`, `MsgpackEncoder`)
        # and nobody imports them, so banning those paths would add noise
        # without closing a route anyone can take.
        if info.name.startswith("_"):
            continue
        try:
            modules[f"msgspec.{info.name}"] = importlib.import_module(
                f"msgspec.{info.name}"
            )
        except ImportError:  # pragma: no cover - an optional extra is absent
            continue
    return {
        f"{mod_name}.{name}"
        for mod_name, module in modules.items()
        for name in dir(module)
        if not name.startswith("_")
        and any(
            hook in (inspect.getdoc(getattr(module, name)) or "")
            for hook in ("enc_hook", "dec_hook")
        )
    }


def _banned_apis() -> set[str]:
    """The ban list as ruff will read it."""
    config = tomllib.loads(
        (REPO_ROOT / "python" / "pyproject.toml").read_text(encoding="utf-8")
    )
    return set(config["tool"]["ruff"]["lint"]["flake8-tidy-imports"]["banned-api"])


def test_the_ban_covers_every_hook_taking_entry_point_msgspec_offers() -> None:
    """Rule 52's question — *which spellings?* — asked of the library itself.

    A hand-written ban list is a snapshot of what its author remembered. This
    binds it to what msgspec actually exposes, so `Encoder`/`Decoder` (the form
    a performance-minded caller reaches for) and `convert`/`to_builtins` cannot
    be the ones nobody thought of.
    """
    uncovered = _hook_taking_apis() - _banned_apis()

    assert uncovered == set(), (
        f"msgspec entry points that take a conversion hook and are NOT banned: "
        f"{sorted(uncovered)}. Each is a way to bypass the codec with its own "
        f"hook table — add it to [tool.ruff.lint.flake8-tidy-imports.banned-api]"
    )


def test_the_coverage_check_is_reading_a_real_surface() -> None:
    """Control arm: `uncovered == set()` is satisfied for free by an empty scan.

    A typo in a module name or a msgspec that moved its API would make the
    check above vacuously green, which is the failure mode it exists to prevent.
    """
    discovered = _hook_taking_apis()

    assert len(discovered) >= 10, f"only found {len(discovered)}: {sorted(discovered)}"
    assert "msgspec.json.encode" in discovered
    assert "msgspec.json.Encoder" in discovered
    assert "msgspec.Struct" not in discovered, (
        "the scan matched a type that takes no hook — it is over-broad, and "
        "banning `Struct` would make declaring a model impossible"
    )


@pytest.mark.parametrize(
    "call",
    [
        "msgspec.json.encode(1)",
        "msgspec.msgpack.encode(1)",
        "msgspec.convert(1, int)",
        "msgspec.to_builtins(1)",
    ],
)
def test_a_direct_msgspec_call_is_rejected_by_the_linter(
    call: str, tmp_path: Path
) -> None:
    """The gate, driven end to end rather than read out of the config.

    Asserting the pyproject key exists would pass whether or not ruff honours
    it — and TID251's resolution of *attribute* access (as opposed to a plain
    import) is exactly the part being relied on. So this feeds ruff files that
    must fail and requires the failure ([[probes-need-a-control-arm]] rule 9).

    Four shapes rather than one: the two obvious formats plus the two entry
    points a hand-written ban list would have missed.
    """
    offender = tmp_path / "offender.py"
    offender.write_text(
        f'"""Temporary probe."""\n\nimport msgspec\n\n{call}\n', encoding="utf-8"
    )

    proc = _ruff_external(offender)

    assert "TID251" in proc.stdout, (
        f"ruff did not flag `{call}` — the AC4 gate is not armed for it. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )


def test_declaring_a_model_is_not_caught_by_the_ban(tmp_path: Path) -> None:
    """Control arm: a ban broad enough to catch `msgspec.Struct` is unusable.

    Without this, "the linter rejects a msgspec call" is indistinguishable from
    "the linter rejects the word msgspec", and the gate would be reported as
    working while making the library unusable.
    """
    innocent = tmp_path / "innocent.py"
    innocent.write_text(
        '"""Temporary probe."""\n\nimport msgspec\n\n\n'
        "class S(msgspec.Struct):\n"
        '    """A model."""\n\n'
        "    x: int\n",
        encoding="utf-8",
    )

    proc = _ruff_external(innocent)

    assert "TID251" not in proc.stdout, (
        f"declaring a msgspec model trips the ban — it is over-broad: {proc.stdout!r}"
    )


def test_the_codec_module_itself_is_allowed_to_call_msgspec(tmp_path: Path) -> None:
    """Control arm: a ban with no exemption would make the module unwritable.

    ⚠️ The first version of this test PASSED with the exemption deleted, and the
    mutation that caught it is why the module dispatches the way it does. The
    module used to hold `_CODECS = {Format.JSON: msgspec.json}` and call
    `_codec(fmt).encode(...)` — an attribute on a *runtime value*, which ruff
    cannot resolve statically. So the banned path never appeared in the file,
    the per-file allowance was dead configuration, and this test asserted the
    absence of a violation that could not have occurred.

    Hence the two arms below, and note what the FIRST attempt at arming this
    got wrong: it asserted the module's *text* contained a banned path, and
    passed on the indirect version anyway — because this module's own docstring
    quotes `msgspec.json.encode` as an example. A file's documentation had
    satisfied a contract about its wiring, which `python/AGENTS.md` records as
    the way 11 of 33 contract tokens were being met.

    So the arm below asks ruff, not a substring: the same source, at a path the
    allowance does not cover, MUST be flagged. That fails on indirection,
    because indirection is precisely what ruff cannot see.
    """
    package = REPO_ROOT / "python" / "src" / "dotfiles_setup"
    source = (package / "codec.py").read_text(encoding="utf-8")

    unexempt = tmp_path / "codec.py"
    unexempt.write_text(source, encoding="utf-8")

    without_allowance = _ruff_external(unexempt)

    assert "TID251" in without_allowance.stdout, (
        "the same source at an unexempt path is NOT flagged, so codec.py's "
        "TID251 allowance is dead config and this test cannot fail. The usual "
        "cause is indirect dispatch — ruff cannot resolve an attribute on a "
        "runtime value, which also means any module could evade the ban that "
        f"way. stdout={without_allowance.stdout!r}"
    )

    proc = _ruff(package / "codec.py")

    assert "TID251" not in proc.stdout, (
        f"the codec module is caught by the ban it exists to satisfy, despite "
        f"its per-file allowance: {proc.stdout!r}"
    )


def test_no_module_outside_the_codec_calls_msgspec_directly() -> None:
    """AC4 as a standing sweep, so a new call site cannot arrive unnoticed.

    The linter gate above proves the RULE fires; this proves the TREE is clean,
    and the two fail for different reasons — a disabled rule leaves this green.
    """
    package = REPO_ROOT / "python" / "src" / "dotfiles_setup"
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted(package.rglob("*.py"))
        if path.name != "codec.py"
        and _IMPORTS_MSGSPEC_RE.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == [], (
        f"modules import msgspec outside the codec: {offenders}. Route them "
        f"through dotfiles_setup.codec so the hooks are applied exactly once"
    )


def test_the_sweep_can_actually_see_a_violation() -> None:
    """Control arm for the sweep above.

    A "no offenders" assertion is satisfied for free by an empty file list,
    which is what a wrong root or a typo'd glob produces. Three arms: the scan
    reaches a real package, its matcher fires on the one module that really
    imports msgspec, and it does NOT fire on prose that merely names it.

    That third arm is review F5. The matcher used to be the bare substring
    `"msgspec"`, so a module documenting the ban would be reported as violating
    it — and `python/AGENTS.md` in this same change tells every author to write
    that sentence, with a failure message telling them to "route it through the
    codec" for a file that has no call at all.
    """
    package = REPO_ROOT / "python" / "src" / "dotfiles_setup"
    scanned = [path for path in package.rglob("*.py") if path.name != "codec.py"]

    assert len(scanned) > 20, f"the sweep found only {len(scanned)} modules to scan"
    assert _IMPORTS_MSGSPEC_RE.search(
        (package / "codec.py").read_text(encoding="utf-8")
    ), (
        "the matcher does not find an import in the one module that has one, "
        "so its zero-result on every other module proves nothing"
    )
    assert not _IMPORTS_MSGSPEC_RE.search(
        "# never call msgspec directly - use dotfiles_setup.codec\n"
    ), (
        "the matcher fires on prose that merely NAMES msgspec, so a module "
        "documenting the ban would be reported as violating it"
    )


# --------------------------------------------------------------------------- #
# The format seam
# --------------------------------------------------------------------------- #


def test_the_binary_format_comes_from_the_same_definitions() -> None:
    """#669: a compact binary form "from the same definitions", one call to swap.

    Pinned because the alternative — a second model or a second hook set for
    msgpack — is exactly the drift this module exists to prevent.
    """
    value = _Sample(workspace=Path("/a"), label="x")

    as_json = codec.encode(value, fmt=codec.Format.JSON)
    as_msgpack = codec.encode(value, fmt=codec.Format.MSGPACK)

    assert as_json != as_msgpack
    assert codec.decode(as_msgpack, _Sample, fmt=codec.Format.MSGPACK) == value


def test_json_is_the_default_format() -> None:
    """#669 chose newline-delimited JSON as the record form.

    A default that silently changed would leave every un-annotated call site
    emitting a binary blob into a log meant to be read with `jq`.
    """
    assert codec.encode(Path("/a")) == codec.encode(Path("/a"), fmt=codec.Format.JSON)


@pytest.mark.parametrize(
    ("call", "kwargs"),
    [(codec.encode, {}), (codec.decode, {})],
)
def test_an_unknown_format_is_refused(
    call: Callable[..., object], kwargs: dict[str, object]
) -> None:
    """Neither entry point may fall back to a default on a bad format.

    Both are parametrised together because a guard added to one and forgotten
    on the other is the realistic half-fix.
    """
    args = (Path("/a"),) if call is codec.encode else (b'"/a"', Path)

    with pytest.raises(ValueError, match="format"):
        call(*args, fmt="yaml", **kwargs)


# --------------------------------------------------------------------------- #
# Regression arms for the `/code-review high` findings (F1-F7)
#
# Each pins a defect that shipped past a green suite, so the fix cannot be
# undone silently. They are grouped rather than scattered because what they have
# in common is the lesson: every one was invisible to tests written from the
# happy path.
# --------------------------------------------------------------------------- #


class _Boxed[T]:
    """A plain generic — deliberately NOT a `msgspec.Struct`.

    A Struct is handled natively, so it never reaches `dec_hook` and cannot
    exercise F1 at all. The review's own illustration used one and decodes fine;
    reaching the hook needs a type msgspec does not know.
    """

    def __init__(self, value: object) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Boxed) and other.value == self.value

    def __hash__(self) -> int:
        return hash(self.value)


def test_an_unregistered_parametrized_generic_fails_loudly() -> None:
    """F1: `Box[int]` has no `__mro__`, so the MRO walk raised `AttributeError`.

    Not merely the wrong exception type — AC3 promises the failure NAMES the
    offending type, and a bare `AttributeError: __mro__` names nothing and does
    not even come from this module.

    `list[int]` hid this for the whole first draft: `types.GenericAlias` proxies
    `__mro__` while `typing._GenericAlias` does not, so the covered spelling and
    the broken one look identical in a test.
    """
    with pytest.raises(codec.UnsupportedTypeError) as excinfo:
        codec.decode(b"1", _Boxed[int])

    assert excinfo.value.offending_type is _Boxed


def test_a_registered_parametrized_generic_can_be_decoded() -> None:
    """F1's sharper half: registration did not help — it could not be reached.

    A caller who did everything right still got `AttributeError`, which makes
    the extension seam unusable for generics rather than merely undiagnosed.
    """
    codec.register(
        _Boxed,
        encode=lambda boxed: boxed.value,
        decode=lambda _target, value: _Boxed(value),
    )
    try:
        assert codec.decode(b"1", _Boxed[int]) == _Boxed(1)
        assert codec.encode(_Boxed(1)) == b"1"
    finally:
        codec.unregister(_Boxed)


def test_the_generic_control_arm_distinguishes_the_two_spellings() -> None:
    """Control arm for F1: prove the two generic spellings really differ.

    Without this, the tests above could be passing because everything has an
    `__mro__` and there was never a bug to fix.
    """
    assert hasattr(list[int], "__mro__"), "types.GenericAlias no longer proxies __mro__"
    assert not hasattr(_Boxed[int], "__mro__"), (
        "typing._GenericAlias now has __mro__, so this whole class of defect is "
        "gone and the unwrapping in _runtime_class is no longer load-bearing"
    )


def test_registering_a_natively_supported_type_is_refused() -> None:
    """F2: it used to succeed and do nothing.

    msgspec never calls a hook for a type it handles itself, so the conversion
    sat in the table forever, unreachable. Measured before the guard:
    `register(Decimal, encode=float, ...)` then `encode(Decimal("1.50"))` still
    gave `b'"1.50"'` — a JSON string, `float` never called. Silent, ineffective,
    and on the module's own extension seam.
    """
    with pytest.raises(codec.AlreadyNativeError) as excinfo:
        codec.register(
            decimal.Decimal,
            encode=float,
            decode=lambda _t, value: decimal.Decimal(value),
        )

    assert excinfo.value.target is decimal.Decimal
    assert "Decimal" in str(excinfo.value)
    assert codec.encode(decimal.Decimal("1.50")) == b'"1.50"'


@pytest.mark.parametrize("native", [datetime.datetime, uuid.UUID, int, str])
def test_the_native_refusal_covers_more_than_the_one_type_that_found_it(
    native: type,
) -> None:
    """F2 across the axis, not just its discovering example.

    Fixing only `Decimal` would leave `datetime` — the other type someone
    plausibly wants re-encoded (as an epoch) — silently no-op.
    """
    with pytest.raises(codec.AlreadyNativeError):
        codec.register(native, encode=str, decode=lambda _t, value: value)


def test_a_type_msgspec_does_not_know_is_still_registrable() -> None:
    """Control arm for F2: a refusal that refused everything would be useless.

    This is the arm that separates "the guard discriminates" from "the guard
    rejects all registrations", and the tests above cannot tell them apart.
    """
    codec.register(
        _Boxed, encode=lambda boxed: boxed.value, decode=lambda _t, value: _Boxed(value)
    )
    codec.unregister(_Boxed)


def test_every_path_flavour_round_trips_into_its_own_type() -> None:
    """F6: the seeded decoder built `Path` regardless of what was asked for.

    So `PureWindowsPath` encoded happily and failed to decode — a write that
    succeeds and a read that fails in another process, which is exactly the
    half-registration `register()`'s docstring says the API exists to prevent.
    The seed had it.
    """
    for flavour in (pathlib.PurePosixPath, pathlib.PureWindowsPath):
        original = flavour("/opt/toolchain/bin")

        restored = codec.decode(codec.encode(original), flavour)

        assert restored == original, f"{flavour.__name__} did not round-trip"
        assert type(restored) is flavour, (
            f"{flavour.__name__} decoded to {type(restored).__name__} — the "
            f"decoder ignored the annotation it was given"
        )


def test_the_ruff_helper_refuses_a_verdict_it_could_not_read() -> None:
    """F3: every negative arm reads stdout, which a failed ruff leaves empty.

    So "no TID251 in stdout" was satisfied for free by a broken venv, a missing
    binary or a bad config path — a check that can only pass. Driven through a
    config path that does not exist, which is the realistic version of that.
    """
    with pytest.raises(AssertionError, match="ruff did not run"):
        _run_ruff(["--config", "/nonexistent/ruff.toml", "tests/test_codec.py"])


def test_the_module_scan_finds_msgspec_submodules_it_was_never_told_about() -> None:
    """F7: the module list was transcribed, defeating the point of deriving it.

    A new hook-taking submodule is the shape most likely to add a wire format,
    and a hand-written list is blind to exactly that. Asserted against a
    submodule NOT in the original four, so a regression to the literal list
    fails here.
    """
    discovered = {name.split(".")[1] for name in _hook_taking_apis() if "." in name}

    assert {"json", "msgpack", "toml", "yaml"} <= discovered
    submodules = {info.name for info in pkgutil.iter_modules(msgspec.__path__)}
    assert "structs" in submodules, (
        "msgspec's package layout changed; the discovery this test guards may "
        "need re-checking"
    )
