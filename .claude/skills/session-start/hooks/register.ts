import type { EngineInterface, Register } from "claude-code";

/**
 * The all-session `session-start` mod (spec
 * `docs/specs/coordinator-auto-handoff-2026-10-02.md` §8; requirements 23).
 *
 * On `session.start` in an interactive session (bg included; `-p` and the SDK
 * skip), asks python once per session id (`dotfiles-setup session-start
 * decide`), queues `/reload-skills` then `/reload-plugins --force` — bg spares
 * can predate the claim, so their skill and plugin state may be stale — and
 * applies the naming convention `<project>-<Chicago ISO ns>.<feature>`:
 * Helpers are deliberately local: each skills-dir plugin loads independently.
 *
 * - `keep`: the `-n` name already conforms;
 * - `rename`: `/rename <name>` with the branch slug as the feature;
 * - `defer`: on the default branch, rename at the FIRST prompt with a short
 *   model-made slug appended to python's prefix (fallback `session`);
 * - `nonconforming`: a `-n` name outside the convention is NEVER renamed —
 *   lanes are addressed by it — only a toast and a status.
 *
 * Python writes its state BEFORE answering, so the session.start a reload may
 * re-fire answers `already-ran` (carrying a still-pending defer prefix, since a
 * reload discards this module's memory). Function-hook failures are skipped
 * silently, so the status line is the heartbeat: `session-start ok…` or
 * `session-start ERROR: <reason>`. Every failure is a value, never a throw.
 */

const DECIDE_TIMEOUT_MS = 60_000;
const SLUG_MODEL = "haiku";
const SLUG_FALLBACK = "session";
const SLUG_MAX_WORDS = 5;
const SLUG_MAX_CHARS = 60;
const PROMPT_MAX_CHARS = 2_000;
const REASON_MAX_CHARS = 80;

/** Mirrors `StartDecision.to_json()` in `python/src/dotfiles_setup/session_start.py`. */
const ACTIONS = [
  "keep", "rename", "defer", "nonconforming", "unknown", "already-ran",
  "non-interactive", "invalid-session-id", "state-write-failed", "state-locked",
] as const; // Mirrors Python StartAction (Literal).
type StartAction = (typeof ACTIONS)[number];
type StartDecision = {
  action: StartAction;
  reload: boolean;
  name: string | null;
  prefix: string | null;
};

/** A deferred rename waiting for the first prompt of this module's lifetime. */
type PendingName = { sessionId: string; prefix: string | null; name: string | null };
const pending = new Map<string, PendingName>();
const pendingChecked = new Set<string>();
const renaming = new Set<string>();

const toasted = new Set<string>();

function toastOnce($: EngineInterface, text: string): void {
  if (toasted.has(text)) return;
  toasted.add(text);
  $.ui.toast(text);
}

