import type { EngineInterface, PluginOptions, Register } from 'claude-code'

import {
  addNote, applyMarks, compose, evidenceHolds, forkPrompt, isOwed, isRepeat, parseReply, promptText,
  fingerprint, fullText, isLedgerShape, midTurnOf, KNOW_SYSTEM, parseKnow, readLedger, renderDigest, ruleSourceOf, rulesText,
  systemBlocks,
} from './core'
import type { Ledger, Mark, Note } from './core'

// side-notes: a side agent that reads the session every few steps and passes
// a note on real risks (wrong facts, unsafe actions, owner rules broken,
// unverified claims) straight to the main agent, with a toast for the person.
//
// Documented APIs only: `turn.step`, `turn.start`, `turn.complete`,
// `prompt.submit` context, `session.start`, `$.model.complete`, `$.model.fork`,
// `$.session.messages`, `$.session.append`, `$.ui.toast`, `$.ui.log`,
// `$.fs`, `$.env`. No processes: never a nested `claude -p`.

const SELF = 'side-notes'
const MAX_API_ERRORS = 3
const DEEP_MIN_STEPS = 12
// Wakes: at most WAKE_CHAIN in a row without a prompt of the person's, WAKES_PER_DAY a UTC day, WAKE_GAP_MS
// apart. The forwarder keeps the same limits on its own, so a session sees at most 2 in a row and 20 a day.
const WAKE_CHAIN = 1
const WAKES_PER_DAY = 10
const WAKE_GAP_MS = 120_000
// Only the person's own prompts end a chain: not a task's notice, a schedule or another session.
const OWNER_KINDS = new Set(['composer', 'bridge'])
// How long a hook on the session's path waits for this mod's own bookkeeping.
const HOOK_WAIT_MS = 3000
// Haiku thinks before it answers even at low effort: in the A/B replay a
// 400-token cap left every reply at one long-session moment empty (2,448
// output tokens, no text). Thinking is billed as output, about $0.001 here.
const REPLY_TOKENS = 3000
// How much of a reply the parser rejected goes into the audit log.
const REJECTED_REPLY_CHARS = 500
// The know check thinks too; Sonnet's replies in the replay used up to about 200 output tokens of text.
const KNOW_REPLY_TOKENS = 4000
// A fork re-sends the main thread's system prompt and tools too, and its reply has no cap.
const FORK_OVERHEAD_TOKENS = 40_000
const FORK_REPLY_TOKENS = 4_000
// A conservative token estimate for text: fewer characters per token than usual.
const tokensFor = (chars: number) => Math.ceil(chars / 3)

type Settings = {
  model: string
  everySteps: number
  maxChecksPerTurn: number
  maxChecksPerSession: number
  maxTokensPerDay: number
  deepCheck: number
  rules: string[]
  stateDir: string
  wakeIdle: boolean
  // End of a trial window (ms since epoch); checks stop after it. Infinity: no window.
  trialUntil: number
  // Audit log folder; '' turns it off.
  logDir: string
  // The know check: its model ('' turns it off), the least minutes between two in a session, and its
  // tokens per session per UTC day (450k is about $1 at Sonnet's list price).
  knowModel: string
  knowEveryMinutes: number
  knowMaxTokensPerDay: number
}

export function settingsOf(o: PluginOptions): Settings {
  const n = (v: unknown, d: number, min: number) => (typeof v === 'number' && Number.isFinite(v) && v >= min ? Math.floor(v) : d)
  return {
    model: typeof o.model === 'string' && o.model.trim() !== '' ? o.model.trim() : 'haiku',
    everySteps: n(o.everySteps, 6, 1),
    maxChecksPerTurn: n(o.maxChecksPerTurn, 2, 0),
    maxChecksPerSession: n(o.maxChecksPerSession, 30, 0),
    maxTokensPerDay: n(o.maxTokensPerDay, 3_000_000, 0),
    deepCheck: n(o.deepCheck, 0, 0),
    rules: (typeof o.rules === 'string' ? o.rules.split(',') : Array.isArray(o.rules) ? o.rules.map(String) : [])
      .map(p => p.trim())
      .filter(p => p !== ''),
    stateDir: typeof o.stateDir === 'string' && o.stateDir.trim() !== '' ? o.stateDir.trim() : '~/.local/state/side-notes',
    wakeIdle: o.wakeIdle === true,
    trialUntil: typeof o.trialUntil === 'string' && o.trialUntil.trim() !== '' && Number.isFinite(Date.parse(o.trialUntil))
      ? Date.parse(o.trialUntil)
      : Number.POSITIVE_INFINITY,
    logDir: typeof o.logDir === 'string' ? o.logDir.trim() : '~/.local/state/side-notes/log',
    knowModel: typeof o.knowModel === 'string' ? o.knowModel.trim() : 'sonnet',
    knowEveryMinutes: n(o.knowEveryMinutes, 30, 0),
    knowMaxTokensPerDay: n(o.knowMaxTokensPerDay, 450_000, 0),
  }
}

