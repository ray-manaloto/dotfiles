url: https://code.claude.com/docs/en/changelog.md
fetched-at: 2026-09-09T18:29:20Z
http-status: 200
note: keep only sections newer than 2.1.257

<Update label="2.1.266" description="September 8, 2026">
  * Fixed a 2.1.265 regression affecting LLM-gateway and proxy setups: the undocumented `CLAUDE_CODE_USE_GATEWAY` environment variable, previously ignored unless `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` were both set, began forcing Cloud-gateway sign-in on its own in 2.1.265, so configurations that set it alongside an API key, `apiKeyHelper`, or custom auth headers failed every request with "Not signed in to the Cloud gateway". The variable on its own is ignored again; no configuration change is needed
</Update>

<Update label="2.1.265" description="September 8, 2026">
  * Added `user.email` and `user.groups` to the telemetry Claude Desktop and Cowork send through a Claude apps gateway, matching terminal sessions
  * Added support for pointing `--plugin-dir` at a folder of plugins: each child folder with a manifest loads, and children added or removed while running are picked up
  * Added a 1 GB cap on tool results saved to disk; the in-conversation preview says when a saved file was truncated
  * Fixed resuming a foreground-spawned subagent changing its tool list and system prompt prefix, which broke prompt-cache reuse for that agent
  * Fixed agent teammates and resumed subagents moving SubagentStart hook context and preloaded skills out of the prompt prefix on later turns, which broke prompt-cache reuse
  * Fixed resume after the previous process died while a tool was running: the last prompt is no longer rewritten, and the interrupted tool call is kept and marked interrupted
  * Fixed `/model opusplan[1m]` being rejected with "Model not found"
  * Fixed syntax-highlighted code in permission prompts and messages sometimes omitting a character after a Ruby `?`, Erlang `$`, or Perl `$` sigil
  * Fixed the fullscreen transcript jumping by one row whenever the slash-command or @-file suggestion list opened or closed
  * Fixed a plugin path containing a backslash bypassing the symlink containment check on macOS and Linux
  * Fixed plugin directories whose names begin with two dots being wrongly refused as outside the plugin root
  * Fixed VS Code and SDK sessions occasionally requiring re-login when a session was closed while refreshing its token
  * Fixed Remote Control sessions sending the end-of-turn signal before the reply's last message, which could show a reply as finished in the Claude app before its last part arrived
  * Fixed background (`--bg`) sessions occasionally being retired mid-turn when a message arrived just before the idle timeout
  * Fixed Claude Code's own git status and diff probes running clean filters configured by a nested repository inside the working tree
  * Fixed the advisor tool and its instructions being re-decided per request from the request's model; the decision is now made once and announced in the conversation when it changes
  * Fixed artifact publish accepting connector tool names the connector doesn't expose; the publish is now refused when none of the declared tools exist, and warned when only some don't
  * Fixed `/add-dir <subdirectory>` refusing to load a subdirectory's agents when managed settings lock only skills to plugins, and promising agents when only agents are locked
  * Fixed two-key keyboard shortcuts cancelling silently when the second key arrived more than a second later, as happens inside tmux; they now wait 3 seconds and show a notice when they time out
  * Fixed forked skills (`context: fork`) not streaming their kickoff prompt and, with `--forward-subagent-text`, their text turns as progress events in stream-json
  * Fixed a plugin's default component folder that the OS cannot check, such as a symlink loop, being silently skipped; it is now reported in `/plugin` with the error code
  * Fixed the Claude apps gateway's OTLP telemetry relay pausing all forwarding to a collector for 30 seconds after it rejected a few payloads as malformed or too large
  * Fixed `/plugin` Discover/Browse and `claude plugin list --json --available` showing no description or display name for marketplace plugins whose metadata lives only in their `plugin.json`
  * Fixed `/login` showing "no gateway URL is configured" when re-run in a session that signed in to a Claude apps gateway set by managed settings
  * Fixed `/model` claiming a model was "saved as your default" when the settings file couldn't be written; it now says the save failed and why
  * Fixed `/clear` from Remote Control waiting on SessionStart hooks and on open terminal dialogs before completing
  * Fixed the `/config` dialog changing height when switching between its tabs
  * Fixed resuming a workflow run after its container restarted; a resume whose run journal is missing now fails with a clear error instead of rerunning every agent
  * Fixed the `claude-api` skill's error-code reference: model access failures return 404 and unavailable beta headers return 400, not 403
  * Fixed non-interactive sessions (`-p` with stream-json input, Agent SDK, cloud sessions) resetting the shell working directory at each new user message; a `cd` now persists across turns
  * Fixed MCP servers configured as `http` that only speak the legacy HTTP+SSE transport never connecting; Claude Code now falls back to SSE as the MCP spec describes
  * Fixed some claude.ai connectors in cloud sessions showing as needing authentication even though they are connected in claude.ai (servers that answer an unsupported request with HTTP 401)
  * Fixed remote sessions keeping their sandbox container alive while a connector approval or sign-in link waits for you
  * Fixed resumed sessions showing long model-facing recovery instructions in "background task didn't finish" notices instead of a short status line
  * Windows: Fixed Read, Write and Edit refusing every file ("symlink resolution changed after permission was checked") when running inside an AppContainer or restricted-token sandbox
  * Improved `--worktree` startup on large repositories: the new worktree is now checked out in parallel (git 2.32+)
  * Improved `/workflows` agent detail: tool calls are marked running, failed or done, the subagent's task list is shown when it has one, and Enter unfolds the listed calls with their inputs and results
  * Improved slash commands typed mid-prompt: matches now show in a list (Tab opens it outside fullscreen) instead of a single suggestion, and a plugin skill is now found by its bare name
  * Improved remote MCP servers that need sign-in: Claude Code no longer registers an OAuth client with them until you actually authenticate
  * Improved the time to resume long sessions that read many files
  * Improved the error shown when an image over the size limits cannot be decoded: it now names the cause and how to fix it instead of only citing the limit
  * Improved the Artifact tool's read of an artifact someone else wrote: the summary now treats the page as untrusted content and flags embedded instructions rather than relaying them
  * Updated the `.claude` folder permission option to say what it actually allows: editing files in the project's `.claude` folder (or `~/.claude`) for the session
  * Changed machines with `forceLoginGatewayUrl` in managed settings to be Claude apps gateway sessions from startup, like `forceLoginMethod: "gateway"`; a leftover claude.ai login or API key is not used
  * Changed image processing to use the runtime's built-in image support; the CLI no longer extracts a native image module to the temp directory
  * Changed plugin display metadata to prefer the marketplace entry over `plugin.json` on the Installed tab and `claude plugin details`, filling gaps from `plugin.json`
  * Changed Claude apps gateway sessions to export OpenTelemetry directly to a collector the gateway's managed settings name in `OTEL_EXPORTER_OTLP_ENDPOINT`, instead of through the gateway's relay; sessions without a named collector still use the relay
  * \[VSCode] Added automatic archiving of sessions inactive for a set period (new "Archive inactive sessions" setting, default 14 days)
  * \[VSCode] Fixed the sidebar chat coming back blank after Reload Window or a restart when the conversation had been open for more than 10 minutes
  * \[VSCode] Fixed the timeline dot sitting below the text on the "Remote Control is active" message
