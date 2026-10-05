/**
 * The conversation state crosstalk keeps for one session: every message it
 * saw go out (SendMessage) or come in (a peer delivery), the peers
 * ListAgents last reported, which conversation the pane shows, and how many
 * messages each peer sent that nobody has looked at yet. Pure: every
 * function returns a new Thread.
 */

export type Direction = 'in' | 'out'

export type Entry = {
  dir: Direction
  peer: string
  text: string
  // When it passed; absent where the source kept no time.
  at?: number
}

export type Peer = {
  name: string
  kind: string
  status: string
}

export type Thread = {
  self?: string
  entries: readonly Entry[]
  peers: readonly Peer[]
  selected?: string
  unread: Readonly<Record<string, number>>
  // A peer's socket address (an envelope's `from`) to its name
  // (`from-name`): a model answers a peer at its address, the pane files the
  // answer under its name.
  aliases: Readonly<Record<string, string>>
}

export type Conversation = {
  peer: string
  status?: string
  unread: number
  last?: Entry
}

/**
 * What `$.store` keeps of a session's thread.
 */
export type Saved = {
  savedAt: number
  entries: Entry[]
  selected?: string
  aliases: Record<string, string>
}

export const EMPTY: Thread = { entries: [], peers: [], unread: {}, aliases: {} }

// ponytail: one flat cap for the whole session, per-peer caps if a chatty
// peer ends up pushing the others' history out.
export const MAX_ENTRIES = 200

export const UNKNOWN_PEER = 'unknown session'

/**
 * The session journal lines worth parsing: a peer delivery (its `origin`)
 * and a SendMessage call. A grep pattern, so a long journal is never read
 * whole.
 */
export const JOURNAL_PATTERN = '"origin":\\{"kind":"peer|"name":"SendMessage","input":'

// Global: only ever used through matchAll, which clones it. A module-level
// /g regex is stateful under .test() or .exec(): do not.
const WRAPPED = /<cross-session-message\b([^>]*)>([\s\S]*?)<\/cross-session-message>/g

const ATTRIBUTE = /\b([a-z-]+)="([^"]*)"/g

const REF_SUFFIX = /\s*\[[0-9a-f]{4,}\]\s*$/i

const SELF_LINE = /^This session is (.+?) \[[0-9a-f]+\]/m

// `  name [ref]  ·  kind  ·  status  ·  started 7d ago`
const PEER_LINE = /^\s+(.+?) \[[0-9a-f]+\]\s+·\s+([^·]+?)\s+·\s+([^·]+?)\s*(?:·.*)?$/

type Inbound = { peer: string; text: string; address?: string }

/**
 * A peer's address as SendMessage or a listing writes it, without the
 * ` [ref]` suffix that only disambiguates two sessions of one name.
 */
export function nameOf(address: string): string {
  return address.replace(REF_SUFFIX, '').trim()
}

/**
 * Every peer message a text carries, in order (a delivery can batch
 * several): `<cross-session-message from="uds:…" from-name="api">`. Named
 * by `from-name` when there is one, since `from` is a socket address.
 */
function envelopesOf(text: string): Inbound[] {
  return [...text.matchAll(WRAPPED)].map(([, head, body]) => {
    const attributes = new Map(
      [...(head ?? '').matchAll(ATTRIBUTE)].map(([, key, value]) => [key, value ?? '']),
    )
    const address = attributes.get('from')
    const sender = attributes.get('from-name') || nameOf(address ?? '')
    const inbound = { peer: sender || UNKNOWN_PEER, text: (body ?? '').trim() }

    return address ? { ...inbound, address } : inbound
  })
}

/**
 * Who sent a delivery, from where, and what it says; the whole text under
 * UNKNOWN_PEER when it has no envelope.
 */
export function inboundOf(text: string): Inbound {
  return envelopesOf(text)[0] ?? { peer: UNKNOWN_PEER, text: text.trim() }
}

/**
 * The conversation a SendMessage `to` belongs to: the name behind a socket
 * address a peer wrote from, else the address without its ref.
 */
export function peerOf(thread: Thread, to: string): string {
  return thread.aliases[to] ?? nameOf(to)
}

/**
 * The thread knowing that `address` is `peer`. A session renamed since it
 * last wrote from that address takes its conversation along.
 */
export function withAlias(thread: Thread, address: string | undefined, peer: string): Thread {
  const before = address === undefined ? undefined : thread.aliases[address]

  if (address === undefined || address === peer || before === peer) {
    return thread
  }

  const known = { ...thread, aliases: { ...thread.aliases, [address]: peer } }

  return before === undefined ? known : renamed(known, before, peer)
}