// Module state: one per process; a reload runs this file afresh, and the
// ledger file carries what must outlive it (caps, the turn's count, a stop).
let settings = settingsOf({})
let isStoodDown = false
// Unknown after a reload: a note is then appended, which is safe either way.
let isWorking: boolean | undefined
let isChecking = false
// A turn ended while a check ran: its end-of-turn check runs once that one is done.
let finalOwed: { isDeep: boolean } | undefined
let turn = { id: '', lastIndex: -1, checks: 0 }
type Rules = { text: string; files: { name: string; path: string }[] }
let rules: Promise<Rules> | undefined
let chain: Promise<unknown> = Promise.resolve()
let sessionId = ''

class StandDown extends Error {}

// The audit log (discrepancy-report.md §3.1): one JSON line per check and per
// delivery, one file per session, so what side-notes looked at and found can
// be compared with the built-in later. `$.fs` has no append, so the file is
// rewritten, keeping its newest LOG_MAX_LINES lines. Best effort: a failure is
// logged to debug once and never touches checks or delivery.
const LOG_MAX_LINES = 1000
export type CheckOutcome =
  | 'note' | 'none' | 'unparsed' | 'not-answered' | 'evidence-missing' | 'repeat' | 'session-changed'
  // The know check found what the built-in already showed: a match, logged and not sent again.
  | 'builtin-repeat'
export type LogEvent =
  | { event: 'check'; trigger: 'step' | 'final' | 'know'; deep: boolean; digestChars: number; tokens: number; outcome: CheckOutcome; line?: string; kind?: string; reply?: string; model?: string; builtinLine?: string }
  | { event: 'skipped'; trigger: 'step' | 'final' | 'know'; reason: 'cap' | 'unchanged' | 'empty' }
  | { event: 'delivered'; route: 'append' | 'prompt' | 'wake'; lines: string[] }

export const appendLog = (existing: string, entries: readonly object[], max = LOG_MAX_LINES): string => {
  const lines = [...existing.split('\n').filter(l => l.trim() !== ''), ...entries.map(e => JSON.stringify(e))]
  return `${lines.slice(-max).join('\n')}\n`
}

let logChain: Promise<unknown> = Promise.resolve()
let isLogBroken = false

// Never throws and never waits on the caller's path.
function log($: EngineInterface, sid: string, event: LogEvent) {
  if (settings.logDir === '' || isLogBroken) return
  const at = new Date().toISOString()
  logChain = logChain
    .then(async () => {
      const path = `${await expand($, settings.logDir)}/side-notes-${sid.replace(/[^A-Za-z0-9_-]/g, '_')}.jsonl`
      const existing = (await $.fs.exists(path)) ? await $.fs.read(path) : ''
      await $.fs.write(path, appendLog(existing, [{ at, mod: SELF, sid, ...event }]))
    })
    .catch((error: unknown) => {
      isLogBroken = true
      try {
        $.ui.log(`${SELF}: audit log off for this process: ${String(error)}`, { to: 'debug' })
      } catch {
        // Nothing left to tell.
      }
    })
}
const noteLines = (marks: readonly Mark[]) => marks.map(m => m.line)