</Update>

<Update label="2.1.263" description="September 6, 2026">
  * Bug fixes and reliability improvements
</Update>

<Update label="2.1.261" description="September 4, 2026">
  * Added an "Organization policy" line to `/status` and `claude doctor` that says why your organization's policy could not be loaded, such as a proxy not passing the endpoint through
  * Added `bashOutputMaxChars` and `taskOutputMaxChars` settings to raise how much command and background-task output Claude receives inline before it is saved to a file, up to 128K characters
  * Added `--append-subagent-system-prompt-file` to read the subagent system prompt from a file, for prompts too large to pass on the command line
  * Added `/skill-doctor` to show which loaded skills go unused and what they cost in context, so you can prune them
  * Fixed typed or pasted characters occasionally landing out of order or being dropped during fast input or key repeat
  * Fixed `/add-dir <subdirectory>` printing a false "couldn't be resolved" error when the working directory is on a `/net` automount
  * Fixed the Bedrock setup wizard hanging when AWS or an AWS credential helper never responds (it now times out with a clear error), and its model checks failing behind a TLS-inspecting proxy
  * Fixed cloud sessions discarding a plugin synced from claude.ai when managed settings force-enable it in `enabledPlugins`, then falling back to a marketplace clone that could fail
  * Fixed being unable to delete the character immediately before an inline `[Image #N]` chip in the prompt input
  * Fixed resuming a session losing hook output and other context around parallel tool calls, which changed the resumed request
  * Fixed Remote Control showing a stale permission mode when a phone, browser, or claude.ai app attaches to a terminal session or after the mode changes in the terminal
  * Fixed Remote Control sessions showing as still working (stuck spinner and Stop button) after stopping a turn from a connected phone or browser, or after a local slash command like `/clear`
  * Fixed SDK and cloud sessions ignoring a Stop or interrupt sent just after the first prompt, before the turn had started; the turn now stops instead of running to completion
  * Fixed Remote Control uploading a session pulled with `/teleport` into the connected session, which appeared appended to the original on phone and web
  * Fixed Remote Control's inbound event stream failing behind TLS-inspecting corporate proxies on native Windows
  * Fixed Remote Control sessions showing the default effort level on claude.ai when the effort comes from settings
  * Fixed `gcpAuthRefresh` opening a browser at startup when the Google credential check was slow, even though the credential was still valid
  * Fixed claude.ai connectors staying absent for the whole session when the startup connector fetch timed out — the CLI now retries in the background
  * Fixed sustained high CPU usage when a background agent could not be resumed and its wake-up was retried in a tight loop
  * Fixed feature flags gated to a newer version occasionally applying to an older Claude Code version running on the same machine
  * Fixed `/usage` and the VS Code usage panel dropping a model-specific weekly limit row when the usage endpoint is rate limited or when opened right after startup
  * Fixed `claude -p --resume <file>` adopting a malformed session ID recorded in the transcript; it now resumes under a fresh session ID instead
  * Fixed the terminal progress indicator (iTerm2, Ghostty, ConEmu) showing the session as finished while a background workflow or agent was still running
  * Fixed a rare layout glitch where a box could render with the wrong height after its container switched between row and column direction
  * Fixed Claude apps gateway client IP when a trusted proxy appends a port to `X-Forwarded-For`; with an access list set, an unreadable entry now gets 403
  * Fixed Claude apps gateway telling Claude Desktop to export OpenTelemetry as JSON even when the terminal CLI uses protobuf, so protobuf-only collectors rejected Desktop's data
  * Fixed Desktop and web showing a session as busy while it only watches an artifact for updates
  * Fixed Claude in Chrome `file_upload` failing with "paths: expected array, received undefined" in local Cowork sessions run from the Claude Desktop app
  * Fixed `SendMessage` to an offline Remote Control session on another machine reading as delivered; the result now says delivery is queued until that machine reconnects
  * Fixed plugin install hints from CLIs run in background Bash commands: they are now detected, and the raw `<claude-code-hint>` tag no longer leaks into the conversation
  * Fixed in-process agent-team teammates re-sending their first-turn tool and skill announcements on the second turn, which changed the request prefix and missed the prompt cache
  * Improved the `/model` picker and the VS Code model pill to show a model's name instead of its raw Bedrock, Vertex AI, or LLM gateway ID when Claude Code recognizes it
  * Improved startup on Google Vertex AI when `GOOGLE_APPLICATION_CREDENTIALS` is set: API client creation no longer re-runs Google Cloud project discovery or spawns extra `gcloud` processes
  * Improved streaming performance: already-rendered blocks are no longer re-checked by layout on each update
  * Improved the dangerous-`rm` safety prompt to also catch `rm -rf` on positional parameters and inside double-quoted `sh -c` scripts
  * Improved handling when the API sends no response headers: the retry now waits up to `API_TIMEOUT_MS` (10 minutes by default) instead of another 3 minutes, and the messages say what to change
  * Changed a Claude apps gateway 403 on the managed settings load (at startup or after `/login`) to say Claude Code may not be enabled for the organization, instead of advising a new sign-in
  * Changed machines whose managed settings pin `forceLoginMethod: "gateway"` to ignore a leftover API key or claude.ai login and ask for `/login`; Bedrock, Vertex AI, and Foundry sessions are unaffected
  * Changed auto mode to treat a link that packs content into a public diagram renderer's URL as an upload to that site: no longer auto-approved unless you asked for it
  * Changed the prompt's word-editing keys to match Bash: Ctrl+W deletes back to whitespace, Alt+F and Alt+D stop at word end, punctuation separates words; `keybindingFlavor` no longer has any effect
  * Changed `/context` token counting to use a local estimate when the token-counting API is unavailable, instead of extra small-model requests
  * \[VSCode] Added a "Build a custom style" walkthrough to the Output styles menu that writes a custom output style file and lists it right away
  * \[VSCode] Added an Add server form and a Remove action to the MCP servers dialog, so MCP servers can be added and removed without leaving the IDE
  * \[VSCode] Added a hollow ring in the session list for sessions open in a terminal, another VS Code window, or Claude Desktop, so they no longer look closed
  * \[VSCode] Added a fold button to permission and question prompts so the conversation behind them can be read without dismissing them; the space beside the prompt now scrolls the conversation
  * \[VSCode] Added "Archive session" to the session list's right-click menu and gave Unarchive its own icon
  * \[VSCode] Fixed a session teleported from Claude Code on the web treating a question that was cut off when the cloud session shut down as declined
  * \[VSCode] Fixed the session tab's Rename box opening empty for a tab restored with the window; it now starts with the current name
  * \[VSCode] Fixed collapsed sections in the session list panel briefly showing expanded each time the panel loaded
  * \[VSCode] Fixed Focus view showing a tool call as still running after Claude had moved on, such as while a question waited for your answer
  * \[VSCode] Fixed the session list's active-row highlight going stale when an unfocused Claude tab's session ID is corrected
  * \[VSCode] Fixed Cmd/Ctrl+Shift+T reopen and deep-link opens placing the Claude tab outside the Claude editor group when a Claude tab has focus
  * \[VSCode] Fixed the session tab's "Add to group" putting a session opened from Claude Code on the Web in two groups; it now moves the entry the session list shows
  * \[VSCode] Fixed the model picker showing models an organization has since disabled until the window was reloaded twice
  * \[VSCode] Fixed a tab opened from the session list jumping back to that session, and a tab opened from a Web session restarting its teleport or staying empty, after VS Code reloads the tab's view
  * \[VSCode] Fixed `/btw` side-question history from earlier sessions being overwritten when a question is asked right after a window reload or while a settings file has errors
  * \[VSCode] Fixed the pending question card not reappearing after the Claude panel reloads when signed in with a Claude.ai or Console account
  * \[VSCode] Fixed claude.ai-only features staying visible in a window's other Claude panels after one panel picked up a third-party provider from a settings file
  * \[VSCode] Fixed the sign-in screen appearing despite the Disable Login Prompt setting when Claude Code reports no login or a request fails for lack of one
  * \[VSCode] Fixed the next queued permission prompt keeping text typed on the previous prompt and accepting an immediate second click
  * \[VSCode] Fixed install-plugin links opening the Claude sidebar without the install dialog in a window where only the session list had been shown
  * \[VSCode] Fixed the sidebar usage meter staying empty on a new window until the Account & usage dialog was opened, and a 0% usage limit being left out of the meter
  * \[VSCode] Fixed "Start new session in this group" losing the group after New conversation, and a missing unread dot for a session that finished before the sidebar's unread list loaded
  * \[VSCode] Fixed the editor tab badge showing unread during a running turn or missing on a tab opened from the session list, and "Add Session Tab to Group" doing nothing for an archived session
  * \[VSCode] Fixed "Enable Remote Control for all sessions" so flipping it also applies right away to sessions open in other VS Code windows
  * \[VSCode] Fixed the session list's Open filter for sessions continued from claude.ai whose tab was still recorded under the web session, and labeled the filter menu's sections for screen readers
  * \[VSCode] Changed the model picker to one flat list of every model, with rows kept for older model spellings listed last
