import type { Register } from "claude-code";

/**
 * The repo's first production function hook.
 *
 * Two handlers, and the split is load-bearing rather than stylistic. Grilling
 * decision Q13 put the REPORT on `classic.SessionStart` and the DENIAL on
 * `classic.PreToolUse` because SessionStart structurally cannot block: the
 * harness documents it as "Context only - No blocking or decision control",
 * and universal result fields are accepted by every event and discarded by
 * some.
 *
 * That is invisible to the build gates. `ClassicResultOf` in
 * `.claude/types/claude-code.d.ts` types every non-PreToolUse classic event
 * with `preventContinuation` and `block`, so a SessionStart handler that tried
 * to block would compile cleanly, pass `claude plugin validate`, pass `tsc`,
 * and then silently do nothing at runtime. Function-hook failures fail open and
 * silent. Verify this module by observed behaviour, never by a green build.
 *
 * The verdict is computed at session start and cached in module scope for
 * PreToolUse to read. Only a call that would otherwise be denied re-establishes
 * it, with a short reuse interval so a repair loop does not spawn
 * `claude doctor` plus a release-list lookup on every attempt.
 */

/** Mirrors `DoctorVerdict.to_json()` in `python/src/dotfiles_setup/claude_doctor.py`. */
type DoctorReport = {
  verdict: "ok" | "invalid" | "unknown" | "drift";
  enforcement_eligible: boolean;
  disabled_by_baseline: boolean;
  baseline_path?: string;
  findings: string[];
};

/**
 * The last verdict, or `null` before SessionStart has run.
 *
 * `null` means "not yet established", which is NOT the same as OK - but it is
 * treated permissively for the same reason `Verdict.UNKNOWN` is: a question
 * that was never asked must never block a tool call.
 */
let cachedReport: DoctorReport | null = null;

/** Reuse a deny-path refresh briefly; the injected clock keeps tests sleepless. */
const REFRESH_REUSE_MS = 7_500;
let lastRefreshAtMs: number | null = null;

type HookServices = {
  clock: { now: () => Promise<number> };
  env: { get: (name: string) => Promise<string | undefined> };
  fs: {
    stat: (
      path: string,
      options?: { resolve: boolean },
    ) => Promise<{ isLink: boolean; realPath?: string }>;
  };
  process: {
    run: (
      argv: readonly string[],
      init?: { cwd?: string; env?: Record<string, string>; timeoutMs?: number },
    ) => Promise<{ exitCode: number; stdout: string; stderr: string }>;
  };
  session: { root: () => Promise<string> };
};

/**
 * Runs the Python check with the ambient PATH captured from this process.
 *
 * The capture is the whole reason this is not a one-liner. `uv run` executes
 * under mise's activated environment, which prepends mise install dirs to PATH
 * before Python starts - so a check that reads its own inherited PATH resolves
 * mise's pinned `claude` rather than the native install the operator actually
 * runs. (That pin was `npm:` until #1043 and produced a broken launcher; it is
 * `github:` now, which is a real binary - but still not the operator's
 * install, so the capture matters either way.) Handing down `DOTFILES_AMBIENT_PATH`
 * (this process's PATH, which is the launching shell's) is what makes the
 * check measure the right binary; without it `resolve_ambient_path` falls back
 * to the rewritten one.
 */
/** Validate untrusted subprocess JSON before it can enter the session cache. */
function parseDoctorReport(value: unknown): DoctorReport | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const verdict = record.verdict;
  if (
    verdict !== "ok" &&
    verdict !== "invalid" &&
    verdict !== "unknown" &&
    verdict !== "drift"
  ) {
    return null;
  }
  if (
    !Array.isArray(record.findings) ||
    !record.findings.every((finding) => typeof finding === "string")
  ) {
    return null;
  }
  if (record.baseline_path !== undefined && typeof record.baseline_path !== "string") {
    return null;
  }
  if (
    record.disabled_by_baseline !== undefined &&
    typeof record.disabled_by_baseline !== "boolean"
  ) {
    return null;
  }
  return {
    verdict,
    enforcement_eligible: record.enforcement_eligible === true,
    disabled_by_baseline: record.disabled_by_baseline === true,
    ...(record.baseline_path === undefined ? {} : { baseline_path: record.baseline_path }),
    findings: record.findings,
  };
}

async function readVerdict($: HookServices): Promise<DoctorReport | null> {
  try {
    const ambientPath = await $.env.get("PATH");
    const projectDir = await $.env.get("CLAUDE_PROJECT_DIR");
    const { stdout } = await $.process.run(
      ["uv", "run", "--project", "python", "dotfiles-setup", "claude-doctor"],
      {
        cwd: projectDir,
        env: ambientPath ? { DOTFILES_AMBIENT_PATH: ambientPath } : {},
        timeoutMs: 90_000,
      },
    );
    // rc is deliberately ignored: it encodes enforcement eligibility, not
    // success, and the JSON carries the verdict either way.
    return parseDoctorReport(JSON.parse(stdout) as unknown);
  } catch {
    // A hook that throws fails open and silent, so failure must be a value.
    // Leaving the cache null means PreToolUse denies nothing, which is correct:
    // nothing was established.
    return null;
  }
}

