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

type ProcessResponse = { exitCode: number; stdout: string; stderr: string } | "throw";

type Options = {
  env?: Record<string, string>;
  responses?: ProcessResponse[];
  commands?: string[];
  runRejects?: boolean;
  projectDir?: string | null;
};

function makeServices(options: Options = {}) {
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
  };
  const services = {
    env: {
      get: async (name: string) => (name in env ? env[name] : undefined),
    },
    session: {
      id: async () => SESSION,
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

// Below the default limit: ZERO process calls, and the heartbeat says so.
for (const percent of [23, 29.9]) {
  const { services, calls } = makeServices();
  await run(services, measured(percent));
  assert.equal(calls.process.length, 0);
  assert.equal(calls.lists, 0);
  assert.equal(lastStatus(calls), `handoff ${percent}%/30%`);
  arms += 1;
}

// A configured limit moves the pre-filter; an invalid one falls back to 30.
{
  const raised = makeServices({ env: { DOTFILES_COORDINATOR_HANDOFF_PCT: "50" } });
  await run(raised.services, measured(40));
  assert.equal(raised.calls.process.length, 0);
  assert.equal(lastStatus(raised.calls), "handoff 40%/50%");

  const invalid = makeServices({ env: { DOTFILES_COORDINATOR_HANDOFF_PCT: "abc" } });
  await run(invalid.services, measured(23));
  assert.equal(invalid.calls.process.length, 0);
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
    SESSION,
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
  assert.deepEqual(calls.runs, [{ command: "coordinator-handoff", args: `${SESSION} 30` }]);
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
    { command: "coordinator-handoff:coordinator-handoff", args: `${SESSION} 36` },
  ]);

  const both = makeServices({
    commands: ["coordinator-handoff:coordinator-handoff", "coordinator-handoff"],
    responses: [decision({ fire: true, reason: "fire", level: 35, percent: 36 })],
  });
  await run(both.services, measured(36));
  assert.deepEqual(both.calls.runs, [{ command: "coordinator-handoff", args: `${SESSION} 36` }]);
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
  arms += 1;
}

// The skill missing from the listing is a visible ERROR, never a silent skip.
{
  const { services, calls } = makeServices({
    commands: ["compact"],
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.equal(calls.runs.length, 0);
  assert.equal(lastStatus(calls), "handoff ERROR: skill not listed");
  assert.equal(calls.toasts.at(-1), "coordinator-handoff: skill not listed");
  arms += 1;
}

// A command.run rejection lands on the status line and as a toast.
{
  const { services, calls } = makeServices({
    runRejects: true,
    responses: [decision({ fire: true, reason: "fire", level: 30, percent: 30 })],
  });
  await run(services, measured(30));
  assert.equal(calls.runs.length, 1);
  assert.equal(lastStatus(calls), "handoff ERROR: command.run rejected: scripted reject");
  assert.equal(calls.toasts.at(-1), "coordinator-handoff: command.run rejected: scripted reject");
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

console.log(JSON.stringify({ arms }));
