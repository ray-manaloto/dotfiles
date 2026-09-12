import type { Register } from "claude-code";

export const register: Register = (on) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$, e, next) => {
    const result = await next(e);
    return { ...result, additionalContext: ["fixture-valid"] };
  });
};
