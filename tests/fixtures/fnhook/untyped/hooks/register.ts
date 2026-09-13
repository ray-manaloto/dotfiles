const ESCAPE_HATCH_TOOLS = new Set(["AskUserQuestion", "SendUserMessage"]);

export const register = (on: any, _options: any) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$: any, e: any, next: any) =>
    ESCAPE_HATCH_TOOLS.has(e.tool) ? next(e) : next(e),
  );
};
