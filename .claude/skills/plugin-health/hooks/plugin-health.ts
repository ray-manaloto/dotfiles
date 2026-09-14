import type { PluginHealthCode } from "../../../types/plugin-health";
import type { Register } from "claude-code";

/**
 * SessionStart hook for plugin/skill health.
 *
 * Reconciles plugins declared in `.claude/settings.json` (enabledPlugins)
 * against what's actually installed and enabled (`claude plugin list --json`).
 * Reports drift only — OK result has no additionalContext.
 */

type PluginHealthReport = {
  code: number; // PluginHealthCode member
  declared_not_effective?: string[];
  effective_not_declared?: string[];
  cli_failed_diagnostic?: string | null;
};

/**
 * Runs the plugin health check with the ambient PATH.
 */
async function readPluginHealth($: {
  env: { get: (name: string) => Promise<string | undefined> };
  process: {
    run: (
      argv: readonly string[],
      init?: {
        cwd?: string;
        env?: Record<string, string>;
        timeoutMs?: number;
      },
    ) => Promise<{ exitCode: number; stdout: string; stderr: string }>;
  };
}): Promise<PluginHealthReport | null> {
  const ambientPath = await $.env.get("PATH");
  const projectDir = await $.env.get("CLAUDE_PROJECT_DIR");
  try {
    const { stdout } = await $.process.run(
      ["uv", "run", "--project", "python", "dotfiles-setup", "plugin-health"],
      {
        cwd: projectDir,
        env: ambientPath ? { DOTFILES_AMBIENT_PATH: ambientPath } : {},
        timeoutMs: 30_000,
      },
    );
    // The rc is authoritative (unlike claude-doctor), so we read it.
    // But the JSON carries the detail either way.
    return JSON.parse(stdout) as PluginHealthReport;
  } catch {
    // A hook that throws fails open and silent.
    return null;
  }
}

export const register: Register = (on) => {
  on("classic.SessionStart", async ($, e, next) => {
    const result = await next(e);
    const health = await readPluginHealth($);

    if (health === null) {
      // Could not run the check — fail open, no context.
      return result;
    }

    if (health.code === 0) {
      // OK — no drift.
      return result;
    }

    // Any other code = drift or error. Report it.
    const lines: string[] = [];

    if (health.declared_not_effective && health.declared_not_effective.length > 0) {
      lines.push(
        `plugin-health: declared but NOT effective: ${health.declared_not_effective.join(", ")}`,
      );
    }

    if (health.effective_not_declared && health.effective_not_declared.length > 0) {
      lines.push(
        `plugin-health: effective but NOT declared: ${health.effective_not_declared.join(", ")}`,
      );
    }

    if (health.cli_failed_diagnostic) {
      lines.push(`plugin-health: claude plugin list failed: ${health.cli_failed_diagnostic}`);
    }

    return {
      ...result,
      additionalContext: lines.length > 0 ? lines : result.additionalContext,
    };
  });
};