/** Tools that only READ. Denying these is how a gate becomes unrecoverable. */
const READ_ONLY_TOOLS = new Set(["Read", "Glob", "Grep", "NotebookRead", "TodoWrite"]);

/**
 * Tools that cannot repair anything, and must never be denied anyway.
 *
 * `READ_ONLY_TOOLS` is scoped by what a tool DOES; this set is scoped by what
 * denying it COSTS. The split is deliberate rather than tidy: appending these
 * to a constant documented as "tools that only READ" would make that name lie,
 * and the next reader applying the name literally would remove them as a
 * mistake. Two sets, two reasons, both feeding one permit decision.
 *
 * Measured 2026-09-13, three sessions in a row. With the verdict INVALID this
 * hook denied `AskUserQuestion` and `SendUserMessage` — the only tools that can
 * put the repair choice to the operator, or report the finding at all. The
 * session could see the problem and had no way to say so; the fix had to be
 * dictated as plain text and applied by hand. That is precisely the failure
 * this module's own contract names above: a gate you cannot talk your way out
 * of does not protect the session, it ends it.
 *
 * Neither tool can run a command, so permitting them widens nothing. The gate's
 * whole purpose is preventing silent wrong-version EXECUTION, and asking a
 * question executes nothing.
 */
const ESCAPE_HATCH_TOOLS = new Set(["AskUserQuestion", "SendUserMessage"]);

/** Programs that can repair the install. Matched on a token's basename. */
const REPAIR_PROGRAMS = new Set(["claude", "mise", "uv"]);

/**
 * Where the native installer keeps its versioned binaries.
 *
 * Needed because the repair actually performed on 2026-09-13 was
 * `~/.local/share/claude/versions/2.1.270 install latest` - run by absolute
 * path precisely BECAUSE the launcher symlink was the missing thing. Its
 * basename is a version number, so a basename-only rule refuses the one
 * command that fixes the one failure this gate exists to report.
 */
const NATIVE_VERSIONS_DIR = "/claude/versions/";

/** Shell metacharacters that separate one command from the next. */
const COMMAND_SEPARATORS = /[\s;|&()<>]+/;

type Placement = { realPath: string; isLink: boolean };

/** Resolve an existing path, or place a missing basename through its parent. */
async function placed($: HookServices, path: string): Promise<Placement | undefined> {
  const cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  const name = path.slice(cut + 1);
  const isPlaceable =
    !/^[A-Za-z]:(?![\\/])/.test(path) &&
    !/^[\\/][\\/]/.test(path) &&
    !/^[A-Za-z]:/.test(name) &&
    name !== "" &&
    name !== "." &&
    name !== "..";
  if (!isPlaceable) return undefined;

  const own = await $.fs.stat(path, { resolve: true }).catch(() => undefined);
  if (own !== undefined) {
    return own.realPath === undefined
      ? undefined
      : { realPath: own.realPath, isLink: own.isLink };
  }

  const folder = cut < 0 ? "." : path.slice(0, cut + 1);
  const dir = await $.fs.stat(folder, { resolve: true }).catch(() => undefined);
  if (dir?.realPath === undefined) return undefined;
  return {
    realPath: `${dir.realPath.replace(/[\\/]$/, "")}/${name}`,
    isLink: false,
  };
}

/** True only for Edit/Write of the baseline doctor.toml Python actually read. */
async function isDoctorTomlRepair(
  $: HookServices,
  e: { tool: string } & Record<string, unknown>,
): Promise<boolean> {
  if ((e.tool !== "Edit" && e.tool !== "Write") || typeof e.file_path !== "string") {
    return false;
  }
  try {
    let expectedPath = cachedReport?.baseline_path;
    if (expectedPath === undefined) {
      let root: string | undefined;
      try {
        root = await $.session.root();
      } catch {
        root = await $.env.get("CLAUDE_PROJECT_DIR");
      }
      if (!root) return false;
      expectedPath = `${root.replace(/[\\/]$/, "")}/doctor.toml`;
    }
    const [target, expected] = await Promise.all([
      placed($, e.file_path),
      placed($, expectedPath),
    ]);
    return (
      target !== undefined &&
      expected !== undefined &&
      !target.isLink &&
      !expected.isLink &&
      target.realPath === expected.realPath
    );
  } catch {
    return false;
  }
}

/** INVALID cannot be talked down; an explicit true may make other states enforce. */
function isEnforcementEligible(report: DoctorReport | null): boolean {
  if (report === null) return false;
  return report.verdict === "invalid" || report.enforcement_eligible;
}

/** Accept an enforcing refresh or a positive answer that may clear the deny. */
function isEstablishedRefresh(report: DoctorReport): boolean {
  return (
    isEnforcementEligible(report) ||
    report.verdict === "ok" ||
    report.verdict === "drift" ||
    report.disabled_by_baseline
  );
}

async function refreshCachedReport($: HookServices): Promise<void> {
  const refreshed = await readVerdict($);
  if (refreshed !== null && isEstablishedRefresh(refreshed)) {
    cachedReport = refreshed;
  }
}

