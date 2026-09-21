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
  let projectDir: string | undefined = root;
  let rootAvailable = true;
  let spawnCount = 0;
  const responses: Array<DoctorReport | null> = [];

  const fsPath = (path: string) => (isAbsolute(path) ? path : resolve(cwd, path));
  return {
    clock: {
      now: async () => clockMs,
    },
    env: {
      get: async (name: string) => {
        if (name === "PATH") return "/test/bin:/usr/bin";
        if (name === "CLAUDE_PROJECT_DIR") return projectDir;
        return undefined;
      },
    },
    fs: {
      stat: async (path: string, options?: { resolve?: boolean }) => {
        const absolute = fsPath(path);
        const [linkInfo, targetInfo] = await Promise.all([lstat(absolute), stat(absolute)]);
        return {
          kind: targetInfo.isDirectory() ? "directory" : "file",
          size: targetInfo.size,
          mtimeMs: targetInfo.mtimeMs,
          isLink: linkInfo.isSymbolicLink(),
          realPath: options?.resolve ? await realpath(absolute) : undefined,
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
        return { exitCode: response.enforcement_eligible ? 1 : 0, stdout: JSON.stringify(response), stderr: "" };
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
    disableRoots() {
      rootAvailable = false;
      projectDir = undefined;
    },
    fallBackToProjectDir() {
      rootAvailable = false;
      projectDir = root;
    },
    push(...reports: Array<DoctorReport | null>) {
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

function assertDenied(result: Record<string, unknown>) {
  assert.equal(typeof result.deny, "string");
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
  }
  arms += 1;
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
  assertDenied(await call(services, { tool: "Edit", file_path: refused }));
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

// A successful repair or off-switch immediately replaces the enforcing cache.
{
  const services = makeServices(root);
  await start(services, invalid());
  services.push(ok());
  assert.equal((await call(services, { tool: "Bash", command: "git status" })).allow, true);
  const afterRefresh = services.spawned();
  assert.equal((await call(services, { tool: "Bash", command: "git diff" })).allow, true);
  assert.equal(services.spawned(), afterRefresh);
  arms += 1;
}

// A fresh enforcing verdict and a failed refresh both keep the deny in place.
for (const fresh of [invalid("freshly broken"), null]) {
  const services = makeServices(root);
  await start(services, invalid());
  services.push(fresh);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  assert.equal(services.spawned(), 2);
  arms += 1;
}

// Malformed payloads keep today's verdict fallback instead of failing open.
{
  const malformed = invalid("legacy invalid payload");
  delete malformed.enforcement_eligible;
  const services = makeServices(root);
  await start(services, malformed);
  services.push(malformed);
  assertDenied(await call(services, { tool: "Bash", command: "git status" }));
  arms += 1;
}

// A present eligibility field is authoritative even when the legacy verdict
// value says invalid; TypeScript must not independently re-derive Python's rule.
{
  const explicitlyNonEnforcing = invalid("python ruled this non-enforcing");
  explicitlyNonEnforcing.enforcement_eligible = false;
  const services = makeServices(root);
  await start(services, explicitlyNonEnforcing);
  const before = services.spawned();
  assert.equal((await call(services, { tool: "Bash", command: "git status" })).allow, true);
  assert.equal(services.spawned(), before);
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

console.log(JSON.stringify({ arms }));
