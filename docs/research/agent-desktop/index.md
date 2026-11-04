---
okf_version: "0.2"
---

# agent-desktop 1.1.0 and a background CLion (macOS, 2026-11-03)

How vercel-labs/agent-desktop works on macOS, and how far it, together with CLion's own MCP server, lets an agent check
files for errors while CLion stays behind other apps. Source pages read agent-desktop at main `6660fba` (v1.1.0 plus 5
commits). The live results come from two independent sessions (Claude and Codex), which agreed on one procedure.

* [Live results](results.md) - the cause (`isInActiveProject` with two or more projects open), the T1–T4 runs, stale answers after outside edits, the agreed procedure, and what agent-desktop did live. Start here.
* [How it works](how-it-works.md) - the observe, ref, act, verify loop; headless vs headed; keys, focus and permissions.
* [Ref actions and delivery](actions-and-delivery.md) - action chains, what is read back, and what `delivered_verified` does and doesn't prove.
* [Physical input and focus](physical-input-and-focus.md) - `press` routes, `focus-window`, and why there is no focus restore.
* [Tree, refs and surfaces](tree-refs-and-surfaces.md) - remote AX tokens, surfaces such as the menubar, and what needs the app frontmost.
* [Documented behaviour and limits](documented-behaviour-and-limits.md) - the docs set against the code, including the conflicts.
* [Install, permissions and setup](install-permissions-and-setup.md) - the mise install, the helper, TCC grants, env vars and state.
* [JetBrains side](jetbrains-side.md) - the JBR accessibility bridge and the open-source `get_file_problems` path. Its "no focus gate" conclusion is superseded by results.
* [Avenues for a background CLion](clion-avenues.md) - the ranked avenues before the trials. Superseded by results.
* [Update log](log.md) - what was added, rejected and failed, by date.
* [Critique](critique.md) - an adversarial check of the source reading: claims confirmed, gaps listed.