function renamed(thread: Thread, from: string, to: string): Thread {
  const { [from]: count = 0, ...unread } = thread.unread

  return {
    ...thread,
    entries: thread.entries.map(entry => (entry.peer === from ? { ...entry, peer: to } : entry)),
    unread: count > 0 ? { ...unread, [to]: (unread[to] ?? 0) + count } : unread,
    selected: thread.selected === from ? to : thread.selected,
    aliases: Object.fromEntries(
      Object.entries(thread.aliases).map(([address, name]) => [address, name === from ? to : name]),
    ),
  }
}

/**
 * Where a reply to `peer` goes: its name while ListAgents lists it, else the
 * socket it last wrote from (it outlives a rename, not a restart), else the
 * name as it is.
 */
export function addressOf(thread: Thread, peer: string): string {
  if (thread.peers.some(listed => listed.name === peer)) {
    return peer
  }

  return Object.entries(thread.aliases).findLast(([, name]) => name === peer)?.[0] ?? peer
}

/**
 * The peer sessions and this session's own name, read from ListAgents'
 * text. Only the `Peer sessions` section: subagents are this session's own.
 *
 * ponytail: parses the tool's human-readable listing, the only one it has;
 * swap for a structured source once the engine offers one to plugins.
 */
export function listingOf(text: string): { self?: string; peers: Peer[] } {
  const self = SELF_LINE.exec(text)?.[1]
  const peers: Peer[] = []
  let isPeerSection = false

  for (const line of text.split('\n')) {
    if (/^\S/.test(line)) {
      isPeerSection = line.startsWith('Peer sessions')
      continue
    }

    const match = isPeerSection ? PEER_LINE.exec(line) : null

    if (match) {
      peers.push({
        name: (match[1] ?? '').trim(),
        kind: (match[2] ?? '').trim(),
        status: (match[3] ?? '').trim(),
      })
    }
  }

  return self === undefined ? { peers } : { self, peers }
}

/**
 * The thread with one more message. An incoming one counts as unread unless
 * its conversation is on screen; the first message selects its conversation.
 */
export function record(thread: Thread, entry: Entry, isShown = false): Thread {
  const selected = thread.selected ?? entry.peer
  const isSeen = entry.dir === 'out' || (isShown && selected === entry.peer)

  return {
    ...thread,
    selected,
    entries: [...thread.entries, entry].slice(-MAX_ENTRIES),
    unread: isSeen
      ? thread.unread
      : { ...thread.unread, [entry.peer]: (thread.unread[entry.peer] ?? 0) + 1 },
  }
}

/**
 * The thread showing `peer`'s conversation, its messages now read.
 */
export function select(thread: Thread, peer: string): Thread {
  const { [peer]: _read, ...unread } = thread.unread

  return { ...thread, selected: peer, unread }
}

/**
 * The thread with the peers a fresh listing reported.
 */
export function withListing(
  thread: Thread,
  listing: { self?: string; peers: readonly Peer[] },
): Thread {
  const self = listing.self ?? thread.self

  return self === undefined
    ? { ...thread, peers: listing.peers }
    : { ...thread, self, peers: listing.peers }
}

/**
 * Every conversation worth a row: each peer a message went to or came from,
 * then each local session ListAgents lists that nobody talked to yet. Most
 * recent first, a message without a time counting as the oldest.
 */
export function conversationsOf(thread: Thread): Conversation[] {
  const byPeer = new Map<string, Conversation>()
  const statusOf = new Map(thread.peers.map(peer => [peer.name, peer.status]))

  for (const entry of thread.entries) {
    byPeer.set(entry.peer, {
      peer: entry.peer,
      status: statusOf.get(entry.peer),
      unread: thread.unread[entry.peer] ?? 0,
      last: entry,
    })
  }

  const active = [...byPeer.values()].sort((a, b) => (b.last?.at ?? 0) - (a.last?.at ?? 0))

  const idle = thread.peers
    .filter(peer => peer.kind === 'interactive' && !byPeer.has(peer.name))
    .map(peer => ({ peer: peer.name, status: peer.status, unread: 0 }))

  return [...active, ...idle]
}

/**
 * The messages exchanged with `peer`, oldest first.
 */
export function messagesWith(thread: Thread, peer: string | undefined): Entry[] {
  return peer === undefined ? [] : thread.entries.filter(entry => entry.peer === peer)
}

