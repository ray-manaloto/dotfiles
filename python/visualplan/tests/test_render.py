"""visualplan render, run as the installed console script on real plan.json files."""

import copy
import functools
import json
import subprocess
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from visualplan.cli import DATA_ERROR

SCRIPT = Path(sys.executable).parent / "visualplan"
ROOT = Path(__file__).parents[3]  # the repository root, where //visualplan resolves
PLAN: dict[str, Any] = {
    "title": "Cache the build",
    "status": {"revision": 3, "updated": "2026-11-06T15:04Z", "state": "waiting_on_you", "next": ["Pick a store"]},
    "claims": [
        {
            "id": "c1",
            "text": "Builds reuse the last result",
            "where": "src/build.py:12",
            "children": [
                {"id": "c1a", "text": "Keyed by input hash", "where": "src/key.py:3"},
                {"id": "c1b", "text": "Old entries expire", "children": [{"id": "c1b1", "text": "After a week"}]},
            ],
        },
        {"id": "c2", "text": "Nothing else changes"},
    ],
    "decisions": [
        {
            "id": "d1",
            "claim": "c1",
            "question": "Where does the cache live?",
            "recommended": {"label": "Disk", "why": "No new service"},
            "alternatives": [{"label": "Redis", "why": "Shared across machines"}],
        },
        {
            "id": "d2",
            "question": "Expire after?",
            "recommended": {"label": "A week", "why": "Covers a sprint"},
            "alternatives": [{"label": "A day", "why": "Short"}, {"label": "Never", "why": "Simplest"}],
        },
    ],
    "tests": [
        {"id": "t1", "name": "test_hit", "kind": "unit", "status": "pass"},
        {"id": "t2", "name": "test_expiry", "kind": "unit", "status": "not_run"},
        {"id": "t3", "name": "test_miss", "kind": "integration", "status": "fail"},
    ],
}
# The page's own markup: every element and attribute it writes. A plan text that adds any other is live markup.
TAGS = {"html", "head", "meta", "title", "style", "body", "h1", "h2", "h3", "div", "p", "span", "ul", "li", "code",
        "strong", "table", "tr", "th", "td"}  # fmt: skip
ATTRIBUTES = {"lang", "charset", "name", "content", "class"}


def render(tmp_path: Path, plan: object, page: Path | None = None) -> tuple[int, list[dict], list[dict], Path]:
    source = tmp_path / "plan.json"
    source.write_text(json.dumps(plan))
    out = page or tmp_path / "page.html"
    done = subprocess.run([SCRIPT, "render", source, out], capture_output=True, text=True, check=False)
    return done.returncode, lines(done.stdout), lines(done.stderr), out


def lines(stream: str) -> list[dict]:
    return [json.loads(line) for line in stream.splitlines()]


class Markup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.attributes: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        self.attributes.update(name for name, _ in attrs)


def markup(page: str) -> Markup:
    parser = Markup()
    parser.feed(page)
    return parser


def test_the_page_shows_status_claims_decisions_and_tests_failing_first(tmp_path: Path) -> None:
    rc, out, err, page = render(tmp_path, PLAN)
    assert (rc, out, err) == (0, [{"wrote": str(page)}], [])
    html = page.read_text()
    assert "Waiting on you</span> · revision 3 · updated 2026-11-06T15:04Z" in html
    assert "<li>Pick a store</li>" in html
    assert '<li><code>c1a</code> Keyed by input hash <span class="where">src/key.py:3</span></li>' in html
    assert '<span class="rec">Recommended:</span> <strong>Disk</strong>: No new service' in html
    assert "<li><strong>Redis</strong>: Shared across machines</li>" in html
    assert '<h3><code>d1</code> Where does the cache live? <span class="where">(claim c1)</span></h3>' in html
    assert html.index("test_miss") < html.index("test_expiry") < html.index("test_hit")
    assert '<td class="not_run">not run</td>' in html
    assert "<li><code>c1b1</code> After a week</li>" in html
    assert "<li><strong>Never</strong>: Simplest</li>" in html


