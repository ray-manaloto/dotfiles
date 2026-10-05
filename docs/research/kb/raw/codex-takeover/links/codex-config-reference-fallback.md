# Configuration Reference
## Search the docs


*You can find the latest JSON schema for config.toml here.*

Complete reference for Codex config.toml and requirements.toml

Use this page as a searchable reference for Codex configuration files. For conceptual guidance and examples, start with [Config basics](https://learn.chatgpt.com/codex/config-file/config-basic) and [Advanced Config](https://learn.chatgpt.com/codex/config-file/config-advanced).


## Settings for Local computer access with Work Cloud


With Local computer access with Work Cloud enabled, OpenAI’s cloud coordinates the task while supported tools run in the cloud or on a connected computer. Requirements set limits; configuration values provide defaults.


Use the policy API to manage Global settings. To manage Local or Codex Cloud settings, use the Agent Security UI. Existing Global API workflows remain available after migration. Test your scripts and Terraform integrations, and confirm that policy assignments and ordering are unchanged. Support for a `requirements.toml` field does not by itself establish API compatibility.


| Setting or setting family | Scope in Local computer access with Work Cloud | Guidance |
| --- | --- | --- |
| Approval policies and review requirements | Global orchestrator policy when managed policy is enabled | Keep approval and review controls in Global. Environment overrides cannot change orchestrator controls. Local execution and cloud-container execution have separate policy scopes. |
| Managed apps, MCP servers, plugins, marketplaces, and command rules | Global policy | Keep these controls global. Do not treat the field’s presence in a schema as proof that the field can be edited per environment. |
| File, sandbox, and portable network requirements | Local execution | For local execution, MDM and legacy managed-device requirements rank above Agent Security. The device’s system requirements file ranks below Agent Security. The new enterprise `requirements.toml` configuration does not apply to Work cloud containers, which retain existing Work Cloud policies. |
| Platform-specific executor controls | Computer running the step | Support depends on the executor and platform. |
| Managed hooks | Where enabled, admin-defined MCP hooks that run on the cloud coordinator (orchestrator) for supported lifecycle and tool events. | Before relying on these hooks, test the callback connection, confirm the events it receives, and check how failures affect the task. MCP hooks do not provide a complete Compliance API audit trail. Command, local-config, and plugin hooks are unsupported with cloud orchestration, even when tools execute locally. Existing supported hooks still apply to local-only Work and Codex threads where orchestration and execution are both local. |
| Proxy listener addresses, ports, and process settings | Not portable environment policy | Managed HTTP/SOCKS listener ports and non-loopback proxy listeners are unsupported by the cloud runtime; socket-rule support depends on the execution path. Custom proxy configuration is separate from supported destination restrictions. |
| App-only settings and ordinary local defaults | Not necessarily consumed by cloud coordination | App-enforced controls can remain effective even when Local computer access with Work Cloud does not consume them. Cloud delivery and cloud-browser behavior need separate validation. |


### Agent Security requirements for Local computer access with Work Cloud


For Work with local access and dots, supported Global policy applies to the shared cloud orchestrator when managed policy is enabled. Local execution requirements govern the connected computer. Work cloud containers and dots cloud computers use their own execution configuration and requirements. Test local and cloud controls separately.


#### Exposed in the Agent Security UI


- Allowed approval policies
- Allowed web search modes


#### Configured through TOML


- `allowed_approvals_reviewers`
- `auto_review`
- `guardian_policy_config`
- `apps`
- `mcp_servers`
- `plugins`
- `rules`


These orchestrator requirements stay in Global. They do not configure shared cloud capability permissions or make local execution settings portable to Work cloud containers or dots cloud computers.


### Local computer access with Work Cloud compatibility limits


Support depends on the field, how the policy is delivered, and where the task runs. Check the member’s effective policy before enabling sync. Some controls need to be tested in your deployment, as noted in the table.


Within a policy, the order from highest to lowest is OS-specific environment override → all-OS environment override → Global. A higher-priority policy wins even when a lower-priority policy is more specific.


For local execution, MDM and legacy managed-device requirements take precedence over Agent Security, which takes precedence over the device’s system requirements file. Some requirements, including network requirements, have field-specific merge rules and runtime limits. See [Managed configuration](https://learn.chatgpt.com/codex/enterprise/managed-configuration) for examples.


| **Setting or family** | **Local computer access with Work Cloud compatibility** | **Admin guidance** |
| --- | --- | --- |
| `sqlite_home`, `log_dir`, `model_catalog_json` | Not supported as managed cloud overrides. | Local paths cannot move cloud storage or logs. A local model catalog does not carry over. |
| `model_provider`, `model_providers` | Not supported in managed Local computer access with Work Cloud requirements or configuration. | Custom inference gateways and provider connections do not carry over through these fields. This is separate from model selection. |
| `enforce_residency` | Blocks Local computer access with Work Cloud when enabled in any cloud policy. | If `enforce_residency` is enabled in any cloud policy, **Allow local computer access** is disabled for both Work and dots. This safeguard does not configure workspace residency or, by itself, disable Work Cloud or dots. |
| `application.network.enabled` and `application.network.domains` | Not supported by Local computer access with Work Cloud. | Do not use these application-destination restrictions as Local computer access with Work Cloud command-networking controls. |
| `allow_browser_and_computer_use`, `in_app_browser`, `additional_developer_instructions` | Cloud policy delivery needs validation. Local computer access with Work Cloud rejects these managed requirement keys. | Browser restrictions have app-side checks. That does not prove cloud delivery or cloud-browser enforcement. `additional_developer_instructions` requires orchestrator support. |
| `experimental_network` and `permissions.<profile>.network` | Partial. Supported destination and executor restrictions differ from custom proxy configuration. | Managed HTTP/SOCKS listener ports and non-loopback proxy listeners are unsupported by the cloud runtime; socket-rule support depends on the execution path. Local-execution merge behavior is separate. Command-network restrictions do not disable hosted search, MCP, or app tools. |
| features / `feature_requirements`, models, `computer_use` | Partial. | Retired switches such as `tool_search` = false, `tool_search_always_defer_mcp_tools` = false, `js_repl` = true, and `remote_control` = true are rejected. Some computer-use settings still need end-to-end validation. |
| `browser_use`, `allow_appshots`, feedback, `allow_remote_control`, marketplace source restrictions | The app or app-server enforces these controls on some policy delivery paths. | App controls can still apply when Local computer access with Work Cloud ignores a field. Desktop browser site rules do not apply to Work cloud containers. Validate the actual surface and policy delivery path. |


The configuration schema includes keys that may not work with Local computer access with Work Cloud or support environment overrides. See [Managed configuration](https://learn.chatgpt.com/codex/enterprise/managed-configuration) for the global baseline and precedence.


## `config.toml`


User-level configuration lives in `~/.codex/config.toml`. You can also add project-scoped overrides in `.codex/config.toml` files. Codex loads project-scoped config files only when you trust the project.


Project-scoped config can’t override machine-local provider, auth, host-owned app request metadata, notification, configuration profile selection, or telemetry routing keys. Codex ignores `openai_base_url`, `chatgpt_base_url`, `apps_mcp_product_sku`, `model_provider`, `model_providers`, `notify`, `profile`, `profiles`, `experimental_realtime_ws_base_url`, and `otel` when they appear in a project-local `.codex/config.toml`; put provider, notification, and telemetry keys in user-level config instead. Config [profile files](https://learn.chatgpt.com/codex/config-file/config-advanced#profiles) live next to `config.toml` as `$CODEX_HOME/profile-name.config.toml`; select one with `--profile profile-name`.


For sandbox and approval keys (`approval_policy`, `sandbox_mode`, and `sandbox_workspace_write.*`), pair this reference with [Sandbox and approvals](https://learn.chatgpt.com/codex/agent-approvals-security#sandbox-and-approvals), [Protected paths in writable roots](https://learn.chatgpt.com/codex/agent-approvals-security#protected-paths-in-writable-roots), and [Network access](https://learn.chatgpt.com/codex/agent-approvals-security#network-access). For beta permission profiles, see [Permissions](https://learn.chatgpt.com/codex/permissions).


Codex and ChatGPT Work no longer support `approval_policy = "untrusted"`. Remove the setting or choose a supported policy. Project entries with `trust_level = "untrusted"` in user-level `~/.codex/config.toml` remain supported. See [Migrate from the retired `untrusted` approval policy](https://learn.chatgpt.com/codex/agent-approvals-security#migrate-from-the-retired-untrusted-approval-policy) for examples and approval tradeoffs.


Set `model` to one available to your signed-in account or workspace. See [GPT-6.1 Sol availability](https://learn.chatgpt.com/codex/models#gpt-6.1-sol) before using the example value.


Key

Type / Values

Details

`agents`

`table`

Multi-agent settings and custom role declarations. Scalar setting names are reserved and can't be used as custom role names.

`agents.<name>.config_file`

`string (path)`

Path to a TOML config layer for that role; relative paths resolve from the config file that declares the role.

`agents.<name>.description`

`string`

Role guidance shown to Codex when choosing and spawning that agent type.

`agents.default_subagent_model`

`string`

Default model for spawned agents. An explicit spawn model takes precedence.

`agents.default_subagent_reasoning_effort`

`string`

Default reasoning effort for spawned agents. An explicit spawn effort takes precedence.

`agents.enabled`

`boolean`

Enable or disable multi-agent tools (default: true).

`agents.interrupt_message`

`boolean`

Record a model-visible message when an agent turn is interrupted (default: true).

`agents.max_concurrent_threads_per_session`

`number`

Maximum number of spawned-agent threads that can be open concurrently, excluding the primary thread. When unset, Codex chooses the default.

`agents.max_threads`

`number`

Legacy alias for `agents.max_concurrent_threads_per_session`.

`allow_login_shell`

`boolean`

Allow shell-based tools to use login-shell semantics. Defaults to `true`; when `false`, `login = true` requests are rejected and omitted `login` defaults to non-login shells.

`analytics.enabled`

`boolean`

Enable or disable analytics for this machine/profile. When unset, the client default applies.

`approval_policy`

`on-request | never | { granular = { sandbox_approval = bool, rules = bool, mcp_elicitations = bool, request_permissions = bool, skill_approval = bool } }`

Controls when Codex pauses for approval before executing commands. You can also use `approval_policy = { granular = { ... } }` to allow or auto-reject specific prompt categories while keeping other prompts interactive. `untrusted` is unsupported, and `on-failure` is deprecated; use `on-request` for interactive runs or `never` for non-interactive runs.

`approval_policy.granular.mcp_elicitations`

`boolean`

When `true`, MCP elicitation prompts are allowed to surface instead of being auto-rejected.

`approval_policy.granular.request_permissions`

`boolean`

When `true`, prompts from the `request_permissions` tool are allowed to surface.

`approval_policy.granular.rules`

`boolean`

When `true`, approvals triggered by execpolicy `prompt` rules are allowed to surface.

`approval_policy.granular.sandbox_approval`

`boolean`

When `true`, sandbox escalation approval prompts are allowed to surface.

`approval_policy.granular.skill_approval`

`boolean`

When `true`, skill-script approval prompts are allowed to surface.

`approvals_reviewer`

`user | auto_review`

Who reviews eligible approval prompts under `on-request` or granular approval policies. Defaults to `user`; `auto_review` uses the reviewer subagent. This setting doesn't change sandboxing or review actions already allowed inside the sandbox.

`apps._default.approvals_reviewer`

`user | auto_review`

Default reviewer for app tool approval prompts unless overridden per app. When omitted, apps inherit the top-level `approvals_reviewer` value.

`apps._default.default_tools_approval_mode`

`auto | prompt | writes | approve`

Default approval behavior for app tools without per-app or per-tool overrides.

`apps._default.destructive_enabled`

`boolean`

Default allow/deny for app tools with `destructive_hint = true`.

`apps._default.enabled`

`boolean`

Default app enabled state for all apps unless overridden per app.

`apps._default.open_world_enabled`

`boolean`

Default allow/deny for app tools with `open_world_hint = true`.

`apps.<id>.approvals_reviewer`

`user | auto_review`

Reviewer for this app's tool approval prompts. Overrides `apps._default.approvals_reviewer`.

`apps.<id>.default_tools_approval_mode`

`auto | prompt | writes | approve`

Default approval behavior for tools in this app unless a per-tool override exists.

`apps.<id>.default_tools_enabled`

`boolean`

Default enabled state for tools in this app unless a per-tool override exists.

`apps.<id>.destructive_enabled`

`boolean`

Allow or block tools in this app that advertise `destructive_hint = true`.

`apps.<id>.enabled`

`boolean`

Enable or disable a specific app/connector by id (default: true).

`apps.<id>.open_world_enabled`

`boolean`

Allow or block tools in this app that advertise `open_world_hint = true`.

`apps.<id>.tools.<tool>.approval_mode`

`auto | prompt | writes | approve`

Per-tool approval behavior override for a single app tool.

`apps.<id>.tools.<tool>.enabled`

`boolean`

Per-tool enabled override for an app tool (for example `repos/list`).

`auto_review.extra_policy`

`string`

Additional local Markdown policy for automatic review, included alongside the main policy. Managed `guardian_extra_policy` takes precedence. Blank values are ignored.

`auto_review.policy`

`string`

Local Markdown policy instructions for automatic review. Managed `guardian_policy_config` takes precedence. Blank values are ignored.

`background_terminal_max_timeout`

`number`

Maximum poll window in milliseconds for empty `write_stdin` polls (background terminal polling). Default: `300000` (5 minutes). Replaces the older `background_terminal_timeout` key.

`browser_use.allow_history_access`

`boolean`

Set to `false` to restrict browser-history access. Managed requirements can enforce this restriction.

`browser_use.default_origin_policy`

`table`

Fallback browser-origin restrictions. Supports `access`, `uploads`, `downloads`, and `full_cdp_access`, each set to `allow` or `deny`.

`browser_use.origins.<origin>`

`table`

Per-origin browser restrictions with the same fields as `browser_use.default_origin_policy`. Include an HTTP or HTTPS scheme and optional port; omit paths, queries, and fragments. Local values cannot relax managed denies.

`chatgpt_base_url`

`string`

Override the base URL used during the ChatGPT login flow.

`check_for_update_on_startup`

`boolean`

Check for Codex updates on startup (set to false only when updates are centrally managed).

`cli_auth_credentials_store`

`file | keyring | auto | ephemeral`

Control where the CLI stores cached credentials.

`compact_prompt`

`string`

Inline override for the history compaction prompt.

`computer_use.default_app_access`

`allow | deny`

Fallback native-app access policy for Computer Use. App-specific entries can supply a policy; local configuration cannot relax managed restrictions.

`computer_use.macos.bundle_ids`

`map<string, allow | deny>`

Native macOS app access keyed by bundle identifier.

`computer_use.windows.always_allowed_app_ids`

`array<string>`

Windows app identifiers that Computer Use can open without prompting. Apps not in the list require approval; remove saved entries from the ChatGPT desktop app's Computer Use settings.

`computer_use.windows.aumids`

`map<string, allow | deny>`

Packaged Windows app access keyed by Application User Model ID (AUMID).

`computer_use.windows.exes`

`array<table>`

Windows executable access rules. Each rule requires `publisher_name`, `product_name`, and `access` (`allow` or `deny`); `binary_name` is optional.

`default_permissions`

`string`

Name of the default permissions profile to apply to sandboxed tool calls. Built-ins are `:read-only`, `:workspace`, and `:danger-full-access`; custom profile names require matching `[permissions.<name>]` tables. Don't combine with `sandbox_mode` or `[sandbox_workspace_write]`.

`desktop.custom_file_handlers.<id>`

`table`

User-level only. Defines an additional **Open in** target for the ChatGPT desktop app. See [Add custom file handlers](https://learn.chatgpt.com/codex/config-file/config-advanced#add-custom-file-handlers) for examples and handler ID constraints.

`desktop.custom_file_handlers.<id>.args`

`array<string>`

Arguments inserted between the command and file input (default: `[]`).

`desktop.custom_file_handlers.<id>.command`

`string`

Executable path or command name to detect and launch. Required.

`desktop.custom_file_handlers.<id>.icon`

`string`

Bundled asset path, Base64-encoded `data:image/...` URL, file URI, or absolute local path for the handler icon. Required; unsupported sources use the default VS Code icon.

`desktop.custom_file_handlers.<id>.input`

`path | json_argument | json_stdin`

How the app sends file input to the handler (default: `path`).

`desktop.custom_file_handlers.<id>.label`

`string`

Display name shown in **Open in** menus. Required.

`desktop.custom_file_handlers.<id>.supports_ssh`

`boolean`

Offer the handler for files in SSH workspaces (default: `false`).

`developer_instructions`

`string`

Additional developer instructions injected into the session (optional).

`disable_paste_burst`

`boolean`

Disable burst-paste detection in the TUI.

`experimental_compact_prompt_file`

`string (path)`

Load the compaction prompt override from a file (experimental).

`experimental_use_unified_exec_tool`

`boolean`

Legacy name for enabling unified exec; prefer `[features].unified_exec` or `codex --enable unified_exec`.

`features.apps`

`boolean`

Enable app (connector) integrations (stable; on by default). App and connector traffic is not controlled by the sandboxed-command network proxy or its domain allowlist.

`features.code_mode.direct_only_tool_namespaces`

`array<string>`

Tool namespaces code mode can use only through direct tool calls.

`features.code_mode.enabled`

`boolean`

Enable code mode feature configuration. This feature is under development and off by default.

`features.code_mode.excluded_tool_namespaces`

`array<string>`

Tool namespaces code mode excludes from nested code-mode tool guidance and executor exposure.

`features.context_management.experimental_mode`

`boolean`

Experimental context-management setting. The feature is not currently available.

`features.enable_request_compression`

`boolean`

Compress streaming request bodies with zstd when supported (stable; on by default).

`features.fast_mode`

`boolean`

Enable model-catalog service tier selection in the TUI, including Fast-tier commands when the active model advertises them (stable; on by default).

`features.goals`

`boolean`

Enable persisted goals and automatic continuation (stable; on by default).

`features.hooks`

`boolean`

Enable lifecycle hooks loaded from `hooks.json` or inline `[hooks]` config. `features.codex_hooks` is a deprecated alias.

`features.memories`

`boolean`

Enable [Memories](https://learn.chatgpt.com/codex/customization/memories) (off by default).

`features.multi_agent`

`boolean`

Enable multi-agent collaboration tools (`spawn_agent`, `send_input`, `resume_agent`, `wait_agent`, and `close_agent`) (stable; on by default).

`features.network_proxy`

`boolean | table`

Start the network proxy for sandboxed commands (experimental; off by default). Required to enforce permission-profile domain rules unless enabled administrator-managed `experimental_network` requirements start the proxy. Use a table when setting feature-level policy options such as `domains`. Does not filter web search, apps, MCP, or other hosted tools.

`features.network_proxy.allow_local_binding`

`boolean`

Allow broader local/private-network access. Defaults to `false`; exact local IP literal or `localhost` allow rules can still permit specific local targets.

`features.network_proxy.allow_upstream_proxy`

`boolean`

Allow chaining through an upstream proxy from the environment. Defaults to `true`.

`features.network_proxy.dangerously_allow_all_unix_sockets`

`boolean`

Permit arbitrary Unix socket destinations instead of allowlist-only access. Defaults to `false`; use only in tightly controlled environments.

`features.network_proxy.dangerously_allow_non_loopback_proxy`

`boolean`

Permit non-loopback listener addresses. Defaults to `false`; enabling it can expose proxy listeners beyond localhost.

`features.network_proxy.domains`

`map<string, allow | deny>`

Domain policy for sandboxed networking. Unset by default, which means no external destinations are allowed until you add `allow` rules. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules. Prefer scoped rules because `*` broadly opens public outbound access. Add `deny` rules for blocked destinations; `deny` wins on conflicts.

`features.network_proxy.enable_socks5`

`boolean`

Expose SOCKS5 support. Defaults to `true`.

`features.network_proxy.enable_socks5_udp`

`boolean`

Allow UDP over SOCKS5. Defaults to `true`.

`features.network_proxy.enabled`

`boolean`

Start the sandboxed-command network proxy when command network access is enabled. Defaults to `false`; permission-profile domain rules are not enforced while the proxy is off.

`features.network_proxy.proxy_url`

`string`

HTTP listener URL for sandboxed networking. Defaults to `"http://127.0.0.1:3128"`.

`features.network_proxy.socks_url`

`string`

SOCKS5 listener URL. Defaults to `"http://127.0.0.1:8081"`.

`features.network_proxy.unix_sockets`

`map<string, allow | deny>`

Unix socket policy for sandboxed networking. Unset by default; add `allow` entries for permitted sockets.

`features.personality`

`boolean`

Enable personality selection controls (stable; on by default).

`features.prevent_idle_sleep`

`boolean`

Prevent the machine from sleeping while a turn is actively running (experimental; off by default).

`features.remote_plugin`

`boolean`

Enable the remote plugin catalog (stable; on by default).

`features.rollout_budget.enabled`

`boolean`

Enable rollout budget tracking. This feature is under development and off by default. When enabled, `features.rollout_budget.limit_tokens` is required.

`features.rollout_budget.limit_tokens`

`integer`

Positive token limit for rollout budget tracking. Required when rollout budget is enabled.

`features.rollout_budget.prefill_token_weight`

`number`

Finite non-negative multiplier for prefill tokens in rollout budget accounting. Defaults to `1.0`.

`features.rollout_budget.reminder_interval_tokens`

`integer`

Positive token interval between rollout budget reminders. Defaults to 10% of `limit_tokens`, with a minimum of 1 token.

`features.rollout_budget.sampling_token_weight`

`number`

Finite non-negative multiplier for sampled tokens in rollout budget accounting. Defaults to `1.0`.

`features.shell_snapshot`

`boolean`

Snapshot shell environment to speed up repeated commands (stable; on by default).

`features.shell_tool`

`boolean`

Enable the default `shell` tool for running commands (stable; on by default).

`features.skill_mcp_dependency_install`

`boolean`

Allow prompting and installing missing MCP dependencies for skills (stable; on by default).

`features.unified_exec`

`boolean`

Use the unified PTY-backed exec tool (stable; enabled by default except on Windows).

`features.web_search`

`boolean`

Deprecated legacy toggle; prefer the top-level `web_search` setting.

`features.web_search_cached`

`boolean`

Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "cached"`.

`features.web_search_request`

`boolean`

Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "live"`.

`feedback.enabled`

`boolean`

Enable feedback submission via `/feedback` across local clients (default: true).

`file_opener`

`vscode | vscode-insiders | windsurf | cursor | none`

URI scheme used to open citations from Codex output (default: `vscode`).

`forced_chatgpt_workspace_id`

`string (uuid)`

Limit ChatGPT logins to a specific workspace identifier.

`forced_login_method`

`chatgpt | api`

Restrict Codex to a specific authentication method.

`hide_agent_reasoning`

`boolean`

Suppress reasoning events in both the TUI and `codex exec` output.

`history.max_bytes`

`number`

If set, caps the history file size in bytes by dropping oldest entries.

`history.persistence`

`save-all | none`

Control whether Codex saves session transcripts to history.jsonl.

`hooks`

`table`

Lifecycle hooks configured inline in `config.toml`. Uses the same event schema as `hooks.json`; see the Hooks guide for examples and supported events.

`hooks.<Event>`

`array<table>`

Matcher groups for hook events such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, `Stop`, or `Interrupt`.

`hooks.<Event>[].hooks`

`array<table>`

Hook handlers for a matcher group. Command and MCP tool hooks are supported while prompt and agent hook handlers are parsed but skipped.

`hooks.<Event>[].hooks[].additionalContextLimit`

`integer`

Approximate per-handler token threshold for saving oversized `additionalContext` to disk and showing the model a shorter preview. Defaults to `2500`; `0` passes the full context directly to the model. See [Large hook output](https://learn.chatgpt.com/codex/hooks#large-hook-output).

`hooks.<Event>[].hooks[].async`

`boolean`

Run a command hook in the background without delaying the triggering operation. Defaults to `false`; `SessionEnd` always runs synchronously. See [Run hooks in the background](https://learn.chatgpt.com/codex/hooks#run-hooks-in-the-background).

`hooks.<Event>[].hooks[].commandWindows`

`string`

Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted.

`instructions`

`string`

Reserved for future use; prefer `model_instructions_file` or `AGENTS.md`.

`log_dir`

`string (path)`

Directory where Codex writes log files; defaults to `$CODEX_HOME/log`. Setting this explicitly also enables the opt-in plaintext TUI log, `codex-tui.log`, in that directory.

`marketplaces.<name>.ref`

`string`

Optional Git branch, tag, or commit for the marketplace.

`marketplaces.<name>.source`

`string`

Git repository location or local marketplace root directory. Use an absolute path for a local source; the directory contains .agents/plugins/marketplace.json.

`marketplaces.<name>.source_type`

`git | local`

Source kind for a configured plugin marketplace. Marketplaces can be defined in system, cloud-managed, user, or trusted-project config.toml.

`marketplaces.<name>.sparse_paths`

`array<string>`

Optional sparse checkout paths for a Git marketplace. Include the marketplace catalog and any local plugin directories it references.

`mcp_oauth_callback_port`

`integer`

Optional global fixed port for the local HTTP callback server used during MCP OAuth login. A server-specific `oauth.callback_port` takes precedence. When neither is set, Codex binds to an ephemeral port chosen by the OS.

`mcp_oauth_callback_url`

`string`

Optional base callback URL for MCP OAuth login, such as a devbox ingress URL. Newly added pre-registered clients use this URL unchanged when the authorization server supports issuer identification; existing clients without a saved callback append a server-specific callback ID. Without issuer support, any pre-registered MCP server whose configured callback lacks the required ID falls back to this URL with the ID appended. Callback URL ports don't select the listener port.

`mcp_oauth_credentials_store`

`auto | file | keyring`

Preferred store for MCP OAuth credentials.

`mcp_optional_startup_grace_ms`

`integer (milliseconds)`

Shared wait for optional MCP servers when building the initial tool catalog. Defaults to `1000`. Set to `0` to wait for each server's `startup_timeout_sec` instead.

`mcp_servers.<id>.args`

`array<string>`

Arguments passed to the MCP stdio server command.

`mcp_servers.<id>.auth`

`oauth | chatgpt`

Authentication fallback for an MCP HTTP server after configured bearer tokens and authorization headers. `oauth` (default) uses stored MCP OAuth credentials when available. `chatgpt` uses the current ChatGPT session for the trusted first-party ChatGPT origin, then falls back to stored OAuth. Both modes can connect without authentication if no credential source resolves.

`mcp_servers.<id>.bearer_token_env_var`

`string`

Environment variable sourcing the bearer token for an MCP HTTP server.

`mcp_servers.<id>.command`

`string`

Launcher command for an MCP stdio server.

`mcp_servers.<id>.cwd`

`string`

Working directory for the MCP stdio server process.

`mcp_servers.<id>.default_tools_approval_mode`

`auto | prompt | writes | approve`

Default approval behavior for MCP tools on this server unless a per-tool override exists.

`mcp_servers.<id>.disabled_tools`

`array<string>`

Deny list applied after `enabled_tools` for the MCP server.

`mcp_servers.<id>.enabled`

`boolean`

Disable an MCP server without removing its configuration.

`mcp_servers.<id>.enabled_tools`

`array<string>`

Allow list of tool names exposed by the MCP server.

`mcp_servers.<id>.env`

`map<string,string>`

Environment variables forwarded to the MCP stdio server.

`mcp_servers.<id>.env_http_headers`

`map<string,string>`

HTTP headers populated from environment variables for an MCP HTTP server.

`mcp_servers.<id>.env_vars`

`array<string | { name = string, source = "local" | "remote" }>`

Additional environment variables to whitelist for an MCP stdio server. String entries default to `source = "local"`; use `source = "remote"` only with executor-backed remote stdio.

`mcp_servers.<id>.experimental_environment`

`local | remote`

Experimental placement for an MCP server. `remote` starts stdio servers through a remote executor environment; streamable HTTP remote placement is not implemented.

`mcp_servers.<id>.http_headers`

`map<string,string>`

Static HTTP headers included with each MCP HTTP request.

`mcp_servers.<id>.http_headers_helper`

`string (command)`

Local command that prints a JSON object of HTTP header names and values. Supported only for locally connected HTTP MCP servers. Explicit bearer tokens and OAuth credentials take precedence over helper-provided Authorization headers.

`mcp_servers.<id>.oauth_resource`

`string`

Optional RFC 8707 OAuth resource parameter to include during MCP login.

`mcp_servers.<id>.oauth.callback_port`

`integer`

Fixed OAuth callback listener port for this MCP server. Overrides `mcp_oauth_callback_port`. For a direct loopback callback with an explicit URL port, configure the same listener port.

`mcp_servers.<id>.oauth.callback_url`

`string`

Server-specific OAuth callback. Pre-registered clients reuse it when issuer identification is supported or the URL already ends in the server-specific callback ID. Otherwise, Codex uses the global or default callback with that ID appended. Clients without a pre-registered ID use this callback during client registration.

`mcp_servers.<id>.oauth.client_id`

`string`

Pre-registered OAuth client ID used for authorization and token exchange with this MCP server.

`mcp_servers.<id>.required`

`boolean`

When true, fail startup/resume if this enabled MCP server cannot initialize.

`mcp_servers.<id>.scopes`

`array<string>`

OAuth scopes to request when authenticating to that MCP server.

`mcp_servers.<id>.startup_timeout_ms`

`number`

Alias for `startup_timeout_sec` in milliseconds.

`mcp_servers.<id>.startup_timeout_sec`

`number`

Override the default 10s startup timeout for an MCP server.

`mcp_servers.<id>.tool_timeout_sec`

`number`

Override the default 60s per-tool timeout for an MCP server.

`mcp_servers.<id>.tools.<tool>.approval_mode`

`auto | prompt | writes | approve`

Per-tool approval behavior override for one MCP tool on this server.

`mcp_servers.<id>.tools.<tool>.output_token_limit`

`integer (positive)`

Token budget for one MCP tool's output, before the standard 20% serialization allowance. Overrides the model's default output truncation budget for that tool.

`mcp_servers.<id>.url`

`string`

Endpoint for an MCP streamable HTTP server.

`memories.consolidation_model`

`string`

Optional model override for global memory consolidation.

`memories.disable_on_external_context`

`boolean`

When `true`, threads that use external context such as MCP tool calls, web search, or tool search are kept out of memory generation. Defaults to `false`. Legacy alias: `memories.no_memories_if_mcp_or_web_search`.

`memories.extract_model`

`string`

Optional model override for per-thread memory extraction.

`memories.generate_memories`

`boolean`

When `false`, newly created threads are not stored as memory-generation inputs. Defaults to `true`.

`memories.max_raw_memories_for_consolidation`

`number`

Maximum recent raw memories retained for global consolidation. Defaults to `256` and is capped at `4096`.

`memories.max_rollout_age_days`

`number`

Maximum age of threads considered for memory generation. Defaults to `30` and is clamped to `0` - `90`.

`memories.max_rollouts_per_startup`

`number`

Maximum rollout candidates processed per startup pass. Defaults to `16` and is capped at `128`.

`memories.max_unused_days`

`number`

Maximum days since a memory was last used before it becomes ineligible for consolidation. Defaults to `30` and is clamped to `0` - `365`.

`memories.min_rate_limit_remaining_percent`

`number`

Minimum remaining percentage required in Codex rate-limit windows before memory generation starts. Defaults to `25` and is clamped to `0` - `100`.

`memories.min_rollout_idle_hours`

`number`

Minimum idle time before a thread is considered for memory generation. Defaults to `6` and is clamped to `1` - `48`.

`memories.use_memories`

`boolean`

When `false`, Codex skips injecting existing memories into future sessions. Defaults to `true`.

`model`

`string`

Model to use (e.g., `gpt-6.1-sol`).

`model_auto_compact_token_limit`

`number`

Token threshold that triggers automatic history compaction (unset uses model defaults).

`model_auto_compact_token_limit_scope`

`total | body_after_prefix`

Controls whether the auto-compaction threshold counts the full active context (`total`, the default) or only growth after the carried compaction-window prefix (`body_after_prefix`).

`model_catalog_json`

`string (path)`

Optional path to a JSON model catalog loaded on startup. A selected `$CODEX_HOME/profile-name.config.toml` profile file can override this per profile.

`model_context_window`

`number`

Context window tokens available to the active model.

`model_instructions_file`

`string (path)`

Replacement for built-in instructions instead of `AGENTS.md`.

`model_provider`

`string`

Provider id from `model_providers` (default: `openai`).

`model_providers.<id>`

`table`

Custom provider definition. Built-in provider IDs (`openai`, `ollama`, and `lmstudio`) are reserved and cannot be overridden.

`model_providers.<id>.auth`

`table`

Command-backed bearer token configuration for a custom provider. Do not combine with `env_key`, `experimental_bearer_token`, or `requires_openai_auth`.

`model_providers.<id>.auth.args`

`array<string>`

Arguments passed to the token command.

`model_providers.<id>.auth.command`

`string`

Command to run when Codex needs a bearer token. The command must print the token to stdout.

`model_providers.<id>.auth.cwd`

`string (path)`

Working directory for the token command.

`model_providers.<id>.auth.refresh_interval_ms`

`number`

How often Codex proactively refreshes the token in milliseconds (default: 300000). Set to `0` to refresh only after an authentication retry.

`model_providers.<id>.auth.timeout_ms`

`number`

Maximum token command runtime in milliseconds (default: 5000).

`model_providers.<id>.base_url`

`string`

API base URL for the model provider.

`model_providers.<id>.env_http_headers`

`map<string,string>`

HTTP headers populated from environment variables when present.

`model_providers.<id>.env_key`

`string`

Environment variable supplying the provider API key.

`model_providers.<id>.env_key_instructions`

`string`

Optional setup guidance for the provider API key.

`model_providers.<id>.experimental_bearer_token`

`string`

Direct bearer token for the provider (discouraged; use `env_key`).

`model_providers.<id>.http_headers`

`map<string,string>`

Static HTTP headers added to provider requests.

`model_providers.<id>.name`

`string`

Display name for a custom model provider.

`model_providers.<id>.query_params`

`map<string,string>`

Extra query parameters appended to provider requests.

`model_providers.<id>.request_max_retries`

`number`

Retry count for HTTP requests to the provider (default: 4).

`model_providers.<id>.requires_openai_auth`

`boolean`

The provider uses OpenAI authentication (defaults to false).

`model_providers.<id>.stream_idle_timeout_ms`

`number`

Idle timeout for SSE streams in milliseconds (default: 300000).

`model_providers.<id>.stream_max_retries`

`number`

Retry count for SSE streaming interruptions (default: 5).

`model_providers.<id>.supports_standalone_web_search`

`boolean`

Advertise support for a compatible standalone web search endpoint (default: false). Standalone search remains under development and off by default; provider compatibility alone doesn't enable it.

`model_providers.<id>.supports_websockets`

`boolean`

Whether that provider supports the Responses API WebSocket transport.

`model_providers.<id>.wire_api`

`responses`

Protocol used by the provider. `responses` is the only supported value, and it is the default when omitted.

`model_providers.amazon-bedrock.aws.profile`

`string`

AWS profile name used by the built-in `amazon-bedrock` provider.

`model_providers.amazon-bedrock.aws.region`

`string`

AWS region used by the built-in `amazon-bedrock` provider.

`model_reasoning_effort`

`string`

Reasoning effort advertised by the selected model, such as `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`. Available levels depend on the model and client.

`model_reasoning_summary`

`auto | concise | detailed | none`

Select reasoning summary detail or disable summaries entirely.

`model_supports_reasoning_summaries`

`boolean`

Force Codex to send or not send reasoning metadata.

`model_verbosity`

`low | medium | high`

Optional GPT-5 Responses API verbosity override; when unset, the selected model/preset default is used.

`notice.hide_full_access_warning`

`boolean`

Track acknowledgement of the full access warning prompt.

`notice.hide_gpt-5.1-codex-max_migration_prompt`

`boolean`

Track acknowledgement of the gpt-5.1-codex-max migration prompt.

`notice.hide_gpt5_1_migration_prompt`

`boolean`

Track acknowledgement of the GPT-5.1 migration prompt.

`notice.hide_rate_limit_model_nudge`

`boolean`

Track opt-out of the rate limit model switch reminder.

`notice.hide_world_writable_warning`

`boolean`

Track acknowledgement of the Windows world-writable directories warning.

`notice.model_migrations`

`map<string,string>`

Track acknowledged model migrations as old->new mappings.

`notify`

`array<string>`

Command invoked for notifications; receives a JSON payload from Codex.

`openai_base_url`

`string`

Base URL override for the built-in `openai` model provider.

`oss_provider`

`lmstudio | ollama`

Default local provider used when running with `--oss` (defaults to prompting if unset).

`otel.environment`

`string`

Environment tag applied to emitted OpenTelemetry events (default: `dev`).

`otel.exporter`

`none | otlp-http | otlp-grpc`

Select the OpenTelemetry exporter and provide any endpoint metadata.

`otel.exporter.<id>.endpoint`

`string`

Exporter endpoint for OTEL logs.

`otel.exporter.<id>.headers`

`map<string,string>`

Static headers included with OTEL exporter requests.

`otel.exporter.<id>.protocol`

`binary | json`

Protocol used by the OTLP/HTTP exporter.

`otel.exporter.<id>.tls.ca-certificate`

`string`

CA certificate path for OTEL exporter TLS.

`otel.exporter.<id>.tls.client-certificate`

`string`

Client certificate path for OTEL exporter TLS.

`otel.exporter.<id>.tls.client-private-key`

`string`

Client private key path for OTEL exporter TLS.

`otel.log_user_prompt`

`boolean`

Opt in to exporting raw user prompts with OpenTelemetry logs.

`otel.metrics_exporter`

`none | statsig | otlp-http | otlp-grpc`

Select the OpenTelemetry metrics exporter (defaults to `statsig`).

`otel.trace_exporter`

`none | otlp-http | otlp-grpc`

Select the OpenTelemetry trace exporter and provide any endpoint metadata.

`otel.trace_exporter.<id>.endpoint`

`string`

Trace exporter endpoint for OTEL logs.

`otel.trace_exporter.<id>.headers`

`map<string,string>`

Static headers included with OTEL trace exporter requests.

`otel.trace_exporter.<id>.protocol`

`binary | json`

Protocol used by the OTLP/HTTP trace exporter.

`otel.trace_exporter.<id>.tls.ca-certificate`

`string`

CA certificate path for OTEL trace exporter TLS.

`otel.trace_exporter.<id>.tls.client-certificate`

`string`

Client certificate path for OTEL trace exporter TLS.

`otel.trace_exporter.<id>.tls.client-private-key`

`string`

Client private key path for OTEL trace exporter TLS.

`permissions.<name>.description`

`string`

Human-readable description for this named profile. A profile does not inherit its parent's description through `extends`.

`permissions.<name>.extends`

`string`

Optional parent profile applied before this named profile. Set it to another named profile, `:read-only`, or `:workspace`; `:danger-full-access`, undefined parents, and cycles are rejected.

`permissions.<name>.filesystem`

`table`

Named filesystem permission profile. Each key is an absolute path or special token such as `:minimal` or `:workspace_roots`.

`permissions.<name>.filesystem.":workspace_roots".<subpath-or-glob>`

`"read" | "write" | "deny"`

Scoped filesystem access relative to each effective workspace root. Use `"."` for the root itself; glob subpaths such as `"**/*.env"` can deny reads with `"deny"`.

`permissions.<name>.filesystem.<path-or-glob>`

`"read" | "write" | "deny" | table`

Grant direct access for a path, glob pattern, or special token, or scope nested entries under that root. Use `"deny"` to deny reads for matching paths.

`permissions.<name>.filesystem.glob_scan_max_depth`

`number`

Maximum depth for expanding deny-read glob patterns on platforms that snapshot matches before sandbox startup. Must be at least `1` when set.

`permissions.<name>.network.allow_local_binding`

`boolean`

Permit broader local/private-network access through sandboxed networking. Exact local IP literal or `localhost` allow rules can still permit specific local targets when this stays `false`.

`permissions.<name>.network.allow_upstream_proxy`

`boolean`

Allow sandboxed networking to chain through another upstream proxy.

`permissions.<name>.network.dangerously_allow_all_unix_sockets`

`boolean`

Allow arbitrary Unix socket destinations instead of the default restricted set. Use only in tightly controlled environments.

`permissions.<name>.network.dangerously_allow_non_loopback_proxy`

`boolean`

Permit non-loopback bind addresses for sandboxed networking listeners. Enabling it can expose listeners beyond localhost.

`permissions.<name>.network.domains`

`table`

Domain rules for sandboxed commands. Enforced only when `features.network_proxy` or enabled administrator-managed networking requirements activate the proxy. Supports exact hosts, `*.example.com`, `**.example.com`, and global `*` allow rules; `deny` wins. Does not restrict web search, apps, or MCP servers.

`permissions.<name>.network.domains.<pattern>`

`allow | deny`

Allow or deny an exact host or scoped wildcard pattern such as `*.example.com` or `**.example.com`.

`permissions.<name>.network.enable_socks5`

`boolean`

Expose SOCKS5 support when this permissions profile enables sandboxed networking.

`permissions.<name>.network.enable_socks5_udp`

`boolean`

Allow UDP over the SOCKS5 listener when enabled.

`permissions.<name>.network.enabled`

`boolean`

Enable network access for commands in this permission profile. This does not start the network proxy. Without `features.network_proxy` or enabled administrator-managed networking requirements, command network access is direct and profile domain rules are not enforced.

`permissions.<name>.network.mode`

`limited | full`

Network proxy mode used for subprocess traffic.

`permissions.<name>.network.proxy_url`

`string`

HTTP listener URL used when this permissions profile enables sandboxed networking.

`permissions.<name>.network.socks_url`

`string`

SOCKS5 proxy endpoint used by this permissions profile.

`permissions.<name>.network.unix_sockets`

`table`

Unix socket allowlist overrides for sandboxed networking. Use socket paths as keys; `allow` adds a path, and `deny` rejects it.

`permissions.<name>.network.unix_sockets.<path>`

`allow | deny`

Add an absolute Unix socket path to the effective allowlist with `allow`, or reject it with `deny`. Denied entries are omitted from the effective allowlist.

`permissions.<name>.workspace_roots`

`table`

Profile-defined workspace roots that receive `:workspace_roots` filesystem rules alongside the session's runtime workspace roots.

`permissions.<name>.workspace_roots.<path>`

`boolean`

Opt a path into the profile's workspace root set when `true`. Disabled entries remain inactive.

`personality`

`none | friendly | pragmatic`

Default communication style for models that advertise `supportsPersonality`; can be overridden per thread/turn or via `/personality`.

`plan_mode_reasoning_effort`

`string`

Plan-mode-specific reasoning override using a level supported by the selected model. When unset, Plan mode uses its built-in preset default.

`plugins.<plugin>.enabled`

`boolean`

Enable or disable a local-marketplace plugin using a `plugin-name@marketplace-name` key. Read from the effective merged config; trusted-project settings can override user, cloud-managed, and system defaults. Marketplace refresh can install or refresh configured plugins even when disabled. This does not override workspace-managed enabled states.

`plugins.<plugin>.mcp_servers.<server>.default_tools_approval_mode`

`auto | prompt | writes | approve`

Default approval behavior for tools on a plugin-provided MCP server.

`plugins.<plugin>.mcp_servers.<server>.disabled_tools`

`array<string>`

Deny list applied after `enabled_tools` for a plugin-provided MCP server.

`plugins.<plugin>.mcp_servers.<server>.enabled`

`boolean`

Enable or disable an MCP server bundled by an installed plugin without changing the plugin manifest.

`plugins.<plugin>.mcp_servers.<server>.enabled_tools`

`array<string>`

Allow list of tools exposed from a plugin-provided MCP server.

`plugins.<plugin>.mcp_servers.<server>.tools.<tool>.approval_mode`

`auto | prompt | writes | approve`

Per-tool approval behavior override for a plugin-provided MCP tool.

`project_doc_fallback_filenames`

`array<string>`

Additional filenames to try when `AGENTS.md` is missing.

`project_doc_max_bytes`

`number`

Maximum bytes read from `AGENTS.md` when building project instructions.

`project_root_markers`

`array<string>`

List of project root marker filenames; used when searching parent directories for the project root.

`projects.<path>.trust_level`

`string`

Mark a project or worktree as trusted or untrusted (`"trusted"` | `"untrusted"`). Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules.

`review_model`

`string`

Optional model override used by `/review` (defaults to the current session model).

`sandbox_mode`

`read-only | workspace-write | danger-full-access`

Sandbox policy for filesystem and network access during command execution.

`sandbox_workspace_write.exclude_slash_tmp`

`boolean`

Exclude `/tmp` from writable roots in workspace-write mode.

`sandbox_workspace_write.exclude_tmpdir_env_var`

`boolean`

Exclude `$TMPDIR` from writable roots in workspace-write mode.

`sandbox_workspace_write.network_access`

`boolean`

Allow outbound network access inside the workspace-write sandbox.

`sandbox_workspace_write.writable_roots`

`array<string>`

Additional writable roots when `sandbox_mode = "workspace-write"`.

`service_tier`

`string`

Preferred service tier for new turns. Use `fast` or another tier advertised by the active model; `fast` maps to the request value `priority`.

`shell_environment_policy.exclude`

`array<string>`

Legacy environment-variable exclusion patterns. Use `shell_environment_policy.filters` for new configuration; don't combine both forms in the same layer.

`shell_environment_policy.experimental_use_profile`

`boolean`

Use the user shell profile when spawning subprocesses.

`shell_environment_policy.filters`

`map<string, include | exclude>`

Canonical case-insensitive environment-variable pattern filters. Include entries create an allowlist and can't restore excluded values. Explicit `set` values apply after exclusions. Don't combine filters with legacy `exclude` or `include_only` arrays in the same layer.

`shell_environment_policy.ignore_default_excludes`

`boolean`

Keep variables containing KEY, SECRET, or TOKEN before other filters run (default: true). Set to false to apply automatic secret-name exclusions.

`shell_environment_policy.include_only`

`array<string>`

Legacy allowlist of environment-variable patterns. Use `shell_environment_policy.filters` for new configuration; don't combine both forms in the same layer.

`shell_environment_policy.inherit`

`all | core | none`

Baseline environment inheritance when spawning subprocesses.

`shell_environment_policy.set`

`map<string,string>`

Explicit environment values injected after exclusions; include filters can still remove them.

`show_raw_agent_reasoning`

`boolean`

Surface raw reasoning content when the active model emits it.

`skills.config`

`array<object>`

Per-skill enablement overrides stored in config.toml.

`skills.config.<index>.enabled`

`boolean`

Enable or disable the referenced skill.

`skills.config.<index>.path`

`string (path)`

Path to a skill folder containing `SKILL.md`.

`skills.max_context_tokens`

`integer (positive)`

Token budget for the available-skills catalog. Defaults to 2% of the model's context window. Explicit values are capped at `10000` tokens.

`sqlite_home`

`string (path)`

Directory where Codex stores the SQLite-backed state DB used by agent jobs and other resumable runtime state.

`suppress_unstable_features_warning`

`boolean`

Suppress the warning that appears when under-development feature flags are enabled.

`tool_output_token_limit`

`number`

Token budget for storing individual tool/function outputs in history.

`tool_suggest.disabled_tools`

`array<table>`

Disable suggestions for specific discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`.

`tool_suggest.discoverables`

`array<table>`

Allow tool suggestions for additional discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`.

`tools.view_image`

`boolean`

Enable the local-image attachment tool `view_image`.

`tools.web_search`

`boolean | { context_size = "low|medium|high", allowed_domains = [string], location = { country, region, city, timezone } }`

Optional web search tool configuration. The object form can set search context size, allowed search domains, and approximate user location. These search-domain filters are separate from sandboxed-command network domain rules and do not restrict connectors or MCP servers.

`tui`

`table`

TUI-specific options such as enabling inline desktop notifications.

`tui.alternate_screen`

`auto | always | never`

Control alternate screen usage for the TUI (default: auto; auto skips it in Zellij to preserve scrollback).

`tui.animations`

`boolean`

Enable terminal animations (welcome screen, shimmer, spinner) (default: true).

`tui.keymap.<context>.<action>`

`string | array<string>`

Keyboard shortcut binding for a TUI action. Supported contexts include `global`, `chat`, `composer`, `editor`, `vim_normal`, `vim_operator`, `vim_text_object`, `pager`, `list`, and `approval`. Selected composer actions fall back to matching `tui.keymap.global` bindings; context-specific bindings take precedence when supported.

`tui.keymap.<context>.<action> = []`

`empty array`

Unbind the action in that keymap context. Key names use normalized strings such as `ctrl-a`, `shift-enter`, `page-down`, or `minus`.

`tui.model_availability_nux.<model>`

`integer`

Internal startup-tooltip state keyed by model slug.

`tui.notification_condition`

`unfocused | always`

Control whether TUI notifications fire only when the terminal is unfocused or regardless of focus. Defaults to `unfocused`.

`tui.notification_method`

`auto | osc9 | bel`

Notification method for terminal notifications (default: auto).

`tui.notifications`

`boolean | array<string>`

Enable TUI notifications; optionally restrict to specific event types.

`tui.raw_output_mode`

`boolean`

Start the TUI in raw scrollback mode for copy-friendly terminal selection (default: false). You can toggle it with `/raw` or the default `alt-r` key binding.

`tui.resume_cwd`

`current | session`

Working directory to use when resuming or forking a session. When unset, Codex asks you to choose if your current directory differs from the session's saved directory.

`tui.show_tooltips`

`boolean`

Show onboarding tooltips in the TUI welcome screen (default: true).

`tui.status_line`

`array<string> | null`

Ordered list of TUI footer status-line item identifiers. `null` disables the status line.

`tui.terminal_title`

`array<string> | null`

Ordered list of terminal window/tab title item identifiers. Defaults to `["spinner", "project"]`; `null` disables title updates.

`tui.theme`

`string`

Syntax-highlighting theme override (kebab-case theme name).

`tui.vim_mode_default`

`boolean`

Start the composer in Vim normal mode instead of insert mode (default: false). You can still toggle it per session with `/vim`.

`web_search`

`disabled | cached | indexed | live`

Web search mode (default: `"cached"`; cached uses an OpenAI-maintained index without external web access; indexed permits external access only when gated by the search index; if you use `--yolo` or another full access sandbox setting, it defaults to `"live"`). Use `"live"` for unrestricted live retrieval, or `"disabled"` to remove the tool.

`windows_wsl_setup_acknowledged`

`boolean`

Track Windows onboarding acknowledgement (Windows only).

`windows.sandbox`

`unelevated | elevated | mxc`

Windows-only native sandbox mode when running Codex natively on Windows.

Key `agents` Type / Values `table` Details Multi-agent settings and custom role declarations. Scalar setting names are reserved and can't be used as custom role names. Key `agents.<name>.config_file` Type / Values `string (path)` Details Path to a TOML config layer for that role; relative paths resolve from the config file that declares the role. Key `agents.<name>.description` Type / Values `string` Details Role guidance shown to Codex when choosing and spawning that agent type. Key `agents.default_subagent_model` Type / Values `string` Details Default model for spawned agents. An explicit spawn model takes precedence. Key `agents.default_subagent_reasoning_effort` Type / Values `string` Details Default reasoning effort for spawned agents. An explicit spawn effort takes precedence. Key `agents.enabled` Type / Values `boolean` Details Enable or disable multi-agent tools (default: true). Key `agents.interrupt_message` Type / Values `boolean` Details Record a model-visible message when an agent turn is interrupted (default: true). Key `agents.max_concurrent_threads_per_session` Type / Values `number` Details Maximum number of spawned-agent threads that can be open concurrently, excluding the primary thread. When unset, Codex chooses the default. Key `agents.max_threads` Type / Values `number` Details Legacy alias for `agents.max_concurrent_threads_per_session`. Key `allow_login_shell` Type / Values `boolean` Details Allow shell-based tools to use login-shell semantics. Defaults to `true`; when `false`, `login = true` requests are rejected and omitted `login` defaults to non-login shells. Key `analytics.enabled` Type / Values `boolean` Details Enable or disable analytics for this machine/profile. When unset, the client default applies. Key `approval_policy` Type / Values `on-request | never | { granular = { sandbox_approval = bool, rules = bool, mcp_elicitations = bool, request_permissions = bool, skill_approval = bool } }` Details Controls when Codex pauses for approval before executing commands. You can also use `approval_policy = { granular = { ... } }` to allow or auto-reject specific prompt categories while keeping other prompts interactive. `untrusted` is unsupported, and `on-failure` is deprecated; use `on-request` for interactive runs or `never` for non-interactive runs. Key `approval_policy.granular.mcp_elicitations` Type / Values `boolean` Details When `true`, MCP elicitation prompts are allowed to surface instead of being auto-rejected. Key `approval_policy.granular.request_permissions` Type / Values `boolean` Details When `true`, prompts from the `request_permissions` tool are allowed to surface. Key `approval_policy.granular.rules` Type / Values `boolean` Details When `true`, approvals triggered by execpolicy `prompt` rules are allowed to surface. Key `approval_policy.granular.sandbox_approval` Type / Values `boolean` Details When `true`, sandbox escalation approval prompts are allowed to surface. Key `approval_policy.granular.skill_approval` Type / Values `boolean` Details When `true`, skill-script approval prompts are allowed to surface. Key `approvals_reviewer` Type / Values `user | auto_review` Details Who reviews eligible approval prompts under `on-request` or granular approval policies. Defaults to `user`; `auto_review` uses the reviewer subagent. This setting doesn't change sandboxing or review actions already allowed inside the sandbox. Key `apps._default.approvals_reviewer` Type / Values `user | auto_review` Details Default reviewer for app tool approval prompts unless overridden per app. When omitted, apps inherit the top-level `approvals_reviewer` value. Key `apps._default.default_tools_approval_mode` Type / Values `auto | prompt | writes | approve` Details Default approval behavior for app tools without per-app or per-tool overrides. Key `apps._default.destructive_enabled` Type / Values `boolean` Details Default allow/deny for app tools with `destructive_hint = true`. Key `apps._default.enabled` Type / Values `boolean` Details Default app enabled state for all apps unless overridden per app. Key `apps._default.open_world_enabled` Type / Values `boolean` Details Default allow/deny for app tools with `open_world_hint = true`. Key `apps.<id>.approvals_reviewer` Type / Values `user | auto_review` Details Reviewer for this app's tool approval prompts. Overrides `apps._default.approvals_reviewer`. Key `apps.<id>.default_tools_approval_mode` Type / Values `auto | prompt | writes | approve` Details Default approval behavior for tools in this app unless a per-tool override exists. Key `apps.<id>.default_tools_enabled` Type / Values `boolean` Details Default enabled state for tools in this app unless a per-tool override exists. Key `apps.<id>.destructive_enabled` Type / Values `boolean` Details Allow or block tools in this app that advertise `destructive_hint = true`. Key `apps.<id>.enabled` Type / Values `boolean` Details Enable or disable a specific app/connector by id (default: true). Key `apps.<id>.open_world_enabled` Type / Values `boolean` Details Allow or block tools in this app that advertise `open_world_hint = true`. Key `apps.<id>.tools.<tool>.approval_mode` Type / Values `auto | prompt | writes | approve` Details Per-tool approval behavior override for a single app tool. Key `apps.<id>.tools.<tool>.enabled` Type / Values `boolean` Details Per-tool enabled override for an app tool (for example `repos/list`). Key `auto_review.extra_policy` Type / Values `string` Details Additional local Markdown policy for automatic review, included alongside the main policy. Managed `guardian_extra_policy` takes precedence. Blank values are ignored. Key `auto_review.policy` Type / Values `string` Details Local Markdown policy instructions for automatic review. Managed `guardian_policy_config` takes precedence. Blank values are ignored. Key `background_terminal_max_timeout` Type / Values `number` Details Maximum poll window in milliseconds for empty `write_stdin` polls (background terminal polling). Default: `300000` (5 minutes). Replaces the older `background_terminal_timeout` key. Key `browser_use.allow_history_access` Type / Values `boolean` Details Set to `false` to restrict browser-history access. Managed requirements can enforce this restriction. Key `browser_use.default_origin_policy` Type / Values `table` Details Fallback browser-origin restrictions. Supports `access`, `uploads`, `downloads`, and `full_cdp_access`, each set to `allow` or `deny`. Key `browser_use.origins.<origin>` Type / Values `table` Details Per-origin browser restrictions with the same fields as `browser_use.default_origin_policy`. Include an HTTP or HTTPS scheme and optional port; omit paths, queries, and fragments. Local values cannot relax managed denies. Key `chatgpt_base_url` Type / Values `string` Details Override the base URL used during the ChatGPT login flow. Key `check_for_update_on_startup` Type / Values `boolean` Details Check for Codex updates on startup (set to false only when updates are centrally managed). Key `cli_auth_credentials_store` Type / Values `file | keyring | auto | ephemeral` Details Control where the CLI stores cached credentials. Key `compact_prompt` Type / Values `string` Details Inline override for the history compaction prompt. Key `computer_use.default_app_access` Type / Values `allow | deny` Details Fallback native-app access policy for Computer Use. App-specific entries can supply a policy; local configuration cannot relax managed restrictions. Key `computer_use.macos.bundle_ids` Type / Values `map<string, allow | deny>` Details Native macOS app access keyed by bundle identifier. Key `computer_use.windows.always_allowed_app_ids` Type / Values `array<string>` Details Windows app identifiers that Computer Use can open without prompting. Apps not in the list require approval; remove saved entries from the ChatGPT desktop app's Computer Use settings. Key `computer_use.windows.aumids` Type / Values `map<string, allow | deny>` Details Packaged Windows app access keyed by Application User Model ID (AUMID). Key `computer_use.windows.exes` Type / Values `array<table>` Details Windows executable access rules. Each rule requires `publisher_name`, `product_name`, and `access` (`allow` or `deny`); `binary_name` is optional. Key `default_permissions` Type / Values `string` Details Name of the default permissions profile to apply to sandboxed tool calls. Built-ins are `:read-only`, `:workspace`, and `:danger-full-access`; custom profile names require matching `[permissions.<name>]` tables. Don't combine with `sandbox_mode` or `[sandbox_workspace_write]`. Key `desktop.custom_file_handlers.<id>` Type / Values `table` Details User-level only. Defines an additional **Open in** target for the ChatGPT desktop app. See [Add custom file handlers](https://learn.chatgpt.com/codex/config-file/config-advanced#add-custom-file-handlers) for examples and handler ID constraints. Key `desktop.custom_file_handlers.<id>.args` Type / Values `array<string>` Details Arguments inserted between the command and file input (default: `[]`). Key `desktop.custom_file_handlers.<id>.command` Type / Values `string` Details Executable path or command name to detect and launch. Required. Key `desktop.custom_file_handlers.<id>.icon` Type / Values `string` Details Bundled asset path, Base64-encoded `data:image/...` URL, file URI, or absolute local path for the handler icon. Required; unsupported sources use the default VS Code icon. Key `desktop.custom_file_handlers.<id>.input` Type / Values `path | json_argument | json_stdin` Details How the app sends file input to the handler (default: `path`). Key `desktop.custom_file_handlers.<id>.label` Type / Values `string` Details Display name shown in **Open in** menus. Required. Key `desktop.custom_file_handlers.<id>.supports_ssh` Type / Values `boolean` Details Offer the handler for files in SSH workspaces (default: `false`). Key `developer_instructions` Type / Values `string` Details Additional developer instructions injected into the session (optional). Key `disable_paste_burst` Type / Values `boolean` Details Disable burst-paste detection in the TUI. Key `experimental_compact_prompt_file` Type / Values `string (path)` Details Load the compaction prompt override from a file (experimental). Key `experimental_use_unified_exec_tool` Type / Values `boolean` Details Legacy name for enabling unified exec; prefer `[features].unified_exec` or `codex --enable unified_exec`. Key `features.apps` Type / Values `boolean` Details Enable app (connector) integrations (stable; on by default). App and connector traffic is not controlled by the sandboxed-command network proxy or its domain allowlist. Key `features.code_mode.direct_only_tool_namespaces` Type / Values `array<string>` Details Tool namespaces code mode can use only through direct tool calls. Key `features.code_mode.enabled` Type / Values `boolean` Details Enable code mode feature configuration. This feature is under development and off by default. Key `features.code_mode.excluded_tool_namespaces` Type / Values `array<string>` Details Tool namespaces code mode excludes from nested code-mode tool guidance and executor exposure. Key `features.context_management.experimental_mode` Type / Values `boolean` Details Experimental context-management setting. The feature is not currently available. Key `features.enable_request_compression` Type / Values `boolean` Details Compress streaming request bodies with zstd when supported (stable; on by default). Key `features.fast_mode` Type / Values `boolean` Details Enable model-catalog service tier selection in the TUI, including Fast-tier commands when the active model advertises them (stable; on by default). Key `features.goals` Type / Values `boolean` Details Enable persisted goals and automatic continuation (stable; on by default). Key `features.hooks` Type / Values `boolean` Details Enable lifecycle hooks loaded from `hooks.json` or inline `[hooks]` config. `features.codex_hooks` is a deprecated alias. Key `features.memories` Type / Values `boolean` Details Enable [Memories](https://learn.chatgpt.com/codex/customization/memories) (off by default). Key `features.multi_agent` Type / Values `boolean` Details Enable multi-agent collaboration tools (`spawn_agent`, `send_input`, `resume_agent`, `wait_agent`, and `close_agent`) (stable; on by default). Key `features.network_proxy` Type / Values `boolean | table` Details Start the network proxy for sandboxed commands (experimental; off by default). Required to enforce permission-profile domain rules unless enabled administrator-managed `experimental_network` requirements start the proxy. Use a table when setting feature-level policy options such as `domains`. Does not filter web search, apps, MCP, or other hosted tools. Key `features.network_proxy.allow_local_binding` Type / Values `boolean` Details Allow broader local/private-network access. Defaults to `false`; exact local IP literal or `localhost` allow rules can still permit specific local targets. Key `features.network_proxy.allow_upstream_proxy` Type / Values `boolean` Details Allow chaining through an upstream proxy from the environment. Defaults to `true`. Key `features.network_proxy.dangerously_allow_all_unix_sockets` Type / Values `boolean` Details Permit arbitrary Unix socket destinations instead of allowlist-only access. Defaults to `false`; use only in tightly controlled environments. Key `features.network_proxy.dangerously_allow_non_loopback_proxy` Type / Values `boolean` Details Permit non-loopback listener addresses. Defaults to `false`; enabling it can expose proxy listeners beyond localhost. Key `features.network_proxy.domains` Type / Values `map<string, allow | deny>` Details Domain policy for sandboxed networking. Unset by default, which means no external destinations are allowed until you add `allow` rules. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules. Prefer scoped rules because `*` broadly opens public outbound access. Add `deny` rules for blocked destinations; `deny` wins on conflicts. Key `features.network_proxy.enable_socks5` Type / Values `boolean` Details Expose SOCKS5 support. Defaults to `true`. Key `features.network_proxy.enable_socks5_udp` Type / Values `boolean` Details Allow UDP over SOCKS5. Defaults to `true`. Key `features.network_proxy.enabled` Type / Values `boolean` Details Start the sandboxed-command network proxy when command network access is enabled. Defaults to `false`; permission-profile domain rules are not enforced while the proxy is off. Key `features.network_proxy.proxy_url` Type / Values `string` Details HTTP listener URL for sandboxed networking. Defaults to `"http://127.0.0.1:3128"`. Key `features.network_proxy.socks_url` Type / Values `string` Details SOCKS5 listener URL. Defaults to `"http://127.0.0.1:8081"`. Key `features.network_proxy.unix_sockets` Type / Values `map<string, allow | deny>` Details Unix socket policy for sandboxed networking. Unset by default; add `allow` entries for permitted sockets. Key `features.personality` Type / Values `boolean` Details Enable personality selection controls (stable; on by default). Key `features.prevent_idle_sleep` Type / Values `boolean` Details Prevent the machine from sleeping while a turn is actively running (experimental; off by default). Key `features.remote_plugin` Type / Values `boolean` Details Enable the remote plugin catalog (stable; on by default). Key `features.rollout_budget.enabled` Type / Values `boolean` Details Enable rollout budget tracking. This feature is under development and off by default. When enabled, `features.rollout_budget.limit_tokens` is required. Key `features.rollout_budget.limit_tokens` Type / Values `integer` Details Positive token limit for rollout budget tracking. Required when rollout budget is enabled. Key `features.rollout_budget.prefill_token_weight` Type / Values `number` Details Finite non-negative multiplier for prefill tokens in rollout budget accounting. Defaults to `1.0`. Key `features.rollout_budget.reminder_interval_tokens` Type / Values `integer` Details Positive token interval between rollout budget reminders. Defaults to 10% of `limit_tokens`, with a minimum of 1 token. Key `features.rollout_budget.sampling_token_weight` Type / Values `number` Details Finite non-negative multiplier for sampled tokens in rollout budget accounting. Defaults to `1.0`. Key `features.shell_snapshot` Type / Values `boolean` Details Snapshot shell environment to speed up repeated commands (stable; on by default). Key `features.shell_tool` Type / Values `boolean` Details Enable the default `shell` tool for running commands (stable; on by default). Key `features.skill_mcp_dependency_install` Type / Values `boolean` Details Allow prompting and installing missing MCP dependencies for skills (stable; on by default). Key `features.unified_exec` Type / Values `boolean` Details Use the unified PTY-backed exec tool (stable; enabled by default except on Windows). Key `features.web_search` Type / Values `boolean` Details Deprecated legacy toggle; prefer the top-level `web_search` setting. Key `features.web_search_cached` Type / Values `boolean` Details Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "cached"`. Key `features.web_search_request` Type / Values `boolean` Details Deprecated legacy toggle. When `web_search` is unset, true maps to `web_search = "live"`. Key `feedback.enabled` Type / Values `boolean` Details Enable feedback submission via `/feedback` across local clients (default: true). Key `file_opener` Type / Values `vscode | vscode-insiders | windsurf | cursor | none` Details URI scheme used to open citations from Codex output (default: `vscode`). Key `forced_chatgpt_workspace_id` Type / Values `string (uuid)` Details Limit ChatGPT logins to a specific workspace identifier. Key `forced_login_method` Type / Values `chatgpt | api` Details Restrict Codex to a specific authentication method. Key `hide_agent_reasoning` Type / Values `boolean` Details Suppress reasoning events in both the TUI and `codex exec` output. Key `history.max_bytes` Type / Values `number` Details If set, caps the history file size in bytes by dropping oldest entries. Key `history.persistence` Type / Values `save-all | none` Details Control whether Codex saves session transcripts to history.jsonl. Key `hooks` Type / Values `table` Details Lifecycle hooks configured inline in `config.toml`. Uses the same event schema as `hooks.json`; see the Hooks guide for examples and supported events. Key `hooks.<Event>` Type / Values `array<table>` Details Matcher groups for hook events such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, `Stop`, or `Interrupt`. Key `hooks.<Event>[].hooks` Type / Values `array<table>` Details Hook handlers for a matcher group. Command and MCP tool hooks are supported while prompt and agent hook handlers are parsed but skipped. Key `hooks.<Event>[].hooks[].additionalContextLimit` Type / Values `integer` Details Approximate per-handler token threshold for saving oversized `additionalContext` to disk and showing the model a shorter preview. Defaults to `2500`; `0` passes the full context directly to the model. See [Large hook output](https://learn.chatgpt.com/codex/hooks#large-hook-output). Key `hooks.<Event>[].hooks[].async` Type / Values `boolean` Details Run a command hook in the background without delaying the triggering operation. Defaults to `false`; `SessionEnd` always runs synchronously. See [Run hooks in the background](https://learn.chatgpt.com/codex/hooks#run-hooks-in-the-background). Key `hooks.<Event>[].hooks[].commandWindows` Type / Values `string` Details Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted. Key `instructions` Type / Values `string` Details Reserved for future use; prefer `model_instructions_file` or `AGENTS.md`. Key `log_dir` Type / Values `string (path)` Details Directory where Codex writes log files; defaults to `$CODEX_HOME/log`. Setting this explicitly also enables the opt-in plaintext TUI log, `codex-tui.log`, in that directory. Key `marketplaces.<name>.ref` Type / Values `string` Details Optional Git branch, tag, or commit for the marketplace. Key `marketplaces.<name>.source` Type / Values `string` Details Git repository location or local marketplace root directory. Use an absolute path for a local source; the directory contains .agents/plugins/marketplace.json. Key `marketplaces.<name>.source_type` Type / Values `git | local` Details Source kind for a configured plugin marketplace. Marketplaces can be defined in system, cloud-managed, user, or trusted-project config.toml. Key `marketplaces.<name>.sparse_paths` Type / Values `array<string>` Details Optional sparse checkout paths for a Git marketplace. Include the marketplace catalog and any local plugin directories it references. Key `mcp_oauth_callback_port` Type / Values `integer` Details Optional global fixed port for the local HTTP callback server used during MCP OAuth login. A server-specific `oauth.callback_port` takes precedence. When neither is set, Codex binds to an ephemeral port chosen by the OS. Key `mcp_oauth_callback_url` Type / Values `string` Details Optional base callback URL for MCP OAuth login, such as a devbox ingress URL. Newly added pre-registered clients use this URL unchanged when the authorization server supports issuer identification; existing clients without a saved callback append a server-specific callback ID. Without issuer support, any pre-registered MCP server whose configured callback lacks the required ID falls back to this URL with the ID appended. Callback URL ports don't select the listener port. Key `mcp_oauth_credentials_store` Type / Values `auto | file | keyring` Details Preferred store for MCP OAuth credentials. Key `mcp_optional_startup_grace_ms` Type / Values `integer (milliseconds)` Details Shared wait for optional MCP servers when building the initial tool catalog. Defaults to `1000`. Set to `0` to wait for each server's `startup_timeout_sec` instead. Key `mcp_servers.<id>.args` Type / Values `array<string>` Details Arguments passed to the MCP stdio server command. Key `mcp_servers.<id>.auth` Type / Values `oauth | chatgpt` Details Authentication fallback for an MCP HTTP server after configured bearer tokens and authorization headers. `oauth` (default) uses stored MCP OAuth credentials when available. `chatgpt` uses the current ChatGPT session for the trusted first-party ChatGPT origin, then falls back to stored OAuth. Both modes can connect without authentication if no credential source resolves. Key `mcp_servers.<id>.bearer_token_env_var` Type / Values `string` Details Environment variable sourcing the bearer token for an MCP HTTP server. Key `mcp_servers.<id>.command` Type / Values `string` Details Launcher command for an MCP stdio server. Key `mcp_servers.<id>.cwd` Type / Values `string` Details Working directory for the MCP stdio server process. Key `mcp_servers.<id>.default_tools_approval_mode` Type / Values `auto | prompt | writes | approve` Details Default approval behavior for MCP tools on this server unless a per-tool override exists. Key `mcp_servers.<id>.disabled_tools` Type / Values `array<string>` Details Deny list applied after `enabled_tools` for the MCP server. Key `mcp_servers.<id>.enabled` Type / Values `boolean` Details Disable an MCP server without removing its configuration. Key `mcp_servers.<id>.enabled_tools` Type / Values `array<string>` Details Allow list of tool names exposed by the MCP server. Key `mcp_servers.<id>.env` Type / Values `map<string,string>` Details Environment variables forwarded to the MCP stdio server. Key `mcp_servers.<id>.env_http_headers` Type / Values `map<string,string>` Details HTTP headers populated from environment variables for an MCP HTTP server. Key `mcp_servers.<id>.env_vars` Type / Values `array<string | { name = string, source = "local" | "remote" }>` Details Additional environment variables to whitelist for an MCP stdio server. String entries default to `source = "local"`; use `source = "remote"` only with executor-backed remote stdio. Key `mcp_servers.<id>.experimental_environment` Type / Values `local | remote` Details Experimental placement for an MCP server. `remote` starts stdio servers through a remote executor environment; streamable HTTP remote placement is not implemented. Key `mcp_servers.<id>.http_headers` Type / Values `map<string,string>` Details Static HTTP headers included with each MCP HTTP request. Key `mcp_servers.<id>.http_headers_helper` Type / Values `string (command)` Details Local command that prints a JSON object of HTTP header names and values. Supported only for locally connected HTTP MCP servers. Explicit bearer tokens and OAuth credentials take precedence over helper-provided Authorization headers. Key `mcp_servers.<id>.oauth_resource` Type / Values `string` Details Optional RFC 8707 OAuth resource parameter to include during MCP login. Key `mcp_servers.<id>.oauth.callback_port` Type / Values `integer` Details Fixed OAuth callback listener port for this MCP server. Overrides `mcp_oauth_callback_port`. For a direct loopback callback with an explicit URL port, configure the same listener port. Key `mcp_servers.<id>.oauth.callback_url` Type / Values `string` Details Server-specific OAuth callback. Pre-registered clients reuse it when issuer identification is supported or the URL already ends in the server-specific callback ID. Otherwise, Codex uses the global or default callback with that ID appended. Clients without a pre-registered ID use this callback during client registration. Key `mcp_servers.<id>.oauth.client_id` Type / Values `string` Details Pre-registered OAuth client ID used for authorization and token exchange with this MCP server. Key `mcp_servers.<id>.required` Type / Values `boolean` Details When true, fail startup/resume if this enabled MCP server cannot initialize. Key `mcp_servers.<id>.scopes` Type / Values `array<string>` Details OAuth scopes to request when authenticating to that MCP server. Key `mcp_servers.<id>.startup_timeout_ms` Type / Values `number` Details Alias for `startup_timeout_sec` in milliseconds. Key `mcp_servers.<id>.startup_timeout_sec` Type / Values `number` Details Override the default 10s startup timeout for an MCP server. Key `mcp_servers.<id>.tool_timeout_sec` Type / Values `number` Details Override the default 60s per-tool timeout for an MCP server. Key `mcp_servers.<id>.tools.<tool>.approval_mode` Type / Values `auto | prompt | writes | approve` Details Per-tool approval behavior override for one MCP tool on this server. Key `mcp_servers.<id>.tools.<tool>.output_token_limit` Type / Values `integer (positive)` Details Token budget for one MCP tool's output, before the standard 20% serialization allowance. Overrides the model's default output truncation budget for that tool. Key `mcp_servers.<id>.url` Type / Values `string` Details Endpoint for an MCP streamable HTTP server. Key `memories.consolidation_model` Type / Values `string` Details Optional model override for global memory consolidation. Key `memories.disable_on_external_context` Type / Values `boolean` Details When `true`, threads that use external context such as MCP tool calls, web search, or tool search are kept out of memory generation. Defaults to `false`. Legacy alias: `memories.no_memories_if_mcp_or_web_search`. Key `memories.extract_model` Type / Values `string` Details Optional model override for per-thread memory extraction. Key `memories.generate_memories` Type / Values `boolean` Details When `false`, newly created threads are not stored as memory-generation inputs. Defaults to `true`. Key `memories.max_raw_memories_for_consolidation` Type / Values `number` Details Maximum recent raw memories retained for global consolidation. Defaults to `256` and is capped at `4096`. Key `memories.max_rollout_age_days` Type / Values `number` Details Maximum age of threads considered for memory generation. Defaults to `30` and is clamped to `0` - `90`. Key `memories.max_rollouts_per_startup` Type / Values `number` Details Maximum rollout candidates processed per startup pass. Defaults to `16` and is capped at `128`. Key `memories.max_unused_days` Type / Values `number` Details Maximum days since a memory was last used before it becomes ineligible for consolidation. Defaults to `30` and is clamped to `0` - `365`. Key `memories.min_rate_limit_remaining_percent` Type / Values `number` Details Minimum remaining percentage required in Codex rate-limit windows before memory generation starts. Defaults to `25` and is clamped to `0` - `100`. Key `memories.min_rollout_idle_hours` Type / Values `number` Details Minimum idle time before a thread is considered for memory generation. Defaults to `6` and is clamped to `1` - `48`. Key `memories.use_memories` Type / Values `boolean` Details When `false`, Codex skips injecting existing memories into future sessions. Defaults to `true`. Key `model` Type / Values `string` Details Model to use (e.g., `gpt-6.1-sol`). Key `model_auto_compact_token_limit` Type / Values `number` Details Token threshold that triggers automatic history compaction (unset uses model defaults). Key `model_auto_compact_token_limit_scope` Type / Values `total | body_after_prefix` Details Controls whether the auto-compaction threshold counts the full active context (`total`, the default) or only growth after the carried compaction-window prefix (`body_after_prefix`). Key `model_catalog_json` Type / Values `string (path)` Details Optional path to a JSON model catalog loaded on startup. A selected `$CODEX_HOME/profile-name.config.toml` profile file can override this per profile. Key `model_context_window` Type / Values `number` Details Context window tokens available to the active model. Key `model_instructions_file` Type / Values `string (path)` Details Replacement for built-in instructions instead of `AGENTS.md`. Key `model_provider` Type / Values `string` Details Provider id from `model_providers` (default: `openai`). Key `model_providers.<id>` Type / Values `table` Details Custom provider definition. Built-in provider IDs (`openai`, `ollama`, and `lmstudio`) are reserved and cannot be overridden. Key `model_providers.<id>.auth` Type / Values `table` Details Command-backed bearer token configuration for a custom provider. Do not combine with `env_key`, `experimental_bearer_token`, or `requires_openai_auth`. Key `model_providers.<id>.auth.args` Type / Values `array<string>` Details Arguments passed to the token command. Key `model_providers.<id>.auth.command` Type / Values `string` Details Command to run when Codex needs a bearer token. The command must print the token to stdout. Key `model_providers.<id>.auth.cwd` Type / Values `string (path)` Details Working directory for the token command. Key `model_providers.<id>.auth.refresh_interval_ms` Type / Values `number` Details How often Codex proactively refreshes the token in milliseconds (default: 300000). Set to `0` to refresh only after an authentication retry. Key `model_providers.<id>.auth.timeout_ms` Type / Values `number` Details Maximum token command runtime in milliseconds (default: 5000). Key `model_providers.<id>.base_url` Type / Values `string` Details API base URL for the model provider. Key `model_providers.<id>.env_http_headers` Type / Values `map<string,string>` Details HTTP headers populated from environment variables when present. Key `model_providers.<id>.env_key` Type / Values `string` Details Environment variable supplying the provider API key. Key `model_providers.<id>.env_key_instructions` Type / Values `string` Details Optional setup guidance for the provider API key. Key `model_providers.<id>.experimental_bearer_token` Type / Values `string` Details Direct bearer token for the provider (discouraged; use `env_key`). Key `model_providers.<id>.http_headers` Type / Values `map<string,string>` Details Static HTTP headers added to provider requests. Key `model_providers.<id>.name` Type / Values `string` Details Display name for a custom model provider. Key `model_providers.<id>.query_params` Type / Values `map<string,string>` Details Extra query parameters appended to provider requests. Key `model_providers.<id>.request_max_retries` Type / Values `number` Details Retry count for HTTP requests to the provider (default: 4). Key `model_providers.<id>.requires_openai_auth` Type / Values `boolean` Details The provider uses OpenAI authentication (defaults to false). Key `model_providers.<id>.stream_idle_timeout_ms` Type / Values `number` Details Idle timeout for SSE streams in milliseconds (default: 300000). Key `model_providers.<id>.stream_max_retries` Type / Values `number` Details Retry count for SSE streaming interruptions (default: 5). Key `model_providers.<id>.supports_standalone_web_search` Type / Values `boolean` Details Advertise support for a compatible standalone web search endpoint (default: false). Standalone search remains under development and off by default; provider compatibility alone doesn't enable it. Key `model_providers.<id>.supports_websockets` Type / Values `boolean` Details Whether that provider supports the Responses API WebSocket transport. Key `model_providers.<id>.wire_api` Type / Values `responses` Details Protocol used by the provider. `responses` is the only supported value, and it is the default when omitted. Key `model_providers.amazon-bedrock.aws.profile` Type / Values `string` Details AWS profile name used by the built-in `amazon-bedrock` provider. Key `model_providers.amazon-bedrock.aws.region` Type / Values `string` Details AWS region used by the built-in `amazon-bedrock` provider. Key `model_reasoning_effort` Type / Values `string` Details Reasoning effort advertised by the selected model, such as `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`. Available levels depend on the model and client. Key `model_reasoning_summary` Type / Values `auto | concise | detailed | none` Details Select reasoning summary detail or disable summaries entirely. Key `model_supports_reasoning_summaries` Type / Values `boolean` Details Force Codex to send or not send reasoning metadata. Key `model_verbosity` Type / Values `low | medium | high` Details Optional GPT-5 Responses API verbosity override; when unset, the selected model/preset default is used. Key `notice.hide_full_access_warning` Type / Values `boolean` Details Track acknowledgement of the full access warning prompt. Key `notice.hide_gpt-5.1-codex-max_migration_prompt` Type / Values `boolean` Details Track acknowledgement of the gpt-5.1-codex-max migration prompt. Key `notice.hide_gpt5_1_migration_prompt` Type / Values `boolean` Details Track acknowledgement of the GPT-5.1 migration prompt. Key `notice.hide_rate_limit_model_nudge` Type / Values `boolean` Details Track opt-out of the rate limit model switch reminder. Key `notice.hide_world_writable_warning` Type / Values `boolean` Details Track acknowledgement of the Windows world-writable directories warning. Key `notice.model_migrations` Type / Values `map<string,string>` Details Track acknowledged model migrations as old->new mappings. Key `notify` Type / Values `array<string>` Details Command invoked for notifications; receives a JSON payload from Codex. Key `openai_base_url` Type / Values `string` Details Base URL override for the built-in `openai` model provider. Key `oss_provider` Type / Values `lmstudio | ollama` Details Default local provider used when running with `--oss` (defaults to prompting if unset). Key `otel.environment` Type / Values `string` Details Environment tag applied to emitted OpenTelemetry events (default: `dev`). Key `otel.exporter` Type / Values `none | otlp-http | otlp-grpc` Details Select the OpenTelemetry exporter and provide any endpoint metadata. Key `otel.exporter.<id>.endpoint` Type / Values `string` Details Exporter endpoint for OTEL logs. Key `otel.exporter.<id>.headers` Type / Values `map<string,string>` Details Static headers included with OTEL exporter requests. Key `otel.exporter.<id>.protocol` Type / Values `binary | json` Details Protocol used by the OTLP/HTTP exporter. Key `otel.exporter.<id>.tls.ca-certificate` Type / Values `string` Details CA certificate path for OTEL exporter TLS. Key `otel.exporter.<id>.tls.client-certificate` Type / Values `string` Details Client certificate path for OTEL exporter TLS. Key `otel.exporter.<id>.tls.client-private-key` Type / Values `string` Details Client private key path for OTEL exporter TLS. Key `otel.log_user_prompt` Type / Values `boolean` Details Opt in to exporting raw user prompts with OpenTelemetry logs. Key `otel.metrics_exporter` Type / Values `none | statsig | otlp-http | otlp-grpc` Details Select the OpenTelemetry metrics exporter (defaults to `statsig`). Key `otel.trace_exporter` Type / Values `none | otlp-http | otlp-grpc` Details Select the OpenTelemetry trace exporter and provide any endpoint metadata. Key `otel.trace_exporter.<id>.endpoint` Type / Values `string` Details Trace exporter endpoint for OTEL logs. Key `otel.trace_exporter.<id>.headers` Type / Values `map<string,string>` Details Static headers included with OTEL trace exporter requests. Key `otel.trace_exporter.<id>.protocol` Type / Values `binary | json` Details Protocol used by the OTLP/HTTP trace exporter. Key `otel.trace_exporter.<id>.tls.ca-certificate` Type / Values `string` Details CA certificate path for OTEL trace exporter TLS. Key `otel.trace_exporter.<id>.tls.client-certificate` Type / Values `string` Details Client certificate path for OTEL trace exporter TLS. Key `otel.trace_exporter.<id>.tls.client-private-key` Type / Values `string` Details Client private key path for OTEL trace exporter TLS. Key `permissions.<name>.description` Type / Values `string` Details Human-readable description for this named profile. A profile does not inherit its parent's description through `extends`. Key `permissions.<name>.extends` Type / Values `string` Details Optional parent profile applied before this named profile. Set it to another named profile, `:read-only`, or `:workspace`; `:danger-full-access`, undefined parents, and cycles are rejected. Key `permissions.<name>.filesystem` Type / Values `table` Details Named filesystem permission profile. Each key is an absolute path or special token such as `:minimal` or `:workspace_roots`. Key `permissions.<name>.filesystem.":workspace_roots".<subpath-or-glob>` Type / Values `"read" | "write" | "deny"` Details Scoped filesystem access relative to each effective workspace root. Use `"."` for the root itself; glob subpaths such as `"**/*.env"` can deny reads with `"deny"`. Key `permissions.<name>.filesystem.<path-or-glob>` Type / Values `"read" | "write" | "deny" | table` Details Grant direct access for a path, glob pattern, or special token, or scope nested entries under that root. Use `"deny"` to deny reads for matching paths. Key `permissions.<name>.filesystem.glob_scan_max_depth` Type / Values `number` Details Maximum depth for expanding deny-read glob patterns on platforms that snapshot matches before sandbox startup. Must be at least `1` when set. Key `permissions.<name>.network.allow_local_binding` Type / Values `boolean` Details Permit broader local/private-network access through sandboxed networking. Exact local IP literal or `localhost` allow rules can still permit specific local targets when this stays `false`. Key `permissions.<name>.network.allow_upstream_proxy` Type / Values `boolean` Details Allow sandboxed networking to chain through another upstream proxy. Key `permissions.<name>.network.dangerously_allow_all_unix_sockets` Type / Values `boolean` Details Allow arbitrary Unix socket destinations instead of the default restricted set. Use only in tightly controlled environments. Key `permissions.<name>.network.dangerously_allow_non_loopback_proxy` Type / Values `boolean` Details Permit non-loopback bind addresses for sandboxed networking listeners. Enabling it can expose listeners beyond localhost. Key `permissions.<name>.network.domains` Type / Values `table` Details Domain rules for sandboxed commands. Enforced only when `features.network_proxy` or enabled administrator-managed networking requirements activate the proxy. Supports exact hosts, `*.example.com`, `**.example.com`, and global `*` allow rules; `deny` wins. Does not restrict web search, apps, or MCP servers. Key `permissions.<name>.network.domains.<pattern>` Type / Values `allow | deny` Details Allow or deny an exact host or scoped wildcard pattern such as `*.example.com` or `**.example.com`. Key `permissions.<name>.network.enable_socks5` Type / Values `boolean` Details Expose SOCKS5 support when this permissions profile enables sandboxed networking. Key `permissions.<name>.network.enable_socks5_udp` Type / Values `boolean` Details Allow UDP over the SOCKS5 listener when enabled. Key `permissions.<name>.network.enabled` Type / Values `boolean` Details Enable network access for commands in this permission profile. This does not start the network proxy. Without `features.network_proxy` or enabled administrator-managed networking requirements, command network access is direct and profile domain rules are not enforced. Key `permissions.<name>.network.mode` Type / Values `limited | full` Details Network proxy mode used for subprocess traffic. Key `permissions.<name>.network.proxy_url` Type / Values `string` Details HTTP listener URL used when this permissions profile enables sandboxed networking. Key `permissions.<name>.network.socks_url` Type / Values `string` Details SOCKS5 proxy endpoint used by this permissions profile. Key `permissions.<name>.network.unix_sockets` Type / Values `table` Details Unix socket allowlist overrides for sandboxed networking. Use socket paths as keys; `allow` adds a path, and `deny` rejects it. Key `permissions.<name>.network.unix_sockets.<path>` Type / Values `allow | deny` Details Add an absolute Unix socket path to the effective allowlist with `allow`, or reject it with `deny`. Denied entries are omitted from the effective allowlist. Key `permissions.<name>.workspace_roots` Type / Values `table` Details Profile-defined workspace roots that receive `:workspace_roots` filesystem rules alongside the session's runtime workspace roots. Key `permissions.<name>.workspace_roots.<path>` Type / Values `boolean` Details Opt a path into the profile's workspace root set when `true`. Disabled entries remain inactive. Key `personality` Type / Values `none | friendly | pragmatic` Details Default communication style for models that advertise `supportsPersonality`; can be overridden per thread/turn or via `/personality`. Key `plan_mode_reasoning_effort` Type / Values `string` Details Plan-mode-specific reasoning override using a level supported by the selected model. When unset, Plan mode uses its built-in preset default. Key `plugins.<plugin>.enabled` Type / Values `boolean` Details Enable or disable a local-marketplace plugin using a `plugin-name@marketplace-name` key. Read from the effective merged config; trusted-project settings can override user, cloud-managed, and system defaults. Marketplace refresh can install or refresh configured plugins even when disabled. This does not override workspace-managed enabled states. Key `plugins.<plugin>.mcp_servers.<server>.default_tools_approval_mode` Type / Values `auto | prompt | writes | approve` Details Default approval behavior for tools on a plugin-provided MCP server. Key `plugins.<plugin>.mcp_servers.<server>.disabled_tools` Type / Values `array<string>` Details Deny list applied after `enabled_tools` for a plugin-provided MCP server. Key `plugins.<plugin>.mcp_servers.<server>.enabled` Type / Values `boolean` Details Enable or disable an MCP server bundled by an installed plugin without changing the plugin manifest. Key `plugins.<plugin>.mcp_servers.<server>.enabled_tools` Type / Values `array<string>` Details Allow list of tools exposed from a plugin-provided MCP server. Key `plugins.<plugin>.mcp_servers.<server>.tools.<tool>.approval_mode` Type / Values `auto | prompt | writes | approve` Details Per-tool approval behavior override for a plugin-provided MCP tool. Key `project_doc_fallback_filenames` Type / Values `array<string>` Details Additional filenames to try when `AGENTS.md` is missing. Key `project_doc_max_bytes` Type / Values `number` Details Maximum bytes read from `AGENTS.md` when building project instructions. Key `project_root_markers` Type / Values `array<string>` Details List of project root marker filenames; used when searching parent directories for the project root. Key `projects.<path>.trust_level` Type / Values `string` Details Mark a project or worktree as trusted or untrusted (`"trusted"` | `"untrusted"`). Untrusted projects skip project-scoped `.codex/` layers, including project-local config, hooks, and rules. Key `review_model` Type / Values `string` Details Optional model override used by `/review` (defaults to the current session model). Key `sandbox_mode` Type / Values `read-only | workspace-write | danger-full-access` Details Sandbox policy for filesystem and network access during command execution. Key `sandbox_workspace_write.exclude_slash_tmp` Type / Values `boolean` Details Exclude `/tmp` from writable roots in workspace-write mode. Key `sandbox_workspace_write.exclude_tmpdir_env_var` Type / Values `boolean` Details Exclude `$TMPDIR` from writable roots in workspace-write mode. Key `sandbox_workspace_write.network_access` Type / Values `boolean` Details Allow outbound network access inside the workspace-write sandbox. Key `sandbox_workspace_write.writable_roots` Type / Values `array<string>` Details Additional writable roots when `sandbox_mode = "workspace-write"`. Key `service_tier` Type / Values `string` Details Preferred service tier for new turns. Use `fast` or another tier advertised by the active model; `fast` maps to the request value `priority`. Key `shell_environment_policy.exclude` Type / Values `array<string>` Details Legacy environment-variable exclusion patterns. Use `shell_environment_policy.filters` for new configuration; don't combine both forms in the same layer. Key `shell_environment_policy.experimental_use_profile` Type / Values `boolean` Details Use the user shell profile when spawning subprocesses. Key `shell_environment_policy.filters` Type / Values `map<string, include | exclude>` Details Canonical case-insensitive environment-variable pattern filters. Include entries create an allowlist and can't restore excluded values. Explicit `set` values apply after exclusions. Don't combine filters with legacy `exclude` or `include_only` arrays in the same layer. Key `shell_environment_policy.ignore_default_excludes` Type / Values `boolean` Details Keep variables containing KEY, SECRET, or TOKEN before other filters run (default: true). Set to false to apply automatic secret-name exclusions. Key `shell_environment_policy.include_only` Type / Values `array<string>` Details Legacy allowlist of environment-variable patterns. Use `shell_environment_policy.filters` for new configuration; don't combine both forms in the same layer. Key `shell_environment_policy.inherit` Type / Values `all | core | none` Details Baseline environment inheritance when spawning subprocesses. Key `shell_environment_policy.set` Type / Values `map<string,string>` Details Explicit environment values injected after exclusions; include filters can still remove them. Key `show_raw_agent_reasoning` Type / Values `boolean` Details Surface raw reasoning content when the active model emits it. Key `skills.config` Type / Values `array<object>` Details Per-skill enablement overrides stored in config.toml. Key `skills.config.<index>.enabled` Type / Values `boolean` Details Enable or disable the referenced skill. Key `skills.config.<index>.path` Type / Values `string (path)` Details Path to a skill folder containing `SKILL.md`. Key `skills.max_context_tokens` Type / Values `integer (positive)` Details Token budget for the available-skills catalog. Defaults to 2% of the model's context window. Explicit values are capped at `10000` tokens. Key `sqlite_home` Type / Values `string (path)` Details Directory where Codex stores the SQLite-backed state DB used by agent jobs and other resumable runtime state. Key `suppress_unstable_features_warning` Type / Values `boolean` Details Suppress the warning that appears when under-development feature flags are enabled. Key `tool_output_token_limit` Type / Values `number` Details Token budget for storing individual tool/function outputs in history. Key `tool_suggest.disabled_tools` Type / Values `array<table>` Details Disable suggestions for specific discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`. Key `tool_suggest.discoverables` Type / Values `array<table>` Details Allow tool suggestions for additional discoverable connectors or plugins. Each entry uses `type = "connector"` or `"plugin"` and an `id`. Key `tools.view_image` Type / Values `boolean` Details Enable the local-image attachment tool `view_image`. Key `tools.web_search` Type / Values `boolean | { context_size = "low|medium|high", allowed_domains = [string], location = { country, region, city, timezone } }` Details Optional web search tool configuration. The object form can set search context size, allowed search domains, and approximate user location. These search-domain filters are separate from sandboxed-command network domain rules and do not restrict connectors or MCP servers. Key `tui` Type / Values `table` Details TUI-specific options such as enabling inline desktop notifications. Key `tui.alternate_screen` Type / Values `auto | always | never` Details Control alternate screen usage for the TUI (default: auto; auto skips it in Zellij to preserve scrollback). Key `tui.animations` Type / Values `boolean` Details Enable terminal animations (welcome screen, shimmer, spinner) (default: true). Key `tui.keymap.<context>.<action>` Type / Values `string | array<string>` Details Keyboard shortcut binding for a TUI action. Supported contexts include `global`, `chat`, `composer`, `editor`, `vim_normal`, `vim_operator`, `vim_text_object`, `pager`, `list`, and `approval`. Selected composer actions fall back to matching `tui.keymap.global` bindings; context-specific bindings take precedence when supported. Key `tui.keymap.<context>.<action> = []` Type / Values `empty array` Details Unbind the action in that keymap context. Key names use normalized strings such as `ctrl-a`, `shift-enter`, `page-down`, or `minus`. Key `tui.model_availability_nux.<model>` Type / Values `integer` Details Internal startup-tooltip state keyed by model slug. Key `tui.notification_condition` Type / Values `unfocused | always` Details Control whether TUI notifications fire only when the terminal is unfocused or regardless of focus. Defaults to `unfocused`. Key `tui.notification_method` Type / Values `auto | osc9 | bel` Details Notification method for terminal notifications (default: auto). Key `tui.notifications` Type / Values `boolean | array<string>` Details Enable TUI notifications; optionally restrict to specific event types. Key `tui.raw_output_mode` Type / Values `boolean` Details Start the TUI in raw scrollback mode for copy-friendly terminal selection (default: false). You can toggle it with `/raw` or the default `alt-r` key binding. Key `tui.resume_cwd` Type / Values `current | session` Details Working directory to use when resuming or forking a session. When unset, Codex asks you to choose if your current directory differs from the session's saved directory. Key `tui.show_tooltips` Type / Values `boolean` Details Show onboarding tooltips in the TUI welcome screen (default: true). Key `tui.status_line` Type / Values `array<string> | null` Details Ordered list of TUI footer status-line item identifiers. `null` disables the status line. Key `tui.terminal_title` Type / Values `array<string> | null` Details Ordered list of terminal window/tab title item identifiers. Defaults to `["spinner", "project"]`; `null` disables title updates. Key `tui.theme` Type / Values `string` Details Syntax-highlighting theme override (kebab-case theme name). Key `tui.vim_mode_default` Type / Values `boolean` Details Start the composer in Vim normal mode instead of insert mode (default: false). You can still toggle it per session with `/vim`. Key `web_search` Type / Values `disabled | cached | indexed | live` Details Web search mode (default: `"cached"`; cached uses an OpenAI-maintained index without external web access; indexed permits external access only when gated by the search index; if you use `--yolo` or another full access sandbox setting, it defaults to `"live"`). Use `"live"` for unrestricted live retrieval, or `"disabled"` to remove the tool. Key `windows_wsl_setup_acknowledged` Type / Values `boolean` Details Track Windows onboarding acknowledgement (Windows only). Key `windows.sandbox` Type / Values `unelevated | elevated | mxc` Details Windows-only native sandbox mode when running Codex natively on Windows. Expand to view all


You can find the latest JSON schema for `config.toml` [here](https://learn.chatgpt.com/codex/config-schema.json).


To get autocompletion and diagnostics when editing `config.toml` in VS Code or Cursor, you can install the [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) extension and add this line to the top of your `config.toml`:


```
#:schema https://developers.openai.com/codex/config-schema.json
```


Note: Rename `experimental_instructions_file` to `model_instructions_file`. Codex deprecates the old key; update existing configs to the new name.


## `requirements.toml`


`requirements.toml` is an admin-enforced configuration file that constrains security-sensitive settings users can’t override. For details, locations, and examples, see [Admin-enforced requirements](https://learn.chatgpt.com/codex/enterprise/managed-configuration#admin-enforced-requirements-requirementstoml).


For ChatGPT Business and Enterprise users, Codex can also apply cloud-fetched requirements. See the security page for precedence details.


Use `[features]` in `requirements.toml` to pin runtime feature flags by the same canonical keys that `config.toml` uses. Requirements can also include documented app-only keys that don’t belong in `config.toml`. Omitted keys remain unconstrained.


Some managed requirements enforce an exact configuration value instead of an allowlist. Users can’t override an enforced path, update preference, login-shell policy, feedback setting, or Windows private-desktop setting.


Managed permission-profile allowlists require Codex 0.138.0 or later. Codex 0.137.0 and earlier ignore `allowed_permission_profiles` and managed `default_permissions`.


Use `allowed_sandbox_modes` with `sandbox_mode`. For permission-profile deployments, use `allowed_permission_profiles` with managed `default_permissions`.


An `untrusted` entry in `allowed_approval_policies` is still valid for the stricter approval behavior Codex derives when a project uses `trust_level = "untrusted"`. It does not permit explicitly setting `approval_policy = "untrusted"`.


The `[models.new_thread]` table supplies managed defaults, not enforcement. If you explicitly override the model or reasoning effort with `--model`, `--config`, or `--profile`, Codex ignores both `model` and `model_reasoning_effort` in `[models.new_thread]`. `service_tier` is independent.


The browser requirements cover three separate surfaces. `in_app_browser` controls the browser pane that a person opens and uses directly. `browser_use` controls agent-driven work in a browser. `computer_use` controls agent-driven work in native desktop apps.


The nested Browser Use and Computer Use policy values do not grant access by themselves. An origin- or app-specific `allow` can override the fallback for the same policy source, but normal feature, approval, and other policy checks still apply. Where managed requirements and `config.toml` both apply, a `deny` from either one wins.


Key

Type / Values

Details

`additional_developer_instructions`

`string`

Managed developer instructions added as a separate developer message. Codex rejects instructions that exceed a limit of 10,000 estimated tokens, including context markers.

`allow_appshots`

`boolean`

Set to `false` to disable Appshots for managed users. If omitted, Appshots remain unconstrained by requirements and follow normal product availability.

`allow_browser_and_computer_use`

`boolean`

Set to `false` to block both agent-driven Browser Use and native-app Computer Use. Setting it to `true` or omitting it does not enable either feature; the remaining feature, policy, and approval checks still apply.

`allow_login_shell`

`boolean`

Enforce whether shell tools can start a login shell.

`allow_managed_hooks_only`

`boolean`

When `true`, Codex skips user, project, session, and plugin hooks while still allowing managed hooks from `requirements.toml` and other managed config layers.

`allow_remote_control`

`boolean`

Set to `false` to disable device remote control for managed users. If omitted, device remote control remains unconstrained by requirements and follows normal product availability.

`allowed_approval_policies`

`array<string>`

Allowed approval policies, such as `on-request`, `never`, and `granular`. Include `untrusted` to permit the stricter policy derived from an untrusted project; it cannot be selected directly with `approval_policy`.

`allowed_approvals_reviewers`

`array<string>`

Allowed values for `approvals_reviewer`, such as `user` and `auto_review`.

`allowed_chatgpt_workspaces`

`array<string>`

Restrict ChatGPT login, including Codex access tokens, to the listed workspace IDs. An empty list disables ChatGPT login; API authentication remains available when permitted. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored.

`allowed_login_methods`

`array<string>`

Allow `chatgpt`, `api`, or both. If omitted, this setting doesn't restrict login methods. If set, the list must contain at least one method. `api` permits API authentication, including Amazon Bedrock. Set through the local system requirements file or macOS MDM. Cloud-managed values are ignored.

`allowed_permission_profiles`

`table<boolean>`

Complete list of allowed permission profiles. Profiles set to `true` are allowed. Profiles that are omitted or set to `false` are denied, including profiles added in future versions. When requirements sources are combined, entries are matched by profile name.

`allowed_permission_profiles.<name>`

`boolean`

Allow or deny a built-in or custom permission profile defined in a loaded config or requirements source. A later, higher-precedence requirements source can use `false` to turn off a profile allowed by an earlier, lower-precedence source.

`allowed_sandbox_modes`

`array<string>`

Allowed values for `sandbox_mode`.

`allowed_web_search_modes`

`array<string>`

Allowed values for `web_search` (`disabled`, `cached`, `indexed`, `live`). `disabled` is always allowed; an empty list effectively allows only `disabled`.

`apps`

`table`

Managed app requirements keyed by app identifier. Requirements can disable an app or constrain approval behavior for individual tools.

`apps.<id>.enabled`

`boolean`

Set to `false` to disable an app. A disabled requirement remains restrictive when multiple requirements sources are merged.

`apps.<id>.tools.<tool>.approval_mode`

`auto | prompt | writes | approve`

Set the managed approval mode for one app tool.

`auto_review`

`table`

Managed automatic-review requirements.

`auto_review.ignore_rules`

`array<string>`

Full model slugs for which Codex ignores `allow` prefix rules in command execution policy. Match the slug exactly, including its provider namespace when present; unlike `required_on_models`, this does not accept a namespace-free alias. Deny and network rules still apply.

`auto_review.required_on_models`

`array<string>`

Model slugs that must use automatic review. Slugs must be non-empty, omit provider namespaces, and have no surrounding whitespace. Lists from multiple requirements sources are combined.

`browser_use`

`table`

Managed requirements for agent-driven Browser Use.

`browser_use.allow_global_persistent_approval`

`boolean`

Set to `false` to prevent Browser Use from creating or honoring `Always allow` approvals that cover every site, such as allowing downloads from any site. Existing saved approvals are ignored, not deleted. Setting it to `true` or omitting it does not create an approval.

`browser_use.allow_history_access`

`boolean`

Set to `false` to prevent Browser Use from reading browser history. Setting it to `true` or omitting it leaves normal history settings and availability checks in place.

`browser_use.default_origin_policy`

`table`

Fallback for each Browser Use setting when no matching entry under `browser_use.origins` defines it. A matching origin rule replaces the fallback for that source. Codex then applies the stricter result from managed requirements and user configuration.

`browser_use.default_origin_policy.access`

`allow | deny`

Use `deny` to block Browser Use on origins that use the fallback. A denied origin also blocks uploads, downloads, full browser debugging access, and automatic review there. `allow` only lets normal approval and policy checks continue.

`browser_use.default_origin_policy.access_approval_lifetime`

`turn | thread`

Set how long a non-persistent site-access approval lasts: `turn` limits it to the current turn, and `thread` keeps it for the rest of the current thread. `persistent_approval` separately controls whether `Always allow` is available. The product default is `thread`.

`browser_use.default_origin_policy.auto_review`

`allow | deny`

Use `deny` to skip automatic review on origins that use the fallback and ask the user for approval instead. `allow` leaves automatic review available when other settings allow it.

`browser_use.default_origin_policy.downloads`

`allow | deny`

Use `deny` to block Browser Use downloads on origins that use the fallback. `allow` only lets normal approval and policy checks continue.

`browser_use.default_origin_policy.full_cdp_access`

`allow | deny`

Use `deny` to block full Chrome DevTools Protocol (CDP) access on origins that use the fallback. `allow` only lets normal opt-in and approval checks continue.

`browser_use.default_origin_policy.persistent_approval`

`boolean`

Set to `false` to prevent Browser Use from saving or honoring an `Always allow` approval on origins that use the fallback. Approvals for the current turn or thread can still apply. `true` makes `Always allow` available when otherwise permitted but does not create an approval.

`browser_use.default_origin_policy.uploads`

`allow | deny`

Use `deny` to block Browser Use uploads on origins that use the fallback. `allow` only lets normal approval and policy checks continue.

`browser_use.disable_auto_review`

`boolean`

Set to `true` to skip automatic review for Browser Use and ask the user for approval instead. Setting it to `false` or omitting it leaves automatic review available when other settings allow it.

`browser_use.origins`

`map<string, table>`

Origin-specific Browser Use policies. Keys use `<scheme>://<host-pattern>[:<port>]` with `http` or `https`. Use an exact host, `*.example.com` for subdomains only, or `**.example.com` for the base domain and its subdomains. Other `*` wildcards can span dots, so `region*.example.com` also matches `region.api.example.com`; a host of `*` matches every host for that scheme. Schemes and nondefault ports are significant; explicit default ports are normalized away. Paths, queries, embedded usernames or passwords, and wildcard schemes or ports are invalid. Quote the pattern in TOML, for example `[browser_use.origins."https://**.example.com"]`.

`browser_use.origins.<pattern>`

`table`

Policy for origins matching this pattern. If several patterns match, Codex uses the most restrictive value for each capability: `deny` over `allow`, `false` over `true`, and `turn` over `thread`.

`browser_use.origins.<pattern>.access`

`allow | deny`

Use `deny` to block Browser Use on matching origins. Denial also blocks uploads, downloads, full browser debugging access, and automatic review there. `allow` only lets normal approval and policy checks continue.

`browser_use.origins.<pattern>.access_approval_lifetime`

`turn | thread`

Set how long a non-persistent site-access approval for matching origins lasts: `turn` limits it to the current turn, and `thread` keeps it for the rest of the current thread. `persistent_approval` separately controls whether `Always allow` is available.

`browser_use.origins.<pattern>.auto_review`

`allow | deny`

Use `deny` to skip automatic review on matching origins and ask the user for approval instead. `allow` leaves automatic review available when other settings allow it.

`browser_use.origins.<pattern>.downloads`

`allow | deny`

Use `deny` to block Browser Use downloads on matching origins. `allow` only lets normal approval and policy checks continue.

`browser_use.origins.<pattern>.full_cdp_access`

`allow | deny`

Use `deny` to block full Chrome DevTools Protocol (CDP) access on matching origins. `allow` only lets normal opt-in and approval checks continue.

`browser_use.origins.<pattern>.persistent_approval`

`boolean`

Set to `false` to prevent Browser Use from saving or honoring an `Always allow` approval on matching origins. Approvals for the current turn or thread can still apply. `true` makes `Always allow` available when otherwise permitted but does not create an approval.

`browser_use.origins.<pattern>.uploads`

`allow | deny`

Use `deny` to block Browser Use uploads on matching origins. `allow` only lets normal approval and policy checks continue.

`chatgpt_base_url`

`string`

Enforce the ChatGPT service base URL before authentication and cloud-policy retrieval. This doesn't configure every Codex network destination. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored.

`check_for_update_on_startup`

`boolean`

Enforce whether Codex checks for updates when it starts.

`cli_auth_credentials_store`

`file | keyring | auto | ephemeral`

Enforce the CLI credential store before authentication loads. `file` uses `CODEX_HOME/auth.json`; `keyring` requires the OS credential store; `auto` falls back to a file if the credential store is unavailable; `ephemeral` keeps credentials in memory for the current process. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored.

`computer_use`

`table`

Managed requirements for agent-driven work in native desktop apps. Managed app rules and `config.toml` app rules are both enforced; an app must be allowed by each policy source.

`computer_use.allow_locked_computer_use`

`boolean`

Set to `false` to prevent users from enabling Locked Use on a managed macOS device. This requirement removes the enablement controls; it does not turn off Locked Use if it is already enabled. If omitted, normal product availability applies.

`computer_use.allow_persistent_approval`

`boolean`

Set to `false` to remove the option to save app approvals across sessions. Approvals for the current session remain available. Setting it to `true` or omitting it does not approve an app.

`computer_use.default_app_access`

`allow | deny`

Fallback access for native apps that do not match a platform-specific rule. `deny` blocks access. `allow` only lets normal approval and policy checks continue. The product default is `allow`.

`computer_use.macos`

`table`

Computer Use app rules for macOS.

`computer_use.macos.bundle_ids`

`map<string, allow | deny>`

Map exact macOS bundle identifiers to `allow` or `deny`. A matching rule replaces `computer_use.default_app_access` within the same policy source. A deny from either managed requirements or user configuration still blocks access.

`computer_use.macos.bundle_ids.<bundle-id>`

`allow | deny`

Use `deny` to block the exact bundle identifier. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app.

`computer_use.windows`

`table`

Computer Use app rules for packaged and unpackaged Windows apps.

`computer_use.windows.aumids`

`map<string, allow | deny>`

Map exact, registered Application User Model IDs (AUMIDs) for signed packaged apps to `allow` or `deny`. A matching rule replaces `computer_use.default_app_access` within the same policy source.

`computer_use.windows.aumids.<aumid>`

`allow | deny`

Use `deny` to block the exact packaged-app identity. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app.

`computer_use.windows.exes`

`array<table>`

Rules for signed, unpackaged Windows executables. Rules match the executable's verified publisher and signed version information, not its path or current file name. A matching deny takes precedence over matching allows. Unsigned executables use `computer_use.default_app_access`; executables whose signed identity cannot be verified unambiguously are blocked.

`computer_use.windows.exes[].access`

`allow | deny`

Required access decision for matching executables. `deny` blocks access. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app.

`computer_use.windows.exes[].binary_name`

`string`

Optional `OriginalFilename` from the executable's signed version information. Matching is case-insensitive. If a matching publisher and product rule requires this value but the executable does not provide it, Computer Use blocks the executable.

`computer_use.windows.exes[].product_name`

`string`

Required exact `ProductName` from the executable's signed version information.

`computer_use.windows.exes[].publisher_name`

`string`

Required exact publisher name from the executable's trusted signing certificate, formatted as a Windows X.500 distinguished name.

`default_permissions`

`string`

Managed default permission profile. The profile must be allowed by `allowed_permission_profiles`. Set this explicitly for predictable behavior; if omitted, Codex defaults to `:workspace` only when both `:workspace` and `:read-only` are explicitly allowed.

`enforce_residency`

`string`

Require Codex service traffic to use a supported data residency. Currently accepts `us`.

`experimental_network`

`table`

Administrator-managed network requirements for sandboxed local commands, enforced from `requirements.toml`. When enabled, these requirements can start the command network proxy without `features.network_proxy`. Browser tools separately check managed network denies and exclusive allowlists. These requirements do not route browser traffic through the proxy or control web search, apps, MCP servers, native-app traffic, or other capability-specific traffic. On supported managed Codex Cloud paths, these requirements constrain command networking alongside separate Cloud environment internet settings. Approved full sandbox escalation can bypass the command proxy where policy permits it. Work Cloud does not inherit these requirements.

`experimental_network.allow_local_binding`

`boolean`

Permit broader local/private-network access for sandboxed networking. On the supported Codex Cloud proxy path, an explicit false can prevent upstream-proxy access even if a domain is allowed. It defaults to true only if no applicable requirement, selected network profile, or proxy feature setting provides a value. Inherited false remains explicit. A supported higher-priority Cloud override can change it without broadening Global for Local or adding domain Allow entries. Verify executor support. Do not apply this Cloud default to Local.

`experimental_network.allow_upstream_proxy`

`boolean`

Allow sandboxed networking to chain through an upstream proxy from the environment.

`experimental_network.allowed_domains`

`array<string>`

Administrator allow rules for sandboxed-command networking while the managed network proxy is enabled. These rules do not apply to web search, apps, or MCP servers. Do not combine this with `experimental_network.domains`.

`experimental_network.dangerously_allow_all_unix_sockets`

`boolean`

Permit arbitrary Unix socket destinations instead of allowlist-only access. Use only in tightly controlled environments.

`experimental_network.dangerously_allow_non_loopback_proxy`

`boolean`

Permit non-loopback listener addresses for `[experimental_network]` requirements. Enabling it can expose listeners beyond localhost.

`experimental_network.denied_domains`

`array<string>`

List-shaped administrator deny rules for sandboxed networking. Do not combine this with `experimental_network.domains`.

`experimental_network.domains`

`map<string, allow | deny>`

Map-shaped administrator domain policy for sandboxed networking. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules. Prefer scoped rules because `*` broadly opens public outbound access. Environment rules can replace the same Global domain key within a policy. Higher-priority values replace the same key, while other inherited keys remain. After composition, a different matching `deny`, including an inherited wildcard, still blocks a request. Empty environment maps do not clear Global rules. Verify executor support. Do not combine this with `experimental_network.allowed_domains` or `experimental_network.denied_domains`.

`experimental_network.domains.<pattern>`

`allow | deny`

Allow or deny sandboxed network access for the matching domain pattern. A deny rule wins when several patterns match.

`experimental_network.enabled`

`boolean`

Enable sandboxed networking requirements. This does not grant network access when the active sandbox keeps command networking off.

`experimental_network.http_port`

`integer`

Loopback HTTP listener port to use for `[experimental_network]` requirements.

`experimental_network.managed_allowed_domains_only`

`boolean`

When networking requirements are enabled and this is true, ordinary user configuration and per-domain approvals cannot expand the managed proxy allowlist. With no effective configured or inherited Allow entries, ordinary managed commands have no allowed destinations. A deny-only policy does not allow the rest of the internet. This does not cover every tool or approved full sandbox escalation.

`experimental_network.socks_port`

`integer`

Loopback SOCKS5 listener port to use for `[experimental_network]` requirements.

`experimental_network.unix_sockets`

`map<string, allow | deny>`

Administrator-managed Unix socket allowlist for sandboxed networking on macOS. Paths must be absolute.

`experimental_network.unix_sockets.<path>`

`allow | deny`

On macOS, `allow` adds an absolute Unix socket path to the allowlist; `deny` leaves it out. A `deny` entry cannot block a socket when allow-all Unix sockets is enabled.

`features`

`table`

Pinned feature values. Use canonical names from `config.toml` for runtime features; documented app-only requirement keys are also supported here.

`features.<name>`

`boolean`

Require a documented runtime or app feature to stay enabled or disabled.

`features.apps`

`boolean`

Pin Apps integration availability on or off for managed users.

`features.browser_use`

`boolean`

Set to `false` in `requirements.toml` to disable agent-driven Browser Use.

`features.browser_use_external`

`boolean`

Set to `false` in `requirements.toml` to prevent Codex from operating supported browsers through the ChatGPT browser extension, including existing tabs and signed-in sessions.

`features.browser_use_full_cdp_access`

`boolean`

Set to `false` in `requirements.toml` to disable full Chrome DevTools Protocol access in the local runtime, including Browser Developer mode, and prevent the ChatGPT desktop app from enabling the corresponding setting. If omitted, normal product availability applies.

`features.computer_use`

`boolean`

Set to `false` in `requirements.toml` to disable Computer Use, Record & Replay, and related install or enablement flows.

`features.fast_mode`

`boolean`

Pin the canonical `fast_mode` feature on or off for managed users.

`features.guardian_approval`

`boolean`

Pin Guardian approval availability on or off for managed users.

`features.in_app_browser`

`boolean`

Set to `false` in `requirements.toml` to disable the built-in browser pane that users open and control directly.

`features.in_app_chat`

`boolean`

Set to `false` to hide ChatGPT and ChatGPT Work conversation screens and related cloud automation UI in the ChatGPT desktop app. This setting does not block ChatGPT Voice or stop existing cloud tasks. Setting it to `true` does not bypass account, workspace-permission, or rollout checks.

`features.in_app_dictation`

`boolean`

Set to `false` to disable in-app dictation in the desktop app. Setting it to `true` does not bypass other availability checks.

`features.in_app_local_automation`

`boolean`

Set to `false` to disable local scheduled tasks in the desktop app. Setting it to `true` does not bypass other availability checks.

`features.in_app_updates`

`boolean`

Set to `false` in `requirements.toml` to disable in-app updates. Updates remain enabled by default when this requirement is omitted.

`features.memories`

`boolean`

Pin Memories availability on or off for managed users.

`features.multi_agent`

`boolean`

Pin multi-agent availability on or off for managed users.

`features.plugin_sharing`

`boolean`

Set to `false` in cloud-managed `requirements.toml` to disable workspace sharing for locally built plugins.

`features.plugins`

`boolean`

Pin plugin availability on or off for managed users.

`features.realtime_conversation`

`boolean`

Set to `false` to disable the experimental `/voice` command in the Codex CLI. Do not rely on this setting to block [ChatGPT Voice](https://learn.chatgpt.com/codex/features/voice) in the desktop app or app-server voice sessions. Setting it to `true` does not bypass client or rollout checks.

`features.remote_plugin`

`boolean`

Pin remote plugin catalog availability on or off for managed users.

`features.workspace_dependencies`

`boolean`

Pin bundled workspace-dependency runtime availability on or off for managed users.

`feedback`

`table`

Managed feedback settings.

`feedback.enabled`

`boolean`

Enforce whether users can submit feedback across Codex clients.

`guardian_extra_policy`

`string`

Additional managed Markdown policy for automatic review, included alongside the main policy. This takes precedence over local `[auto_review].extra_policy`. Blank values are ignored.

`guardian_policy_config`

`string`

Managed Markdown policy instructions for automatic review. This takes precedence over local `[auto_review].policy`. Blank values are ignored.

`hooks`

`table`

Admin-enforced managed lifecycle hooks. Requires a managed hook directory and uses the same event schema as inline `[hooks]` in `config.toml`.

`hooks.<Event>`

`array<table>`

Matcher groups for a hook event such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, or `Stop`.

`hooks.<Event>[].hooks`

`array<table>`

Hook handlers for a matcher group. Command and MCP tool hooks are supported while prompt and agent hook handlers are parsed but skipped.

`hooks.<Event>[].hooks[].additionalContextLimit`

`integer`

Approximate per-handler token threshold for saving oversized `additionalContext` to disk and showing the model a shorter preview. Defaults to `2500`; `0` passes the full context directly to the model. See [Large hook output](https://learn.chatgpt.com/codex/hooks#large-hook-output).

`hooks.<Event>[].hooks[].async`

`boolean`

Run a command hook in the background without delaying the triggering operation. Defaults to `false`; `SessionEnd` always runs synchronously. See [Run hooks in the background](https://learn.chatgpt.com/codex/hooks#run-hooks-in-the-background).

`hooks.<Event>[].hooks[].commandWindows`

`string`

Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted.

`hooks.managed_dir`

`string (absolute path)`

Directory containing managed hook scripts on macOS and Linux. Codex validates that it is absolute and exists before loading managed hooks.

`hooks.windows_managed_dir`

`string (absolute path)`

Directory containing managed hook scripts on Windows. Codex validates that it is absolute and exists before loading managed hooks.

`in_app_browser`

`table`

Requirements for the built-in browser pane. These settings do not control agent-driven Browser Use.

`in_app_browser.allow_external_browser_settings_import`

`boolean`

Set to `false` to prevent users from importing settings or browsing data from an external browser into the built-in browser. Setting it to `true` or omitting it leaves the import available when other product checks allow it. This is a managed-only setting with no `config.toml` override.

`log_dir`

`string (path)`

Enforce the directory where Codex writes local log files.

`marketplaces`

`table`

Admin requirements for plugin marketplace sources. Rules take effect when `restrict_to_allowed_sources` is `true`.

`marketplaces.allowed_sources`

`table`

Allowed marketplace sources keyed by administrator-chosen rule name. Distinct names accumulate across requirements layers; fields under the same name use normal layer precedence.

`marketplaces.allowed_sources.<name>`

`table`

One allowed source rule. The final `source` value after requirements merge determines which sibling fields Codex interprets.

`marketplaces.allowed_sources.<name>.host_pattern`

`string`

Regular expression required when `source = "host_pattern"`. Codex matches it against the lowercase hostname parsed from an HTTPS, SSH, or SCP-style Git source. Use `^` and `$` to require a whole-host match.

`marketplaces.allowed_sources.<name>.path`

`string (absolute path)`

Local marketplace directory required when `source = "local"`. Codex requires an absolute path and compares paths after normalization.

`marketplaces.allowed_sources.<name>.ref`

`string`

Optional exact Git ref for a `git` rule. When omitted, the rule allows any ref for the matching repository.

`marketplaces.allowed_sources.<name>.source`

`git | host_pattern | local`

Marketplace source matcher type. Use `git` for one repository, `host_pattern` for Git hosts matched by regular expression, or `local` for one directory.

`marketplaces.allowed_sources.<name>.url`

`string`

Git repository URL required when `source = "git"`. Codex normalizes the configured and allowed URLs before requiring an exact repository match.

`marketplaces.restrict_to_allowed_sources`

`boolean`

When `true`, require configured marketplace sources to match `allowed_sources` for marketplace add, plugin install, refresh, and runtime loading. OpenAI-curated Git catalogs, including the API-key catalog, must also match the allowlist. Bundled and remotely installed workspace plugins are separate from this curated Git source policy.

`mcp_servers`

`table`

Allowlist of MCP servers that may be enabled. Both the server name (`<id>`) and its identity must match for the MCP server to be enabled. Any configured MCP server not in the allowlist (or with a mismatched identity) is disabled.

`mcp_servers.<id>.identity`

`table`

Identity rule for a single MCP server. Set either `command` (stdio) or `url` (streamable HTTP).

`mcp_servers.<id>.identity.command`

`string | table`

Allow an MCP stdio server by exact command string, or use a matcher table to require an exact executable and ordered argument matchers. The string form doesn't inspect arguments, `cwd`, `env`, or `env_vars`.

`mcp_servers.<id>.identity.command.args`

`array<table>`

Ordered argument matchers for a stdio server. The configured argument list must have the same length, and every position must match. Command matchers don't inspect `cwd`, `env`, or `env_vars`.

`mcp_servers.<id>.identity.command.args[].expression`

`string`

Regular expression used by a `regex` argument matcher. The expression must be valid and match the complete argument value.

`mcp_servers.<id>.identity.command.args[].match`

`exact | prefix | regex`

Match operation for this argument position.

`mcp_servers.<id>.identity.command.args[].value`

`string`

Value used by an `exact` or `prefix` argument matcher.

`mcp_servers.<id>.identity.command.executable`

`string`

Executable that the stdio server's configured `command` must match exactly.

`mcp_servers.<id>.identity.url`

`string | table`

Allow an MCP streamable HTTP server by exact URL string, or use an `exact`, `prefix`, or `regex` value matcher table.

`mcp_servers.<id>.identity.url.expression`

`string`

Regular expression used by a `regex` URL matcher. The expression must be valid and match the complete URL value.

`mcp_servers.<id>.identity.url.match`

`exact | prefix | regex`

Match operation for the configured MCP server URL.

`mcp_servers.<id>.identity.url.value`

`string`

Value used by an `exact` or `prefix` URL matcher.

`model_catalog_json`

`string (path)`

Enforce the JSON model catalog Codex uses at startup.

`model_provider`

`string`

Enforce the model provider ID, overriding local and session configuration.

`model_providers`

`map<string, table>`

Managed model provider definitions. Each entry replaces the complete configured provider with the same ID; fields aren't merged with the user's definition. Providers with other IDs remain available.

`model_providers.<id>`

`table`

Complete managed provider definition. Uses the same provider fields as `config.toml`, including `name`, `base_url`, authentication, and transport settings.

`models`

`table`

Contains the `[models.new_thread]` table.

`models.new_thread`

`table`

Optional defaults to apply when a new local thread starts. They take priority over user and project defaults, but can be superseded by explicit overrides.

`models.new_thread.model`

`string`

Default model for new threads. An explicit override of either the model or reasoning effort causes both fields to be ignored.

`models.new_thread.model_reasoning_effort`

`string`

Default reasoning effort for new threads. An explicit override of either the model or reasoning effort causes both fields to be ignored.

`models.new_thread.service_tier`

`string`

Default service tier for new threads. An explicit service-tier override causes this field to be ignored.

`permissions`

`table`

Admin-defined permission profiles keyed by profile name. Uses the same profile fields as `config.toml`.

`permissions.<name>`

`table`

Admin-defined permission profile. The name can't start with `:`, use the reserved name `filesystem`, or duplicate a profile from a loaded config. Uses the same profile fields as `config.toml`; see the Permissions guide for the complete profile schema.

`permissions.filesystem.deny_read`

`array<string>`

Admin-enforced filesystem read denials. Entries can be paths or glob patterns, and users cannot weaken them with local config.

`plugins`

`table`

Plugin-specific MCP server allowlists keyed by plugin identifier. When this table is present, plugin-bundled servers without a matching plugin and server entry are disabled.

`plugins.<plugin>.mcp_servers`

`table`

Allowlist for MCP servers bundled with one plugin. Plugin server requirements use the same exact identity and matcher forms as top-level `mcp_servers` requirements.

`plugins.<plugin>.mcp_servers.<server>.identity`

`table`

Identity rule for one plugin-bundled MCP server. Set either `command` (stdio) or `url` (streamable HTTP).

`plugins.<plugin>.mcp_servers.<server>.identity.command`

`string | table`

Allow a plugin's stdio MCP server by exact command string, or use a matcher table to require an exact executable and ordered argument matchers.

`plugins.<plugin>.mcp_servers.<server>.identity.command.args`

`array<table>`

Ordered argument matchers for a plugin-bundled stdio server. The configured argument list must have the same length, and every position must match.

`plugins.<plugin>.mcp_servers.<server>.identity.command.args[].expression`

`string`

Regular expression used by a `regex` argument matcher. The expression must match the complete argument value.

`plugins.<plugin>.mcp_servers.<server>.identity.command.args[].match`

`exact | prefix | regex`

Match operation for this argument position.

`plugins.<plugin>.mcp_servers.<server>.identity.command.args[].value`

`string`

Value used by an `exact` or `prefix` argument matcher.

`plugins.<plugin>.mcp_servers.<server>.identity.command.executable`

`string`

Executable that the plugin-bundled stdio server's configured command must match exactly.

`plugins.<plugin>.mcp_servers.<server>.identity.url`

`string | table`

Allow a plugin's streamable HTTP MCP server by exact URL string, or use an `exact`, `prefix`, or `regex` value matcher table.

`plugins.<plugin>.mcp_servers.<server>.identity.url.expression`

`string`

Regular expression used by a `regex` URL matcher. The expression must match the complete URL value.

`plugins.<plugin>.mcp_servers.<server>.identity.url.match`

`exact | prefix | regex`

Match operation for the plugin-bundled MCP server URL.

`plugins.<plugin>.mcp_servers.<server>.identity.url.value`

`string`

Value used by an `exact` or `prefix` URL matcher.

`remote_sandbox_config`

`array<table>`

Host-specific sandbox requirements. The first entry whose `hostname_patterns` match the resolved host name overrides top-level `allowed_sandbox_modes` for that requirements source. Host-specific entries currently override sandbox modes only.

`remote_sandbox_config[].allowed_sandbox_modes`

`array<string>`

Allowed sandbox modes to apply when this host-specific entry matches.

`remote_sandbox_config[].hostname_patterns`

`array<string>`

Case-insensitive host name patterns. Supports `*` for any sequence of characters and `?` for one character.

`rules`

`table`

Admin-enforced command rules merged with `.rules` files. Requirements rules must be restrictive.

`rules.prefix_rules`

`array<table>`

List of enforced prefix rules. Each rule must include `pattern` and `decision`.

`rules.prefix_rules[].decision`

`prompt | forbidden`

Required. Requirements rules can only prompt or forbid (not allow).

`rules.prefix_rules[].justification`

`string`

Optional non-empty rationale surfaced in approval prompts or rejection messages.

`rules.prefix_rules[].pattern`

`array<table>`

Command prefix expressed as pattern tokens. Each token sets either `token` or `any_of`.

`rules.prefix_rules[].pattern[].any_of`

`array<string>`

A list of allowed alternative tokens at this position.

`rules.prefix_rules[].pattern[].token`

`string`

A single literal token at this position.

`sqlite_home`

`string (path)`

Enforce the directory where Codex stores SQLite-backed runtime state.

`windows`

`table`

Native Windows sandbox requirements.

`windows.allowed_sandbox_implementations`

`array<string>`

Allowed legacy native Windows sandbox implementations (`elevated` and `unelevated`). The list must not be empty. When both are allowed and no mode is selected, Codex prefers `elevated`. This list does not restrict the `mxc` sandbox when it is available.

Key `additional_developer_instructions` Type / Values `string` Details Managed developer instructions added as a separate developer message. Codex rejects instructions that exceed a limit of 10,000 estimated tokens, including context markers. Key `allow_appshots` Type / Values `boolean` Details Set to `false` to disable Appshots for managed users. If omitted, Appshots remain unconstrained by requirements and follow normal product availability. Key `allow_browser_and_computer_use` Type / Values `boolean` Details Set to `false` to block both agent-driven Browser Use and native-app Computer Use. Setting it to `true` or omitting it does not enable either feature; the remaining feature, policy, and approval checks still apply. Key `allow_login_shell` Type / Values `boolean` Details Enforce whether shell tools can start a login shell. Key `allow_managed_hooks_only` Type / Values `boolean` Details When `true`, Codex skips user, project, session, and plugin hooks while still allowing managed hooks from `requirements.toml` and other managed config layers. Key `allow_remote_control` Type / Values `boolean` Details Set to `false` to disable device remote control for managed users. If omitted, device remote control remains unconstrained by requirements and follows normal product availability. Key `allowed_approval_policies` Type / Values `array<string>` Details Allowed approval policies, such as `on-request`, `never`, and `granular`. Include `untrusted` to permit the stricter policy derived from an untrusted project; it cannot be selected directly with `approval_policy`. Key `allowed_approvals_reviewers` Type / Values `array<string>` Details Allowed values for `approvals_reviewer`, such as `user` and `auto_review`. Key `allowed_chatgpt_workspaces` Type / Values `array<string>` Details Restrict ChatGPT login, including Codex access tokens, to the listed workspace IDs. An empty list disables ChatGPT login; API authentication remains available when permitted. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored. Key `allowed_login_methods` Type / Values `array<string>` Details Allow `chatgpt`, `api`, or both. If omitted, this setting doesn't restrict login methods. If set, the list must contain at least one method. `api` permits API authentication, including Amazon Bedrock. Set through the local system requirements file or macOS MDM. Cloud-managed values are ignored. Key `allowed_permission_profiles` Type / Values `table<boolean>` Details Complete list of allowed permission profiles. Profiles set to `true` are allowed. Profiles that are omitted or set to `false` are denied, including profiles added in future versions. When requirements sources are combined, entries are matched by profile name. Key `allowed_permission_profiles.<name>` Type / Values `boolean` Details Allow or deny a built-in or custom permission profile defined in a loaded config or requirements source. A later, higher-precedence requirements source can use `false` to turn off a profile allowed by an earlier, lower-precedence source. Key `allowed_sandbox_modes` Type / Values `array<string>` Details Allowed values for `sandbox_mode`. Key `allowed_web_search_modes` Type / Values `array<string>` Details Allowed values for `web_search` (`disabled`, `cached`, `indexed`, `live`). `disabled` is always allowed; an empty list effectively allows only `disabled`. Key `apps` Type / Values `table` Details Managed app requirements keyed by app identifier. Requirements can disable an app or constrain approval behavior for individual tools. Key `apps.<id>.enabled` Type / Values `boolean` Details Set to `false` to disable an app. A disabled requirement remains restrictive when multiple requirements sources are merged. Key `apps.<id>.tools.<tool>.approval_mode` Type / Values `auto | prompt | writes | approve` Details Set the managed approval mode for one app tool. Key `auto_review` Type / Values `table` Details Managed automatic-review requirements. Key `auto_review.ignore_rules` Type / Values `array<string>` Details Full model slugs for which Codex ignores `allow` prefix rules in command execution policy. Match the slug exactly, including its provider namespace when present; unlike `required_on_models`, this does not accept a namespace-free alias. Deny and network rules still apply. Key `auto_review.required_on_models` Type / Values `array<string>` Details Model slugs that must use automatic review. Slugs must be non-empty, omit provider namespaces, and have no surrounding whitespace. Lists from multiple requirements sources are combined. Key `browser_use` Type / Values `table` Details Managed requirements for agent-driven Browser Use. Key `browser_use.allow_global_persistent_approval` Type / Values `boolean` Details Set to `false` to prevent Browser Use from creating or honoring `Always allow` approvals that cover every site, such as allowing downloads from any site. Existing saved approvals are ignored, not deleted. Setting it to `true` or omitting it does not create an approval. Key `browser_use.allow_history_access` Type / Values `boolean` Details Set to `false` to prevent Browser Use from reading browser history. Setting it to `true` or omitting it leaves normal history settings and availability checks in place. Key `browser_use.default_origin_policy` Type / Values `table` Details Fallback for each Browser Use setting when no matching entry under `browser_use.origins` defines it. A matching origin rule replaces the fallback for that source. Codex then applies the stricter result from managed requirements and user configuration. Key `browser_use.default_origin_policy.access` Type / Values `allow | deny` Details Use `deny` to block Browser Use on origins that use the fallback. A denied origin also blocks uploads, downloads, full browser debugging access, and automatic review there. `allow` only lets normal approval and policy checks continue. Key `browser_use.default_origin_policy.access_approval_lifetime` Type / Values `turn | thread` Details Set how long a non-persistent site-access approval lasts: `turn` limits it to the current turn, and `thread` keeps it for the rest of the current thread. `persistent_approval` separately controls whether `Always allow` is available. The product default is `thread`. Key `browser_use.default_origin_policy.auto_review` Type / Values `allow | deny` Details Use `deny` to skip automatic review on origins that use the fallback and ask the user for approval instead. `allow` leaves automatic review available when other settings allow it. Key `browser_use.default_origin_policy.downloads` Type / Values `allow | deny` Details Use `deny` to block Browser Use downloads on origins that use the fallback. `allow` only lets normal approval and policy checks continue. Key `browser_use.default_origin_policy.full_cdp_access` Type / Values `allow | deny` Details Use `deny` to block full Chrome DevTools Protocol (CDP) access on origins that use the fallback. `allow` only lets normal opt-in and approval checks continue. Key `browser_use.default_origin_policy.persistent_approval` Type / Values `boolean` Details Set to `false` to prevent Browser Use from saving or honoring an `Always allow` approval on origins that use the fallback. Approvals for the current turn or thread can still apply. `true` makes `Always allow` available when otherwise permitted but does not create an approval. Key `browser_use.default_origin_policy.uploads` Type / Values `allow | deny` Details Use `deny` to block Browser Use uploads on origins that use the fallback. `allow` only lets normal approval and policy checks continue. Key `browser_use.disable_auto_review` Type / Values `boolean` Details Set to `true` to skip automatic review for Browser Use and ask the user for approval instead. Setting it to `false` or omitting it leaves automatic review available when other settings allow it. Key `browser_use.origins` Type / Values `map<string, table>` Details Origin-specific Browser Use policies. Keys use `<scheme>://<host-pattern>[:<port>]` with `http` or `https`. Use an exact host, `*.example.com` for subdomains only, or `**.example.com` for the base domain and its subdomains. Other `*` wildcards can span dots, so `region*.example.com` also matches `region.api.example.com`; a host of `*` matches every host for that scheme. Schemes and nondefault ports are significant; explicit default ports are normalized away. Paths, queries, embedded usernames or passwords, and wildcard schemes or ports are invalid. Quote the pattern in TOML, for example `[browser_use.origins."https://**.example.com"]`. Key `browser_use.origins.<pattern>` Type / Values `table` Details Policy for origins matching this pattern. If several patterns match, Codex uses the most restrictive value for each capability: `deny` over `allow`, `false` over `true`, and `turn` over `thread`. Key `browser_use.origins.<pattern>.access` Type / Values `allow | deny` Details Use `deny` to block Browser Use on matching origins. Denial also blocks uploads, downloads, full browser debugging access, and automatic review there. `allow` only lets normal approval and policy checks continue. Key `browser_use.origins.<pattern>.access_approval_lifetime` Type / Values `turn | thread` Details Set how long a non-persistent site-access approval for matching origins lasts: `turn` limits it to the current turn, and `thread` keeps it for the rest of the current thread. `persistent_approval` separately controls whether `Always allow` is available. Key `browser_use.origins.<pattern>.auto_review` Type / Values `allow | deny` Details Use `deny` to skip automatic review on matching origins and ask the user for approval instead. `allow` leaves automatic review available when other settings allow it. Key `browser_use.origins.<pattern>.downloads` Type / Values `allow | deny` Details Use `deny` to block Browser Use downloads on matching origins. `allow` only lets normal approval and policy checks continue. Key `browser_use.origins.<pattern>.full_cdp_access` Type / Values `allow | deny` Details Use `deny` to block full Chrome DevTools Protocol (CDP) access on matching origins. `allow` only lets normal opt-in and approval checks continue. Key `browser_use.origins.<pattern>.persistent_approval` Type / Values `boolean` Details Set to `false` to prevent Browser Use from saving or honoring an `Always allow` approval on matching origins. Approvals for the current turn or thread can still apply. `true` makes `Always allow` available when otherwise permitted but does not create an approval. Key `browser_use.origins.<pattern>.uploads` Type / Values `allow | deny` Details Use `deny` to block Browser Use uploads on matching origins. `allow` only lets normal approval and policy checks continue. Key `chatgpt_base_url` Type / Values `string` Details Enforce the ChatGPT service base URL before authentication and cloud-policy retrieval. This doesn't configure every Codex network destination. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored. Key `check_for_update_on_startup` Type / Values `boolean` Details Enforce whether Codex checks for updates when it starts. Key `cli_auth_credentials_store` Type / Values `file | keyring | auto | ephemeral` Details Enforce the CLI credential store before authentication loads. `file` uses `CODEX_HOME/auth.json`; `keyring` requires the OS credential store; `auto` falls back to a file if the credential store is unavailable; `ephemeral` keeps credentials in memory for the current process. Set through the local system requirements file or macOS MDM; cloud-managed values are ignored. Key `computer_use` Type / Values `table` Details Managed requirements for agent-driven work in native desktop apps. Managed app rules and `config.toml` app rules are both enforced; an app must be allowed by each policy source. Key `computer_use.allow_locked_computer_use` Type / Values `boolean` Details Set to `false` to prevent users from enabling Locked Use on a managed macOS device. This requirement removes the enablement controls; it does not turn off Locked Use if it is already enabled. If omitted, normal product availability applies. Key `computer_use.allow_persistent_approval` Type / Values `boolean` Details Set to `false` to remove the option to save app approvals across sessions. Approvals for the current session remain available. Setting it to `true` or omitting it does not approve an app. Key `computer_use.default_app_access` Type / Values `allow | deny` Details Fallback access for native apps that do not match a platform-specific rule. `deny` blocks access. `allow` only lets normal approval and policy checks continue. The product default is `allow`. Key `computer_use.macos` Type / Values `table` Details Computer Use app rules for macOS. Key `computer_use.macos.bundle_ids` Type / Values `map<string, allow | deny>` Details Map exact macOS bundle identifiers to `allow` or `deny`. A matching rule replaces `computer_use.default_app_access` within the same policy source. A deny from either managed requirements or user configuration still blocks access. Key `computer_use.macos.bundle_ids.<bundle-id>` Type / Values `allow | deny` Details Use `deny` to block the exact bundle identifier. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app. Key `computer_use.windows` Type / Values `table` Details Computer Use app rules for packaged and unpackaged Windows apps. Key `computer_use.windows.aumids` Type / Values `map<string, allow | deny>` Details Map exact, registered Application User Model IDs (AUMIDs) for signed packaged apps to `allow` or `deny`. A matching rule replaces `computer_use.default_app_access` within the same policy source. Key `computer_use.windows.aumids.<aumid>` Type / Values `allow | deny` Details Use `deny` to block the exact packaged-app identity. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app. Key `computer_use.windows.exes` Type / Values `array<table>` Details Rules for signed, unpackaged Windows executables. Rules match the executable's verified publisher and signed version information, not its path or current file name. A matching deny takes precedence over matching allows. Unsigned executables use `computer_use.default_app_access`; executables whose signed identity cannot be verified unambiguously are blocked. Key `computer_use.windows.exes[].access` Type / Values `allow | deny` Details Required access decision for matching executables. `deny` blocks access. `allow` overrides only this policy source's default and still requires any other policy source and the normal approval flow to allow the app. Key `computer_use.windows.exes[].binary_name` Type / Values `string` Details Optional `OriginalFilename` from the executable's signed version information. Matching is case-insensitive. If a matching publisher and product rule requires this value but the executable does not provide it, Computer Use blocks the executable. Key `computer_use.windows.exes[].product_name` Type / Values `string` Details Required exact `ProductName` from the executable's signed version information. Key `computer_use.windows.exes[].publisher_name` Type / Values `string` Details Required exact publisher name from the executable's trusted signing certificate, formatted as a Windows X.500 distinguished name. Key `default_permissions` Type / Values `string` Details Managed default permission profile. The profile must be allowed by `allowed_permission_profiles`. Set this explicitly for predictable behavior; if omitted, Codex defaults to `:workspace` only when both `:workspace` and `:read-only` are explicitly allowed. Key `enforce_residency` Type / Values `string` Details Require Codex service traffic to use a supported data residency. Currently accepts `us`. Key `experimental_network` Type / Values `table` Details Administrator-managed network requirements for sandboxed local commands, enforced from `requirements.toml`. When enabled, these requirements can start the command network proxy without `features.network_proxy`. Browser tools separately check managed network denies and exclusive allowlists. These requirements do not route browser traffic through the proxy or control web search, apps, MCP servers, native-app traffic, or other capability-specific traffic. On supported managed Codex Cloud paths, these requirements constrain command networking alongside separate Cloud environment internet settings. Approved full sandbox escalation can bypass the command proxy where policy permits it. Work Cloud does not inherit these requirements. Key `experimental_network.allow_local_binding` Type / Values `boolean` Details Permit broader local/private-network access for sandboxed networking. On the supported Codex Cloud proxy path, an explicit false can prevent upstream-proxy access even if a domain is allowed. It defaults to true only if no applicable requirement, selected network profile, or proxy feature setting provides a value. Inherited false remains explicit. A supported higher-priority Cloud override can change it without broadening Global for Local or adding domain Allow entries. Verify executor support. Do not apply this Cloud default to Local. Key `experimental_network.allow_upstream_proxy` Type / Values `boolean` Details Allow sandboxed networking to chain through an upstream proxy from the environment. Key `experimental_network.allowed_domains` Type / Values `array<string>` Details Administrator allow rules for sandboxed-command networking while the managed network proxy is enabled. These rules do not apply to web search, apps, or MCP servers. Do not combine this with `experimental_network.domains`. Key `experimental_network.dangerously_allow_all_unix_sockets` Type / Values `boolean` Details Permit arbitrary Unix socket destinations instead of allowlist-only access. Use only in tightly controlled environments. Key `experimental_network.dangerously_allow_non_loopback_proxy` Type / Values `boolean` Details Permit non-loopback listener addresses for `[experimental_network]` requirements. Enabling it can expose listeners beyond localhost. Key `experimental_network.denied_domains` Type / Values `array<string>` Details List-shaped administrator deny rules for sandboxed networking. Do not combine this with `experimental_network.domains`. Key `experimental_network.domains` Type / Values `map<string, allow | deny>` Details Map-shaped administrator domain policy for sandboxed networking. Supports exact hosts, `*.example.com` for subdomains only, `**.example.com` for apex plus subdomains, and global `*` allow rules. Prefer scoped rules because `*` broadly opens public outbound access. Environment rules can replace the same Global domain key within a policy. Higher-priority values replace the same key, while other inherited keys remain. After composition, a different matching `deny`, including an inherited wildcard, still blocks a request. Empty environment maps do not clear Global rules. Verify executor support. Do not combine this with `experimental_network.allowed_domains` or `experimental_network.denied_domains`. Key `experimental_network.domains.<pattern>` Type / Values `allow | deny` Details Allow or deny sandboxed network access for the matching domain pattern. A deny rule wins when several patterns match. Key `experimental_network.enabled` Type / Values `boolean` Details Enable sandboxed networking requirements. This does not grant network access when the active sandbox keeps command networking off. Key `experimental_network.http_port` Type / Values `integer` Details Loopback HTTP listener port to use for `[experimental_network]` requirements. Key `experimental_network.managed_allowed_domains_only` Type / Values `boolean` Details When networking requirements are enabled and this is true, ordinary user configuration and per-domain approvals cannot expand the managed proxy allowlist. With no effective configured or inherited Allow entries, ordinary managed commands have no allowed destinations. A deny-only policy does not allow the rest of the internet. This does not cover every tool or approved full sandbox escalation. Key `experimental_network.socks_port` Type / Values `integer` Details Loopback SOCKS5 listener port to use for `[experimental_network]` requirements. Key `experimental_network.unix_sockets` Type / Values `map<string, allow | deny>` Details Administrator-managed Unix socket allowlist for sandboxed networking on macOS. Paths must be absolute. Key `experimental_network.unix_sockets.<path>` Type / Values `allow | deny` Details On macOS, `allow` adds an absolute Unix socket path to the allowlist; `deny` leaves it out. A `deny` entry cannot block a socket when allow-all Unix sockets is enabled. Key `features` Type / Values `table` Details Pinned feature values. Use canonical names from `config.toml` for runtime features; documented app-only requirement keys are also supported here. Key `features.<name>` Type / Values `boolean` Details Require a documented runtime or app feature to stay enabled or disabled. Key `features.apps` Type / Values `boolean` Details Pin Apps integration availability on or off for managed users. Key `features.browser_use` Type / Values `boolean` Details Set to `false` in `requirements.toml` to disable agent-driven Browser Use. Key `features.browser_use_external` Type / Values `boolean` Details Set to `false` in `requirements.toml` to prevent Codex from operating supported browsers through the ChatGPT browser extension, including existing tabs and signed-in sessions. Key `features.browser_use_full_cdp_access` Type / Values `boolean` Details Set to `false` in `requirements.toml` to disable full Chrome DevTools Protocol access in the local runtime, including Browser Developer mode, and prevent the ChatGPT desktop app from enabling the corresponding setting. If omitted, normal product availability applies. Key `features.computer_use` Type / Values `boolean` Details Set to `false` in `requirements.toml` to disable Computer Use, Record & Replay, and related install or enablement flows. Key `features.fast_mode` Type / Values `boolean` Details Pin the canonical `fast_mode` feature on or off for managed users. Key `features.guardian_approval` Type / Values `boolean` Details Pin Guardian approval availability on or off for managed users. Key `features.in_app_browser` Type / Values `boolean` Details Set to `false` in `requirements.toml` to disable the built-in browser pane that users open and control directly. Key `features.in_app_chat` Type / Values `boolean` Details Set to `false` to hide ChatGPT and ChatGPT Work conversation screens and related cloud automation UI in the ChatGPT desktop app. This setting does not block ChatGPT Voice or stop existing cloud tasks. Setting it to `true` does not bypass account, workspace-permission, or rollout checks. Key `features.in_app_dictation` Type / Values `boolean` Details Set to `false` to disable in-app dictation in the desktop app. Setting it to `true` does not bypass other availability checks. Key `features.in_app_local_automation` Type / Values `boolean` Details Set to `false` to disable local scheduled tasks in the desktop app. Setting it to `true` does not bypass other availability checks. Key `features.in_app_updates` Type / Values `boolean` Details Set to `false` in `requirements.toml` to disable in-app updates. Updates remain enabled by default when this requirement is omitted. Key `features.memories` Type / Values `boolean` Details Pin Memories availability on or off for managed users. Key `features.multi_agent` Type / Values `boolean` Details Pin multi-agent availability on or off for managed users. Key `features.plugin_sharing` Type / Values `boolean` Details Set to `false` in cloud-managed `requirements.toml` to disable workspace sharing for locally built plugins. Key `features.plugins` Type / Values `boolean` Details Pin plugin availability on or off for managed users. Key `features.realtime_conversation` Type / Values `boolean` Details Set to `false` to disable the experimental `/voice` command in the Codex CLI. Do not rely on this setting to block [ChatGPT Voice](https://learn.chatgpt.com/codex/features/voice) in the desktop app or app-server voice sessions. Setting it to `true` does not bypass client or rollout checks. Key `features.remote_plugin` Type / Values `boolean` Details Pin remote plugin catalog availability on or off for managed users. Key `features.workspace_dependencies` Type / Values `boolean` Details Pin bundled workspace-dependency runtime availability on or off for managed users. Key `feedback` Type / Values `table` Details Managed feedback settings. Key `feedback.enabled` Type / Values `boolean` Details Enforce whether users can submit feedback across Codex clients. Key `guardian_extra_policy` Type / Values `string` Details Additional managed Markdown policy for automatic review, included alongside the main policy. This takes precedence over local `[auto_review].extra_policy`. Blank values are ignored. Key `guardian_policy_config` Type / Values `string` Details Managed Markdown policy instructions for automatic review. This takes precedence over local `[auto_review].policy`. Blank values are ignored. Key `hooks` Type / Values `table` Details Admin-enforced managed lifecycle hooks. Requires a managed hook directory and uses the same event schema as inline `[hooks]` in `config.toml`. Key `hooks.<Event>` Type / Values `array<table>` Details Matcher groups for a hook event such as `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `UserPromptSubmit`, or `Stop`. Key `hooks.<Event>[].hooks` Type / Values `array<table>` Details Hook handlers for a matcher group. Command and MCP tool hooks are supported while prompt and agent hook handlers are parsed but skipped. Key `hooks.<Event>[].hooks[].additionalContextLimit` Type / Values `integer` Details Approximate per-handler token threshold for saving oversized `additionalContext` to disk and showing the model a shorter preview. Defaults to `2500`; `0` passes the full context directly to the model. See [Large hook output](https://learn.chatgpt.com/codex/hooks#large-hook-output). Key `hooks.<Event>[].hooks[].async` Type / Values `boolean` Details Run a command hook in the background without delaying the triggering operation. Defaults to `false`; `SessionEnd` always runs synchronously. See [Run hooks in the background](https://learn.chatgpt.com/codex/hooks#run-hooks-in-the-background). Key `hooks.<Event>[].hooks[].commandWindows` Type / Values `string` Details Windows-only command override for command hooks. The TOML alias `command_windows` is also accepted. Key `hooks.managed_dir` Type / Values `string (absolute path)` Details Directory containing managed hook scripts on macOS and Linux. Codex validates that it is absolute and exists before loading managed hooks. Key `hooks.windows_managed_dir` Type / Values `string (absolute path)` Details Directory containing managed hook scripts on Windows. Codex validates that it is absolute and exists before loading managed hooks. Key `in_app_browser` Type / Values `table` Details Requirements for the built-in browser pane. These settings do not control agent-driven Browser Use. Key `in_app_browser.allow_external_browser_settings_import` Type / Values `boolean` Details Set to `false` to prevent users from importing settings or browsing data from an external browser into the built-in browser. Setting it to `true` or omitting it leaves the import available when other product checks allow it. This is a managed-only setting with no `config.toml` override. Key `log_dir` Type / Values `string (path)` Details Enforce the directory where Codex writes local log files. Key `marketplaces` Type / Values `table` Details Admin requirements for plugin marketplace sources. Rules take effect when `restrict_to_allowed_sources` is `true`. Key `marketplaces.allowed_sources` Type / Values `table` Details Allowed marketplace sources keyed by administrator-chosen rule name. Distinct names accumulate across requirements layers; fields under the same name use normal layer precedence. Key `marketplaces.allowed_sources.<name>` Type / Values `table` Details One allowed source rule. The final `source` value after requirements merge determines which sibling fields Codex interprets. Key `marketplaces.allowed_sources.<name>.host_pattern` Type / Values `string` Details Regular expression required when `source = "host_pattern"`. Codex matches it against the lowercase hostname parsed from an HTTPS, SSH, or SCP-style Git source. Use `^` and `$` to require a whole-host match. Key `marketplaces.allowed_sources.<name>.path` Type / Values `string (absolute path)` Details Local marketplace directory required when `source = "local"`. Codex requires an absolute path and compares paths after normalization. Key `marketplaces.allowed_sources.<name>.ref` Type / Values `string` Details Optional exact Git ref for a `git` rule. When omitted, the rule allows any ref for the matching repository. Key `marketplaces.allowed_sources.<name>.source` Type / Values `git | host_pattern | local` Details Marketplace source matcher type. Use `git` for one repository, `host_pattern` for Git hosts matched by regular expression, or `local` for one directory. Key `marketplaces.allowed_sources.<name>.url` Type / Values `string` Details Git repository URL required when `source = "git"`. Codex normalizes the configured and allowed URLs before requiring an exact repository match. Key `marketplaces.restrict_to_allowed_sources` Type / Values `boolean` Details When `true`, require configured marketplace sources to match `allowed_sources` for marketplace add, plugin install, refresh, and runtime loading. OpenAI-curated Git catalogs, including the API-key catalog, must also match the allowlist. Bundled and remotely installed workspace plugins are separate from this curated Git source policy. Key `mcp_servers` Type / Values `table` Details Allowlist of MCP servers that may be enabled. Both the server name (`<id>`) and its identity must match for the MCP server to be enabled. Any configured MCP server not in the allowlist (or with a mismatched identity) is disabled. Key `mcp_servers.<id>.identity` Type / Values `table` Details Identity rule for a single MCP server. Set either `command` (stdio) or `url` (streamable HTTP). Key `mcp_servers.<id>.identity.command` Type / Values `string | table` Details Allow an MCP stdio server by exact command string, or use a matcher table to require an exact executable and ordered argument matchers. The string form doesn't inspect arguments, `cwd`, `env`, or `env_vars`. Key `mcp_servers.<id>.identity.command.args` Type / Values `array<table>` Details Ordered argument matchers for a stdio server. The configured argument list must have the same length, and every position must match. Command matchers don't inspect `cwd`, `env`, or `env_vars`. Key `mcp_servers.<id>.identity.command.args[].expression` Type / Values `string` Details Regular expression used by a `regex` argument matcher. The expression must be valid and match the complete argument value. Key `mcp_servers.<id>.identity.command.args[].match` Type / Values `exact | prefix | regex` Details Match operation for this argument position. Key `mcp_servers.<id>.identity.command.args[].value` Type / Values `string` Details Value used by an `exact` or `prefix` argument matcher. Key `mcp_servers.<id>.identity.command.executable` Type / Values `string` Details Executable that the stdio server's configured `command` must match exactly. Key `mcp_servers.<id>.identity.url` Type / Values `string | table` Details Allow an MCP streamable HTTP server by exact URL string, or use an `exact`, `prefix`, or `regex` value matcher table. Key `mcp_servers.<id>.identity.url.expression` Type / Values `string` Details Regular expression used by a `regex` URL matcher. The expression must be valid and match the complete URL value. Key `mcp_servers.<id>.identity.url.match` Type / Values `exact | prefix | regex` Details Match operation for the configured MCP server URL. Key `mcp_servers.<id>.identity.url.value` Type / Values `string` Details Value used by an `exact` or `prefix` URL matcher. Key `model_catalog_json` Type / Values `string (path)` Details Enforce the JSON model catalog Codex uses at startup. Key `model_provider` Type / Values `string` Details Enforce the model provider ID, overriding local and session configuration. Key `model_providers` Type / Values `map<string, table>` Details Managed model provider definitions. Each entry replaces the complete configured provider with the same ID; fields aren't merged with the user's definition. Providers with other IDs remain available. Key `model_providers.<id>` Type / Values `table` Details Complete managed provider definition. Uses the same provider fields as `config.toml`, including `name`, `base_url`, authentication, and transport settings. Key `models` Type / Values `table` Details Contains the `[models.new_thread]` table. Key `models.new_thread` Type / Values `table` Details Optional defaults to apply when a new local thread starts. They take priority over user and project defaults, but can be superseded by explicit overrides. Key `models.new_thread.model` Type / Values `string` Details Default model for new threads. An explicit override of either the model or reasoning effort causes both fields to be ignored. Key `models.new_thread.model_reasoning_effort` Type / Values `string` Details Default reasoning effort for new threads. An explicit override of either the model or reasoning effort causes both fields to be ignored. Key `models.new_thread.service_tier` Type / Values `string` Details Default service tier for new threads. An explicit service-tier override causes this field to be ignored. Key `permissions` Type / Values `table` Details Admin-defined permission profiles keyed by profile name. Uses the same profile fields as `config.toml`. Key `permissions.<name>` Type / Values `table` Details Admin-defined permission profile. The name can't start with `:`, use the reserved name `filesystem`, or duplicate a profile from a loaded config. Uses the same profile fields as `config.toml`; see the Permissions guide for the complete profile schema. Key `permissions.filesystem.deny_read` Type / Values `array<string>` Details Admin-enforced filesystem read denials. Entries can be paths or glob patterns, and users cannot weaken them with local config. Key `plugins` Type / Values `table` Details Plugin-specific MCP server allowlists keyed by plugin identifier. When this table is present, plugin-bundled servers without a matching plugin and server entry are disabled. Key `plugins.<plugin>.mcp_servers` Type / Values `table` Details Allowlist for MCP servers bundled with one plugin. Plugin server requirements use the same exact identity and matcher forms as top-level `mcp_servers` requirements. Key `plugins.<plugin>.mcp_servers.<server>.identity` Type / Values `table` Details Identity rule for one plugin-bundled MCP server. Set either `command` (stdio) or `url` (streamable HTTP). Key `plugins.<plugin>.mcp_servers.<server>.identity.command` Type / Values `string | table` Details Allow a plugin's stdio MCP server by exact command string, or use a matcher table to require an exact executable and ordered argument matchers. Key `plugins.<plugin>.mcp_servers.<server>.identity.command.args` Type / Values `array<table>` Details Ordered argument matchers for a plugin-bundled stdio server. The configured argument list must have the same length, and every position must match. Key `plugins.<plugin>.mcp_servers.<server>.identity.command.args[].expression` Type / Values `string` Details Regular expression used by a `regex` argument matcher. The expression must match the complete argument value. Key `plugins.<plugin>.mcp_servers.<server>.identity.command.args[].match` Type / Values `exact | prefix | regex` Details Match operation for this argument position. Key `plugins.<plugin>.mcp_servers.<server>.identity.command.args[].value` Type / Values `string` Details Value used by an `exact` or `prefix` argument matcher. Key `plugins.<plugin>.mcp_servers.<server>.identity.command.executable` Type / Values `string` Details Executable that the plugin-bundled stdio server's configured command must match exactly. Key `plugins.<plugin>.mcp_servers.<server>.identity.url` Type / Values `string | table` Details Allow a plugin's streamable HTTP MCP server by exact URL string, or use an `exact`, `prefix`, or `regex` value matcher table. Key `plugins.<plugin>.mcp_servers.<server>.identity.url.expression` Type / Values `string` Details Regular expression used by a `regex` URL matcher. The expression must match the complete URL value. Key `plugins.<plugin>.mcp_servers.<server>.identity.url.match` Type / Values `exact | prefix | regex` Details Match operation for the plugin-bundled MCP server URL. Key `plugins.<plugin>.mcp_servers.<server>.identity.url.value` Type / Values `string` Details Value used by an `exact` or `prefix` URL matcher. Key `remote_sandbox_config` Type / Values `array<table>` Details Host-specific sandbox requirements. The first entry whose `hostname_patterns` match the resolved host name overrides top-level `allowed_sandbox_modes` for that requirements source. Host-specific entries currently override sandbox modes only. Key `remote_sandbox_config[].allowed_sandbox_modes` Type / Values `array<string>` Details Allowed sandbox modes to apply when this host-specific entry matches. Key `remote_sandbox_config[].hostname_patterns` Type / Values `array<string>` Details Case-insensitive host name patterns. Supports `*` for any sequence of characters and `?` for one character. Key `rules` Type / Values `table` Details Admin-enforced command rules merged with `.rules` files. Requirements rules must be restrictive. Key `rules.prefix_rules` Type / Values `array<table>` Details List of enforced prefix rules. Each rule must include `pattern` and `decision`. Key `rules.prefix_rules[].decision` Type / Values `prompt | forbidden` Details Required. Requirements rules can only prompt or forbid (not allow). Key `rules.prefix_rules[].justification` Type / Values `string` Details Optional non-empty rationale surfaced in approval prompts or rejection messages. Key `rules.prefix_rules[].pattern` Type / Values `array<table>` Details Command prefix expressed as pattern tokens. Each token sets either `token` or `any_of`. Key `rules.prefix_rules[].pattern[].any_of` Type / Values `array<string>` Details A list of allowed alternative tokens at this position. Key `rules.prefix_rules[].pattern[].token` Type / Values `string` Details A single literal token at this position. Key `sqlite_home` Type / Values `string (path)` Details Enforce the directory where Codex stores SQLite-backed runtime state. Key `windows` Type / Values `table` Details Native Windows sandbox requirements. Key `windows.allowed_sandbox_implementations` Type / Values `array<string>` Details Allowed legacy native Windows sandbox implementations (`elevated` and `unelevated`). The list must not be empty. When both are allowed and no mode is selected, Codex prefers `elevated`. This list does not restrict the `mxc` sandbox when it is available. Expand to view all