function fail($: EngineInterface, reason: string): void {
  const short = reason.length > REASON_MAX_CHARS ? `${reason.slice(0, REASON_MAX_CHARS)}…` : reason;
  try {
    $.ui.status(`session-start ERROR: ${short}`);
    toastOnce($, `session-start: ${short}`);
  } catch {
    // Nothing left to report through.
  }
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Queue a slash command; never awaited, its rejection made visible. */
function queue($: EngineInterface, command: string, args?: string): void {
  void $.command
    .run(args === undefined ? { command } : { command, args })
    .catch((error: unknown) => fail($, `/${command} rejected: ${errorText(error)}`));
}

function parseStart(stdout: string): StartDecision | null {
  let value: unknown;
  try {
    value = JSON.parse(stdout);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const { action, reload, name, prefix } = value as Record<string, unknown>;
  if (typeof action !== "string" || typeof reload !== "boolean") return null;
  if (!ACTIONS.some((candidate) => candidate === action)) return null;
  if (name !== null && typeof name !== "string") return null;
  if (prefix !== null && typeof prefix !== "string") return null;
  return { action: action as StartAction, reload, name, prefix };
}

async function python(
  $: EngineInterface,
  args: readonly string[],
): Promise<{ exitCode: number; stdout: string }> {
  const projectDir = (await $.env.get("CLAUDE_PROJECT_DIR")) ?? (await $.session.root());
  return $.process.run(
    ["uv", "run", "--project", "python", "dotfiles-setup", "session-start", ...args],
    { cwd: projectDir, timeoutMs: DECIDE_TIMEOUT_MS },
  );
}

async function decide(
  $: EngineInterface,
  sessionId: string,
  cwd: string,
): Promise<StartDecision | string> {
  let run: { exitCode: number; stdout: string };
  try {
    run = await python($, ["decide", "--session-id", sessionId, "--cwd", cwd]);
  } catch {
    return "decide failed to run";
  }
  if (run.exitCode !== 0) return `decide rc ${run.exitCode}`;
  return parseStart(run.stdout) ?? "decide output not JSON";
}

/** At most five lowercase kebab words; empty when nothing usable came back. */
function toSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter((word) => word !== "")
    .slice(0, SLUG_MAX_WORDS)
    .join("-")
    .slice(0, SLUG_MAX_CHARS)
    .replace(/-+$/, "");
}

/** Compatibility boundary: vendored 2.1.277 says string; 2.1.288 returns an object.
 * Coordinator must regenerate vendor types separately; do not patch declarations.
 */
function completionText(reply: string | { isAnswered: boolean; text: string }): string | undefined {
  return typeof reply === "string" ? reply : (reply.isAnswered ? reply.text : undefined);
}

async function confirmRename($: EngineInterface, sessionId: string, name: string): Promise<void> {
  // Only called from an unawaited task: the command runs once the session is idle.
  await $.command.run({ command: "rename", args: name });
  const marked = await python($, ["renamed", "--session-id", sessionId, "--name", name]);
  if (marked.exitCode !== 0) throw new Error(`renamed rc ${marked.exitCode}`);
  pending.delete(sessionId);
  $.ui.status("session-start ok (renamed)");
}

async function renameFromPrompt(
  $: EngineInterface,
  claim: PendingName,
  text: string,
): Promise<void> {
  let slug = SLUG_FALLBACK;
  try {
    const reply = await $.model.complete({
      model: SLUG_MODEL,
      prompt:
        "Name the task below in at most five lowercase words. Reply with the words only.\n\n" +
        text.slice(0, PROMPT_MAX_CHARS),
      maxTokens: 30,
    });
    slug = toSlug(completionText(reply) ?? "") || SLUG_FALLBACK;
  } catch {
    slug = SLUG_FALLBACK;
  }
  await confirmRename($, claim.sessionId, claim.name ?? `${claim.prefix}.${slug}`);
}

function scheduleRename($: EngineInterface, claim: PendingName, text?: string): void {
  if (renaming.has(claim.sessionId)) return;
  renaming.add(claim.sessionId);
  pending.set(claim.sessionId, claim);
  const work = claim.name === null
    ? renameFromPrompt($, claim, text ?? "")
    : confirmRename($, claim.sessionId, claim.name);
  void work.catch((error: unknown) => {
    // Keep the claim and Python prefix: a rejected rename is still pending.
    fail($, `rename failed: ${errorText(error)}`);
  }).finally(() => renaming.delete(claim.sessionId));
}

async function recoverPending($: EngineInterface, sessionId: string): Promise<void> {
  if (pendingChecked.has(sessionId)) return;
  pendingChecked.add(sessionId);
  const run = await python($, ["pending", "--session-id", sessionId]);
  if (run.exitCode !== 0) throw new Error(`pending rc ${run.exitCode}`);
  const decision = parseStart(run.stdout);
  if (decision === null) throw new Error("pending output not JSON");
  if (decision.action === "rename" && decision.name !== null) {
    pending.set(sessionId, { sessionId, name: decision.name, prefix: null });
  } else if (decision.prefix !== null) {
    pending.set(sessionId, { sessionId, prefix: decision.prefix, name: null });
  } else if (["invalid-session-id", "state-write-failed", "state-locked"].includes(decision.action)) {
    throw new Error(decision.action);
  }
}

async function start($: EngineInterface, cwd: string): Promise<void> {
  const sessionId = await $.session.id();
  const decision = await decide($, sessionId, cwd);
  if (typeof decision === "string") {
    fail($, decision);
    return;
  }
  // A repeat with no prefix can still have an unconfirmed branch rename.
  if (decision.action !== "already-ran" || decision.prefix !== null) pendingChecked.add(sessionId);
  applyStart($, sessionId, decision);
  if (decision.reload) {
    queue($, "reload-skills");
    queue($, "reload-plugins", "--force");
  }
}

function applyStart($: EngineInterface, sessionId: string, decision: StartDecision): void {
  switch (decision.action) {
    case "keep":
      $.ui.status("session-start ok");
      return;
    case "rename":
      if (decision.name === null) {
        fail($, "rename without a name");
        return;
      }
      $.ui.status("session-start pending rename");
      scheduleRename($, { sessionId, name: decision.name, prefix: null });
      return;
    case "defer":
    case "already-ran":
      if (decision.prefix !== null) {
        pending.set(sessionId, { sessionId, prefix: decision.prefix, name: null });
        $.ui.status("session-start ok (name at first prompt)");
      } else if (decision.action === "defer") {
        fail($, "defer without a prefix");
      } else {
        $.ui.status("session-start ok");
      }
      return;
    case "nonconforming":
      $.ui.status("session-start: name not in convention");
      toastOnce(
        $,
        `session-start: "${decision.name ?? "?"}" is outside <project>-<yyyyMMdd'T'HHmmss.ns±HH>.<feature>; left as is`,
      );
      return;
    case "unknown":
      $.ui.status("session-start: name unknown");
      return;
    default:
      fail($, decision.action);
  }
}

export const register: Register = (on) => {
  on("session.start", async ($, e, next) => {
    const result = await next(e);
    try {
      if (!e.isInteractive) return result;
      await start($, e.cwd);
    } catch (error: unknown) {
      fail($, `hook failed: ${errorText(error)}`);
    }
    return result;
  });

  on("prompt.submit", async ($, e, next) => {
    const result = await next(e);
    try {
      const sessionId = await $.session.id();
      await recoverPending($, sessionId);
      const claim = pending.get(sessionId);
      if (claim !== undefined) scheduleRename($, claim, e.text);
    } catch (error: unknown) {
      fail($, `pending rename failed: ${errorText(error)}`);
    }
    return result;
  });
};