function standDown($: EngineInterface, why: string) {
  if (isStoodDown) return
  isStoodDown = true
  try {
    $.ui.log(`${SELF}: stopped for this session (${why}). No more side checks run.`)
  } catch {
    // Nothing left to tell.
  }
  // Best effort: a reload of this process reads it and stays stopped.
  if (sessionId !== '') void markStopped($, sessionId, why).catch(() => undefined)
}

// Ledger jobs run one at a time; one queued before a stand-down does nothing.
function run<T>($: EngineInterface, job: () => Promise<T>): Promise<T | undefined> {
  const p = chain
    .then(() => (isStoodDown ? undefined : job()))
    .catch((error: unknown) => {
      standDown($, error instanceof StandDown ? error.message : `error: ${String(error)}`)
      return undefined
    })
  chain = p
  return p
}

// A wait on the session's path: past `HOOK_WAIT_MS` the mod stops and the hook goes on.
async function bounded<T>($: EngineInterface, p: Promise<T | undefined>): Promise<T | undefined> {
  let isSettled = false
  const late = $.clock.sleep(HOOK_WAIT_MS).then(() => {
    if (!isSettled) standDown($, `its bookkeeping took over ${HOOK_WAIT_MS / 1000} s`)
    return undefined
  })
  try {
    return await Promise.race([p, late])
  } finally {
    isSettled = true
  }
}

async function expand($: EngineInterface, path: string) {
  return path.startsWith('~/') ? `${(await $.env.get('HOME')) ?? ''}${path.slice(1)}` : path
}

// One JSON file per session under `stateDir`, read afresh for every change, so
// a reload, a restart or a resume keeps the caps and never sends a note twice.
// Not `$.store`: that file would live under ~/.claude/plugins/, which needs the
// owner's OK.
async function ledgerPath($: EngineInterface, sid: string) {
  return `${await expand($, settings.stateDir)}/session-${sid.replace(/[^A-Za-z0-9_-]/g, '_')}.json`
}

// A missing file is a new session; an unreadable or broken one stops the mod.
async function load($: EngineInterface, sid: string): Promise<Ledger> {
  const path = await ledgerPath($, sid)
  if (!(await $.fs.exists(path))) return readLedger(undefined, Date.now())
  let stored: unknown
  try {
    stored = JSON.parse(await $.fs.read(path))
  } catch (error) {
    throw new StandDown(`its ledger ${path} is unreadable: ${String(error)}`)
  }
  if (!isLedgerShape(stored)) throw new StandDown(`its ledger ${path} has an unknown shape`)
  const ledger = readLedger(stored, Date.now())
  if (ledger.stopped !== undefined) throw new StandDown(`stopped earlier: ${ledger.stopped}`)
  return ledger
}

async function save($: EngineInterface, sid: string, ledger: Ledger) {
  // A late job after a stop must not overwrite the stop marker.
  if (isStoodDown) return
  try {
    await $.fs.write(await ledgerPath($, sid), JSON.stringify({ ...ledger, at: Date.now() }))
  } catch (error) {
    throw new StandDown(`its ledger could not be saved: ${String(error)}`)
  }
}

async function markStopped($: EngineInterface, sid: string, why: string) {
  const path = await ledgerPath($, sid)
  let stored: unknown
  try {
    stored = JSON.parse(await $.fs.read(path))
  } catch {
    // None yet: a fresh one records the stop.
  }
  await $.fs.write(path, JSON.stringify({ ...readLedger(stored, Date.now()), stopped: why, at: Date.now() }))
}

const update = <T>($: EngineInterface, sid: string, f: (l: Ledger) => T | Promise<T>) =>
  run($, async () => {
    const ledger = await load($, sid)
    const out = await f(ledger)
    await save($, sid, ledger)
    return out
  })

async function readRules($: EngineInterface): Promise<Rules> {
  const files: { name: string; path: string; text: string }[] = []
  for (const raw of settings.rules) {
    const path = await expand($, raw)
    try {
      const stat = await $.fs.stat(path)
      if (stat.kind === 'dir') {
        const names = (await $.fs.list(path)).filter(e => e.kind === 'file' && e.name.endsWith('.md')).map(e => e.name).sort()
        for (const name of names) {
          files.push({ name: name.replace(/\.md$/, ''), path: `${path}/${name}`, text: await $.fs.read(`${path}/${name}`) })
        }
      } else {
        files.push({ name: (path.split('/').at(-1) ?? path).replace(/\.md$/, ''), path, text: await $.fs.read(path) })
      }
    } catch (error) {
      $.ui.log(`${SELF}: rules path skipped: ${raw} (${String(error)})`, { to: 'debug' })
    }
  }
  return { text: rulesText(files), files: files.map(({ name, path }) => ({ name, path })) }
}

