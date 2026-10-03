import assert from "node:assert/strict";

import { register } from "../../../.claude/skills/session-start/hooks/register.ts";

/**
 * Drives the PRODUCTION `register` of the session-start mod with a scripted
 * `$`, one arm per block, and prints `{"arms": N}` for
 * `tests/test_session_start_hook.py` to pin.
 *
 * The module keeps process-wide state — a pending deferred rename and a
 * "toasted" set — exactly as it does in one engine worker, so every arm that
 * leaves a rename pending consumes it before the next arm, and toast counts
 * use reasons no earlier arm produced.
 */

type Handler = (
  services: unknown,
  event: Record<string, unknown>,
  next: (event: Record<string, unknown>) => Promise<unknown>,
) => Promise<unknown>;

const handlers = new Map<string, Handler>();
register(((event: string, handler: Handler) => handlers.set(event, handler)) as never, {} as never);
const sessionStart = handlers.get("session.start");
const promptSubmit = handlers.get("prompt.submit");
assert(sessionStart, "session.start handler was not registered");
assert(promptSubmit, "prompt.submit handler was not registered");

const SESSION = "11111111-aaaa-4000-8000-000000000001";
let sessionSequence = 0;
const PREFIX = "dotfiles-20261002T163103.123456789-05";

type ProcessResponse = { exitCode: number; stdout: string; stderr: string } | "throw";

type Options = {
  responses?: ProcessResponse[];
  runRejects?: boolean;
  reply?: string | { isAnswered: boolean; text: string };
  sessionId?: string;
  renameRejects?: boolean;
  deferRename?: boolean;
};

function makeServices(options: Options = {}) {
  const sessionId = options.sessionId ?? `${SESSION}-${++sessionSequence}`;
  const responses = [...(options.responses ?? [])];
  const calls = {
    process: [] as { argv: readonly string[]; init: Record<string, unknown> | undefined }[],
    statuses: [] as (string | undefined)[],
    toasts: [] as string[],
    runs: [] as { command: string; args?: string }[],
    completions: [] as { model: string; prompt: string; maxTokens?: number }[],
    sessionId,
    resolveRename: null as (() => void) | null,
  };
  const services = {
    env: {
      get: async (name: string) => (name === "CLAUDE_PROJECT_DIR" ? "/repo" : undefined),
    },
    session: {
      id: async () => sessionId,
      root: async () => "/session-root",
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
      log: () => undefined,
    },
    command: {
      list: async () => [],
      run: async (input: { command: string; args?: string }) => {
        calls.runs.push(input);
        if (options.runRejects || (input.command === "rename" && options.renameRejects)) {
          throw new Error("scripted reject");
        }
        if (input.command === "rename" && options.deferRename) {
          await new Promise<void>((resolve) => { calls.resolveRename = resolve; });
        }
        return {};
      },
    },
    model: {
      complete: async (request: { model: string; prompt: string; maxTokens?: number }) => {
        calls.completions.push(request);
        if (options.reply === undefined || options.reply === "throw") {
          throw new Error("scripted model failure");
        }
        return options.reply;
      },
    },
  };
  return { services, calls };
}

function answer(fields: {
  action: string;
  reload: boolean;
  name?: string | null;
  prefix?: string | null;
}) {
  return {
    exitCode: 0,
    stdout: JSON.stringify({
      session_id: SESSION,
      warnings: [],
      name: null,
      prefix: null,
      ...fields,
    }),
    stderr: "",
  };
}

const ok = { exitCode: 0, stdout: "", stderr: "" };
const RELOADS = [{ command: "reload-skills" }, { command: "reload-plugins", args: "--force" }];

const startSentinel = { cwd: "/work" };
const promptSentinel = { text: "typed" };
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
const lastStatus = (calls: { statuses: (string | undefined)[] }) => calls.statuses.at(-1);

async function start(services: unknown, isInteractive = true) {
  const result = await sessionStart(
    services,
    { cwd: "/work", surface: isInteractive ? "terminal" : null, isInteractive },
    async () => startSentinel,
  );
  await flush();
  assert.equal(result, startSentinel, "session.start returns next's result");
}

