import assert from "node:assert/strict";

import { register } from "../../../.claude/skills/coordinator-handoff/hooks/register.ts";

/**
 * Drives the PRODUCTION `register` of the coordinator-handoff mod with a
 * scripted `$`, one arm per block, and prints `{"arms": N}` for
 * `tests/test_coordinator_handoff_hook.py` to pin.
 *
 * The module keeps one process-wide "toasted" set (one toast per distinct
 * reason), so arms that count toasts use reasons no earlier arm produced.
 */

type Handler = (
  services: unknown,
  event: Record<string, unknown>,
  next: (event: Record<string, unknown>) => Promise<unknown>,
) => Promise<unknown>;

const handlers = new Map<string, Handler>();
register(((event: string, handler: Handler) => handlers.set(event, handler)) as never, {} as never);
const measure = handlers.get("session.measure");
assert(measure, "session.measure handler was not registered");
assert.equal(handlers.size, 1, "only session.measure is hooked");

const SESSION = "abcdef12-0000-4000-8000-000000000001";
let sessionSequence = 0;

type ProcessResponse = { exitCode: number; stdout: string; stderr: string } | "throw";

type Options = {
  env?: Record<string, string>;
  responses?: ProcessResponse[];
  commands?: string[];
  runRejects?: boolean;
  projectDir?: string | null;
  sessionId?: string;
  listThrows?: boolean;
};

function makeServices(options: Options = {}) {
  const sessionId = options.sessionId ?? `${SESSION}-${++sessionSequence}`;
  const env: Record<string, string> = { ...(options.env ?? {}) };
  if (options.projectDir !== null) env.CLAUDE_PROJECT_DIR = options.projectDir ?? "/repo";
  const responses = [...(options.responses ?? [])];
  const commands = options.commands ?? ["compact", "coordinator-handoff"];
  const calls = {
    process: [] as { argv: readonly string[]; init: Record<string, unknown> | undefined }[],
    statuses: [] as (string | undefined)[],
    toasts: [] as string[],
    logs: [] as string[],
    lists: 0,
    runs: [] as { command: string; args?: string }[],
    roots: 0,
    sessionId,
  };
  const services = {
    env: {
      get: async (name: string) => (name in env ? env[name] : undefined),
    },
    session: {
      id: async () => sessionId,
      root: async () => {
        calls.roots += 1;
        return "/session-root";
      },
    },
    process: {
      run: async (argv: readonly string[], init?: Record<string, unknown>) => {
        calls.process.push({ argv, init });
        const response = responses.shift();
        if (response === undefined || response === "throw") {
          throw new Error("scripted process failure");
        }
        return response;
      },
    },
    ui: {
      status: (text: string | undefined) => {
        calls.statuses.push(text);
      },
      toast: (text: string) => {
        calls.toasts.push(text);
      },
      log: (text: string) => {
        calls.logs.push(text);
      },
    },
    command: {
      list: async () => {
        calls.lists += 1;
        if (options.listThrows) throw new Error("scripted list failure");
        return commands.map((name) => ({ name, description: "", source: "plugin" }));
      },
      run: async (input: { command: string; args?: string }) => {
        calls.runs.push(input);
        if (options.runRejects) throw new Error("scripted reject");
        return {};
      },
    },
  };
  return { services, calls };
}

function decision(fields: {
  fire: boolean;
  reason: string;
  level: number | null;
  percent: number;
  warnings?: string[];
}) {
  return {
    exitCode: 0,
    stdout: JSON.stringify({
      session_id: SESSION,
      name: "dotfiles-x.coordinator",
      warnings: [],
      ...fields,
    }),
    stderr: "",
  };
}

function measured(percent: number | undefined, changed: string[] = ["context"]) {
  return {
    context: percent === undefined ? { window: 200_000 } : { percent, window: 200_000 },
    rateLimits: [],
    changed,
  };
}

const sentinel = { changed: ["context"] };
const next = async () => sentinel;
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const lastStatus = (calls: { statuses: (string | undefined)[] }) => calls.statuses.at(-1);

async function run(services: unknown, event: Record<string, unknown>) {
  const result = await measure(services, event, next);
  await flush();
  assert.equal(result, sentinel, "every path returns next's result");
  return result;
}

let arms = 0;
const regressions: string[] = [];
const ok = { exitCode: 0, stdout: "", stderr: "" };