/**
 * How many messages wait unread, all conversations together.
 */
export function unreadCount(thread: Thread): number {
  return Object.values(thread.unread).reduce((sum, count) => sum + count, 0)
}

/**
 * What to keep in `$.store`.
 */
export function toSaved(thread: Thread, now: number): Saved {
  const saved = { savedAt: now, entries: [...thread.entries], aliases: { ...thread.aliases } }

  return thread.selected === undefined ? saved : { ...saved, selected: thread.selected }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isEntry(value: unknown): value is Entry {
  return (
    isRecord(value) &&
    (value.dir === 'in' || value.dir === 'out') &&
    typeof value.peer === 'string' &&
    typeof value.text === 'string' &&
    (value.at === undefined || typeof value.at === 'number')
  )
}

/**
 * The thread `$.store` kept, or undefined when the value is not one.
 */
export function fromSaved(value: unknown): Thread | undefined {
  if (!isRecord(value) || !Array.isArray(value.entries) || !isRecord(value.aliases)) {
    return undefined
  }

  const aliases = Object.fromEntries(
    Object.entries(value.aliases).filter(
      (pair): pair is [string, string] => typeof pair[1] === 'string',
    ),
  )
  const thread = { ...EMPTY, entries: value.entries.filter(isEntry), aliases }

  return typeof value.selected === 'string' ? { ...thread, selected: value.selected } : thread
}

/**
 * When a stored thread was saved, 0 when the value is not one.
 */
export function savedAtOf(value: unknown): number {
  return isRecord(value) && typeof value.savedAt === 'number' ? value.savedAt : 0
}

/**
 * The thread a session journal already holds, every message read: peer
 * deliveries (a `user` row or a `queued_command` attachment carrying an
 * `origin` of kind peer*, one per `msg_id`) and the model's SendMessage
 * calls, in order, with their times.
 *
 * ponytail: reads Claude Code's own session journal, an undocumented format
 * the plugin API does not expose (it hides peer rows from
 * `$.session.messages()`); a format change empties the rebuilt history, it
 * breaks nothing else. A refused SendMessage still shows as sent.
 */
export function fromJournal(lines: readonly string[]): Thread {
  const seen = new Set<string>()
  let thread = EMPTY

  for (const line of lines) {
    let row: unknown

    try {
      row = JSON.parse(line)
    } catch {
      continue
    }

    if (!isRecord(row)) {
      continue
    }

    const at = typeof row.timestamp === 'string' ? Date.parse(row.timestamp) : Number.NaN
    const time = Number.isNaN(at) ? {} : { at }
    const attachment = isRecord(row.attachment) ? row.attachment : {}
    const origin = isRecord(row.origin)
      ? row.origin
      : isRecord(attachment.origin)
        ? attachment.origin
        : {}
    const message = isRecord(row.message) ? row.message : {}

    if (typeof origin.kind === 'string' && origin.kind.startsWith('peer')) {
      const id = typeof origin.msg_id === 'string' ? origin.msg_id : undefined

      if (id !== undefined && seen.has(id)) {
        continue
      }

      if (id !== undefined) {
        seen.add(id)
      }

      const framed = [message.content, attachment.prompt].find(t => typeof t === 'string')
      const envelope = typeof framed === 'string' ? envelopesOf(framed)[0] : undefined
      const address = typeof origin.from === 'string' ? origin.from : envelope?.address
      const peer =
        (typeof origin.name === 'string' && origin.name) ||
        envelope?.peer ||
        nameOf(address ?? '') ||
        UNKNOWN_PEER
      const text = (typeof origin.body === 'string' ? origin.body : (envelope?.text ?? '')).trim()

      thread = record(withAlias(thread, address, peer), { dir: 'in', peer, text, ...time })
      continue
    }

    if (row.type === 'assistant' && Array.isArray(message.content)) {
      for (const block of message.content) {
        const input = isRecord(block) && isRecord(block.input) ? block.input : {}
        const isSend =
          isRecord(block) &&
          block.type === 'tool_use' &&
          block.name === 'SendMessage' &&
          typeof input.to === 'string' &&
          typeof input.message === 'string'

        if (isSend) {
          const peer = peerOf(thread, String(input.to))

          thread = record(thread, { dir: 'out', peer, text: String(input.message), ...time })
        }
      }
    }
  }

  const selected = thread.entries.at(-1)?.peer

  return selected === undefined ? thread : { ...thread, unread: {}, selected }
}
