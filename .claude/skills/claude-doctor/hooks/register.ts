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
 * The verdict is computed ONCE, at session start, and cached in module scope
 * for PreToolUse to read. Recomputing per tool call would spawn `claude doctor`
 * plus a release-list lookup on every single call.
 */

/** Mirrors `DoctorVerdict.to_json()` in `python/src/dotfiles_setup/claude_doctor.py`. */
type DoctorReport = {
  verdict: "ok" | "invalid" | "unknown";
  enforcement_eligible: boolean;
  findings: string[];
  running_version: string | null;
  install_method: string | null;
  latest_version: string | null;
};

/**
 * The last verdict, or `null` before SessionStart has run.
 *
 * `null` means "not yet established", which is NOT the same as OK - but it is
 * treated permissively for the same reason `Verdict.UNKNOWN` is: a question
 * that was never asked must never block a tool call.
 */
let cachedReport: DoctorReport | null = null;

/**
 * Runs the Python check with the ambient PATH captured from this process.
 *
 * The capture is the whole reason this is not a one-liner. `uv run` executes
 * under mise's activated environment, which prepends mise install dirs to PATH
 * before Python starts - so a check that reads its own inherited PATH resolves
 * mise's pinned `npm:@anthropic-ai/claude-code` shim rather than the native
 * install the operator actually runs. Handing down `DOTFILES_AMBIENT_PATH`
 * (this process's PATH, which is the launching shell's) is what makes the
 * check measure the right binary; without it `resolve_ambient_path` falls back
 * to the rewritten one.
 */
async function readVerdict($: {
  env: { get: (name: string) => Promise<string | undefined> };
  process: {
    run: (
      argv: readonly string[],
      init?: { cwd?: string; env?: Record<string, string>; timeoutMs?: number },
    ) => Promise<{ exitCode: number; stdout: string; stderr: string }>;
  };
}): Promise<DoctorReport | null> {
  const ambientPath = await $.env.get("PATH");
  const projectDir = await $.env.get("CLAUDE_PROJECT_DIR");
  try {
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
    return JSON.parse(stdout) as DoctorReport;
  } catch {
    // A hook that throws fails open and silent, so failure must be a value.
    // Leaving the cache null means PreToolUse denies nothing, which is correct:
    // nothing was established.
    return null;
  }
}

/** Tools that only READ. Denying these is how a gate becomes unrecoverable. */
const READ_ONLY_TOOLS = new Set(["Read", "Glob", "Grep", "NotebookRead", "TodoWrite"]);

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
function isRepairPermitted(e: { tool: string } & Record<string, unknown>): boolean {
  if (READ_ONLY_TOOLS.has(e.tool)) {
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
        : "claude-doctor: could not determine whether your install is current (this is NOT 'it is fine').";
    return {
      ...result,
      additionalContext: [[lead, ...cachedReport.findings].join(" ")],
    };
  });

  on("classic.PreToolUse", async ($, e, next) => {
    const result = await next(e);
    // Only INVALID enforces. UNKNOWN and a null cache pass through untouched -
    // a question that could not be asked must never block.
    if (cachedReport?.verdict !== "invalid") {
      return result;
    }
    if (isRepairPermitted(e)) {
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
        ...cachedReport.findings,
      ].join(" "),
      additionalContext: result.additionalContext,
    };
  });
};
