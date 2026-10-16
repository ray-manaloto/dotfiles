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
# Only the caller's own prose in the first 32 KiB counts. Lines are read once:
# CommonMark fences (an unclosed fence runs to the end), blockquote, JSON, log,
# indented-code, `#` heading, task-list, commit-subject (`fix(scope)!:`) and
# colon-ended lines are skipped, and a bare marker line (`Ticket:`, `Issue:`,
# `Spec:`, `Acceptance criteria:`, `---`) ends the prose. Inline code and quote
# spans are cut out, and a label key or a ticket id before `:` drops the rest of
# its line. A request is an imperative at a clause start whose object is not
# local: a rooted, two-slash or file-name path, a dotfile, an identifier or a
# call is local; a URL, an owner/repo slug or a capitalised `Name.js` is
# upstream. Each step is a str method or a regex without nested quantifiers,
# and every scan resumes past its last stop.


def _vocab(words: str) -> frozenset[str]:
    return frozenset(words.split())


_SCAN_LIMIT = 32 * 1024  # a request sits in the opening prose (security P3-4)
_RULE = 3  # a fence or a `---` marker line
_MARKERS = frozenset({"ticket:", "issue:", "spec:", "acceptance criteria:"})
_LOG_LINE = re.compile(r"\[?\d{4}-\d\d-\d\d")
_TICKET = re.compile(r"#\d+|[a-z][a-z0-9]*-\d+")
# A conventional-commit subject quotes its line; `Goal:` and `Plan:` stay prose.
_COMMIT = re.compile(
    r"(?:[-*+]\s+)?(?:feat|fix|chore|docs|refactor|test|ci|build|perf|style)"
    r"(?:\([^()]*\))?!?:"
)
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
# A clause opening with one of these labels quotes the rest of its line.
_LABELS = _vocab(
    "ticket issue spec task title story bug acceptance todo fixme note summary "
    "body description"
)
_LEAD_WORDS = _vocab("please kindly go now also next first then and so hey ok just")
_LEAD_PHRASES = {
    "can": (("you",),),
    "could": (("you",),),
    "would": (("you",),),
    "will": (("you",),),
    "let's": ((),),
    "let": (("us",),),
    "i": (("need", "you", "to"), ("want", "you", "to")),
    "i'd": (("like", "you", "to"),),
}
# A leading subordinate clause (`Before we decide, research X`) ends at its comma.
_SUBORDINATE = _vocab(
    "before after once when whenever if since while until unless because although"
)
# `research` + an auxiliary or copula (a closed class) is a subject or status.
_AUX = _vocab(
    "is are was were be been am has have had does did will would shall should "
    "can could may might must done"
)
# Finite verbs that follow `research` as a subject (`Research uses the cache`,
# CG-36 r2's CG-3). Closed and anchored at the word after `research`; a plural
# noun object (`Research releases of uv`) is never on it.
_SUBJECT_VERBS = _vocab(
    "uses needs runs covers takes shows found finds requires says suggests "
    "returns fails passes works depends gets lives belongs happens helps means "
    "matters seems starts stops goes stays remains involves"
)
# One adverb may sit between a subject `research` and its verb.
_ADVERBS = _vocab(
    "also still now just only already never always often usually then currently "
    "sometimes"
)
# A lowercase `-s` word then one of these reads as a verb: `Research writes the`.
# `that` and `those` are left out: `Research tools that generate SBOMs`.
_DETERMINERS = _vocab("the a an this these our your its their my it them")
# The one closed list left: this repository's own research-* components. No
# grammar tells `research gate tests fail` from `research uv releases`.
_COMPONENTS = _vocab(
    "gate gates scope fanout record records receipt receipts directive "
    "directives hint cache coverage notes"
)
_WH = _vocab("how what why when where who whether which if")
_OWNERS = _vocab("this the our")
_PLACES = _vocab("repo repository codebase worktree branch pr")
_FRESH = _vocab("latest newest current")
_WEB = _vocab("web internet online github")
_EXTERNAL = (
    _FRESH
    | _WEB
    | _vocab("upstream changelog release releases docs documentation version versions")
)
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