// Appends what is owed as a row the model reads at its next request. Reserved
// and saved first, so a refused append is released and goes with the next
// prompt. Never throws: a failure stops the mod.
async function deliverNow($: EngineInterface, sid: string) {
  try {
    const message = await update($, sid, ledger => {
      const m = compose(ledger, settings.model)
      if (m !== undefined) applyMarks(ledger, m.marks, 'reserve')
      return m
    })
    if (message === undefined) return
    let isAppended = false
    try {
      // A /clear may have started another session meanwhile: that one gets nothing of this.
      if (!isStoodDown && (await $.session.id()) === sid) {
        const answer = await $.session.append({ message: { type: 'user', content: [{ type: 'text', text: message.text }] } })
        isAppended = answer.deny === undefined
        if (isAppended) log($, sid, { event: 'delivered', route: 'append', lines: noteLines(message.marks) })
      }
    } finally {
      if (!isAppended) await update($, sid, ledger => applyMarks(ledger, message.marks, 'release'))
    }
  } catch (error) {
    standDown($, `delivery failed: ${String(error)}`)
  }
}

// Idle, with wakeIdle on: starts a turn of its own with what is owed, within the
// wake limits above. Reserved first; released if the prompt was dropped. A wake due
// inside the gap is tried again when the gap ends.
async function wake($: EngineInterface, sid: string) {
  try {
    const now = await $.clock.now()
    const today = utcDay(now)
    let retryIn = 0
    const message = await update($, sid, ledger => {
      const dayWakes = ledger.wakeDay === today ? ledger.dayWakes : 0
      if (ledger.wakeChain >= WAKE_CHAIN || dayWakes >= WAKES_PER_DAY) return undefined
      const m = compose(ledger, settings.model)
      if (m === undefined) return undefined
      if (ledger.wakeDay !== '' && now - ledger.wakeAt < WAKE_GAP_MS) {
        retryIn = ledger.wakeAt + WAKE_GAP_MS - now
        return undefined
      }
      ledger.wakes += 1
      ledger.wakeChain += 1
      ledger.wakeAt = now
      ledger.wakeDay = today
      ledger.dayWakes = dayWakes + 1
      applyMarks(ledger, m.marks, 'reserve')
      return m
    })
    if (retryIn > 0) {
      void $.clock
        .sleep(retryIn)
        .then(() => (isWorking === false && !isStoodDown ? wake($, sid) : undefined))
        .catch(() => undefined)
    }
    if (message === undefined) return
    let isEntered = false
    try {
      if (!isStoodDown && (await $.session.id()) === sid) {
        const result = await $.prompt.submit({ text: message.text })
        isEntered = result.drop === undefined
        if (isEntered) log($, sid, { event: 'delivered', route: 'wake', lines: noteLines(message.marks) })
      }
    } finally {
      if (!isEntered) await update($, sid, ledger => applyMarks(ledger, message.marks, 'release'))
    }
  } catch (error) {
    standDown($, `wake failed: ${String(error)}`)
  }
}

type Usage = { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number }
const spent = (u: Usage | undefined) =>
  u === undefined ? 0 : u.input_tokens + u.output_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens

// Messages that reached the agent mid-turn live only in the api view (see
// midTurnOf); a failed read just leaves them out of the digest.
async function midTurn($: EngineInterface) {
  try {
    return midTurnOf(await $.session.messages({ as: 'api' }))
  } catch {
    return new Map<string, string[]>()
  }
}

