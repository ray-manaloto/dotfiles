import type { EngineInterface, Register, Timer, ToolCallArgs, ToolCallResult, UiPane } from 'claude-code'

import * as Thread from './thread'
import * as View from './view'

export const COMMAND = 'crosstalk'
export const PANE_ID = 'crosstalk'

// How often the open pane asks ListAgents who is around.
export const REFRESH_MS = 15_000

// How long after `/crosstalk` the pane asks for the keyboard again.
export const FOCUS_RETRY_MS = 150

// How long after a view switch the pane asks for the keyboard back: the keys
// have to have fallen back to the prompt, or the ask is refused.
export const REFOCUS_MS = 400

const PEER_ORIGINS = { kind: ['peer', 'peer-send-message'] } as const

// An inbox row's key: the prefix, then the peer's name.
const ROW_PREFIX = 'open:'

// One store key a session: `thread:<session id>`.
const STORE_PREFIX = 'thread:'

// ponytail: the 50 most recent sessions' threads stay in the store, the
// rest go at a start; a size cap if a session's thread grows past use.
export const MAX_SESSIONS = 50

/**
 * The engine calls crosstalk needs after `session.start`, bound once there
 * so the pane's closures (a pick, a submit, a timer) can reach them.
 */
type Host = {
  now: () => Promise<number>
  every: (ms: number, fn: () => void) => Timer
  after: (ms: number, fn: () => void) => Timer
  invalidate: () => void
  status: (text: string | undefined) => void
  open: () => Promise<void>
  close: () => Promise<void>
  focus: (key: string) => Promise<boolean>
  panes: () => Promise<readonly UiPane[]>
  call: (args: ToolCallArgs) => Promise<ToolCallResult>
  save: (value: Thread.Saved) => Promise<void>
}

/**
 * Why a SendMessage call did not reach anyone, or undefined when it did. A
 * recipient no session answers to is `{ success: false }`, not an error.
 */
function refusalOf(result: ToolCallResult): string | undefined {
  const record: unknown = result.result
  const field = (key: string) =>
    typeof record === 'object' && record !== null ? Reflect.get(record, key) : undefined

  if (result.deny !== undefined) {
    return result.deny
  }

  if (result.isError === true || field('success') === false) {
    const reason = field('display') ?? field('message') ?? result.text

    return typeof reason === 'string' ? reason : 'refused'
  }

  return undefined
}

/**
 * The lines of this session's journal worth parsing (Thread.fromJournal):
 * found by id under the config directory's projects/, filtered by grep so a
 * long journal is never read whole into the plugin.
 */
async function journalOf($: EngineInterface, id: string): Promise<string[]> {
  const config =
    (await $.env.get('CLAUDE_CONFIG_DIR')) ?? `${(await $.env.get('HOME')) ?? ''}/.claude`
  const found = await $.process.run([
    'find',
    `${config}/projects`,
    '-maxdepth',
    '2',
    '-name',
    `${id}.jsonl`,
  ])
  const file = found.stdout.split('\n').find(Boolean)

  if (file === undefined) {
    return []
  }

  const { stdout } = await $.process.run(['grep', '-E', Thread.JOURNAL_PATTERN, file])

  return stdout.split('\n').filter(Boolean)
}

/**
 * Drops the stored threads of all but the MAX_SESSIONS most recent sessions.
 */
async function prune($: EngineInterface): Promise<void> {
  const keys = (await $.store.keys()).filter(key => key.startsWith(STORE_PREFIX))

  if (keys.length <= MAX_SESSIONS) {
    return
  }

  const dated = await Promise.all(
    keys.map(async key => ({ key, at: Thread.savedAtOf(await $.store.get(key)) })),
  )
  const oldest = dated.sort((a, b) => a.at - b.at).slice(0, keys.length - MAX_SESSIONS)

  await Promise.all(oldest.map(({ key }) => $.store.delete(key)))
}

/**
 * Registers crosstalk: `/crosstalk` toggles a pane holding this session's
 * conversations with its peers. Incoming peer deliveries (`session.receive`)
 * and outgoing SendMessage calls (`tool.call`) are recorded as they pass;
 * neither is changed. A reply typed in the pane goes out as SendMessage.
 */
