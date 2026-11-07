"""Turn a plan.json into one self-contained HTML page: inline CSS, no JavaScript, no URLs."""

# Every piece of plan text goes through html.escape and lands only as element text or a quoted attribute value;
# no element or attribute name, URL or markup comes from the plan. The one class from plan data is a Result value.

from html import escape
from pathlib import Path

from .models import Claim, Decision, Option, Plan, PlanTest, Result

CSS = """
body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#111;background:#fff}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:2rem;border-bottom:1px solid #ccc}
.status{border:1px solid #ccc;border-radius:6px;padding:.5rem 1rem;background:#f6f6f6}
.state{font-weight:600}.where{font:13px ui-monospace,monospace;color:#555}
.rec{color:#146c2e;font-weight:600}.fail{color:#b3261e;font-weight:600}.pass{color:#146c2e}.not_run{color:#555}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.3rem .5rem;text-align:left}
"""
STATE = {"waiting_on_you": "Waiting on you", "working": "Working", "done": "Done"}
GENERATOR = '<meta name="generator" content="visualplan">'  # marks a page this renderer wrote
ORDER = {Result.fail: 0, Result.not_run: 1, Result.pass_: 2}  # failing tests first


def claim_item(claim: Claim) -> str:
    where = f' <span class="where">{escape(claim.where)}</span>' if claim.where else ""
    inner = f"<ul>{''.join(claim_item(c) for c in claim.children)}</ul>" if claim.children else ""
    return f"<li><code>{escape(claim.id)}</code> {escape(claim.text)}{where}{inner}</li>"


def option_item(option: Option, mark: str = "") -> str:
    return f"<li>{mark}<strong>{escape(option.label)}</strong>: {escape(option.why)}</li>"


def decision_block(decision: Decision) -> str:
    about = f' <span class="where">(claim {escape(decision.claim)})</span>' if decision.claim else ""
    recommended = option_item(decision.recommended, '<span class="rec">Recommended:</span> ')
    options = recommended + "".join(option_item(o) for o in decision.alternatives)
    return f"<h3><code>{escape(decision.id)}</code> {escape(decision.question)}{about}</h3><ul>{options}</ul>"


def test_row(test: PlanTest) -> str:
    return (
        f"<tr><td>{escape(test.name)}</td><td>{escape(test.kind)}</td>"
        f'<td class="{test.status.value}">{test.status.value.replace("_", " ")}</td></tr>'
    )


def render(plan: Plan) -> str:
    s = plan.status
    nexts = "".join(f"<li>{escape(n)}</li>" for n in s.next)
    tests = "".join(test_row(t) for t in sorted(plan.tests, key=lambda t: ORDER[t.status]))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
{GENERATOR}
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(plan.title)}</title>
<style>{CSS}</style>
</head>
<body>
<h1>{escape(plan.title)}</h1>
<div class="status"><p><span class="state">{STATE[s.state.value]}</span> · revision {s.revision} · updated \
{escape(s.updated)}</p>{f"<p>Next:</p><ul>{nexts}</ul>" if nexts else ""}</div>
<h2>Claims</h2>
<ul>{"".join(claim_item(c) for c in plan.claims)}</ul>
<h2>Decisions</h2>
{"".join(decision_block(d) for d in plan.decisions)}
<h2>Tests</h2>
<table><tr><th>Test</th><th>Kind</th><th>Status</th></tr>{tests}</table>
</body>
</html>
"""


def load(path: Path) -> Plan:
    return Plan.model_validate_json(path.read_bytes())