// One side check, in the background. Never throws.
async function check($: EngineInterface, turnId: string, isFinal: boolean, isDeep: boolean) {
  try {
    const sid = await $.session.id()
    sessionId = sid
    const messages = await $.session.messages()
    const mid = await midTurn($)
    const digest = renderDigest(messages, undefined, mid)
    // A deep check reads the whole conversation, so its quote is held to all of it.
    const source = isDeep ? fullText(messages, mid) : digest
    rules ??= readRules($)
    const rulesNow = await rules
    const system = systemBlocks(rulesNow.text)
    const today = utcDay(await $.clock.now())
    const before = await update($, sid, ledger => {
      // The check and token caps count per UTC day, so a busy session is checked again the next day.
      if (ledger.day !== today) {
        ledger.day = today
        ledger.dayChecks = 0
        ledger.dayTokens = 0
      }
      if (ledger.turnId !== turnId) {
        ledger.turnId = turnId
        ledger.turnChecks = 0
      }
      const raised = [...ledger.notes]
      const prompt = isDeep ? forkPrompt(rulesNow.text, raised) : promptText(raised, digest)
      // What this check may cost at most, counted before it is sent.
      const estimate = isDeep
        ? tokensFor(source.length + prompt.length) + FORK_OVERHEAD_TOKENS + FORK_REPLY_TOKENS
        : tokensFor(system.length + prompt.length) + REPLY_TOKENS
      // Mid-turn checks leave one of the turn's checks for its end, counted in the ledger so a reload keeps it.
      const turnLimit = isFinal || settings.maxChecksPerTurn < 2 ? settings.maxChecksPerTurn : settings.maxChecksPerTurn - 1
      const isOver =
        ledger.dayChecks >= settings.maxChecksPerSession ||
        ledger.turnChecks >= turnLimit ||
        ledger.dayTokens + estimate > settings.maxTokensPerDay
      const seen = fingerprint(digest)
      if (isOver || digest === '' || seen === ledger.seen) {
        return { skip: isOver ? ('cap' as const) : digest === '' ? ('empty' as const) : ('unchanged' as const) }
      }
      ledger.checks += 1
      ledger.dayChecks += 1
      ledger.turnChecks += 1
      if (isDeep) ledger.deepChecks += 1
      ledger.seen = seen
      // Charged now, settled to the real usage afterwards: a reload in between keeps the charge.
      ledger.tokens += estimate
      ledger.dayTokens += estimate
      return { prompt, estimate, skip: undefined }
    })
    const trigger = isFinal ? ('final' as const) : ('step' as const)
    if (before?.skip !== undefined) log($, sid, { event: 'skipped', trigger, reason: before.skip })
    if (before === undefined || before.skip !== undefined || isStoodDown) return
    const reply = isDeep
      ? await $.model.fork({ prompt: before.prompt, effort: 'low' })
      : await $.model.complete({
          model: settings.model,
          system: [{ text: system, cache: true }],
          prompt: before.prompt,
          maxTokens: REPLY_TOKENS,
          effort: 'low',
          timeoutMs: 60_000,
        })
    const usage = 'usage' in reply ? reply.usage : undefined
    const failed = !reply.isAnswered && (reply.reason === 'api-error' || reply.reason === 'aborted')
    let outcome: CheckOutcome = 'none'
    let found: { line: string; kind: string } | undefined
    let rejected: string | undefined
    const note = await update($, sid, async ledger => {
      ledger.tokens += spent(usage) - before.estimate
      // Settled on the day it was charged; after a rollover the new day starts clean.
      if (ledger.day === today) ledger.dayTokens = Math.max(0, ledger.dayTokens + spent(usage) - before.estimate)
      ledger.apiErrors = failed ? ledger.apiErrors + 1 : 0
      if (ledger.apiErrors >= MAX_API_ERRORS) throw new StandDown(`${MAX_API_ERRORS} side checks in a row failed at the API`)
      if (!reply.isAnswered) return void (outcome = 'not-answered')
      const parsed = parseReply(reply.text)
      if (parsed.kind !== 'note') {
        // Kept so the audit log can show which format rule the reply broke.
        if (parsed.kind !== 'none') rejected = reply.text.slice(0, REJECTED_REPLY_CHARS)
        return void (outcome = parsed.kind === 'none' ? 'none' : 'unparsed')
      }
      found = { line: parsed.note.line, kind: parsed.note.kind }
      // Dropped: a quote that is not in the session, or a note already raised.
      if (!evidenceHolds(parsed.note.evidence, source)) return void (outcome = 'evidence-missing')
      if (isRepeat(parsed.note.line, ledger.notes)) return void (outcome = 'repeat')
      // The session changed under the check (/clear): the note is dropped.
      if ((await $.session.id()) !== sid) return void (outcome = 'session-changed')
      const note = { ...parsed.note, ruleSource: ruleSourceOf(parsed.note.rule, rulesNow.files) }
      addNote(ledger, note)
      outcome = 'note'
      return note
    })
    log($, sid, { event: 'check', trigger, deep: isDeep, digestChars: digest.length, tokens: spent(usage), outcome, ...found, ...(rejected === undefined ? {} : { reply: rejected }) })
    if (note === undefined || isStoodDown) return
    $.ui.toast(`Side note · ${note.line}`, { timeoutMs: 8000 })
    // Idle: it waits for the next prompt, or the next turn that starts without one.
    if (isWorking !== false) await deliverNow($, sid)
    else if (settings.wakeIdle) await wake($, sid)
  } catch (error) {
    standDown($, `error: ${String(error)}`)
  }
}