/**
 * May this tool call proceed while the install is provably broken?
 *
 * Grilling decision Q18 is "deny everything except named repair commands", and
 * the constraint that shapes it is recoverability: **whatever this refuses
 * cannot be used to fix the thing being complained about.** A gate you cannot
 * talk your way out of does not protect the session, it ends it.
 *
 * So the rule is deliberately usability-first:
 *
 * - read-only tools always pass, because the first thing anyone needs is to
 *   SEE the finding, this file, and the settings that disable the plugin;
 * - escape-hatch tools always pass, because the second thing anyone needs is to
 *   ASK about it or REPORT it, and neither executes anything;
 * - Edit/Write pass only when resolved placement identifies the repository-root
 *   `doctor.toml`, so the reviewed off-switch can be changed in-session;
 * - a Bash command passes when ANY of its tokens names a repair program.
 *
 * Scanning tokens rather than anchoring at the start is the load-bearing
 * choice. `^\s*(claude|mise)` looks stricter and is mostly a trap: it refuses
 * `cd /repo && claude install latest`, `FOO=1 mise run doctor`, and every
 * absolute-path invocation - the shapes a real repair actually takes.
 *
 * The cost, stated plainly: a command that merely MENTIONS a repair program
 * (`echo claude`, `rm -rf x # claude`) also passes. That is accepted. This is a
 * guard against a broken install, not against a user working around their own
 * gate - and the failure it prevents is silent wrong-version execution, not
 * malice.
 */
async function isRepairPermitted(
  $: HookServices,
  e: { tool: string } & Record<string, unknown>,
): Promise<boolean> {
  if (READ_ONLY_TOOLS.has(e.tool) || ESCAPE_HATCH_TOOLS.has(e.tool)) {
    return true;
  }
  if (await isDoctorTomlRepair($, e)) {
    return true;
  }
  if (e.tool !== "Bash") {
    return false;
  }
  const command = typeof e.command === "string" ? e.command : "";
  return command
    .split(COMMAND_SEPARATORS)
    .some((token) => {
      if (token.includes(NATIVE_VERSIONS_DIR)) {
        return true;
      }
      // Drop a `VAR=value` prefix and any directory part, so `/usr/bin/mise`
      // and `MISE_ENV=x mise` both reduce to the program name.
      const program = token.split("=").pop() ?? "";
      return REPAIR_PROGRAMS.has(program.slice(program.lastIndexOf("/") + 1));
    });
}

export const register: Register = (on) => {
  on("classic.SessionStart", async ($, e, next) => {
    const result = await next(e);
    cachedReport = await readVerdict($);
    lastRefreshAtMs = null;

    if (cachedReport === null) {
      return {
        ...result,
        additionalContext: [
          "claude-doctor: the check could not run. This is not a clean bill of health - it is an unanswered question.",
        ],
      };
    }
    if (cachedReport.verdict === "ok") {
      return result;
    }
    const lead =
      cachedReport.verdict === "invalid"
        ? "claude-doctor: your Claude Code install is BROKEN."
        : cachedReport.verdict === "drift"
          ? "claude-doctor: the repository's Claude Code pin is stale."
          : "claude-doctor: could not determine whether your install is current (this is NOT 'it is fine').";
    return {
      ...result,
      additionalContext: [[lead, ...cachedReport.findings].join(" ")],
    };
  });

  on("classic.PreToolUse", async ($, e, next) => {
    const result = await next(e);
    // Python owns the judgement. UNKNOWN, DRIFT and a null cache pass through;
    // malformed older JSON retains the prior INVALID fallback.
    if (!isEnforcementEligible(cachedReport)) {
      return result;
    }
    if (await isRepairPermitted($, e)) {
      return result;
    }

    // Only the about-to-deny path refreshes. A null, malformed, or unanswered
    // refresh never weakens the prior enforcing verdict. The timestamp is read
    // rather than awaited as a delay: the hook clock stops during every `$` call
    // except a `$.clock` wait (`claude-code.d.ts:4173-4175`).
    try {
      const now = await $.clock.now();
      if (
        lastRefreshAtMs === null ||
        now < lastRefreshAtMs ||
        now - lastRefreshAtMs >= REFRESH_REUSE_MS
      ) {
        lastRefreshAtMs = now;
        await refreshCachedReport($);
      }
    } catch {
      await refreshCachedReport($);
    }
    if (!isEnforcementEligible(cachedReport)) {
      return result;
    }
    // NOT `{ ...result, deny }`. A deny is one arm of a discriminated union, so
    // spreading a result that already decided `allow: true` yields
    // `{ allow: true, deny: "..." }` - which `claude plugin validate` accepts
    // and `tsc` rejects. The two build gates are complementary, and this is the
    // class the typecheck exists to catch.
    return {
      deny: [
        "claude-doctor: refusing tool calls until the Claude Code install is repaired.",
        ...(cachedReport?.findings ?? []),
      ].join(" "),
      additionalContext: result.additionalContext,
    };
  });
};
