import assert from "node:assert/strict";
import {
  lstat,
  mkdir,
  mkdtemp,
  realpath,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, resolve } from "node:path";

import { register } from "../../../.claude/skills/claude-doctor/hooks/register.ts";

type DoctorReport = {
  verdict: "ok" | "invalid" | "unknown" | "drift";
  enforcement_eligible?: boolean;
  disabled_by_baseline?: boolean;
  baseline_path?: string;
  findings: string[];
  running_version: string | null;
  install_method: string | null;
  latest_version: string | null;
};

type Handler = (
  services: ReturnType<typeof makeServices>,
  event: Record<string, unknown>,
  next: (event: Record<string, unknown>) => Promise<Record<string, unknown>>,
) => Promise<Record<string, unknown>>;

const handlers = new Map<string, Handler>();
register(((event: string, handler: Handler) => handlers.set(event, handler)) as never);

const invalid = (finding = "host install is broken"): DoctorReport => ({
  verdict: "invalid",
  enforcement_eligible: true,
  findings: [finding],
  running_version: "2.1.278",
  install_method: "npm-global",
  latest_version: "2.1.278",
});

const ok = (): DoctorReport => ({
  verdict: "ok",
  enforcement_eligible: false,
  findings: [],
  running_version: "2.1.278",
  install_method: "native",
  latest_version: "2.1.278",
});

const unknown = (finding = "the host question could not be asked"): DoctorReport => ({
  verdict: "unknown",
  enforcement_eligible: false,
  findings: [finding],
  running_version: null,
  install_method: null,
  latest_version: null,
});

const disabled = (baselinePath: string): DoctorReport => ({
  ...unknown("claude-doctor is disabled by doctor.toml"),
  disabled_by_baseline: true,
  baseline_path: baselinePath,
});

const drift = (): DoctorReport => ({
  verdict: "drift",
  enforcement_eligible: false,
  findings: [
    "schemas/sources.toml pins claude-code at 2.1.278 but 2.1.279 is published.",
  ],
  running_version: "2.1.279",
  install_method: "native",
  latest_version: "2.1.279",
});

function makeServices(root: string, cwd = root) {
  let clockMs = 1_000;
  let clockRejects = false;
  let envRejects = false;
  let projectDir: string | undefined = root;
  let rootAvailable = true;
  let spawnCount = 0;
  const responses: unknown[] = [];

  const fsPath = (path: string) => (isAbsolute(path) ? path : resolve(cwd, path));
  return {
    clock: {
      now: async () => {
        if (clockRejects) throw new Error("scripted clock failure");
        return clockMs;
      },
    },
    env: {
      get: async (name: string) => {
        if (envRejects) throw new Error("scripted environment failure");
        if (name === "PATH") return "/test/bin:/usr/bin";
        if (name === "CLAUDE_PROJECT_DIR") return projectDir;
        return undefined;
      },
    },
    fs: {
      stat: async (path: string, options?: { resolve?: boolean }) => {
        const absolute = fsPath(path);
        const linkInfo = await lstat(absolute);
        const targetInfo = await stat(absolute).catch(() => undefined);
        const info = targetInfo ?? linkInfo;
        return {
          kind:
            targetInfo === undefined
              ? "other"
              : targetInfo.isDirectory()
                ? "dir"
                : targetInfo.isFile()
                  ? "file"
                  : "other",
          size: info.size,
          mtimeMs: info.mtimeMs,
          isLink: linkInfo.isSymbolicLink(),
          realPath:
            options?.resolve && targetInfo !== undefined
              ? await realpath(absolute)
              : undefined,
        };
      },
    },
    process: {
      run: async () => {
        spawnCount += 1;
        const response = responses.shift();
        if (response === null || response === undefined) {
          throw new Error("scripted claude-doctor failure");
        }
        const eligible =
          typeof response === "object" &&
          response !== null &&
          "enforcement_eligible" in response &&
          response.enforcement_eligible === true;
        return { exitCode: eligible ? 1 : 0, stdout: JSON.stringify(response), stderr: "" };
      },
    },
    session: {
      root: async () => {
        if (!rootAvailable) throw new Error("session root unavailable");
        return root;
      },
    },
    advanceClock(ms: number) {
      clockMs += ms;
    },
    setClock(ms: number) {
      clockMs = ms;
    },
    rejectClock() {
      clockRejects = true;
    },
    rejectEnvironment() {
      envRejects = true;
    },
    disableRoots() {
      rootAvailable = false;
      projectDir = undefined;
    },
    fallBackToProjectDir() {
      rootAvailable = false;
      projectDir = root;
    },
    push(...reports: unknown[]) {
      responses.push(...reports);
    },
    spawned() {
      return spawnCount;
    },
  };
}

