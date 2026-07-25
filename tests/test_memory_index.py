"""Tests for the memory-index checker (dotfiles_setup.memory_index).

Covers memory-dir discovery (env-aware, never hardcoded), index parsing, the
distinctive-fact extractor and its per-kind normalized matching (the prototype's
over-report is what these pin), the index_only/elsewhere split that decides
whether a trim would destroy a fact, inbound-ref lookup before a delete, budget
accounting, report rendering, and the exit code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import memory_index as mi

if TYPE_CHECKING:
    # Annotation-only: pytest injects fixtures by parameter NAME, so nothing
    # here needs pytest at runtime.
    import pytest

# --------------------------------------------------------------------- discovery


def test_memory_dir_uses_config_dir_env() -> None:
    got = mi.memory_dir(Path("/dev/dotfiles"), {"CLAUDE_CONFIG_DIR": "/x/cfg"}, None)
    assert got == Path("/x/cfg/projects/-dev-dotfiles/memory")


def test_memory_dir_defaults_to_home_claude() -> None:
    got = mi.memory_dir(Path("/dev/dotfiles"), {}, Path("/home/u"))
    assert got == Path("/home/u/.claude/projects/-dev-dotfiles/memory")


def test_memory_dir_is_sibling_of_transcripts() -> None:
    """The memory dir shares the encoded-project dir with the transcripts.

    Pins the reuse: if command_audit's path encoding ever changes, this fails
    rather than the two silently drifting to different projects.
    """
    root, env = Path("/dev/dot.files"), {"CLAUDE_CONFIG_DIR": "/cfg"}
    assert mi.memory_dir(root, env, None).parent == Path("/cfg/projects/-dev-dot-files")


def test_load_memories_excludes_the_index_itself(tmp_path: Path) -> None:
    """MEMORY.md must not count as a topic file: it holds every hook already."""
    (tmp_path / "MEMORY.md").write_text("- [A](a.md) — #12")
    (tmp_path / "a.md").write_text("body")
    assert mi.load_memories(tmp_path) == {"a.md": "body"}


# ------------------------------------------------------------------ index parsing


def test_parse_index_captures_title_target_hook_and_line() -> None:
    text = "# Index\n\n## Project\n\n- [My Thing](project_thing.md) — did #5\n"
    (entry,) = mi.parse_index(text)
    assert (entry.title, entry.target) == ("My Thing", "project_thing.md")
    assert entry.hook == "did #5"
    assert entry.line_no == 5


def test_parse_index_accepts_plain_double_dash_separator() -> None:
    (entry,) = mi.parse_index("- [T](f.md) -- hook text")
    assert entry.hook == "hook text"


def test_parse_index_ignores_non_entry_lines() -> None:
    assert mi.parse_index("# Title\n\nSome prose.\n\n## Section\n") == []


# ------------------------------------------------------------ unreadable entries


def test_a_link_line_with_the_wrong_separator_is_reported_not_skipped() -> None:
    """The worst silent failure: a line no check can see, in a clean report.

    `parse_index` drops it, so its facts are never compared and its link is
    never resolved — yet the report would still claim to have audited the
    index. It must fail instead.
    """
    result = mi.audit_index("- [T](a.md): shipped #244", {"a.md": "nothing"})
    assert result.entries == 0
    assert result.unparsed == ((1, "- [T](a.md): shipped #244"),)
    assert not result.ok


def test_a_link_line_with_no_hook_at_all_is_reported() -> None:
    """No hook means no facts, but its link still goes unresolved — report it."""
    result = mi.audit_index("- [T](gone.md)", {"a.md": "x"})
    assert [line for _, line in result.unparsed] == ["- [T](gone.md)"]
    assert not result.ok


def test_prose_and_headings_are_not_mistaken_for_unreadable_entries() -> None:
    text = "# Index\n\n## Project\n\nSee [the docs](https://x.dev) for detail.\n"
    assert mi.audit_index(text, {}).unparsed == ()


def test_a_well_formed_entry_is_never_reported_as_unreadable() -> None:
    """Both separators the index uses must parse — em dash and plain `--`."""
    text = "## Project\n- [A](a.md) — did #1\n- [B](b.md) -- did #2"
    result = mi.audit_index(text, {"a.md": "#1", "b.md": "#2"})
    assert (result.entries, result.unparsed) == (2, ())


# ------------------------------------------------------- distinctive-fact extraction


def test_distinctive_facts_finds_issues_shas_and_sizes() -> None:
    facts = mi.distinctive_facts("PR #244 at 8010c61 cut :dev to 17.5 GB")
    assert facts == [
        mi.Fact("issue", "#244"),
        mi.Fact("sha", "8010c61"),
        mi.Fact("size", "17.5GB"),
    ]


def test_distinctive_facts_deduplicates() -> None:
    assert mi.distinctive_facts("#5 and #5 again") == [mi.Fact("issue", "#5")]


def test_distinctive_facts_ignores_hex_looking_english_words() -> None:
    """`acceded`/`defaced` are pure [a-f] — a sha needs a digit too."""
    assert mi.distinctive_facts("acceded to the defaced facade") == []


def test_distinctive_facts_ignores_plain_numbers_that_are_all_hex_digits() -> None:
    """Every decimal digit is also hex, so a sha needs a LETTER too.

    Without the `[a-f]` lookahead these all read as commit shas — and the
    `research-YYYYMMDD-*` slug is this repo's own directory convention, so the
    false positive was one hook away from being live, not hypothetical.
    """
    assert mi.distinctive_facts("research-20260714-hook-enforcement") == []
    assert mi.distinctive_facts("run 16283746152 failed") == []
    assert mi.distinctive_facts("1234567 files") == []


def test_a_real_sha_still_extracts() -> None:
    """The letter requirement must not cost the shas the index actually holds."""
    facts = mi.distinctive_facts("green at c2cecd7, 53bedf4 and 352063a")
    assert [f.value for f in facts] == ["c2cecd7", "53bedf4", "352063a"]


def test_distinctive_facts_ignores_bare_numbers_and_prose_after_them() -> None:
    """An open unit suffix would read `4 facts` as a size; the unit set is closed."""
    assert mi.distinctive_facts("4 facts across 562 tests in 600s") == []


def test_distinctive_facts_ignores_a_short_hex_run() -> None:
    """Under 7 chars is not an abbreviated sha; `1234` would match everything."""
    assert mi.distinctive_facts("abc123 is not a sha") == []


# ---------------------------------------------------------- normalized fact matching


def test_size_matches_across_a_space_the_prototype_reported_as_missing() -> None:
    """THE over-report the prototype had: `25.8GB` vs `25.8 GB` is one fact."""
    assert mi.fact_present("shrank to 25.8 GB total", mi.Fact("size", "25.8GB"))
    assert mi.fact_present("shrank to 25.8GB total", mi.Fact("size", "25.8 GB"))


def test_size_unit_case_is_ignored_but_the_number_is_not() -> None:
    assert mi.fact_present("17.5 gb", mi.Fact("size", "17.5GB"))
    assert not mi.fact_present("17.6 GB", mi.Fact("size", "17.5GB"))


def test_sha_matches_a_longer_abbreviation_in_either_direction() -> None:
    """Authors abbreviate to taste; `8010c61` and `8010c61f2` are one commit."""
    assert mi.fact_present("landed 8010c61f2a", mi.Fact("sha", "8010c61"))
    assert mi.fact_present("landed 8010c61", mi.Fact("sha", "8010c61f2a"))


def test_sha_does_not_match_a_different_commit() -> None:
    assert not mi.fact_present("landed at c2cecd7", mi.Fact("sha", "3adff36"))


def test_issue_ref_does_not_match_a_longer_number() -> None:
    """`#24` must not be satisfied by `#244` — a word boundary, not a prefix."""
    assert not mi.fact_present("see #244", mi.Fact("issue", "#24"))
    assert mi.fact_present("see #24 here", mi.Fact("issue", "#24"))


# ------------------------------------------------------------- the index_only split


def test_fact_only_in_the_hook_is_index_only_and_fails_the_check() -> None:
    result = mi.audit_index(
        "- [T](a.md) — shipped #244", {"a.md": "unrelated body", "b.md": "also not it"}
    )
    (finding,) = result.findings
    assert finding.severity == "index_only"
    assert finding.fact == mi.Fact("issue", "#244")
    assert result.index_only == (finding,)
    assert not result.ok


def test_fact_in_another_memory_is_elsewhere_and_passes() -> None:
    """A trim cannot destroy a fact some other file records — so it is not an alarm."""
    result = mi.audit_index(
        "- [T](a.md) — shipped #244", {"a.md": "nothing", "b.md": "#244 landed here"}
    )
    (finding,) = result.findings
    assert finding.severity == "elsewhere"
    assert finding.elsewhere == ("b.md",)
    assert result.index_only == ()
    assert result.ok


def test_a_matching_size_in_an_unrelated_memory_is_not_the_same_fact() -> None:
    """`elsewhere` is only sound for globally-unique ids — a size is not one.

    `17.5 GB` of container image and `17.5 GB` of free disk share a number and
    nothing else. Treating the coincidence as survival downgraded a genuinely
    index-only measurement to informational and passed.
    """
    result = mi.audit_index(
        "- [Image](image.md) — :dev is 17.5GB after the strip",
        {
            "image.md": "the dev image shrank a lot",
            "unrelated_disk.md": "my laptop has 17.5 GB free",
        },
    )
    (finding,) = result.index_only
    assert finding.fact == mi.Fact("size", "17.5GB")
    assert finding.elsewhere == ()
    assert not result.ok


def test_a_fact_in_the_title_is_checked_not_just_the_hook() -> None:
    """The index really carries issue refs in titles (`PR #140 MERGED`).

    A curator shortens the whole `- [Title](file.md) — hook` line, so scanning
    only the hook let a title rewrite destroy an issue ref, report clean.
    """
    result = mi.audit_index(
        "- [GHA redesign epic #116 COMPLETE](gha.md) — all phases done",
        {"gha.md": "the epic is finished"},
    )
    (finding,) = result.index_only
    assert finding.fact == mi.Fact("issue", "#116")


def test_a_title_fact_present_in_the_topic_file_is_not_a_finding() -> None:
    result = mi.audit_index(
        "- [PR #140 MERGED](pr.md) — R2 fix", {"pr.md": "#140 landed the R2 fix"}
    )
    assert result.findings == ()


def test_fact_present_in_the_linked_file_is_not_a_finding() -> None:
    result = mi.audit_index("- [T](a.md) — shipped #244", {"a.md": "#244 shipped"})
    assert result.findings == ()
    assert result.ok


def test_the_index_does_not_satisfy_its_own_facts() -> None:
    """Searching MEMORY.md for a hook's fact always hits — it must stay excluded.

    Enforced inside audit_index, not just in load_memories: passing the index in
    would otherwise resolve every fact as "recorded somewhere" and return a
    clean report — the one failure mode a loss-checker cannot have.
    """
    index = "- [T](a.md) — shipped #244"
    result = mi.audit_index(index, {"a.md": "nothing", "MEMORY.md": index})
    assert result.index_only[0].fact == mi.Fact("issue", "#244")
    assert result.orphans == ()  # nor may it be reported as an unindexed memory


def test_broken_link_is_reported_and_fails_without_a_crash() -> None:
    """A dead target must not be read as `no facts to check`."""
    result = mi.audit_index("- [T](gone.md) — shipped #244", {"a.md": "x"})
    assert [e.target for e in result.broken] == ["gone.md"]
    assert result.findings == ()
    assert not result.ok


def test_orphan_is_reported_but_does_not_fail_the_check() -> None:
    """An unindexed memory loses nothing; failing on it would devalue the rc."""
    result = mi.audit_index("- [T](a.md) — hook", {"a.md": "x", "lonely.md": "y"})
    assert result.orphans == ("lonely.md",)
    assert result.ok


def test_the_real_stale_sha_finding_is_index_only() -> None:
    """The checker's first live hit, pinned.

    The hook claimed CI green at `3adff36` while its topic file said `c2cecd7`
    (a later commit). The fact was real, index-only, and STALE — which is why
    the report describes rather than prescribes: migrating `3adff36` down would
    have pushed an outdated sha into a file that already superseded it.
    """
    result = mi.audit_index(
        "- [Phase 1 status](p1.md) — Develop phase COMPLETE/closed (CI green 3adff36)",
        {"p1.md": "**Final CI state:** Green at `c2cecd7` (post-PR #44 fix)."},
    )
    (finding,) = result.index_only
    assert finding.fact == mi.Fact("sha", "3adff36")
    assert finding.elsewhere == ()


# ------------------------------------------------------------------------- budget


def test_budget_counts_lines_and_bytes() -> None:
    result = mi.audit_index("- [T](a.md) — hook\nsecond line\n", {"a.md": "hook"})
    assert (result.lines, result.size) == (2, 33)


def test_bytes_are_counted_as_utf8_not_characters() -> None:
    """The index is full of em dashes; a character count would understate it."""
    assert mi.audit_index("— x", {}).size == 5


def test_entries_past_the_load_cutoff_fail_the_check() -> None:
    """Past 200 lines an entry is not loaded at all — invisible, not just long."""
    text = "\n" * mi.LINE_BUDGET + "- [Late](a.md) — hook"
    result = mi.audit_index(text, {"a.md": "hook"})
    assert [e.title for e in result.beyond_budget] == ["Late"]
    assert not result.ok


def test_an_entry_past_the_byte_cutoff_fails_even_when_under_200_lines() -> None:
    """The byte cap binds FIRST on this index — and was the unenforced one.

    An earlier revision checked only `line_no > LINE_BUDGET`, on the belief that
    lines were the nearer ceiling. At ~149 bytes/line the 25KB cap lands near
    line 168, so the line cap is never reached and the ONLY axis that could fire
    was the one not enforced: the report printed `OVER` in its own budget table
    and still exited 0.

    `Early` sits before the byte cutoff and `Late` after it, so this pins that
    the cutoff is located, not just that something failed.
    """
    text = (
        "- [Early](a.md) — hook\n" + ("x" * 399 + "\n") * 63 + "- [Late](b.md) — hook\n"
    )
    result = mi.audit_index(text, {"a.md": "hook", "b.md": "hook"})
    assert result.lines < mi.LINE_BUDGET  # under the line cap...
    assert result.size > mi.BYTE_BUDGET  # ...but over the byte cap
    assert [e.title for e in result.beyond_budget] == ["Late"]
    assert not result.ok


def test_load_cutoff_line_returns_the_line_budget_when_bytes_never_breach() -> None:
    assert mi.load_cutoff_line("- [T](a.md) — hook\n") == mi.LINE_BUDGET


def test_load_cutoff_line_counts_the_newline_bytes_too() -> None:
    """The loader pays for line endings, so `keepends` is not incidental."""
    line = "x" * 99 + "\n"  # exactly 100 bytes with its newline
    text = line * 300
    assert mi.load_cutoff_line(text) == mi.BYTE_BUDGET // 100


def test_an_over_cap_index_never_reports_over_and_exits_0() -> None:
    """The table and the exit code must not tell the reader opposite things."""
    result = mi.audit_index("x" * (mi.BYTE_BUDGET + 1), {})
    assert result.over_cap
    assert not result.ok


def test_report_names_bytes_as_the_nearer_ceiling_when_they_are() -> None:
    """The claim that lines bind first was wrong; the report computes it instead.

    Both the handoff and the memory asserted "the LINE count is the nearer
    ceiling" over numbers that said otherwise (60% of lines vs 82% of bytes).
    A dense, short index runs out of bytes first.
    """
    dense = "- [T](a.md) — " + "x" * 900 + "\n"
    report = mi.render_report(mi.audit_index(dense, {"a.md": "x" * 900}))
    assert "**bytes** is the nearer ceiling" in report


def test_report_names_lines_as_the_nearer_ceiling_when_they_are() -> None:
    sparse = "\n" * 150
    report = mi.render_report(mi.audit_index(sparse, {}))
    assert "**lines** is the nearer ceiling" in report


# -------------------------------------------------------------------- inbound refs


def test_inbound_refs_finds_every_citation_form_the_memories_use() -> None:
    """Wikilink, alias, bare filename, and bare backticked stem.

    The bare-stem form is the one an earlier revision missed: measured against
    the live memory dir it made 4 real citations invisible, and reported a
    memory that IS cited as having none — the false reassurance that precedes a
    delete.
    """
    files = {
        "feedback_target.md": "self",
        "cites_wiki.md": "see [[feedback_target]] for detail",
        "cites_alias.md": "see [[feedback_target|the target]] for detail",
        "cites_path.md": "absorbed into feedback_target.md",
        "cites_stem.md": "The `feedback_target` memory is authoritative",
        "unrelated.md": "nothing",
    }
    assert mi.inbound_refs("feedback_target.md", files) == [
        "cites_alias.md",
        "cites_path.md",
        "cites_stem.md",
        "cites_wiki.md",
    ]


def test_inbound_refs_accepts_a_name_without_the_extension() -> None:
    assert mi.inbound_refs("t.md", {"a.md": "[[t]]"}) == ["a.md"]


def test_inbound_refs_never_counts_the_file_itself() -> None:
    """A memory's own frontmatter `name:` must not read as a citation."""
    assert mi.inbound_refs("t.md", {"t.md": "name: t\n[[t]]"}) == []