// Built-in notes the forwarder logged as shown in this session, so the know check does not repeat them.
// Best effort: no log, no list.
async function builtinLines($: EngineInterface, sid: string): Promise<string[]> {
  if (settings.logDir === '') return []
  try {
    const path = `${await expand($, settings.logDir)}/builtin-${sid.replace(/[^A-Za-z0-9_-]/g, '_')}.jsonl`
    if (!(await $.fs.exists(path))) return []
    return (await $.fs.read(path))
      .split('\n')
      .flatMap(l => {
        try {
          const e = JSON.parse(l) as { event?: string; line?: unknown }
          return e.event === 'shown' && typeof e.line === 'string' ? [e.line] : []
        } catch {
          return []
        }
      })
  } catch {
    return []
  }
}

const utcDay = (ms: number) => new Date(ms).toISOString().slice(0, 10)
let isKnowing = false
// Not before this time (ms, the mod clock): mid-turn steps ask often, and most are too early.
let knowNextAt = 0

// The know check: what the owner should know now (the built-in's kind of
// note), on `knowModel`, at most once per `knowEveryMinutes` and within
// `knowMaxTokensPerDay`. Asked at a turn's end and every `everySteps` steps
// within a turn, so a turn that runs for hours is still looked at. Its own
// budget, apart from the risk check's caps. Never throws.
async function knowCheck($: EngineInterface) {
  try {
    const now = await $.clock.now()
    if (now < knowNextAt) return
    const sid = await $.session.id()
    sessionId = sid
    const messages = await $.session.messages()
    const digest = renderDigest(messages, undefined, await midTurn($))
    const shown = await builtinLines($, sid)
    const before = await update($, sid, ledger => {
      // knowSeen is set by the first know check of a session; until then nothing is too early.
      knowNextAt = ledger.knowSeen === '' ? 0 : ledger.knowAt + settings.knowEveryMinutes * 60_000
      if (now < knowNextAt) return { skip: 'early' as const }
      if (ledger.knowDay !== utcDay(now)) {
        ledger.knowDay = utcDay(now)
        ledger.knowTokens = 0
      }
      // Only side-notes' own notes count as raised. The built-in's are left out on purpose: the trial measures
      // whether this check finds the same issues, and a find that repeats one is caught after the reply instead.
      const prompt = promptText(ledger.notes, digest)
      const estimate = tokensFor(KNOW_SYSTEM.length + prompt.length) + KNOW_REPLY_TOKENS
      const seen = fingerprint(digest)
      if (digest === '' || seen === ledger.knowSeen) return { skip: digest === '' ? ('empty' as const) : ('unchanged' as const) }
      if (ledger.knowTokens + estimate > settings.knowMaxTokensPerDay) return { skip: 'cap' as const }
      ledger.knowAt = now
      ledger.knowSeen = seen
      knowNextAt = now + settings.knowEveryMinutes * 60_000
      ledger.knowTokens += estimate
      return { prompt, estimate, skip: undefined }
    })
    if (before?.skip === 'cap' || before?.skip === 'empty' || before?.skip === 'unchanged') {
      log($, sid, { event: 'skipped', trigger: 'know', reason: before.skip })
    }
    if (before === undefined || before.skip !== undefined || isStoodDown) return
    const reply = await $.model.complete({
      model: settings.knowModel,
      system: [{ text: KNOW_SYSTEM, cache: true }],
      prompt: before.prompt,
      maxTokens: KNOW_REPLY_TOKENS,
      effort: 'low',
      timeoutMs: 120_000,
    })
    const usage = 'usage' in reply ? reply.usage : undefined
    const failed = !reply.isAnswered && (reply.reason === 'api-error' || reply.reason === 'aborted')
    let outcome: CheckOutcome = 'none'
    let found: { line: string; kind: string } | undefined
    let rejected: string | undefined
    let matched: string | undefined
    const note = await update($, sid, async ledger => {
      ledger.knowTokens += spent(usage) - before.estimate
      // Failures count toward the shared stop; a success here leaves the risk check's streak alone.
      if (failed) ledger.apiErrors += 1
      if (ledger.apiErrors >= MAX_API_ERRORS) throw new StandDown(`${MAX_API_ERRORS} side checks in a row failed at the API`)
      if (!reply.isAnswered) return void (outcome = 'not-answered')
      const parsed = parseKnow(reply.text)
      if (parsed.kind !== 'note') {
        if (parsed.kind !== 'none') rejected = reply.text.slice(0, REJECTED_REPLY_CHARS)
        return void (outcome = parsed.kind === 'none' ? 'none' : 'unparsed')
      }
      found = { line: parsed.note.line, kind: parsed.note.kind }
      if (isRepeat(parsed.note.line, ledger.notes)) return void (outcome = 'repeat')
      const same = shown.find(line => isRepeat(parsed.note.line, [{ line, kind: 'situation', evidence: '' }]))
      if (same !== undefined) {
        matched = same
        return void (outcome = 'builtin-repeat')
      }
      if ((await $.session.id()) !== sid) return void (outcome = 'session-changed')
      const note = { ...parsed.note, model: settings.knowModel }
      addNote(ledger, note)
      outcome = 'note'
      return note
    })
    log($, sid, {
      event: 'check', trigger: 'know', deep: false, digestChars: digest.length, tokens: spent(usage), outcome,
      model: settings.knowModel, ...found, ...(rejected === undefined ? {} : { reply: rejected }),
      ...(matched === undefined ? {} : { builtinLine: matched }),
    })
    if (note === undefined || isStoodDown) return
    $.ui.toast(`Side note · ${note.line}`, { timeoutMs: 8000 })
    if (isWorking !== false) await deliverNow($, sid)
    else if (settings.wakeIdle) await wake($, sid)
  } catch (error) {
    standDown($, `error: ${String(error)}`)
  }
}