const sessionStart = handlers.get("classic.SessionStart");
const preToolUse = handlers.get("classic.PreToolUse");
assert(sessionStart, "SessionStart handler was not registered");
assert(preToolUse, "PreToolUse handler was not registered");

const next = async () => ({ allow: true, additionalContext: ["base context"] });

async function start(services: ReturnType<typeof makeServices>, report: DoctorReport) {
  services.push(report);
  return sessionStart(services, {}, next);
}

async function call(
  services: ReturnType<typeof makeServices>,
  event: Record<string, unknown>,
) {
  return preToolUse(services, event, next);
}

function assertDenied(result: Record<string, unknown>, expectedFinding?: string) {
  assert.equal(typeof result.deny, "string");
  const deny = result.deny as string;
  assert.match(
    deny,
    /^claude-doctor: refusing tool calls until the Claude Code install is repaired\./,
  );
  if (expectedFinding !== undefined) {
    assert.ok(deny.includes(expectedFinding), `deny omitted cached finding: ${expectedFinding}`);
  }
  assert.equal("allow" in result, false, "a deny must not spread the allow result");
}

const scratch = await mkdtemp(join(tmpdir(), "claude-doctor-hook-"));
const root = join(scratch, "repo");
const otherRoot = join(scratch, "other-clone");
await mkdir(join(root, "x"), { recursive: true });
await mkdir(otherRoot, { recursive: true });
await writeFile(join(root, "doctor.toml"), "[claude]\nenabled = true\n");
await writeFile(join(root, "x", "doctor.toml"), "not the root baseline\n");
await writeFile(join(root, "doctor.toml.bak"), "backup\n");
await writeFile(join(root, "contains-doctor.toml-name"), "not the baseline\n");
await writeFile(join(otherRoot, "doctor.toml"), "another clone\n");

let arms = 0;
let caseAliasExercised = false;
let caseAliasSkippedReason: string | null = null;

// An enforcing cache permits only the resolved root baseline and never refreshes
// on the permitted path.
{
  const services = makeServices(root);
  await start(services, invalid());
  const result = await call(services, { tool: "Edit", file_path: join(root, "doctor.toml") });
  assert.equal(result.allow, true);
  assert.equal(services.spawned(), 1);
  arms += 1;
}

// A case alias accepted by the filesystem resolves to the same actual file.
{
  const alias = join(root, "DOCTOR.TOML");
  const aliasExists = await realpath(alias).catch(() => undefined);
  if (aliasExists !== undefined) {
    const services = makeServices(root);
    await start(services, invalid());
    const result = await call(services, { tool: "Edit", file_path: alias });
    assert.equal(result.allow, true);
    caseAliasExercised = true;
    arms += 1;
  } else {
    caseAliasSkippedReason = "the fixture filesystem is case-sensitive";
  }
}