def _code_token(raw: str) -> bool:
    """A local path, file name, identifier or call; never a URL or a slug."""
    token = raw.strip(_EDGE).rstrip(_ENDS)
    if "://" in token:
        return False  # a URL names an upstream page
    stem, dot, ext = token.rpartition(".")
    owner, slash, repo = token.partition("/")
    library = ext == "js" and stem[:1].isupper()  # Node.js, Vue.js
    return (
        token.startswith(("./", "../", "~/", "/"))
        or token.count("/") > 1
        or bool(dot and stem and ext.casefold() in _EXTENSIONS and not library)
        or bool(slash and not (owner and repo))  # `src/`; owner/repo is upstream
        or (not slash and ("_" in token or "()" in raw))
        or (token[:1] == "." and token[1:2].islower())  # a dotfile such as .env
    )


def _local(raws: list[str], words: list[str], *, nouns: bool) -> bool:
    """A code token, `in this|the|our repo|branch|PR...` or (nouns) a local word."""
    for at, raw in enumerate(raws):
        place = (*words[at : at + 3], "", "")
        if (
            _code_token(raw)
            or (nouns and words[at] in _LOCAL)
            or (place[0] == "in" and place[1] in _OWNERS and place[2] in _PLACES)
        ):
            return True
    return False


def _named(raws: list[str]) -> bool:
    """An upstream object: a capitalised or versioned name, or an upstream word."""
    return any(
        raw.strip(_EDGE)[:1].isupper()
        or any(char.isdigit() for char in raw)
        or _norm(raw) in _EXTERNAL
        for raw in raws
    )


def _lead_end(words: list[str]) -> int:
    """Skip polite lead-ins such as `please`, `can you`, `I need you to`."""
    at = 0
    while at < len(words):
        rest = next(
            (
                rest
                for rest in _LEAD_PHRASES.get(words[at], ())
                if tuple(words[at + 1 : at + 1 + len(rest)]) == rest
            ),
            None,
        )
        if words[at] in _LEAD_WORDS:
            at += 1
        elif rest is not None:
            at += 1 + len(rest)
        else:
            break
    return at


def _do_research(v: list[str]) -> bool:
    """`do [some|more|a bit of] [deep] research [on|into|about|for ...]`."""
    rest = v[4:] if v[1:4] == ["a", "bit", "of"] else v[1:]
    rest = rest[1:] if rest[0] in {"some", "more"} else rest
    rest = rest[1:] if rest[0] == "deep" else rest
    return rest[0] == "research" and rest[1] in {"on", "into", "about", "for", ""}


def _research(v: list[str], raws: list[str]) -> bool:
    """`research X`, never a heading, a status, a subject or a named component."""
    if not v[2]:
        return False  # `Research done.`, `Research: N/A`, a `research:` key
    if raws[0].endswith(":"):  # `Research: X` reads X as free text
        return not (raws[1].endswith(",") or v[1] in _COMPONENTS)
    at = 2 if v[1] in _ADVERBS else 1  # `Research also uses ...`
    verb, after = v[at], v[at + 1]
    return not (
        raws[1].endswith(",")  # `Research done, now fix it.`
        or verb in _AUX
        or verb in _SUBJECT_VERBS
        or (
            raws[at][:1].islower()
            and verb.endswith("s")
            and not verb.endswith("ss")
            and (after in _DETERMINERS or not after)
        )
        or v[1].endswith(("n't", "ed"))
        or (v[2] in _AUX and v[1] not in _WH)  # `Research notes are ...`
        or v[1] in _COMPONENTS
    )


