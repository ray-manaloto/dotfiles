import type { EngineInterface, Register } from "claude-code";

/**
 * Auto-submits `/coordinator-handoff` when a dotfiles coordinator's context
 * reaches the configured limit (spec:
 * `docs/specs/coordinator-auto-handoff-2026-10-02.md` §3d).
 *
 * The module owns only a cheap pre-filter and the visible heartbeat; python
 * (`dotfiles-setup coordinator-handoff decide`) owns every judgement: the role
 * check against the bg job record, the fired-level state, the re-fire step.
 *
 * Function-hook failures are skipped SILENTLY by the engine, so a broken
 * trigger would look exactly like "below the limit" until "Prompt is too
 * long". Every measurement therefore overwrites this plugin's status line —
 * `handoff 23%/30%`, `handoff fired @30%`, `handoff next @35%`,
 * `handoff n/a (not coordinator)`, `handoff DRY-RUN @30%`, or
 * `handoff ERROR: <reason>` — and an absent or stale entry itself means the
 * hook did not run. Every failure is a value, never a throw.
 */

const SKILL = "coordinator-handoff";
const DEFAULT_LIMIT_PCT = 30;
const MAX_PCT = 100;
/** `uv run` can be cold; the engine's own default (30 s) is too tight. */
const DECIDE_TIMEOUT_MS = 60_000;
const REASON_MAX_CHARS = 80;

/** Mirrors `Decision.to_json()` in `python/src/dotfiles_setup/coordinator_handoff.py`. */
type Decision = {
  fire: boolean;
  reason: string;
  level: number | null;
  percent: number;
  warnings: string[];
};

/** One toast per distinct reason: a repeating failure must not flood the bar. */
const toasted = new Set<string>();

function toastOnce($: EngineInterface, text: string): void {
  if (toasted.has(text)) return;
  toasted.add(text);
  $.ui.toast(text);
}

function fail($: EngineInterface, reason: string): void {
  const short = reason.length > REASON_MAX_CHARS ? `${reason.slice(0, REASON_MAX_CHARS)}…` : reason;
  try {
    $.ui.status(`handoff ERROR: ${short}`);
    toastOnce($, `coordinator-handoff: ${short}`);
  } catch {
    // Nothing left to report through; the engine skips a throw silently anyway.
  }
}

/** Same acceptance as python's `_parse_pct`: a number in (0, 100], else 30. */
function parseLimit(raw: string | undefined): number {
  if (raw === undefined || raw.trim() === "") return DEFAULT_LIMIT_PCT;
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 && value <= MAX_PCT ? value : DEFAULT_LIMIT_PCT;
}