// Every spelling that is not the root baseline remains denied after a fresh,
// still-enforcing verdict.
for (const refused of [
  join(root, "x", "doctor.toml"),
  join(root, "doctor.toml.bak"),
  join(otherRoot, "doctor.toml"),
  join(root, "contains-doctor.toml-name"),
]) {
  const services = makeServices(root);
  await start(services, invalid());
  services.push(invalid("still broken"));
  assertDenied(await call(services, { tool: "Edit", file_path: refused }), "still broken");
  assert.equal(services.spawned(), 2);
  arms += 1;
}

// A Write that creates the absent baseline is a repair, using parent placement.
{
  const absentRoot = join(scratch, "absent-baseline");
  await mkdir(absentRoot);
  const services = makeServices(absentRoot);
  await start(services, invalid());
  const result = await call(services, {
    tool: "Write",
    file_path: join(absentRoot, "doctor.toml"),
  });
  assert.equal(result.allow, true);
  assert.equal(services.spawned(), 1);
  arms += 1;
}

// Both operands resolve through a symlinked repository root before comparison.
{
  const realRoot = join(scratch, "real-root");
  const linkedRoot = join(scratch, "linked-root");
  await mkdir(realRoot);
  await writeFile(join(realRoot, "doctor.toml"), "[claude]\n");
  await symlink(realRoot, linkedRoot);
  const services = makeServices(linkedRoot);
  await start(services, invalid());
  const result = await call(services, {
    tool: "Edit",
    file_path: join(linkedRoot, "doctor.toml"),
  });
  assert.equal(result.allow, true);
  arms += 1;
}

// A final-component symlink named doctor.toml may not widen the write target.
{
  const linkedFileRoot = join(scratch, "linked-file-root");
  const outside = join(scratch, "outside.toml");
  await mkdir(linkedFileRoot);
  await writeFile(outside, "outside\n");
  await symlink(outside, join(linkedFileRoot, "doctor.toml"));
  const services = makeServices(linkedFileRoot);
  await start(services, invalid());
  services.push(invalid("still broken"));
  assertDenied(
    await call(services, {
      tool: "Edit",
      file_path: join(linkedFileRoot, "doctor.toml"),
    }),
  );
  arms += 1;
}

// The real fs service describes a dangling link instead of rejecting it. The
// faithful fake must therefore reach production's missing-realPath refusal.
{
  const danglingRoot = join(scratch, "dangling-file-root");
  await mkdir(danglingRoot);
  await symlink(
    join(scratch, "missing-outside.toml"),
    join(danglingRoot, "doctor.toml"),
  );
  const services = makeServices(danglingRoot);
  await start(services, invalid());
  services.push(invalid("still broken"));
  assertDenied(
    await call(services, {
      tool: "Write",
      file_path: join(danglingRoot, "doctor.toml"),
    }),
  );
  arms += 1;
}

// Session root is preferred, but the documented environment fallback can keep
// the repair path alive; only losing both roots refuses it.
{
  const fallback = makeServices(root);
  fallback.fallBackToProjectDir();
  await start(fallback, invalid());
  assert.equal(
    (await call(fallback, { tool: "Edit", file_path: join(root, "doctor.toml") })).allow,
    true,
  );

  const unavailable = makeServices(root);
  unavailable.disableRoots();
  await start(unavailable, invalid());
  unavailable.push(invalid("still broken"));
  assertDenied(
    await call(unavailable, { tool: "Edit", file_path: join(root, "doctor.toml") }),
  );
  arms += 2;
}

// Relative paths are handed to the filesystem service as-is, so their identity
// is determined by the session cwd rather than by joining them to the root.
{
  const nestedCwd = join(root, "x");
  const services = makeServices(root, nestedCwd);
  await start(services, invalid());
  services.push(invalid("still broken"));
  assertDenied(await call(services, { tool: "Edit", file_path: "doctor.toml" }));
  arms += 1;
}

