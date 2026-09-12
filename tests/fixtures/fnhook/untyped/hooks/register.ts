export const register = (on: any, _options: any) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$: any, e: any, next: any) =>
    next(e),
  );
};