function maybeKnow($: EngineInterface) {
  if (isStoodDown || isTrialOver || isKnowing || settings.knowModel === '' || Date.now() >= settings.trialUntil) return
  isKnowing = true
  void knowCheck($).finally(() => {
    isKnowing = false
  })
}

// Starts a check if the caps allow one. Synchronous, so a step never waits.
// Mid-turn checks leave one of the turn's checks for its end.
let isTrialOver = false

function maybeCheck($: EngineInterface, isFinal: boolean, isDeep = false) {
  if (isStoodDown || isTrialOver) return
  // Past the trial window: no more checks. Notes already found are still delivered.
  if (Date.now() >= settings.trialUntil) {
    isTrialOver = true
    $.ui.log(`${SELF}: trial window ended at ${new Date(settings.trialUntil).toISOString()}; no more side checks run.`)
    return
  }
  if (isChecking) {
    if (isFinal) finalOwed = { isDeep }
    return
  }
  const limit = isFinal || settings.maxChecksPerTurn < 2 ? settings.maxChecksPerTurn : settings.maxChecksPerTurn - 1
  if (turn.checks >= limit) return
  isChecking = true
  turn.checks += 1
  void check($, turn.id, isFinal, isDeep).finally(() => {
    isChecking = false
    const owed = finalOwed
    finalOwed = undefined
    if (owed !== undefined && isWorking === false) maybeCheck($, true, owed.isDeep)
  })
}