def test_inbound_refs_does_not_match_a_longer_neighbour_name() -> None:
    assert mi.inbound_refs("t.md", {"a.md": "[[t_extended]] and t_extended.md"}) == []


def test_render_refs_warns_even_when_nothing_cites_the_memory() -> None:
    """The colima case: no citation still does not make a delete safe."""
    out = mi.render_refs("x.md", [], known=True)
    assert "No inbound citations" in out
    assert "still true" in out


# --------------------------------------------------------------- rendering / main


def test_report_says_so_when_a_trim_is_safe() -> None:
    report = mi.render_report(mi.audit_index("- [T](a.md) — #5", {"a.md": "#5"}))
    assert "_None — every distinctive fact" in report
    assert "Index-only facts" in report


def test_report_lists_the_offending_line_number() -> None:
    report = mi.render_report(mi.audit_index("- [T](a.md) — #5", {"a.md": "x"}))
    assert "| 1 | `#5` | issue | `a.md` | — |" in report


def _seed_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index: str, **files: str
) -> Path:
    """A project root whose memory dir holds ``index`` + ``files``."""
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    directory = mi.memory_dir(root)
    directory.mkdir(parents=True)
    (directory / "MEMORY.md").write_text(index)
    for name, text in files.items():
        (directory / f"{name}.md").write_text(text)
    return root