// A measurement that did not move the context does nothing at all.
{
  const { services, calls } = makeServices();
  await run(services, measured(90, ["rateLimits"]));
  assert.equal(calls.process.length, 0);
  assert.equal(calls.statuses.length, 0);
  arms += 1;
}

// A context with no percent yet (fresh window) does nothing at all.
{
  const { services, calls } = makeServices();
  await run(services, measured(undefined));
  assert.equal(calls.process.length, 0);
  assert.equal(calls.statuses.length, 0);
  arms += 1;
}

// R4: first measurement discovers the role even below the limit. Then zero processes.
for (const percent of [23, 29.9]) {
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "below-limit", level: 30, percent })],
  });
  await run(services, measured(percent));
  assert.equal(calls.process.length, 1);
  await run(services, measured(percent));
  assert.equal(calls.process.length, 1, "cached coordinator under limit needs no second process");
  assert.equal(calls.lists, 0);
  assert.equal(lastStatus(calls), `handoff ${percent}%/30%`);
  arms += 1;
}

// A configured limit moves the pre-filter; an invalid one falls back to 30.
{
  const raised = makeServices({ env: { DOTFILES_COORDINATOR_HANDOFF_PCT: "50" },
    responses: [decision({ fire: false, reason: "below-limit", level: 50, percent: 40 })],
  });
  await run(raised.services, measured(40));
  assert.equal(raised.calls.process.length, 1);
  assert.equal(lastStatus(raised.calls), "handoff 40%/50%");

  const invalid = makeServices({ env: { DOTFILES_COORDINATOR_HANDOFF_PCT: "abc" },
    responses: [decision({ fire: false, reason: "below-limit", level: 30, percent: 23 })],
  });
  await run(invalid.services, measured(23));
  assert.equal(invalid.calls.process.length, 1);
  assert.equal(lastStatus(invalid.calls), "handoff 23%/30%");
  arms += 2;
}

// At or above the limit python decides; the argv, cwd and env are exact.
{
  const { services, calls } = makeServices({
    env: { DOTFILES_COORDINATOR_HANDOFF_PCT: "30", DOTFILES_COORDINATOR_HANDOFF_STEP_PCT: "5" },
    responses: [decision({ fire: false, reason: "not-coordinator", level: null, percent: 90 })],
  });
  await run(services, measured(90));
  assert.equal(calls.process.length, 1);
  assert.deepEqual(calls.process[0].argv, [
    "uv",
    "run",
    "--project",
    "python",
    "dotfiles-setup",
    "coordinator-handoff",
    "decide",
    "--session-id",
    calls.sessionId,
    "--percent",
    "90",
  ]);
  assert.equal(calls.process[0].init?.cwd, "/repo");
  assert.deepEqual(calls.process[0].init?.env, {
    DOTFILES_COORDINATOR_HANDOFF_PCT: "30",
    DOTFILES_COORDINATOR_HANDOFF_STEP_PCT: "5",
  });
  // fire:false submits nothing and does not even list commands.
  assert.equal(calls.lists, 0);
  assert.equal(calls.runs.length, 0);
  assert.equal(lastStatus(calls), "handoff n/a (not coordinator)");
  arms += 1;
}

// Without CLAUDE_PROJECT_DIR the session root is the cwd.
{
  const { services, calls } = makeServices({
    projectDir: null,
    responses: [decision({ fire: false, reason: "not-coordinator", level: null, percent: 31 })],
  });
  await run(services, measured(31));
  assert.equal(calls.roots, 1);
  assert.equal(calls.process[0].init?.cwd, "/session-root");
  arms += 1;
}

// After a fire, below the next step: no submit, the heartbeat names the step.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "below-next-step", level: 35, percent: 34 })],
  });
  await run(services, measured(34));
  assert.equal(calls.runs.length, 0);
  assert.equal(lastStatus(calls), "handoff next @35%");
  arms += 1;
}

// Python's own below-limit answer (a limit it parsed differently) is a heartbeat.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "below-limit", level: 40, percent: 31 })],
  });
  await run(services, measured(31));
  assert.equal(calls.runs.length, 0);
  assert.equal(lastStatus(calls), "handoff 31%/40%");
  arms += 1;
}