def test_a_plan_with_nothing_next_shows_no_next_list(tmp_path: Path) -> None:
    plan = copy.deepcopy(PLAN)
    plan["status"]["next"] = []
    rc, _, _, page = render(tmp_path, plan)
    assert rc == 0
    assert "Next:" not in page.read_text()


# Every text field of PLAN, as the path of keys and indexes that reaches it.
TEXT_FIELDS: list[tuple[str | int, ...]] = [
    ("title",),
    ("status", "next", 0),
    *(("claims", 0, *child, key) for child in [(), ("children", 0)] for key in ("id", "text", "where")),
    *(("decisions", 0, key) for key in ("id", "claim", "question")),
    *(("decisions", 0, *option, key) for option in [("recommended",), ("alternatives", 0)] for key in ("label", "why")),
    *(("tests", 0, key) for key in ("name", "kind")),
]


def test_plan_text_in_every_field_comes_out_as_text(tmp_path: Path) -> None:
    plan, payloads = copy.deepcopy(PLAN), []
    for n, (*path, key) in enumerate(TEXT_FIELDS):
        payload = f'<script>f{n}</script>"><img src=x onerror=f{n}>& f{n}' + (":7" if key == "where" else "")
        holder: Any = functools.reduce(lambda node, step: node[step], path, plan)
        holder[key] = payload
        payloads.append(payload)
    rc, _, err, page = render(tmp_path, plan)
    assert rc == 0, err
    html = page.read_text()
    for payload in payloads:
        assert escape(payload) in html
        assert payload not in html
    found = markup(html)
    assert found.tags <= TAGS, found.tags - TAGS
    assert found.attributes <= ATTRIBUTES, found.attributes - ATTRIBUTES


def test_a_second_render_replaces_the_page_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    render(tmp_path, PLAN)
    rc, _, _, page = render(tmp_path, {**PLAN, "title": "Cache the build, take two"})
    assert rc == 0
    assert "<title>Cache the build, take two</title>" in page.read_text()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page.html", "plan.json"]


def test_a_plan_that_breaks_the_schema_is_one_error_line_and_no_page(tmp_path: Path) -> None:
    rc, out, err, page = render(tmp_path, {**PLAN, "status": {**PLAN["status"], "state": "maybe"}})
    assert (rc, out, len(err)) == (DATA_ERROR, [], 1)
    assert "status.state" in err[0]["error"]
    assert not page.exists()


def test_a_page_path_that_is_a_folder_is_one_error_line_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    (tmp_path / "page.html").mkdir()
    rc, _, err, _ = render(tmp_path, PLAN)
    assert rc == DATA_ERROR
    assert "page.html" in err[0]["error"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page.html", "plan.json"]


@pytest.mark.parametrize("name", ["notes.html", "plan.json"], ids=["another file", "the plan itself"])
def test_a_page_path_holding_a_file_visualplan_did_not_write_is_refused_and_kept(tmp_path: Path, name: str) -> None:
    page = tmp_path / name
    if name != "plan.json":
        page.write_text("<p>my notes</p>")
    rc, _, err, _ = render(tmp_path, PLAN, page=page)
    kept = json.dumps(PLAN) if name == "plan.json" else "<p>my notes</p>"
    assert rc == DATA_ERROR
    assert err == [{"error": f"{page} is not a page visualplan wrote: move it away or write the page to another file"}]
    assert page.read_text() == kept


def test_the_render_task_takes_hostile_paths_literally(tmp_path: Path) -> None:
    folder = tmp_path / "a b $(echo x) ; 'q' \"d\" `id`"
    folder.mkdir()
    source, page = folder / "plan $HOME.json", folder / "page *.html"
    source.write_text(json.dumps(PLAN))
    task = ["mise", "run", "//visualplan:render", source, page]
    done = subprocess.run(
        task, cwd=ROOT, capture_output=True, text=True, check=False
    )  # mise from PATH, as a user runs it
    assert done.returncode == 0, done.stderr
    assert lines(done.stdout) == [{"wrote": str(page)}]
    assert sorted(p.name for p in folder.iterdir()) == ["page *.html", "plan $HOME.json"]
