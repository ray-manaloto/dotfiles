import type { EngineInterface, Register } from "claude-code";

const LOG = "/Users/rmanaloto/.claude/jobs/fc5ba9a3/tmp/s0/log";
let seq = 0;

async function log($: EngineInterface, kind: string, data: unknown): Promise<void> {
  const id = await $.session.id();
  seq += 1;
  await $.fs.write(`${LOG}/${Date.now()}-${id.slice(0, 8)}-${seq}-${kind}.json`, JSON.stringify({ kind, id, data }));
}

export const register: Register = (on) => {
  on("session.start", async ($, e, next) => { await log($, "start", {}); return next(e); });

  on("session.send", async ($, e, next) => {
    await log($, "send", { to: e.to, origin: e.origin, agentId: e.agentId, text: e.text.slice(0, 120) });
    if (e.to === "s0-alias") {
      const r = await next({ ...e, to: "s0-recv" });
      await log($, "send-readdressed-result", r);
      return r;
    }
    const r = await next(e);
    await log($, "send-result", r);
    return r;
  });

  on("session.receive", async ($, e, next) => {
    await log($, "receive", { origin: e.origin, text: e.text.slice(0, 200) });
    if (e.text.includes("S0 BURST")) {
      const results: unknown[] = [];
      for (let i = 0; i < 12; i++) results.push(await $.session.send({ to: "s0-sink", text: `S0 burst ${i}` }));
      await log($, "burst-results", results);
    }
    return next(e);
  });

  on("prompt.submit", async ($, e, next) => {
    await log($, "prompt", { origin: e.origin, text: e.text.slice(0, 200) });
    return next(e);
  });
};