</Update>

<Update label="2.1.260" description="September 3, 2026">
  * Added a diff panel that opens beside the conversation in fullscreen mode and shows your uncommitted changes as Claude edits; toggle it with `/diff`
  * Added a likely cause for prompt-cache misses (e.g. tool definitions or system prompt changed, idle past the TTL) to `/cost` and the status line's `prompt_cache` field
  * Added `/reload-plugins` to headless sessions, so it appears in the Claude Code Desktop and SDK command lists
  * Added a text form of `/advisor` (`/advisor`, `/advisor <model>`, `/advisor off`) for the desktop app, Remote Control, and other headless (`-p`/Agent SDK) sessions
  * Added `oidc.scope_on_refresh` to the Claude apps gateway for IdPs that return an id\_token on refresh only when asked for `openid` again
  * Added Claude apps gateway support for newer Claude Desktop keys in `desktop` policy blocks, including `userPluginMarketplacesEnabled` and `userPluginUploadsEnabled`
  * Fixed `Edit`/`Write`/`Read` permission rules whose path contains parentheses being dropped as invalid or ignored by the Bash sandbox, which left "read-only" folders writable
  * Fixed one file permission rule with an uncompilable pattern (e.g. an unclosed `[`) making every file edit fail with `Invalid regular expression`; such a deny rule now guards the literal path it spells
  * Fixed Bash permission checks auto-approving zsh commands that hide a command substitution in a REPORTTIME, REPORTMEMORY or DIRSTACKSIZE assignment; these now prompt for approval
  * Fixed Bedrock model discovery, token counting and AWS SSO/STS credential calls failing with "unable to get local issuer certificate" when the corporate root CA is only in the OS certificate store
  * Fixed `permissions.blockReadsOutsideWorkingDirectories` on macOS hiding the user's git config from sandboxed git and hiding a worktree-isolated sub-agent's own checkout
  * Fixed managed settings not loading for claude.ai Enterprise/Team users who also had a leftover API key from an earlier `/login`
  * Fixed `/status` listing a signed-in claude.ai account and a configured API key as if both were in effect; the credential not in use is now marked
  * Fixed managed `skillOverrides` entries keyed on a bundled skill's alias (e.g. `checkup` for `/doctor`) not applying, and `Skill(name)` deny rules not covering a nested skill listed as `<dir>:name`
  * Fixed `model: fable` agents ignoring the `[1m]` tag on an `ANTHROPIC_DEFAULT_FABLE_MODEL` pin and silently running with a 200K context window
  * Fixed the `/model` picker not showing Fable 5.1 for organizations that can use it, which was only accepted when typed as `/model claude-fable-5-1`
  * Fixed prompt caching on Claude Fable 5.1 not covering the context attached after tool results, so it was re-sent as uncached input on every tool-call turn
  * Fixed model switching staying blocked for the rest of the session after a plugin hook load failure; each switch now re-checks and the refusal names the cause
  * Fixed model switching being blocked for the session when an organization-managed plugin's marketplace could not be loaded
  * Fixed SDK-provided MCP servers (e.g. Desktop connectors) sometimes missing from the first turn and only appearing on the next one
  * Fixed Claude in Chrome tools failing with "Not connected" mid-task in cloud-hosted claude.ai sessions when a connector was added or removed
  * Fixed flags, joined emoji and accented letters splitting across wrapped lines, and stale text staying on screen when a flag or joined emoji falls in the terminal's last two columns (now shown as `…`)
  * Fixed Remote Control accepting a model pick that is not a valid model name; it is now refused with an error instead of failing on the next message
  * Fixed `/rewind` and `--rewind-files` reporting success when checkpoint backup files were missing and nothing was actually restored
  * Fixed `/rewind` leaving stale file-read tracking from the rewound-away turns, which caused "File unchanged since last read" stubs and full-file re-injection after external edits
  * Fixed `-p --resume`/`--continue` (as used by the desktop app) failing on every retry once a session's worktree directory lost its git metadata; it now fails once, then resumes without the worktree
  * Fixed a subagent that resumed another agent via SendMessage never being woken by that agent's completion (the notification went to the main conversation instead)
  * Fixed agent teams: an in-process teammate's transcript losing messages, or going blank, during long API retry waits (e.g. under `CLAUDE_CODE_RETRY_WATCHDOG`) as retry notices evicted real messages
  * Fixed a session that moved to the background appearing twice in ListAgents (once as a phantom "interactive" twin with the same name) and receiving SendMessage deliveries in the viewer
  * Fixed intermittent "task output swap refused" errors when many sessions share a project directory
  * Fixed Ctrl+Z in fullscreen leaving the shell on the alternate screen, drawn over the paused interface
  * Fixed Workflow tool subagents being restarted as stalled while a long context compaction was still in progress
  * Fixed plugins from a URL marketplace failing to install with "marketplace entry path does not stay inside the marketplace directory" when a host app (e.g. Claude Desktop) stores it as a directory
  * Fixed an extra browser tab opening when an artifact is published in a session you're driving from claude.ai, the desktop app, or mobile (Remote Control)
  * Fixed the Artifact tool's first call failing with an "Invalid tool parameters" validation error in some Cowork sessions
  * Fixed IDE line selections being dropped when running a skill or slash command (the "N lines selected" context now reaches Claude)
  * Fixed repository detection for GitLab projects in nested subgroups (e.g. `gitlab.com/group/subgroup/project`)
  * Fixed `owner/repo#123` issue references in rendered output linking to github.com when working in a GitLab repository; they now link to the gitlab.com issue
  * Glob/Grep: Fixed the search path being probed on disk before the permission check; a missing path is now reported after permission is decided, as Read does
  * Reverted the 2.1.259 change applying `Read()` deny rules to Bash arguments; it denied `npm run build` under a `Read(./**/build/**)` rule in every mode and made `cd … && grep` prompt even in auto mode
  * Improved structured output: Workflow `agent({schema})` rejects a JSON Schema that can never be satisfied up front, and retry-cap errors now include the last validation failure
  * Improved deleting a background session whose worktree has unpushed commits: the message now names the branch and commit count, and deleting again discards the worktree
  * Improved the Claude apps gateway's refresh-failure log to name the step that failed
  * Improved idle CPU usage of non-interactive (`-p` / SDK) sessions
  * Improved the Claude apps gateway on Amazon Bedrock: input tokens for an aborted request are now counted with AWS's free CountTokens API (grant `bedrock:CountTokens`) instead of a one-token request
  * Improved the settings error for rules such as `Edit(C:\dir\(name)\**)`, where `\(` is read as an escaped parenthesis rather than a path separator, to suggest an unambiguous spelling
  * Improved auto-compact for 1M-context models: Opus and Fable sessions now compact shortly before the 1M-token limit, and recovery compaction on very large contexts no longer times out at 10 minutes
  * Improved `/ultrareview` and `claude ultrareview` to wait up to 45 minutes (previously 30) for long-running cloud reviews
  * Improved `/effort` on Claude Fable 5.1 so changing effort mid-session no longer invalidates the prompt cache
  * Updated the bundled `claude-api` skill so its Go, Java, and C# samples use current-generation model IDs, and clarified that cheaper worker or sub-agent models should be current-generation too
  * Changed `ctrl+l` / `cmd+k` in fullscreen mode to clear the transcript view like a terminal `clear`; scroll up to see earlier messages
  * Changed permission rules with text after the closing parenthesis (e.g. `Bash(ls) x`), which never matched anything, to be reported as invalid settings instead of being silently ignored
  * Changed server-managed settings so a managed CLAUDE.md (`claudeMd`) no longer triggers the security approval dialog; hooks, shell-command, sandbox, and unsafe `env` settings still require approval
  * Changed Claude in Chrome to follow your organization's Claude in Chrome admin setting; when an admin turns it off, `--chrome`, `/chrome` and the browser tools are unavailable
  * Changed Claude apps gateway to send `orgPluginSettings` in the list form read by Claude Desktop 1.15200.0 and later; older desktops ignore it
  * Changed Claude apps gateway to also refuse to start, naming the field, when a `desktop` policy misspells a field in a nested object of a `managedMcpServers` or `orgPluginSettings` entry
  * Changed commands typed at the `!` bash-mode prompt to run outside the sandbox even when strict sandbox mode (`sandbox.allowUnsandboxedCommands: false`) is on, like typing into your own terminal
  * Changed self-hosted runner `--kill-session-after-min` to release a session that is only waiting on its user (paused, resumable on the next message) instead of killing it and reporting a failure
  * Removed the one-hour time limit on background commands started by subagents; they now run until they exit or are stopped, matching the main session
  * \[VSCode] Added the selected effort level to the footer model pill, fixed a stale effort level after switching models, and returned the footer pills to their earlier compact size
  * \[VSCode] Added Open and Closed to the session list's status filter menu
  * \[VSCode] Fixed the welcome screen disappearing in a new session when Remote Control turns on automatically
  * \[VSCode] Fixed the session history picker loading a session a second time when it is already open in another tab; it now switches to that tab
  * \[VSCode] Fixed the session tab's Rename command silently doing nothing while the tab's view was reloading; it now always applies
  * \[VSCode] Fixed a half-finished message, an empty tool card or an extra "Thought for" line staying on screen after Claude Code retried a dropped response
  * \[VSCode] Fixed "Enable Remote Control for all sessions" not applying to a session tab that was still starting when the toggle was flipped