async function prompt(services: unknown, text = "Fix the CI gate for the lock refresh") {
  const result = await promptSubmit(
    services,
    { text, wait: false, origin: { kind: "composer" } },
    async () => promptSentinel,
  );
  await flush();
  assert.equal(result, promptSentinel, "prompt.submit returns next's result");
}

let arms = 0;
const regressions: string[] = [];

// Nothing pending: a prompt does nothing at all.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "already-ran", reload: false })],
  });
  await prompt(services);
  await prompt(services);
  assert.equal(calls.process.length, 1, "first prompt recovers pending state exactly once");
  assert.equal(calls.process[0].argv[6], "pending");
  assert.equal(calls.runs.length, 0);
  assert.equal(calls.completions.length, 0);
  arms += 1;
}

// Non-interactive (-p / SDK): no process, no command, no status.
{
  const { services, calls } = makeServices();
  await start(services, false);
  assert.equal(calls.process.length, 0);
  assert.equal(calls.runs.length, 0);
  assert.equal(calls.statuses.length, 0);
  arms += 1;
}

// keep: the exact decide argv and cwd; the two reloads queued IN ORDER; no rename.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "keep", reload: true, name: `${PREFIX}.lane` })],
  });
  await start(services);
  assert.deepEqual(calls.process[0].argv, [
    "uv",
    "run",
    "--project",
    "python",
    "dotfiles-setup",
    "session-start",
    "decide",
    "--session-id",
    calls.sessionId,
    "--cwd",
    "/work",
  ]);
  assert.equal(calls.process[0].init?.cwd, "/repo");
  assert.deepEqual(calls.runs, RELOADS);
  assert.equal(lastStatus(calls), "session-start ok");
  arms += 1;
}

// R12: `/rename` is queued BEFORE reloads; record only after it resolves.
{
  const name = `${PREFIX}.coordinator-auto-handoff`;
  const { services, calls } = makeServices({
    responses: [answer({ action: "rename", reload: true, name }), ok],
  });
  await start(services);
  assert.deepEqual(calls.runs, [{ command: "rename", args: name }, ...RELOADS]);
  assert.equal(calls.process[1].argv[6], "renamed");
  assert.equal(lastStatus(calls), "session-start ok (renamed)");
  arms += 1;
}

// nonconforming: never renamed; a status and a toast instead.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "nonconforming", reload: true, name: "lane-g" })],
  });
  await start(services);
  assert.deepEqual(calls.runs, RELOADS);
  assert.ok(!calls.runs.some((run) => run.command === "rename"));
  assert.equal(lastStatus(calls), "session-start: name not in convention");
  assert.equal(calls.toasts.length, 1);
  assert.match(calls.toasts[0], /"lane-g" is outside/);
  await prompt(services);
  assert.ok(!calls.runs.some((run) => run.command === "rename"), "nor at the first prompt");
  arms += 1;
}

// defer: reloads only at start; the FIRST prompt renames with a model slug and
// records it; the second prompt does nothing.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: "Fix The CI Gate, now!",
  });
  await start(services);
  assert.deepEqual(calls.runs, RELOADS);
  assert.equal(lastStatus(calls), "session-start ok (name at first prompt)");
  await prompt(services);
  assert.equal(calls.completions.length, 1);
  assert.equal(calls.completions[0].model, "haiku");
  assert.ok(calls.completions[0].prompt.includes("Fix the CI gate for the lock refresh"));
  const name = `${PREFIX}.fix-the-ci-gate-now`;
  assert.deepEqual(calls.runs, [...RELOADS, { command: "rename", args: name }]);
  assert.deepEqual(calls.process[1].argv, [
    "uv",
    "run",
    "--project",
    "python",
    "dotfiles-setup",
    "session-start",
    "renamed",
    "--session-id",
    calls.sessionId,
    "--name",
    name,
  ]);
  assert.equal(lastStatus(calls), "session-start ok (renamed)");
  await prompt(services, "a second prompt");
  assert.equal(calls.completions.length, 1, "first prompt only");
  assert.equal(calls.runs.length, 3);
  assert.equal(calls.process.length, 2);
  arms += 1;
}