def _lookup(v: list[str], raws: list[str]) -> bool:
    """A look-up verb at the clause start whose object names something upstream."""
    if v[0] in {"find", "check"}:
        return v[1] == "the" and v[2] in _FRESH and _named(raws[3:])
    if v[:2] == ["look", "up"]:
        return (
            not _EXTERNAL.isdisjoint(v[2:])
            or v[2:5] in (["what's", "new", "in"], ["what", "is", "new"])
            or any("://" in raw for raw in raws)
        )
    if v[0] == "compare":
        name = 2 if v[1] == "the" else 1
        return v[name + 1] == "and" and _named(raws[1:])
    if v[:2] == ["what", "is"] or v[0] == "what's":
        asked = v[2:5] if v[0] == "what" else v[1:4]
        return asked[:2] == ["new", "in"] or (
            asked[0] == "the"
            and asked[1] in _FRESH
            and asked[2] in {"version", "release"}
        )
    return False


def _request(raws: list[str]) -> bool:
    """Whether one clause opens with an imperative research request."""
    words = [_norm(raw) for raw in raws]
    start = _lead_end(words)
    raws, words = raws[start:], words[start:]
    v = [*words, "", "", "", "", "", "", ""]
    if v[0] == "research":
        found = _research(v, raws)
    elif v[0] == "do":
        found = _do_research(v)
    elif v[0] == "search":
        at = 2 if v[1] == "the" else 1  # not `search the web module`
        found = v[at] in _WEB and v[at + 1] in {"for", "about", "on", "to", "and", ""}
    else:
        return _lookup(v, raws) and not _local(raws, words, nouns=True)
    return found and not _local(raws, words, nouns=False)


def _feed(body: str, pending: list[str]) -> bool:
    """Add one prose line to the open clause; True once a clause is a request."""
    words = _unquoted(body).split()
    if words and (words[0] in {"-", "*", "+", "//"} or words[0].rstrip(".)").isdigit()):
        del words[0]
    for raw in words:
        pending.append(raw)
        if raw.endswith(",") and _norm(pending[0]) in _SUBORDINATE:
            pending.clear()  # `Before we decide,` is not the request
            continue
        end = raw.rstrip(_EDGE)[-1:]
        if not end or end not in _ENDS:
            continue
        key = _norm(raw)
        if end == ":" and pending == [raw] and raw[:1] == "R" and key == "research":
            continue  # `Research:` or `RESEARCH:` labels the rest of the clause
        if _request(pending):
            return True
        first, label = pending[0], _norm(pending[0])
        pending.clear()
        if end == ":" and (
            key in _KEYS
            or label in _LABELS
            or first == "research:"  # a YAML-style key quotes its value
            or key.endswith(("error", "exception"))
            or _TICKET.fullmatch(key) is not None
        ):
            break
    return False


def _quoted_line(line: str, body: str) -> bool:
    """Pasted or structural: quotes, data, code, logs, headings, task items."""
    return (
        not body
        or body[0] in ">{[#"
        or body.endswith(":")
        or _COMMIT.match(body) is not None
        or (body[0] in "-*+" and body[1:].lstrip()[:3] in {"[ ]", "[x]", "[X]"})
        or line.startswith(("\t", "    "))
        or _LOG_LINE.match(body) is not None
    )


def intent(prompt: str) -> bool:
    """Whether the caller's own prose asks the assistant to research something."""
    head = prompt[:_SCAN_LIMIT]
    if len(prompt) > _SCAN_LIMIT:
        # Drop the partial last line, or the partial last word of one line.
        head = head.rpartition("\n")[0] or head.rpartition(" ")[0]
    pending: list[str] = []
    fence = ""
    for line in head.split("\n"):
        body = line.strip()
        if fence:
            # CommonMark: the same character, at least as long, nothing after.
            if len(body) >= len(fence) and not body.strip(fence[0]):
                fence = ""
            continue
        if body.casefold() in _MARKERS or (len(body) >= _RULE and not body.strip("-")):
            break
        if body.startswith(("```", "~~~")):
            fence = body[: len(body) - len(body.lstrip(body[0]))]
        skip = bool(fence) or _quoted_line(line, body)
        # A lowercase line continues a wrapped clause; anything else starts one.
        if skip or not body[0].islower():
            if _request(pending):
                return True
            pending.clear()
        if not skip and _feed(body, pending):
            return True
    return _request(pending)