</Update>

<Update label="2.1.259" description="September 2, 2026">
  * Added `managedMcpServers` managed setting: organizations can provide HTTP/SSE MCP servers to every user (same entry shape as `.mcp.json`); entries that name a command to run are skipped
  * Added `--permission-prompts none` for unattended headless hosts: anything that would prompt is denied automatically while the active permission mode (including auto mode) keeps deciding
  * Added recognition of `glab mr create/merge/close/reopen/note/update` so GitLab merge requests show as `MR !N` in the collapsed tool summary and refresh the footer MR badge
  * Added `--json` to `claude plugin validate` for a machine-readable validation report
  * Fixed concurrent sessions silently reverting each other's `~/.claude.json` changes — workspace trust no longer resets and MCP/project state is no longer lost when running many sessions at once
  * Fixed a conversation whose thinking was rejected once being rejected again on every later turn
  * Fixed Bash `Read()` deny rules not covering files given as option values (`--ignore-revs-file=.env`, `-f.env`, `@file`), `git diff`/`git grep` file operands, or `cd DIR && cat FILE` compounds; `grep -r`/`cp -r` over a directory holding a denied file now asks
  * Fixed the prompt cache being invalidated when the OAuth token refreshed in sessions with telemetry disabled
  * Fixed fullscreen mode showing a blank conversation after a long turn with hundreds of tool calls
  * Fixed auto mode running a turn on a model it doesn't support when a command or skill's frontmatter `model:` named one; the turn now keeps the session model
  * Fixed `CLAUDE_CODE_MAX_CONTEXT_TOKENS` being ignored for Vertex-style model IDs (`@YYYYMMDD` suffix) of model versions Claude Code doesn't recognize
  * Fixed the live output preview of a running shell command hiding its newest lines when an earlier line wrapped
  * Fixed a background GitHub connection check that ran on every launch for claude.ai users; the result is now remembered across launches
  * Fixed `--resume` failing (and `--continue` opening an empty conversation) when a saved session contains an attachment entry with no payload
  * Fixed frontmatter `model:` on custom commands and skills being ignored in interactive sessions
  * Fixed Artifact publishing failing once with an "unexpected parameter `note`" error in conversations continued from an older version
  * Fixed managed `forceRemoteSettingsRefresh` being ignored at startup when a policy helper configured by MDM or the managed settings file had already run
  * Fixed worktree isolation refusing hook-created worktrees on machines where `git rev-parse` fails with a message other than "not a git repository"
  * Fixed OpenTelemetry metrics and events from cloud sessions missing the `user.email`, `organization.id`, and `user.account_uuid` attributes
  * Fixed MCP servers that disconnect while their tools are being listed at startup showing as connected with no tools instead of reporting the error
  * Fixed the file edit permission dialog sometimes showing a changed line cut short with no indication
  * Fixed repository detection dropping a known repo identity after a transient git probe failure
  * Fixed managed settings silently going unenforced when the managed-settings file, a drop-in, the MDM plist, or the HKLM value cannot be parsed: Claude Code now refuses to start and names the source
  * Fixed Stop not actually stopping background agents and workflows in remote-control sessions: killed tasks now stay visible and re-stoppable until their processes exit
  * Fixed resuming a workflow run while its previous stopped run was still exiting, which could run duplicate copies of its agents
  * Fixed marketplace repo URLs on github.com with a trailing slash or dangling `?`/`#` producing an unusable `.git` clone URL
  * Fixed blocking Stop hooks causing the turn after a block to lose the model's reasoning from that turn and, on some models, miss the prompt cache
  * Fixed remote (claude.ai) sessions taking 60 seconds to start a turn after a browser-hosted MCP server's page had gone away
  * Fixed worktree-isolated sessions refusing common Bash loops, xargs pipelines and launcher-wrapped commands that cannot reach the main checkout
  * Improved terminal resize and first-render performance for long responses by reusing text measurements
  * Improved `/workflows` agent detail: JSON outcomes are pretty-printed with syntax colors and real line breaks, and long outcomes fold behind an expand toggle
  * Improved headless/SDK session start: the first turn begins up to 50 ms sooner when MCP servers finish connecting
  * Improved `/install-github-app` to explain it is GitHub-only and point to the GitLab CI/CD docs when run inside a GitLab repository
  * Improved nested background subagent results to be saved in the parent subagent's transcript, so resumed subagents keep them and shared transcripts show the delivery
  * Changed `allowedMcpServers` to govern only servers users add: a literal `managed-mcp.json` server your allowlist used to filter out now loads on upgrade; use `deniedMcpServers` to keep it off
  * \[VSCode] Added an Active quick filter and a status filter menu (Needs input, Working, Completed) to the session list sidebar
  * Fixed remote and scheduled sessions doing nothing after a connector-tool permission prompt was approved while the session was paused
</Update>

<Update label="2.1.258" description="September 1, 2026">
  * Fixed Claude Code failing to launch on macOS 12 (Monterey), a regression introduced in 2.1.255
  * Fixed remote and scheduled sessions failing with "user messages must have non-empty content" after a re-sent permission approval could not be applied
</Update>