// defer: a long reply keeps five words; a failing model falls back to `session`.
{
  const long = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: "one two three four five six seven",
  });
  await start(long.services);
  await prompt(long.services);
  assert.deepEqual(long.calls.runs.at(-1), {
    command: "rename",
    args: `${PREFIX}.one-two-three-four-five`,
  });

  const failing = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: "throw",
  });
  await start(failing.services);
  await prompt(failing.services);
  assert.deepEqual(failing.calls.runs.at(-1), { command: "rename", args: `${PREFIX}.session` });

  const empty = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: "!!!",
  });
  await start(empty.services);
  await prompt(empty.services);
  assert.deepEqual(empty.calls.runs.at(-1), { command: "rename", args: `${PREFIX}.session` });
  arms += 3;
}

// already-ran after a reload: no second reload; a still-pending defer prefix
// is honoured once at the next prompt.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "already-ran", reload: false, prefix: PREFIX }), ok],
    reply: "lock refresh",
  });
  await start(services);
  assert.equal(calls.runs.length, 0, "already-ran queues no reload");
  await prompt(services);
  assert.deepEqual(calls.runs, [{ command: "rename", args: `${PREFIX}.lock-refresh` }]);
  arms += 1;
}

// already-ran with nothing pending: no command now or at the next prompt.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "already-ran", reload: false, name: `${PREFIX}.x` }),
      answer({ action: "already-ran", reload: false, name: `${PREFIX}.x` })],
  });
  await start(services);
  await prompt(services);
  assert.equal(calls.runs.length, 0);
  assert.equal(calls.completions.length, 0);
  assert.equal(lastStatus(calls), "session-start ok");
  arms += 1;
}

// A throwing process: next's result, ERROR status, a toast, no command.
{
  const { services, calls } = makeServices({ responses: ["throw"] });
  await start(services);
  assert.equal(lastStatus(calls), "session-start ERROR: decide failed to run");
  assert.equal(calls.toasts.length, 1);
  assert.equal(calls.runs.length, 0);
  arms += 1;
}

// A non-zero exit and non-JSON stdout are ERRORRs, never a silent skip.
{
  const nonzero = makeServices({ responses: [{ exitCode: 4, stdout: "", stderr: "x" }] });
  await start(nonzero.services);
  assert.equal(lastStatus(nonzero.calls), "session-start ERROR: decide rc 4");

  const garbage = makeServices({ responses: [{ exitCode: 0, stdout: "nope", stderr: "" }] });
  await start(garbage.services);
  assert.equal(lastStatus(garbage.calls), "session-start ERROR: decide output not JSON");
  assert.equal(garbage.calls.runs.length, 0);
  arms += 2;
}

// An unknown python action (state-write-failed) is an ERROR and queues nothing.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "state-write-failed", reload: false })],
  });
  await start(services);
  assert.equal(lastStatus(calls), "session-start ERROR: state-write-failed");
  assert.equal(calls.runs.length, 0);
  arms += 1;
}

// A rejected queued command surfaces as an ERROR status and a toast.
{
  const { services, calls } = makeServices({
    runRejects: true,
    responses: [answer({ action: "keep", reload: true, name: `${PREFIX}.lane` })],
  });
  await start(services);
  assert.equal(calls.runs.length, 2);
  assert.match(lastStatus(calls) ?? "", /^session-start ERROR: \/reload-(skills|plugins) rejected: scripted reject$/);
  assert.ok(calls.toasts.some((toast) => toast.includes("rejected: scripted reject")));
  arms += 1;
}

// The rename bookkeeping failing is visible too.
{
  const { services, calls } = makeServices({
    responses: [
      answer({ action: "defer", reload: true, prefix: PREFIX }),
      { exitCode: 2, stdout: "", stderr: "no decision" },
    ],
    reply: "lane work",
  });
  await start(services);
  await prompt(services);
  assert.deepEqual(calls.runs.at(-1), { command: "rename", args: `${PREFIX}.lane-work` });
  assert.equal(lastStatus(calls), "session-start ERROR: rename failed: renamed rc 2");
  arms += 1;
}

