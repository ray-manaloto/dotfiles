# Copyright (c) 2026 Raymond Manaloto
"""Read the caller's research scope from the native prompt submission.

The native event is the authority, not a later declaration file or model text.
Only the research scope writes hook state (round 4); its record is an
integrity record, not protection against a process with write access to hook
state. Native client qualification must establish delivery of the caller's
original prompt to UserPromptSubmit.
"""

from __future__ import annotations

import re
import unicodedata

LOCAL_ONLY_DIRECTIVE = "[research-scope: local-only]"
RESEARCH_DIRECTIVE = "[research-scope: research]"
IMPLEMENTATION_DIRECTIVE = "[research-scope: implementation]"
# Only research requires a receipt; the other scopes write no hook state.
SCOPES = frozenset({"local-only", "implementation", "text-edit", "research"})
_DIRECTIVE = re.compile(r"\[research-scope: ([a-z-]+)\]")
_NEAR_MISS_PREFIX = "[research-scope"


def _first_line(prompt: str) -> str:
    return prompt.partition("\n")[0].removesuffix("\r")


def directive(prompt: str) -> str | None:
    """Return the scope an exact caller first line declares, else None.

    A CRLF line ending is accepted; case, spacing and lookalikes are not.
    """
    match = _DIRECTIVE.fullmatch(_first_line(prompt))
    return match[1] if match is not None and match[1] in SCOPES else None


def near_miss(prompt: str) -> bool:
    """Whether line 1 looks like a directive but is not an exact one.

    Leading blanks and a BOM are dropped, then a bounded head is NFKC-folded
    (fullwidth brackets) and casefolded; each step is linear.
    """
    if directive(prompt) is not None:
        return False
    head = _first_line(prompt).lstrip().lstrip("﻿").lstrip()[:64]
    folded = unicodedata.normalize("NFKC", head).casefold()
    return folded.startswith(_NEAR_MISS_PREFIX)


# --- Research intent (cg36b, D246 item 3) -----------------------------------
# Only the caller's own prose counts. Lines are read once: fenced blocks (an
# unclosed fence runs to the end), blockquote, JSON, timestamped-log and
# indented-code lines are skipped, and a bare marker line (`Ticket:`, `Issue:`,
# `Spec:`, `Acceptance criteria:`, `---`) ends the prose. Inline code and quote
# spans are cut out, and `title:`-style data keys drop the rest of their line.
# A request is an imperative at a clause start. Each step is a str method or a
# regex without nested quantifiers, and every scan resumes past its last stop.


def _vocab(words: str) -> frozenset[str]:
    return frozenset(words.split())


_RULE = 3  # a fence or a `---` marker line
_MARKERS = frozenset({"ticket:", "issue:", "spec:", "acceptance criteria:"})
_LOG_LINE = re.compile(r"\[?\d{4}-\d\d-\d\d")
_OPEN = re.compile("[`\"'\u2018\u201c\u201e]")
_CLOSE = {
    "`": re.compile("`"),
    '"': re.compile('"'),
    "\u201c": re.compile("[\u201c\u201d]"),
    "\u201e": re.compile("[\u201c\u201d]"),
    "\u2018": re.compile("\u2019(?!\\w)"),
    # An apostrophe never closes; a sentence end inside means no span.
    "'": re.compile(r"'(?!\w)|[;.!?](?=\s)"),
}
_EDGE = ",()[]{}<>*\"'`\u2018\u2019\u201c\u201d"
_ENDS = ".!?;:"
_KEYS = _vocab(
    "title name task description summary body subject message text says said "
    "reads titled named file mode run id prompt query output info warn warning "
    "debug fatal"
)
_LEAD_WORDS = _vocab("please kindly go now also next first then and so hey ok just")
_LEAD_PHRASES = {
    "can": ("you",),
    "could": ("you",),
    "would": ("you",),
    "will": ("you",),
    "let's": (),
    "let": ("us",),
    "i": ("need", "you", "to"),
}
# "research" followed by one of these is a noun or a subject, not a request.
_NOUN_USE = _vocab(
    "gate gates note notes record records receipt receipts scope workflow fanout "
    "cache summary doc docs hook hooks hint coverage failure failures lane lanes "
    "provider providers task tasks team mode step phase result results output "
    "report reports directive directives log logs code test tests file files is "
    "are was were has had will should can must may fails failed passes passed"
)
_FRESH = _vocab("latest newest current")
_WEB = _vocab("web internet online github")
_EXTERNAL = (
    _FRESH
    | _WEB
    | _vocab("upstream changelog release releases docs documentation version versions")
)
_NOT_NAMES = _vocab("two old new these those both first second previous") | {""}
_LOCAL = _vocab(
    "this these our here local locally repo repository codebase branch commit "
    "commits diff function functions method class definition test tests lockfile "
    "log logs git file files fixture fixtures bug crash ci pr changes output "
    "outputs manifest parser gate schema script module worktree history run main "
    "master head"
)
_EXTENSIONS = _vocab(
    "py rs toml json md yml yaml lock sh txt ts js c cc cpp h hpp go rb lua cfg "
    "ini log sql"
)