// Python's reported baseline path wins when the installed package root and the
// session root diverge. Editing the session-root lookalike must not unbrick.
{
  const pythonRoot = join(scratch, "installed-package-root");
  const sessionRoot = join(scratch, "nested-session-root");
  await mkdir(pythonRoot);
  await mkdir(sessionRoot);
  await writeFile(join(pythonRoot, "doctor.toml"), "[claude]\n");
  await writeFile(join(sessionRoot, "doctor.toml"), "[claude]\n");
  const report = invalid();
  report.baseline_path = join(pythonRoot, "doctor.toml");

  const refused = makeServices(sessionRoot);
  await start(refused, report);
  refused.push(invalid("still broken"));
  assertDenied(
    await call(refused, {
      tool: "Edit",
      file_path: join(sessionRoot, "doctor.toml"),
    }),
  );

  const permitted = makeServices(sessionRoot);
  await start(permitted, report);
  assert.equal(
    (
      await call(permitted, {
        tool: "Edit",
        file_path: join(pythonRoot, "doctor.toml"),
      })
    ).allow,
    true,
  );
  arms += 1;
}

// Every POSIX-reachable isPlaceable clause is discriminating: with the named
// clause removed, target and reported baseline resolve to the same placement.
const driveRelative = "C:folder/doctor.toml";
await mkdir(join(root, "C:folder"));
await writeFile(join(root, driveRelative), "[claude]\n");
const driveNamed = join(root, "C:doctor.toml");
await writeFile(driveNamed, "[claude]\n");
const doubleSlash = `/${join(root, "doctor.toml")}`;
for (const refused of [
  driveRelative,
  doubleSlash,
  driveNamed,
  `${join(root, "x")}/`,
  `${join(root, "x")}/.`,
  `${join(root, "x")}/..`,
]) {
  const report = invalid("unplaceable baseline");
  report.baseline_path = refused;
  const services = makeServices(root);
  await start(services, report);
  services.push(invalid("still broken"));
  assertDenied(await call(services, { tool: "Edit", file_path: refused }));
  arms += 1;
}

// Each positive answer immediately replaces the enforcing cache: repaired host,
// pin-only drift, or the explicit baseline off-switch.
for (const fresh of [ok(), drift(), disabled(join(root, "doctor.toml"))]) {
  const services = makeServices(root);
  await start(services, invalid());
  services.push(fresh);
  assert.equal((await call(services, { tool: "Bash", command: "git status" })).allow, true);
  const afterRefresh = services.spawned();
  assert.equal((await call(services, { tool: "Bash", command: "git diff" })).allow, true);
  assert.equal(services.spawned(), afterRefresh);
  arms += 1;
}

// A fresh enforcing verdict, an unanswered question, and a failed refresh all
// keep the prior deny in place.
for (const fresh of [invalid("freshly broken"), unknown(), null]) {
  const services = makeServices(root);
  await start(services, invalid());
  services.push(fresh);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  assert.equal(services.spawned(), 2);
  arms += 1;
}

// A missing eligibility key remains compatible: INVALID itself still enforces.
{
  const malformed = invalid("legacy invalid payload");
  delete malformed.enforcement_eligible;
  const services = makeServices(root);
  await start(services, malformed);
  services.push(malformed);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  arms += 1;
}

// Malformed-but-establishing JSON must never clear an established deny. Each
// typed-key payload would otherwise qualify through OK or the explicit disabled
// signal; the array remains malformed because JSON arrays cannot carry a named
// verdict property.
for (const malformed of [
  42,
  [],
  { ...unknown(), verdict: "future-verdict", disabled_by_baseline: true },
  { ...ok(), findings: ["valid", 7] },
  { ...ok(), baseline_path: 7 },
  { ...ok(), disabled_by_baseline: "yes" },
  { ...ok(), enforcement_eligible: 1 },
]) {
  const services = makeServices(root);
  await start(services, invalid());
  services.push(malformed);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  arms += 1;
}

// The same validator makes a malformed SessionStart report an unanswered check.
{
  const services = makeServices(root);
  services.push(42);
  const context = await sessionStart(services, {}, next);
  assert.match(JSON.stringify(context.additionalContext), /check could not run/);
  arms += 1;
}