/** Validate untrusted subprocess JSON before anything acts on it. */
function parseDecision(stdout: string): Decision | null {
  let value: unknown;
  try {
    value = JSON.parse(stdout);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const { fire, reason, level, percent, warnings } = record;
  if (typeof fire !== "boolean" || typeof reason !== "string" || typeof percent !== "number") {
    return null;
  }
  if (level !== null && typeof level !== "number") return null;
  if (!Array.isArray(warnings) || !warnings.every((w) => typeof w === "string")) return null;
  return { fire, reason, level, percent, warnings: warnings as string[] };
}

/** The env the decision depends on, handed down explicitly (literal names only). */
async function decisionEnv($: EngineInterface): Promise<Record<string, string>> {
  const env: Record<string, string> = {};
  const limit = await $.env.get("DOTFILES_COORDINATOR_HANDOFF_PCT");
  const step = await $.env.get("DOTFILES_COORDINATOR_HANDOFF_STEP_PCT");
  if (limit !== undefined) env.DOTFILES_COORDINATOR_HANDOFF_PCT = limit;
  if (step !== undefined) env.DOTFILES_COORDINATOR_HANDOFF_STEP_PCT = step;
  return env;
}

/** Ask python; a string answer is the reason it could not be asked. */
async function decide(
  $: EngineInterface,
  sessionId: string,
  percent: number,
): Promise<Decision | string> {
  let run: { exitCode: number; stdout: string; stderr: string };
  try {
    const projectDir = (await $.env.get("CLAUDE_PROJECT_DIR")) ?? (await $.session.root());
    run = await $.process.run(
      [
        "uv",
        "run",
        "--project",
        "python",
        "dotfiles-setup",
        "coordinator-handoff",
        "decide",
        "--session-id",
        sessionId,
        "--percent",
        String(percent),
      ],
      { cwd: projectDir, env: await decisionEnv($), timeoutMs: DECIDE_TIMEOUT_MS },
    );
  } catch {
    return "decide failed to run";
  }
  if (run.exitCode !== 0) return `decide rc ${run.exitCode}`;
  return parseDecision(run.stdout) ?? "decide output not JSON";
}

/**
 * The skill's command name as the engine lists it — resolved, never assumed
 * (spec P2): a skills-dir plugin may list it bare or plugin-qualified.
 */
async function resolveCommand($: EngineInterface): Promise<string | undefined> {
  const commands = await $.command.list();
  return (
    commands.find((c) => c.name === SKILL)?.name ??
    commands.find((c) => c.name.endsWith(`:${SKILL}`))?.name
  );
}

function belowStatus($: EngineInterface, decision: Decision, percent: number): void {
  if (decision.reason === "not-coordinator") {
    $.ui.status("handoff n/a (not coordinator)");
  } else if (decision.reason === "below-next-step") {
    $.ui.status(`handoff next @${decision.level ?? "?"}%`);
  } else if (decision.reason === "below-limit") {
    $.ui.status(`handoff ${percent}%/${decision.level ?? "?"}%`);
  } else {
    fail($, decision.reason);
  }
}

async function measure($: EngineInterface, percent: number): Promise<void> {
  const limit = parseLimit(await $.env.get("DOTFILES_COORDINATOR_HANDOFF_PCT"));
  if (percent < limit) {
    // Below the limit: no process, just the heartbeat.
    $.ui.status(`handoff ${percent}%/${limit}%`);
    return;
  }
  const sessionId = await $.session.id();
  const decision = await decide($, sessionId, percent);
  if (typeof decision === "string") {
    fail($, decision);
    return;
  }
  for (const warning of decision.warnings) toastOnce($, `coordinator-handoff: ${warning}`);
  if (!decision.fire) {
    belowStatus($, decision, percent);
    return;
  }
  const level = decision.level ?? percent;
  const probe = (await $.env.get("DOTFILES_COORDINATOR_HANDOFF_PROBE")) === "1";
  const args = probe ? "--probe" : `${sessionId} ${percent}`;
  if ((await $.env.get("DOTFILES_COORDINATOR_HANDOFF_DRY_RUN")) === "1") {
    const line = `coordinator-handoff DRY-RUN: would run /${SKILL} ${args} (context ${percent}%, level ${level}%)`;
    $.ui.status(`handoff DRY-RUN @${level}%`);
    $.ui.toast(line);
    $.ui.log(line);
    return;
  }
  const command = await resolveCommand($);
  if (command === undefined) {
    fail($, "skill not listed");
    return;
  }
  const line = `coordinator-handoff: context ${percent}% reached ${level}% — running /${command} ${args}`;
  $.ui.status(`handoff fired @${level}%`);
  $.ui.toast(line);
  $.ui.log(line);
  // Never awaited: `command.run` rejects inside a hook the turn waits on, and
  // it runs once the session is idle anyway. The rejection must be visible.
  void $.command.run({ command, args }).catch((error: unknown) => {
    fail($, `command.run rejected: ${error instanceof Error ? error.message : String(error)}`);
  });
}

export const register: Register = (on) => {
  on("session.measure", async ($, e, next) => {
    const result = await next(e);
    const percent = e.context.percent;
    if (!e.changed.includes("context") || typeof percent !== "number" || !Number.isFinite(percent)) {
      return result;
    }
    try {
      await measure($, percent);
    } catch (error: unknown) {
      fail($, `hook failed: ${error instanceof Error ? error.message : String(error)}`);
    }
    return result;
  });
};