def test_main_exits_1_when_a_trim_would_destroy_a_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _seed_memory(
        tmp_path, monkeypatch, "- [T](a.md) — shipped #244", a="nothing here"
    )
    assert mi.memory_index_main(root) == 1
    assert "#244" in capsys.readouterr().out


def test_main_exits_0_when_the_index_is_lossless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_memory(
        tmp_path, monkeypatch, "- [T](a.md) — shipped #244", a="#244 shipped"
    )
    assert mi.memory_index_main(root) == 0


def test_main_output_writes_file_instead_of_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _seed_memory(tmp_path, monkeypatch, "- [T](a.md) — #244", a="#244")
    assert mi.memory_index_main(root, output=Path(".agent/memory-index.md")) == 0
    assert "Index-only facts" in (root / ".agent" / "memory-index.md").read_text()
    out = capsys.readouterr().out
    assert "wrote" in out
    assert "Index-only facts" not in out  # the body went to the file, not stdout


def test_main_refs_lists_citations_and_always_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A query reports; it does not judge — the rc is reserved for losses."""
    root = _seed_memory(
        tmp_path, monkeypatch, "- [T](a.md) — hook", a="body", b="see [[a]] for detail"
    )
    assert mi.memory_index_main(root, refs="a") == 0
    assert "b.md" in capsys.readouterr().out


def test_main_refs_does_not_audit_so_a_lossy_index_still_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _seed_memory(tmp_path, monkeypatch, "- [T](a.md) — #244", a="nothing")
    assert mi.memory_index_main(root, refs="a") == 0


def test_main_is_quiet_and_passes_when_there_is_no_memory_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fresh clone has no memory yet; that is not a failure."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    assert mi.memory_index_main(tmp_path / "repo") == 0
    assert "no memory directory" in capsys.readouterr().out


def test_cli_accepts_the_documented_flags() -> None:
    """`--output` and `--refs` must exist on the REAL CLI.

    The contract asserts main.py names them; this asserts argparse actually
    accepts them, so the mise task cannot fail only at runtime.
    """
    cmd = ["uv", "run", "--project", "python", "dotfiles-setup", "memory-index"]
    res = subprocess.run(
        [*cmd, "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).parent.parent,
        timeout=120,
    )
    assert res.returncode == 0
    assert "--output" in res.stdout
    assert "--refs" in res.stdout