// R11: the running engine's answered object uses its text, not fallback .session.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: { isAnswered: true, text: "Repair current runtime result" },
  });
  await start(services);
  await prompt(services);
  assert.deepEqual(calls.runs.at(-1), { command: "rename", args: `${PREFIX}.repair-current-runtime-result` });
  regressions.push("r11-answered-object-text");
  arms += 1;
}

// R11: unanswered text is ignored; the documented fallback still applies.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX }), ok],
    reply: { isAnswered: false, text: "This text must not name the session" },
  });
  await start(services);
  await prompt(services);
  assert.deepEqual(calls.runs.at(-1), { command: "rename", args: `${PREFIX}.session` });
  regressions.push("r11-unanswered-object-fallback");
  arms += 1;
}

// R12: promise completion, not queueing, determines bookkeeping and success.
{
  const name = `${PREFIX}.confirmed-task`;
  const { services, calls } = makeServices({ deferRename: true,
    responses: [answer({ action: "rename", reload: true, name }), ok],
  });
  await start(services);
  assert.deepEqual(calls.runs, [{ command: "rename", args: name }, ...RELOADS]);
  assert.equal(calls.process.length, 1, "no renamed record while command is unresolved");
  assert.equal(lastStatus(calls), "session-start pending rename");
  calls.resolveRename?.();
  await flush();
  assert.equal(calls.process[1].argv[6], "renamed");
  assert.equal(lastStatus(calls), "session-start ok (renamed)");
  regressions.push("r12-rename-resolution-before-record");
  arms += 1;
}

// R12: rejected deferred rename leaves Python and module pending state intact.
{
  const rejecting = makeServices({ renameRejects: true,
    responses: [answer({ action: "defer", reload: true, prefix: PREFIX })],
    reply: "keep this pending",
  });
  await start(rejecting.services);
  await prompt(rejecting.services);
  assert.equal(rejecting.calls.process.length, 1, "rejected rename must not record renamed");
  assert.equal(lastStatus(rejecting.calls), "session-start ERROR: rename failed: scripted reject");
  const retry = makeServices({ sessionId: rejecting.calls.sessionId, responses: [ok], reply: "retry naming" });
  await prompt(retry.services);
  assert.deepEqual(retry.calls.runs, [{ command: "rename", args: `${PREFIX}.retry-naming` }]);
  assert.equal(retry.calls.process[0].argv[6], "renamed");
  regressions.push("r12-rejected-rename-stays-pending");
  arms += 1;
}

// R12: no session.start after an unchanged-module reload; first prompt recovers Python state.
{
  const { services, calls } = makeServices({
    responses: [answer({ action: "already-ran", reload: false, prefix: PREFIX }), ok],
    reply: "recover after reload",
  });
  await prompt(services);
  assert.equal(calls.process[0].argv[6], "pending");
  assert.deepEqual(calls.runs, [{ command: "rename", args: `${PREFIX}.recover-after-reload` }]);
  await prompt(services);
  assert.equal(calls.process.length, 2, "pending read cached; one successful rename");
  regressions.push("r12-first-prompt-recovers-persisted-prefix");
  arms += 1;
}

// R10: unknown spare names are visible and never renamed, now or at a prompt.
{
  const { services, calls } = makeServices({ responses: [answer({ action: "unknown", reload: true })] });
  await start(services);
  await prompt(services);
  assert.deepEqual(calls.runs, RELOADS);
  assert.equal(lastStatus(calls), "session-start: name unknown");
  regressions.push("r10-name-unknown-no-rename");
  arms += 1;
}

// R12: a changed module can run start again before recovering an unconfirmed known rename.
{
  const name = `${PREFIX}.retry-known`;
  const { services, calls } = makeServices({ responses: [
    answer({ action: "already-ran", reload: false, name }),
    answer({ action: "rename", reload: false, name }), ok,
  ] });
  await start(services);
  await prompt(services);
  assert.equal(calls.process[1].argv[6], "pending");
  assert.deepEqual(calls.runs, [{ command: "rename", args: name }]);
  assert.equal(calls.process[2].argv[6], "renamed");
  regressions.push("r12-repeat-start-recovers-unconfirmed-name");
  arms += 1;
}

console.log(JSON.stringify({ arms, regressions }));
