import type { Register } from "claude-code";

const READ_ONLY_TOOLS = new Set(["Read", "Grep"]);
const ESCAPE_HATCH_TOOLS = new Set(["AskUserQuestion", "SendUserMessage"]);

export const register: Register = (on) => {
  on("classic.PreToolUse", async (_$, e, next) => {
    const result = await next(e);
    if (READ_ONLY_TOOLS.has(e.tool)) {
      return result;
    }
    return { deny: "fixture denies everything else" };
  });
};