// INVALID cannot be talked down by an inconsistent false eligibility field.
{
  const explicitlyNonEnforcing = invalid("python ruled this non-enforcing");
  explicitlyNonEnforcing.enforcement_eligible = false;
  const services = makeServices(root);
  await start(services, explicitlyNonEnforcing);
  services.push(null);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  arms += 1;
}

// A rejecting clock takes the catch arm, where UNKNOWN still cannot disarm but
// a subsequent positive answer can.
{
  const services = makeServices(root);
  await start(services, invalid());
  services.rejectClock();
  services.push(unknown());
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  services.push(ok());
  assert.equal((await call(services, { tool: "Bash", command: "git diff" })).allow, true);
  assert.equal(services.spawned(), 3);
  arms += 1;
}

// A backward wall-clock jump expires the reuse window instead of freezing it.
{
  const services = makeServices(root);
  await start(services, invalid());
  services.push(invalid("first refresh"));
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  services.setClock(999);
  services.push(ok());
  assert.equal((await call(services, { tool: "Bash", command: "git diff" })).allow, true);
  assert.equal(services.spawned(), 3);
  arms += 1;
}

// An environment-service rejection is a null refresh, not a thrown hook or a
// reason to clear the established deny.
{
  const services = makeServices(root);
  await start(services, invalid());
  services.rejectEnvironment();
  services.push(ok());
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  assert.equal(services.spawned(), 1);
  arms += 1;
}

// The short refresh interval reuses even a still-enforcing result, then expires
// from an injected clock read without sleeping.
{
  const services = makeServices(root);
  await start(services, invalid());
  services.push(invalid("first refresh"));
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  assertDenied(await call(services, { tool: "Bash", command: "git diff" }));
  assert.equal(services.spawned(), 2);
  services.advanceClock(7_500);
  services.push(invalid("expired refresh"));
  assertDenied(await call(services, { tool: "Bash", command: "git log" }));
  assert.equal(services.spawned(), 3);
  arms += 1;
}

// Pin drift is distinct in SessionStart prose and never reaches deny or refresh.
{
  const services = makeServices(root);
  const context = await start(services, drift());
  const rendered = JSON.stringify(context.additionalContext);
  assert.match(rendered, /schemas\/sources\.toml pins claude-code/);
  assert.doesNotMatch(rendered, /BROKEN/);
  assert.doesNotMatch(rendered, /could not determine/);
  const before = services.spawned();
  assert.equal((await call(services, { tool: "Bash", command: "git status" })).allow, true);
  assert.equal(services.spawned(), before);
  arms += 1;
}

// A stale pin does not hide an unreadable running version behind DRIFT prose.
{
  const report = unknown(
    "schemas/sources.toml pins claude-code at 2.1.278 but 2.1.279 is published.",
  );
  report.running_version = "dev-build";
  const services = makeServices(root);
  const context = await start(services, report);
  const rendered = JSON.stringify(context.additionalContext);
  assert.match(rendered, /schemas\/sources\.toml pins claude-code/);
  assert.match(rendered, /could not determine/);
  assert.doesNotMatch(rendered, /BROKEN/);
  arms += 1;
}

// A SessionStart check that cannot run remains report-only and non-enforcing.
{
  const services = makeServices(root);
  services.push(null);
  const context = await sessionStart(services, {}, next);
  assert.match(JSON.stringify(context.additionalContext), /check could not run/);
  const before = services.spawned();
  assert.equal((await call(services, { tool: "Bash", command: "git status" })).allow, true);
  assert.equal(services.spawned(), before);
  arms += 1;
}

console.log(
  JSON.stringify({
    arms,
    case_alias_exercised: caseAliasExercised,
    case_alias_skipped_reason: caseAliasSkippedReason,
  }),
);