export function resetForTests() {
  settings = settingsOf({})
  isTrialOver = false
  isStoodDown = false
  isWorking = undefined
  isChecking = false
  finalOwed = undefined
  turn = { id: '', lastIndex: -1, checks: 0 }
  rules = undefined
  chain = Promise.resolve()
  sessionId = ''
  logChain = Promise.resolve()
  isLogBroken = false
  isKnowing = false
  knowNextAt = 0
}

export const register: Register = (on, options) => {
  resetForTests()
  settings = settingsOf(options)

  on('turn.start', async ($, e, next) => {
    if (e.agentId !== undefined) return next(e)
    isWorking = true
    // A new turn's own checks cover what the last turn's owed check would have seen.
    finalOwed = undefined
    turn = { id: e.turnId, lastIndex: -1, checks: 0 }
    // A turn no prompt started (a task's notification) still gets what waits.
    if (!isStoodDown) {
      await bounded(
        $,
        run($, async () => {
          const sid = await $.session.id()
          sessionId = sid
          if (isOwed(await load($, sid))) void deliverNow($, sid)
        }),
      )
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('turn.step', async function* ($, e, next) {
    if (e.agentId === undefined && !isStoodDown) {
      try {
        if (e.turnId !== turn.id) turn = { id: e.turnId, lastIndex: -1, checks: 0 }
        turn.lastIndex = e.index
        if (e.index > 0 && e.index % settings.everySteps === 0) {
          maybeCheck($, false)
          maybeKnow($)
        }
      } catch (error) {
        standDown($, `error: ${String(error)}`)
      }
    }
    return yield* next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId !== undefined) return next(e)
    isWorking = false
    try {
      // One more check at the end of a turn that used tools: it sees the final
      // answer. An unchanged session is skipped inside the check.
      if (!isStoodDown && turn.lastIndex >= 1) {
        const isDeep =
          settings.deepCheck > 0 &&
          turn.lastIndex + 1 >= DEEP_MIN_STEPS &&
          ((await bounded($, run($, async () => (await load($, await $.session.id())).deepChecks))) ?? Infinity) < settings.deepCheck
        maybeCheck($, true, isDeep)
        maybeKnow($)
      }
    } catch (error) {
      standDown($, `error: ${String(error)}`)
    }
    return next(e)
  }).catch(($, e, next) => next(e))

  on('prompt.submit', async ($, e, next) => {
    if (isStoodDown) return next(e)
    const isOwner = OWNER_KINDS.has((e.origin as { kind: string }).kind)
    const taken = await bounded(
      $,
      run($, async () => {
        const sid = await $.session.id()
        sessionId = sid
        const ledger = await load($, sid)
        // A prompt of the person's ends a chain of woken turns.
        if (isOwner && ledger.wakeChain > 0) {
          ledger.wakeChain = 0
          await save($, sid, ledger)
        }
        const message = compose(ledger, settings.model)
        if (message === undefined) return undefined
        // Reserved before `next`, which starts the turn (whose start would append it again).
        applyMarks(ledger, message.marks, 'reserve')
        await save($, sid, ledger)
        return { sid, ...message }
      }),
    )
    if (taken === undefined) return next(e)
    const release = (marks: readonly Mark[]) => void update($, taken.sid, l => applyMarks(l, marks, 'release'))
    // The session may have changed while the ledger was saved: then this prompt carries nothing of it.
    if (isStoodDown || (await $.session.id()) !== taken.sid) {
      release(taken.marks)
      return next(e)
    }
    try {
      const result = await next({ ...e, context: [...(e.context ?? []), taken.text] })
      if (result.drop !== undefined) release(taken.marks)
      else log($, taken.sid, { event: 'delivered', route: 'prompt', lines: noteLines(taken.marks) })
      return result
    } catch (error) {
      release(taken.marks)
      throw error
    }
  }).catch(($, e, next) => next(e))
}

export type { Note }