def _unquoted(line: str) -> str:
    """Cut inline code and quote spans; an unclosed span runs to line end."""
    kept: list[str] = []
    start = pos = dead = 0
    while (found := _OPEN.search(line, pos)) is not None:
        index, mark = found.start(), found[0]
        pos = index + 1
        before = line[index - 1] if index else " "
        if mark == '"' and before.isalnum():  # an inch mark
            continue
        if mark == "'" and (index < dead or not (before.isspace() or before == "(")):
            continue
        close = _CLOSE[mark].search(line, pos)
        if mark == "'" and (close is None or close[0] != "'"):
            dead = close.start() if close is not None else len(line)
            continue
        kept.append(line[start:index])
        start = pos = close.end() if close is not None else len(line)
    kept.append(line[start:])
    return " \x00 ".join(kept)


def _norm(raw: str) -> str:
    word = raw.strip(_EDGE).rstrip(_ENDS).strip(_EDGE)
    return word.replace("\u2019", "'").casefold()


def _local(raws: list[str]) -> bool:
    """A repository object: a local word, a path, an identifier or a call."""
    for raw in raws:
        token = raw.strip(_EDGE).rstrip(_ENDS)
        stem, dot, ext = token.rpartition(".")
        if (
            _norm(raw) in _LOCAL
            or "_" in token
            or "()" in raw
            or token[:1] in {".", "/", "~"}
            or token.endswith("/")
            or token.count("/") > 1
            or (dot and stem and ext.casefold() in _EXTENSIONS)
        ):
            return True
    return False


def _lead_end(words: list[str]) -> int:
    """Skip polite lead-ins such as `please`, `can you`, `I need you to`."""
    at = 0
    while at < len(words):
        rest = _LEAD_PHRASES.get(words[at])
        if words[at] in _LEAD_WORDS:
            at += 1
        elif rest is not None and tuple(words[at + 1 : at + 1 + len(rest)]) == rest:
            at += 1 + len(rest)
        else:
            break
    return at


def _lookup(v: list[str]) -> bool:
    """A look-up verb at the clause start whose object may be upstream."""
    if v[0] in {"find", "check"}:
        return v[1] == "the" and v[2] in _FRESH
    if v[:2] == ["look", "up"]:
        return not _EXTERNAL.isdisjoint(v[2:])
    if v[0] == "compare":
        name = 2 if v[1] == "the" else 1
        return v[name] not in _NOT_NAMES and v[name + 1] == "and"
    if v[:2] == ["what", "is"] or v[0] == "what's":
        asked = v[2:5] if v[0] == "what" else v[1:4]
        return asked[:2] == ["new", "in"] or (
            asked[0] == "the"
            and asked[1] in _FRESH
            and asked[2] in {"version", "release"}
        )
    return False


def _request(raws: list[str], *, colon: bool) -> bool:
    """Whether one clause opens with an imperative research request."""
    words = [_norm(raw) for raw in raws]
    v = [*words[_lead_end(words) :], "", "", "", ""]
    if v[0] == "research":
        return colon if not v[1] else v[1] not in _NOUN_USE
    if v[0] == "do":
        return "research" in {v[1], v[2] if v[1] in {"some", "more"} else ""}
    if v[0] == "search":
        return (v[2] if v[1] == "the" else v[1]) in _WEB
    return _lookup(v) and not _local(raws)


def _feed(body: str, pending: list[str]) -> bool:
    """Add one prose line to the open clause; True once a clause is a request."""
    words = _unquoted(body).split()
    if words and (words[0] in {"-", "*", "+"} or words[0].rstrip(".)").isdigit()):
        del words[0]
    for raw in words:
        pending.append(raw)
        end = raw.rstrip(_EDGE)[-1:]
        if not end or end not in _ENDS:
            continue
        if _request(pending, colon=end == ":"):
            return True
        pending.clear()
        key = _norm(raw)
        if end == ":" and (key in _KEYS or key.endswith(("error", "exception"))):
            break
    return False


def _quoted_line(line: str, body: str) -> bool:
    return (
        not body
        or body[0] in ">{["
        or line.startswith(("\t", "    "))
        or _LOG_LINE.match(body) is not None
    )


def intent(prompt: str) -> bool:
    """Whether the caller's own prose asks the assistant to research something."""
    pending: list[str] = []
    fence = ""
    for line in prompt.split("\n"):
        body = line.strip()
        if fence:
            fence = "" if body.startswith(fence) else fence
            continue
        if body.casefold() in _MARKERS or (len(body) >= _RULE and not body.strip("-")):
            break
        fence = body[:_RULE] if body.startswith(("```", "~~~")) else ""
        skip = bool(fence) or _quoted_line(line, body)
        # A lowercase line continues a wrapped clause; anything else starts one.
        if skip or not body[0].islower():
            if _request(pending, colon=False):
                return True
            pending.clear()
        if not skip and _feed(body, pending):
            return True
    return _request(pending, colon=False)
