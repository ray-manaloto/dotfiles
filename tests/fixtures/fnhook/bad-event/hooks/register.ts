import type { Register } from "claude-code";

export const register: Register = (on) => {
  on("classic.SessionStartt", async (_$, e, next) => next(e));
};
