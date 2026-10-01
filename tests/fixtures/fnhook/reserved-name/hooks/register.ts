import type { Register } from "claude-code";

// Every module registering classic.PreToolUse must permit these, consulted —
// asserted by `assert_escape_hatch_permitted`. This fixture denies nothing, and
// carries the set anyway: the invariant is deliberately exception-free.
const ESCAPE_HATCH_TOOLS = new Set(["AskUserQuestion", "SendUserMessage"]);

export const register: Register = (on) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$, e, next) => {
    const result = await next(e);
    if (ESCAPE_HATCH_TOOLS.has(e.tool)) {
      return result;
    }
    return { ...result, additionalContext: ["fixture-valid"] };
  });
};