// fire:true submits the skill ONCE, with `<session id> <percent>`, unawaited.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.equal(calls.lists, 1);
  assert.deepEqual(calls.runs, [{ command: "coordinator-handoff", args: `${calls.sessionId} 30` }]);
  assert.equal(lastStatus(calls), "handoff fired @30%");
  assert.equal(calls.toasts.length, 1);
  assert.equal(calls.logs.length, 1);
  arms += 1;
}

// The name is resolved from the listing: plugin-qualified when that is all
// there is, the bare name when both are listed.
{
  const qualified = makeServices({
    commands: ["compact", "coordinator-handoff:coordinator-handoff"],
    responses: [decision({ fire: true, reason: "fire", level: 35, percent: 36 })],
  });
  await run(qualified.services, measured(36));
  assert.deepEqual(qualified.calls.runs, [
    { command: "coordinator-handoff:coordinator-handoff", args: `${qualified.calls.sessionId} 36` },
  ]);

  const both = makeServices({
    commands: ["coordinator-handoff:coordinator-handoff", "coordinator-handoff"],
    responses: [decision({ fire: true, reason: "fire", level: 35, percent: 36 })],
  });
  await run(both.services, measured(36));
  assert.deepEqual(both.calls.runs, [{ command: "coordinator-handoff", args: `${both.calls.sessionId} 36` }]);
  arms += 2;
}

// PROBE: the real command.run path, with `--probe` as the only argument.
{
  const { services, calls } = makeServices({
    env: { DOTFILES_COORDINATOR_HANDOFF_PROBE: "1" },
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.deepEqual(calls.runs, [{ command: "coordinator-handoff", args: "--probe" }]);
  assert.equal(calls.process[0].argv.at(-1), "--no-commit");
  arms += 1;
}

// DRY_RUN: toast + log what it WOULD run; never lists or runs a command.
{
  const { services, calls } = makeServices({
    env: { DOTFILES_COORDINATOR_HANDOFF_DRY_RUN: "1" },
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.equal(calls.runs.length, 0);
  assert.equal(calls.lists, 0);
  assert.equal(calls.toasts.length, 1);
  assert.match(calls.toasts[0], /DRY-RUN: would run \/coordinator-handoff /);
  assert.equal(calls.logs.length, 1);
  assert.equal(lastStatus(calls), "handoff DRY-RUN @30%");
  assert.equal(calls.process[0].argv.at(-1), "--no-commit");
  arms += 1;
}

// The skill missing from the listing is a visible ERROR, never a silent skip.
{
  const { services, calls } = makeServices({
    commands: ["compact"],
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 }), ok],
  });
  await run(services, measured(30));
  assert.equal(calls.runs.length, 0);
  assert.equal(lastStatus(calls), "handoff ERROR: skill not listed");
  assert.equal(calls.toasts.at(-1), "coordinator-handoff: skill not listed");
  assert.deepEqual(calls.process[1].argv.slice(6), ["release", "--session-id", calls.sessionId, "--level", "30"]);
  arms += 1;
}

// A command.run rejection lands on the status line and as a toast.
{
  const { services, calls } = makeServices({
    runRejects: true,
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 }), ok],
  });
  await run(services, measured(30));
  assert.equal(calls.runs.length, 1);
  assert.equal(lastStatus(calls), "handoff ERROR: command.run rejected: scripted reject");
  assert.equal(calls.toasts.at(-1), "coordinator-handoff: command.run rejected: scripted reject");
  assert.equal(calls.process[1].argv[6], "release");
  arms += 1;
}

// A throwing process.run returns next's result, shows ERROR, toasts ONCE per
// distinct reason across repeats.
{
  const { services, calls } = makeServices({ responses: ["throw", "throw"] });
  await run(services, measured(50));
  assert.equal(lastStatus(calls), "handoff ERROR: decide failed to run");
  assert.equal(calls.toasts.length, 1);
  await run(services, measured(51));
  assert.equal(calls.statuses.length, 2);
  assert.equal(lastStatus(calls), "handoff ERROR: decide failed to run");
  assert.equal(calls.toasts.length, 1, "a repeated reason does not toast again");
  assert.equal(calls.runs.length, 0);
  arms += 1;
}