export const register: Register = on => {
  let thread: Thread.Thread = Thread.EMPTY
  let host: Host | undefined
  let isOpen = false
  let refresh: Timer | undefined
  // The reply the pane is sending: recorded by send() itself, since the
  // engine may or may not run this plugin's tool.call hook for its own call.
  let replying: string | undefined
  // What the person has typed in each conversation's reply field so far.
  const drafts = new Map<string, string>()
  // How many messages the thread is scrolled back from its newest one.
  let back = 0
  // Why the last reply did not go, shown in the pane until the next one.
  let notice: string | undefined
  // The inbox, or the conversation opened from it.
  let view: 'inbox' | 'thread' = 'inbox'
  // In a conversation, vim's modes: typing a reply, or moving with keys.
  let mode: 'insert' | 'normal' = 'insert'
  // The key of our element holding the focus ring, as ui.focus last said.
  let ring: string | undefined

  /**
   * Where the ring is decides the mode: on the reply field, typing; on any
   * other element of a conversation, moving.
   */
  function onRing(key: string | undefined): void {
    ring = key

    const now = key === 'reply' ? 'insert' : 'normal'

    if (view === 'thread' && key !== undefined && now !== mode) {
      mode = now
      host?.invalidate()
    }
  }

  /**
   * Moves the ring to `key`. Seen live: the engine raises no ui.focus to the
   * plugin for its own move, so the ring is noted here.
   */
  function focus(key: string): void {
    void host?.focus(key).then(isMoved => {
      if (isMoved) onRing(key)
    })
  }

  /**
   * Whether `peer`'s conversation is on screen: its messages arrive read.
   */
  function isReading(peer: string): boolean {
    return isOpen && view === 'thread' && thread.selected === peer
  }

  /**
   * Gives `key` the keyboard once the view that draws it is drawn. Seen live:
   * the element that held it (a row, ‹) is gone with the old view, and the
   * keys fall back to the prompt; the pane asks for them again, as on open.
   */
  function refocus(key: string): void {
    host?.after(REFOCUS_MS, () => {
      void host
        ?.open()
        .then(() => focus(key))
        .catch(() => undefined)
    })
  }

  /**
   * The inbox rows' keys, top to bottom.
   */
  function rowsOf(): string[] {
    return Thread.conversationsOf(thread).map(c => `${ROW_PREFIX}${c.peer}`)
  }

  /**
   * The element the ring starts on when the pane takes the keyboard: the
   * inbox row last opened, the reply field, or ‹ in normal mode.
   */
  function homeOf(): string {
    if (view === 'thread') {
      return mode === 'insert' ? 'reply' : 'back'
    }

    const peers = Thread.conversationsOf(thread).map(c => c.peer)
    const peer = peers.includes(thread.selected ?? '') ? thread.selected : peers[0]

    return `open:${peer ?? ''}`
  }

  function openThread(peer: string): void {
    thread = Thread.select(thread, peer)
    view = 'thread'
    mode = 'insert'
    back = 0
    notice = undefined
    redraw()
    refocus('reply')
  }

  function openInbox(): void {
    const from = thread.selected

    view = 'inbox'
    back = 0
    redraw()
    refocus(from === undefined ? 'reply' : `open:${from}`)
  }

  /**
   * The thread with a new message in it: drawn, and saved for the next start.
   */
  async function commit(next: Thread.Thread): Promise<void> {
    thread = next
    redraw()
    await host
      ?.now()
      .then(now => host?.save(Thread.toSaved(thread, now)))
      .catch(() => undefined)
  }

  /**
   * Scrolls the selected thread `by` messages back (negative: forward),
   * within its messages.
   */
  function scrollBack(by: number): void {
    const count = Thread.messagesWith(thread, thread.selected).length

    back = Math.min(Math.max(0, back + by), Math.max(0, count - 1))
    host?.invalidate()
  }

  /**
   * Keeps the reader where they are when a message lands in the conversation
   * they have scrolled back in.
   */
  function holdPlace(peer: string): void {
    if (back > 0 && peer === thread.selected) {
      back += 1
    }
  }

  function redraw(): void {
    const unread = Thread.unreadCount(thread)

    host?.invalidate()
    host?.status(unread > 0 && !isOpen ? `crosstalk · ${unread} unread` : undefined)
  }

  async function refreshPeers(): Promise<void> {
    const result = await host?.call({ tool: 'ListAgents' }).catch(() => undefined)
    const record: unknown = result?.result
    const listing = typeof record === 'object' && record ? Reflect.get(record, 'listing') : undefined

    if (typeof listing === 'string') {
      thread = Thread.withListing(thread, Thread.listingOf(listing))
      redraw()
    }
  }

  async function send(text: string): Promise<void> {
    const to = thread.selected
    const message = text.trim()

    if (!host || to === undefined || message === '') {
      return
    }

    replying = message

    const result = await host
      .call({ tool: 'SendMessage', to: Thread.addressOf(thread, to), message, summary: 'crosstalk reply' })
      .catch((error: unknown) => ({ deny: String(error), isError: undefined }))
      .finally(() => {
        replying = undefined
      })
    const refusal = refusalOf(result)

    if (refusal !== undefined) {
      // The open pane holds toasts back: the reason goes in the pane.
      notice = `not sent: ${refusal}`
      host.invalidate()

      return
    }

    back = 0
    await commit(Thread.record(thread, { dir: 'out', peer: to, text: message, at: await host.now() }))
  }

  on('session.start', async ($, e, next) => {
    const id = await $.session.id()
    const key = `${STORE_PREFIX}${id}`

    host = {
      now: () => $.clock.now(),
      every: (ms, fn) => $.clock.every(ms, fn),
      after: (ms, fn) => $.clock.after(ms, fn),
      invalidate: () => $.ui.invalidate('ui.render'),
      status: text => $.ui.status(text),
      open: () =>
        $.ui.open({
          id: PANE_ID,
          title: 'crosstalk',
          focus: true,
          closeOnEscape: true,
          holdToasts: true,
          rows: 20,
          columns: 64,
        }),
      close: () => $.ui.close({ id: PANE_ID }),
      focus: key =>
        $.ui.focus({ requestId: PANE_ID, key }).then(
          result => result.deny === undefined,
          () => false,
        ),
      panes: () => $.ui.panes(),
      call: args => $.tool.call(args),
      save: value => $.store.set(key, value),
    }

    await $.command.register({
      name: COMMAND,
      description: 'Chat with your other Claude Code sessions',
      immediate: true,
    })

    // What this session said before this module ran: its stored thread
    // (a reload, a restart, a --resume), else, on its first start, what its
    // journal holds from before crosstalk was loaded.
    if (thread.entries.length === 0) {
      const saved = Thread.fromSaved(await $.store.get(key).catch(() => undefined))
      const history = saved ?? Thread.fromJournal(await journalOf($, id).catch(() => []))

      thread = Thread.withListing(history, thread)

      if (saved === undefined && history.entries.length > 0) {
        await commit(thread)
      }

      redraw()
    }

    await prune($).catch(() => undefined)

    // A reload (a module edit, a worker respawn) finds its pane still up.
    if ((await host.panes()).some(pane => pane.id === PANE_ID)) {
      isOpen = true
      await refreshPeers()
      refresh ??= host.every(REFRESH_MS, () => void refreshPeers())
    }

    return next(e)
  })

  on('session.receive', { origin: PEER_ORIGINS }, async ($, e, next) => {
    const { peer, text, address } = Thread.inboundOf(e.text)
    const known = Thread.withAlias(thread, address, peer)

    holdPlace(peer)
    await commit(Thread.record(known, { dir: 'in', peer, text, at: await $.clock.now() }, isReading(peer)))

    return next(e)
  })

  on('tool.call', { tool: 'SendMessage' }, async ($, e, next) => {
    const result = await next(e)
    const isSent = refusalOf(result) === undefined && e.message !== replying

    if (isSent && e.tool === 'SendMessage' && typeof e.to === 'string' && typeof e.message === 'string') {
      holdPlace(Thread.peerOf(thread, e.to))
      await commit(
        Thread.record(thread, {
          dir: 'out',
          peer: Thread.peerOf(thread, e.to),
          text: e.message,
          at: await $.clock.now(),
        }),
      )
    }

    return result
  })

  on('command.run', { command: COMMAND }, async ($, e, next) => {
    if (!host) {
      return next(e)
    }

    if (isOpen) {
      await host.close()

      return { text: 'crosstalk closed' }
    }

    await host.open()
    isOpen = true
    view = 'inbox'
    back = 0

    // Focus is granted over an empty composer only, and while this command
    // runs the composer still holds `/crosstalk`: ask again once it cleared.
    // Seen live: without this second open, the pane never takes the keys.
    host.after(FOCUS_RETRY_MS, () => void host?.open().catch(() => undefined))

    await refreshPeers()
    refresh ??= host.every(REFRESH_MS, () => void refreshPeers())
    redraw()

    const pane = (await host.panes()).find(p => p.id === PANE_ID)

    return pane?.isPlaced === false
      ? { text: 'crosstalk is open: widen the terminal to 110 columns to see it' }
      : {}
  })

  on('ui.close', { id: PANE_ID }, async ($, e, next) => {
    // The person's esc in a conversation leaves the reply field for normal
    // mode, then goes back to the inbox, as vim and a messaging app would;
    // /crosstalk and q (the plugin's close) still close.
    if (e.origin.kind === 'person' && view === 'thread') {
      if (mode === 'insert') {
        mode = 'normal'
        host?.invalidate()
        refocus('back')

        return { deny: 'normal mode' }
      }

      openInbox()

      return { deny: 'back to the inbox' }
    }

    const result = await next(e)

    if (result.deny === undefined) {
      isOpen = false
      refresh?.cancel()
      refresh = undefined
      redraw()
    }

    return result
  })

  // The person's moves (Tab, arrows, a click) and the engine's (autoFocus).
  on('ui.focus', async ($, e, next) => {
    const result = await next(e)

    if (e.requestId === PANE_ID && result.deny === undefined) {
      onRing(e.element)
    }

    return result
  })

  // The wheel and the scroll keys move the thread, not the pane: the
  // header and the reply field stay put.
  on('ui.scroll', { requestId: PANE_ID }, ($, e, next) => {
    // The inbox scrolls as a pane does; a conversation moves its thread.
    if (e.origin.kind !== 'person' || view !== 'thread') {
      return next(e)
    }

    scrollBack(-Math.sign(e.by) * Math.max(1, Math.round(Math.abs(e.by) / 3)))

    return {}
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE_ID || (e.surface !== 'terminal' && e.surface !== 'desktop')) {
      return next(e)
    }

    const { Box, Text, Button, Input, Markdown } = await $.ui.resolve(e)

    return View.paneView(
      {
        ui: { Box, Text, Button, Input, Markdown },
        // A column for the left margin, three for the pane's close mark.
        columns: Math.max(16, e.props.bodyColumns - 4),
        rows: e.props.scroll.bodyRows,
        isFocused: e.props.isFocused,
        back,
        draft: drafts.get(thread.selected ?? '') ?? '',
        view,
        mode,
        onOpen: peer => openThread(peer),
        onInbox: () => openInbox(),
        home: homeOf(),
        onMove: delta => {
          const row = View.rowAfter(rowsOf(), ring, delta)

          if (row !== undefined) focus(row)
        },
        onOpenHere: () => {
          const row = View.rowAfter(rowsOf(), ring, 0)

          if (row !== undefined) openThread(row.slice(ROW_PREFIX.length))
        },
        onTop: () => {
          const row = rowsOf()[0]

          if (row !== undefined) focus(row)
        },
        onInsert: () => {
          mode = 'insert'
          host?.invalidate()
          focus('reply')
        },
        onClose: () => void host?.close().catch(() => undefined),
        onBack: by => scrollBack(by),
        onInput: text => {
          drafts.set(thread.selected ?? '', text)
          host?.invalidate()
        },
        notice,
        onSubmit: text => {
          drafts.delete(thread.selected ?? '')
          notice = undefined
          void send(text)
        },
      },
      thread,
    )
  })
}
