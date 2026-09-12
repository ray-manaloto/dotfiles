# Function Hooks for Retrieval: Advisory on Mechanism Choice

**Decision:** Retrieval dedup does NOT require function hooks. Classic `SessionStart` hooks + `doctor.toml` are the right mechanism.

**Status:** DELIVERED 2026-09-11  
**Coordinator:** Raymond Manaloto  
**Evidence base:** GitHub issue #1020 (49 KB, full evidence convention applied)

---

## The Question

A bug has been filed three times (#877 twice, #998 as duplicate) with each re-diagnosis from scratch. The retrieval gap is real: 117 `feedback_*` auto-memory files and two GitHub issues for ONE defect, none of it reaching the moment of need.

Ray asks: Does solving this via function hooks make sense, or is it overengineering? And if function hooks are wrong here, what does that tell us about their broader role?

---

## 1. Does Retrieval Actually Need Function Hooks?

**Answer: NO.** The mechanism should be classic `SessionStart` hook + `doctor.toml`.

### Why classic hooks suffice

The retrieval need is:
- Discover existing issues/memories for a defect class (query GitHub + walk KB)
- Retrieve them at SessionStart (timing)
- Display them to user (output)

The existing `doctor.toml` mechanism already:
- Runs at SessionStart via the declared `SessionStart` hook (`.claude/settings.json`)
- Loads Python code (can query GitHub API, search `feedback_*`, parse TOML)
- Returns a report (silent when healthy; when there's a match, surfaces it)
- Is a **native feature**, not a third-party layer

### Why function hooks would be wrong here

1. **External-source plugin installation problem** (§2 of #1020, line 310-315, DOCUMENTED):
   > *"A plugin that only the project's `.claude/settings.json` enables, and that comes from an external source such as a GitHub repository or npm package, doesn't load until the team member installs it."*
   
   Dotfiles' entire value is "clone it and you are set up." Requiring users to run `claude plugin install` breaks that contract.

2. **Timing gate blocks it anyway** (§ "Timing" of #1020, line 129-143, DECLARED):
   > "The gate is knowledge-base ticket G04 (`ray-manaloto/knowledge-base#757`), which must observe a function-hook mod actually firing before any repo acts on this."
   
   **Dotfiles does nothing this round.** Proposing function hooks for retrieval would require the gate to pass first.

3. **Runtime-unverified** (§4, line 536-540, MEASURED against binary):
   > "Names are observed; FIRING is not... It does not establish that registering one binds a handler, that the handler runs, or that its result is enforced — which is exactly what G04 is for."
   
   No lane has executed a probe showing `session.start` or `classic.SessionStart` function-hook handlers fire. Using an unproven mechanism for a real defect would be backwards.

4. **Rewrite cost with no capability gain**:
   - Function hooks force TypeScript/JavaScript instead of Python
   - Doctor.py already does retrieval + memory + health checks
   - Porting that to JS is work for zero new capability

### The Built-In Principle

`.claude/rules/use-tool-builtins.md` (HARD GATE) states: prefer the existing tool before writing custom logic. Classic hooks ARE the existing tool. Function hooks would be the "custom logic" option.

**Verdict:** Classic hook + doctor.toml is the **right mechanism, today.**

---

## 2. Timing Gate Conflict: Does This Violate KB#757?

**Answer: YES and NO.**

**YES:** Using function hooks for retrieval would violate the gate, because the gate says dotfiles acts only after KB observes firing. But that's circular — retrieving OUR defects shouldn't require KB to prove a capability we didn't even need.

**NO (deeper):** There's no reason to use function hooks for retrieval, so the gate conflict is moot. We'd only hit the conflict if we made the wrong choice. Making the right choice (classic hook) sidesteps it entirely.

---

## 3. What Can Function Hooks Uniquely Do Here?

**Answer: Nothing that justifies adoption.**

Theoretically, function hooks can register on `session.start` (§1, line 2189-2196 in 2.1.267 declarations, DECLARED). But:

1. **Firing is unverified** (§4, line 536-540, MEASURED):
   - The declarations admit `session.start`, but no executed probe in any lane observed it fire
   - The binary analysis at line 463-489 proves the ENGINE KNOWS 33 event names and builds `classic.*` keys from them
   - **That means nothing about firing.** A declared event and a firing handler are not the same thing.

2. **Coexistence with classic hooks is unverified** (§4, line 542-607):
   The declarations describe coexistence for `prompt.submit` (line 552-556) and for `classic.*` chain (line 554-556). **But for native `tool.call` alongside ordinary `PreToolUse` settings hooks, coexistence is UNVERIFIED** (line 569-573).
   
   For `session.start` specifically: no explicit coexistence statement exists in the declarations. Testing this BEFORE adopting it is mandatory.

3. **The "more powerful" framing is marketing, not evidence** (§5, line 672-685):
   > "the declarations expose host capabilities: `$.process.run(argv, init)`, `fs.read`, `env.get`..."
   
   But line 678-685: "Whether that adapter is viable is RUNTIME-UNVERIFIED — loading, budget compatibility, input/output translation, failure semantics and end-to-end latency are all unmeasured."

Function hooks offer a **different shape** (TypeScript, in-process capabilities). They don't offer a **better answer** to retrieval. The built-in is better.

---

## 4. Runtime-Unverified Problem: Cheapest Honest Probe

**The Problem:** #1020 states plainly (§4, line 876-879):
> "No probe of firing, dispatch or enforcement was executed by any lane... so every such claim is UNVERIFIED by construction."

What can move a claim from UNVERIFIED to MEASURED?

### Cheapest two-arm probe

**Setup:** Register a function hook on `classic.SessionStart`.

**Arm 1 (Positive):** Handler logs a marker to a file. Start a Claude Code session. Check: does the marker appear?

**Arm 2 (Negative, load-bearing):** Handler denies the SessionStart event with a `{deny: "test"}` result. Start Claude Code. Check: does the session fail to start?

Only the negative arm discriminates. A handler that fires and does nothing is indistinguishable from one that doesn't fire. The denial proves the handler is called AND its result is enforced.

**Cost:** ~5 min setup + 2 session launches + 2 file checks.

**Control:** A fabricated event name (`SessionBegins`, `SessionLoad`) should show 0 markers and allow session start normally.

This is **exactly what KB#757 (G04) should measure.** Until someone runs this experiment and ships the result, function hooks remain RUNTIME-UNVERIFIED.

### Implication for dotfiles

**Do not adopt function hooks for any guard until KB#757 ships a MEASURED firing/denial result.** A DECLARED shape and a FIRING handler are different classes of evidence.

---

## 5. Sequencing: Where Does Hooks Work Sit?

From #1020 § "What this issue asks for" (line 829-851):

1. **Acknowledge the timing gate:** dotfiles acts only after KB G04 (KB#757) observes function-hook mod actually firing. ✓ (Acknowledged here)

2. **Adopt the reachability rule before any guard census** (§7, line 794-819):
   - Enumerate by REACHABILITY, not filename
   - Publish the list of entry points → imports → call graph
   - Classify each dependency as rewrite/retain/out-of-scope
   - Only THEN estimate cost

3. **Treat the pin as prerequisite, not follow-up** (§6, line 689-747):
   - `kb-setup` is pinned 122 commits stale
   - `kb_setup.graph` is imported in `graphify.py:23`, which is reached from TWO PreToolUse registrations
   - **The stale pin is ALREADY on a hook-reachable path** — not hypothetical
   - **Must update the pin before adopting any shared guard code**

4. **Accept Bash restriction** (§1, line 250-274):
   - anthropics/claude-code#92533: registering a hook reaching Bash breaks every Bash call inside `Agent(isolation: "worktree")` subagent
   - No `tool.call` registration with Bash matcher until verified fixed on deployed version
   - Dotfiles' first two PreToolUse registrations both include Bash (`.claude/settings.json:51-79`)

### Timeline

| Step | Status | When |
|---|---|---|
| Producer PR merge | ✅ Done (`f7eb9fd`) | Already landed |
| #877 fix / #998 close | ➡️ Next | This round |
| Retrieval (doctor.toml SessionStart) | ➡️ Parallel | Can ship with #877 fix (no dep) |
| KB#757 (G04) fires | ⏳ Gate | Blocks any dotfiles function-hooks adoption |
| Reachability audit (Part 7) | ⏳ Prerequisite to migration | AFTER KB#757 + IF adopting |
| Pin update | ⏳ Prerequisite to shared-guard code | AFTER KB#757 + IF adopting shared guards |
| Guard census (if any) | ⏳ Last | AFTER all prerequisites |

**Critical observation:** The retrieval mechanism (doctor.toml) does **not** depend on any of the function-hooks machinery. It ships independently. Use it.

---

## Summary: The Bounded Advisory

| Question | Answer | Evidence |
|---|---|---|
| **1. Retrieval needs function hooks?** | NO. Classic SessionStart hook + doctor.toml suffices. Proposing function hooks violates use-tool-builtins.md. | #1020 §2 (installation requirement violates clone-ready model); §4 (firing unverified); §5 (rewrite cost, zero new capability) |
| **2. Function hooks violate KB#757?** | YES, if used. But unnecessary — moot if correct mechanism is chosen. | #1020 § "Timing" (gate: dotfiles acts after KB observes) |
| **3. Unique capability?** | NO. TypeScript is different shape, not better answer. Coexistence unverified; firing unverified. | #1020 §1 (Bash restriction); §4 (firing/coexistence unverified); §5 (latency unmeasured) |
| **4. Cheapest probe?** | Register SessionStart handler; positive arm (does it fire?); negative arm (does denial block session?). ~5 min, two-arm control. | #1020 §4, line 876-879 (no probes executed yet); standard control-arm methodology |
| **5. Sequencing?** | (1) Producer ✅; (2) #877 ➡️ next; (3) retrieval ➡️ parallel; (4) KB#757 ⏳ gate; (5–7) audit/pin/census after gate. | #1020 § "What this issue asks for" + "Open questions" |

---

## Recommendation to Ray

**Ship the retrieval fix using the classic hook now.** Do not wait for function hooks.

1. Add a `doctor.toml` check that queries open issues with labels `bug` + `ready-for-agent`
2. If any exist, surface them at SessionStart
3. Ship this with the #877 fix, or immediately after

**Function hooks remain on the shelf.** The gate (KB#757) and the unverified evidence mean they are blocked anyway. When KB observes firing and publishes a MEASURED result, revisit. Until then, the built-in is the right call.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject repo; `.claude/settings.json`, `doctor.toml`, `python/src/dotfiles_setup/doctor.py`
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — sibling repo; KB#757 gate, G04 ticket, function-hooks reference mod
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — platform; declarations (2.1.267), event names, #92533 (Bash worktree bug)