// A non-zero exit, non-JSON stdout and a malformed decision are each ERRORRs.
{
  const nonzero = makeServices({ responses: [{ exitCode: 3, stdout: "", stderr: "boom" }] });
  await run(nonzero.services, measured(50));
  assert.equal(lastStatus(nonzero.calls), "handoff ERROR: decide rc 3");

  const garbage = makeServices({ responses: [{ exitCode: 0, stdout: "not json", stderr: "" }] });
  await run(garbage.services, measured(50));
  assert.equal(lastStatus(garbage.calls), "handoff ERROR: decide output not JSON");

  const misshaped = makeServices({
    responses: [{ exitCode: 0, stdout: JSON.stringify({ fire: "yes" }), stderr: "" }],
  });
  await run(misshaped.services, measured(50));
  assert.equal(lastStatus(misshaped.calls), "handoff ERROR: decide output not JSON");
  assert.equal(misshaped.calls.runs.length, 0);
  arms += 3;
}

// An unexpected python reason (state-write-failed) is an ERROR, not a heartbeat.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "state-write-failed", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.equal(lastStatus(calls), "handoff ERROR: state-write-failed");
  assert.equal(calls.runs.length, 0);
  arms += 1;
}

// Python's config warnings are surfaced, never swallowed.
{
  const warning = "DOTFILES_COORDINATOR_HANDOFF_STEP_PCT='abc' is not a number in (0, 100]";
  const { services, calls } = makeServices({
    responses: [
      decision({ fire: false, reason: "below-next-step", level: 35, percent: 33, warnings: [warning] }),
    ],
  });
  await run(services, measured(33));
  assert.ok(calls.toasts.some((toast) => toast.includes(warning)));
  arms += 1;
}

// R4: lane role is queried below limit once, then cached even above it.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "not-coordinator", level: null, percent: 5 })],
  });
  await run(services, measured(5));
  await run(services, measured(90));
  assert.equal(calls.process.length, 1);
  assert.equal(lastStatus(calls), "handoff n/a (not coordinator)");
  regressions.push("r4-first-below-role-cache");
  arms += 1;
}

// R4: cached roles belong to session ids, not the entire loaded module.
{
  const lane = makeServices({ responses: [decision({ fire: false, reason: "not-coordinator", level: null, percent: 5 })] });
  const coordinator = makeServices({ responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })] });
  await run(lane.services, measured(5));
  await run(coordinator.services, measured(30));
  assert.equal(lane.calls.runs.length, 0);
  assert.equal(coordinator.calls.runs.length, 1);
  regressions.push("r4-role-cache-keyed-by-session");
  arms += 1;
}

// R4: a throwing event getter is inside try and overwrites stale status.
{
  const { services, calls } = makeServices();
  await run(services, { get context() { throw new Error("bad context getter"); } });
  assert.equal(lastStatus(calls), "handoff ERROR: hook failed: bad context getter");
  regressions.push("r4-event-getter-fail-open");
  arms += 1;
}

// R3: listing failure releases the exact consumed level and stays ERROR.
{
  const { services, calls } = makeServices({ listThrows: true,
    responses: [decision({ fire: true, reason: "fire", level: 35, percent: 36 }), ok],
  });
  await run(services, measured(36));
  assert.deepEqual(calls.process[1].argv.slice(6), ["release", "--session-id", calls.sessionId, "--level", "35"]);
  assert.equal(lastStatus(calls), "handoff ERROR: delivery failed: scripted list failure");
  regressions.push("r3-list-failure-releases-level");
  arms += 1;
}

// R3: failure to release itself is visible, never a false success.
{
  const { services, calls } = makeServices({ commands: [],
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 }), { exitCode: 2, stdout: "", stderr: "locked" }],
  });
  await run(services, measured(30));
  assert.equal(lastStatus(calls), "handoff ERROR: skill not listed; release rc 2");
  regressions.push("r3-release-failure-visible");
  arms += 1;
}

// R1: durable launch is a quiet terminal state, with no submit.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "already-launched", level: null, percent: 90 })],
  });
  await run(services, measured(90));
  assert.equal(lastStatus(calls), "handoff already launched");
  assert.equal(calls.runs.length, 0);
  regressions.push("r1-already-launched-heartbeat");
  arms += 1;
}

// R4: overlapping first measurements still make one role query.
{
  const { services, calls } = makeServices({
    responses: [decision({ fire: false, reason: "not-coordinator", level: null, percent: 5 })],
  });
  await Promise.all([run(services, measured(5)), run(services, measured(90))]);
  assert.equal(calls.process.length, 1);
  regressions.push("r4-concurrent-first-role-query");
  arms += 1;
}

console.log(JSON.stringify({ arms, regressions }));
