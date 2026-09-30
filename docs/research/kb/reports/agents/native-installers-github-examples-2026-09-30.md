# Native CLI installers (codex / claude / agy) — GitHub code-search examples, 2026-09-30

Method: `gh api -X GET search/code -f q=<query> -f per_page=10`, one query per
alternative (no `OR`). Every returned hit on the first page was re-fetched via the
contents API at the indexed ref and grepped for the query term; hits are marked
CONFIRMED only when the re-fetched bytes contain the term. Bound: only the first
10 hits per query are re-fetched (`total_count` gives the full size). Control arms:
a positive query that must hit (`"[tools]" filename:mise.toml`) and a freshly
invented nonsense token that must return 0.

## Raw query log (written incrementally)

### CONTROL-positive

- query: `"[tools]" filename:mise.toml`
- rc: 0
- total_count: 25280 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [gruntwork-io/cloud-nuke/mise.toml](https://github.com/gruntwork-io/cloud-nuke/blob/306d2b7794b92db4f9b7ad16bf8db7ebee5411ae/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [maxmind/MaxMind-DB-Reader-php/mise.toml](https://github.com/maxmind/MaxMind-DB-Reader-php/blob/c3c430991bafbf6b42d7d5554109fab5637deda0/mise.toml) — CONFIRMED
    - `L4: [tools]`
  - [stencila/stencila/mise.toml](https://github.com/stencila/stencila/blob/508dbf25c62a03b0daab8056b49fbc338c83800d/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [cupcakearmy/cryptgeon/mise.toml](https://github.com/cupcakearmy/cryptgeon/blob/f6ea6376e18a91ac1b72aa44fcaeea34a207ee70/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [sourcegraph/src-cli/mise.toml](https://github.com/sourcegraph/src-cli/blob/2fc111e9c2f446785e7d9a00be85512083390962/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [gronxb/hot-updater/mise.toml](https://github.com/gronxb/hot-updater/blob/d72439d03d6a8d397368401634109eb03a7be2b0/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [get-thriving/thrive/mise.toml.hbs](https://github.com/get-thriving/thrive/blob/43fdb5b5b2c4db0715971c46215f4e6e6ba7d314/mise.toml.hbs) — CONFIRMED
    - `L7: [tools]`
  - [ivangabriele/clamav-desktop/mise.toml](https://github.com/ivangabriele/clamav-desktop/blob/10678fbf85e11d0e63bf69af7bb908d6136d160a/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [michel-kraemer/bson4jackson/mise.toml](https://github.com/michel-kraemer/bson4jackson/blob/c0eb2cba635beb06d5d4282072e114d1b9f9cbe5/mise.toml) — CONFIRMED
    - `L1: [tools]`
  - [Layr-Labs/eigenda/mise.toml](https://github.com/Layr-Labs/eigenda/blob/bfa451e1aaa5eb53ec250758054bbc3267e66208/mise.toml) — CONFIRMED
    - `L1: [tools]`

### CONTROL-negative

- query: `"qvxjwrplmtz_nonexist_20260930" filename:mise.toml`
- rc: 0
- total_count: 0 (incomplete_results=False); re-fetched first 0 (per_page=10)

### disable_tools mise.toml

- query: `"disable_tools" filename:mise.toml`
- rc: 0
- total_count: 116 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [tambo-ai/tambo/mise.toml](https://github.com/tambo-ai/tambo/blob/0c84ae09499bc9e18fd0bd49f6abe53b526026f3/mise.toml) — CONFIRMED
    - `L18: disable_tools = ["npm", "pnpm", "yarn"]`
  - [kumahq/kuma/mise.toml](https://github.com/kumahq/kuma/blob/5ca209a09b2fd1125dfea115e2e9c5c25c69e52e/mise.toml) — CONFIRMED
    - `L34: # ⚠️ If you change any tool name below, update 'MISE_DISABLE_TOOLS' in:`
  - [ethereum-optimism/optimism/mise.toml](https://github.com/ethereum-optimism/optimism/blob/777fc39a9220814391ee1fdf99f56b923ad487ca/mise.toml) — CONFIRMED
    - `L97: disable_tools = ["kontrol", "binary_signer"]`
  - [guillevc/yubal/extension/mise.toml](https://github.com/guillevc/yubal/blob/78d63846712178ded0b5f3c2552a80e952451c3c/extension/mise.toml) — CONFIRMED
    - `L2: disable_tools = ["deno", "github:complexlogic/rsgain", "uv"]`
  - [Lightprotocol/light-protocol/.mise.toml](https://github.com/Lightprotocol/light-protocol/blob/a67a427e6c58a38dd2e6a16a4042ca91d7cf4571/.mise.toml) — CONFIRMED
    - `L4: disable_tools = ["go"]`
  - [vraravam/dotfiles/.mise.toml](https://github.com/vraravam/dotfiles/blob/cbf682a48509b0d6044f8c45596e1c46a38f4fd5/.mise.toml) — CONFIRMED
    - `L14: disable_tools = ["ruby"]`
  - [ethereum-optimism/infra/mise.toml](https://github.com/ethereum-optimism/infra/blob/f70cc485d174f0c2432d182321b3c4773c0e3fdd/mise.toml) — CONFIRMED
    - `L25: disable_tools = ["asterisc", "kontrol", "binary_signer"]`
  - [guideline-tech/subroutine/mise.toml](https://github.com/guideline-tech/subroutine/blob/3873a33fb4a4e4c74eeddce6a663646562770e93/mise.toml) — CONFIRMED
    - `L6: disable_tools = ["lefthook"]`
  - [maplibre/maplibre-compose/mise.toml](https://github.com/maplibre/maplibre-compose/blob/32947a9bf02c96b597fa7aa318732be57cb73ed4/mise.toml) — CONFIRMED
    - `L20: auto_install_disable_tools = ["android-sdk"]`
  - [flayerlabs/flaunchgg-contracts/lib/optimism/mise.toml](https://github.com/flayerlabs/flaunchgg-contracts/blob/77d7d23cd7c8c947e7f63d2c2da95cc766c093ea/lib/optimism/mise.toml) — CONFIRMED
    - `L63: disable_tools = ["asterisc", "kontrol", "binary_signer"]`

### disable_tools config.toml (mise)

- query: `"disable_tools" path:.config/mise`
- rc: 0
- total_count: 20 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [wasp-lang/wasp/.config/mise/config.ci.toml](https://github.com/wasp-lang/wasp/blob/821695e72d65acf1bf60764ac5f9f91b5b76df80/.config/mise/config.ci.toml) — CONFIRMED
    - `L8: disable_tools = [`
  - [wasp-lang/wasp/.config/mise/config.ci-no-haskell.toml](https://github.com/wasp-lang/wasp/blob/821695e72d65acf1bf60764ac5f9f91b5b76df80/.config/mise/config.ci-no-haskell.toml) — CONFIRMED
    - `L10: disable_tools = [`
  - [apphane-dev/nehir/.config/mise/conf.d/tools.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tools.toml) — CONFIRMED
    - `L5: # download a swift.org toolchain that shadows Xcode. 'disable_tools' tells mise`
    - `L8: disable_tools = ["swift"]`
  - [moniquelive/dotfiles/.config/mise/config.freebsd.toml](https://github.com/moniquelive/dotfiles/blob/a73ea7d349d8ab51bd9259fc2b87bbef4e778a78/.config/mise/config.freebsd.toml) — CONFIRMED
    - `L2: disable_tools = [`
  - [hay-kot/dotfiles/.config/mise/config.toml](https://github.com/hay-kot/dotfiles/blob/36ba363fe1a623dadc31303466b3cc0210a73ee8/.config/mise/config.toml) — CONFIRMED
    - `L15: disable_tools = ["git-lfs"]`
  - [MacPaw/cocoa-tools-cli/.config/mise/config.ci.toml](https://github.com/MacPaw/cocoa-tools-cli/blob/c7daf7e890cb7e50b7696ed456dd97274c9fa6ce/.config/mise/config.ci.toml) — CONFIRMED
    - `L6: disable_tools = ["container", "gitleaks", "hk", "pkl", "1password"]`
  - [rokoucha/dotfiles/.config/mise/config.toml](https://github.com/rokoucha/dotfiles/blob/9ecfc05b819a7c975a471b67e8c8ba425898580f/.config/mise/config.toml) — CONFIRMED
    - `L3: disable_tools = ["node"]`
  - [fluffybeing/dotfiles/.config/mise/config.toml](https://github.com/fluffybeing/dotfiles/blob/5598367d72f74d817dedcc40b3c39d601520f99d/.config/mise/config.toml) — CONFIRMED
    - `L17: idiomatic_version_file_disable_tools = ['python'] # disable for specific tools`
    - `L45: disable_tools = ['node']           # disable specific tools, generally used to turn off core tools`
  - [andrew-grechkin/dotfiles/.config/mise/mise](https://github.com/andrew-grechkin/dotfiles/blob/6a62008de9e488600bbce288ab6965ca119582be/.config/mise/mise) — CONFIRMED
    - `L8: disable_tools = ["yarn"]`
  - [hnagato/dotfiles/.config/mise/settings.toml](https://github.com/hnagato/dotfiles/blob/c50195e7c96743fac037911e4220d7dd5bcfc7bd/.config/mise/settings.toml) — CONFIRMED
    - `L2: legacy_version_file_disable_tools = ['python']`

### disable_tools any TOML

- query: `"disable_tools" language:TOML`
- rc: 0
- total_count: 269 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [wasp-lang/wasp/.config/mise/config.ci.toml](https://github.com/wasp-lang/wasp/blob/821695e72d65acf1bf60764ac5f9f91b5b76df80/.config/mise/config.ci.toml) — CONFIRMED
    - `L8: disable_tools = [`
  - [tambo-ai/tambo/mise.toml](https://github.com/tambo-ai/tambo/blob/0c84ae09499bc9e18fd0bd49f6abe53b526026f3/mise.toml) — CONFIRMED
    - `L18: disable_tools = ["npm", "pnpm", "yarn"]`
  - [kumahq/kuma/mise.toml](https://github.com/kumahq/kuma/blob/5ca209a09b2fd1125dfea115e2e9c5c25c69e52e/mise.toml) — CONFIRMED
    - `L34: # ⚠️ If you change any tool name below, update 'MISE_DISABLE_TOOLS' in:`
  - [wasp-lang/wasp/.config/mise/config.ci-no-haskell.toml](https://github.com/wasp-lang/wasp/blob/821695e72d65acf1bf60764ac5f9f91b5b76df80/.config/mise/config.ci-no-haskell.toml) — CONFIRMED
    - `L10: disable_tools = [`
  - [ethereum-optimism/optimism/mise.toml](https://github.com/ethereum-optimism/optimism/blob/777fc39a9220814391ee1fdf99f56b923ad487ca/mise.toml) — CONFIRMED
    - `L97: disable_tools = ["kontrol", "binary_signer"]`
  - [jdx/mise/settings.toml](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/settings.toml) — CONFIRMED
    - `L289: [auto_install_disable_tools]`
    - `L291: env = "MISE_AUTO_INSTALL_DISABLE_TOOLS"`
    - `L559: [disable_tools]`
    - `L562: env = "MISE_DISABLE_TOOLS"`
  - [guillevc/yubal/mise.ci.toml](https://github.com/guillevc/yubal/blob/78d63846712178ded0b5f3c2552a80e952451c3c/mise.ci.toml) — CONFIRMED
    - `L2: disable_tools = ["git-cliff", "github:complexlogic/rsgain"]`
  - [SonarSource/sonar-python/mise.ci.toml](https://github.com/SonarSource/sonar-python/blob/fc9ddc99724022c1858a2b8b116097d2474d543c/mise.ci.toml) — CONFIRMED
    - `L4: disable_tools = ["pipx:tox"]`
  - [guillevc/yubal/extension/mise.toml](https://github.com/guillevc/yubal/blob/78d63846712178ded0b5f3c2552a80e952451c3c/extension/mise.toml) — CONFIRMED
    - `L2: disable_tools = ["deno", "github:complexlogic/rsgain", "uv"]`
  - [Lightprotocol/light-protocol/.mise.toml](https://github.com/Lightprotocol/light-protocol/blob/a67a427e6c58a38dd2e6a16a4042ca91d7cf4571/.mise.toml) — CONFIRMED
    - `L4: disable_tools = ["go"]`

### task update:codex

- query: `"update:codex"`
- rc: 0
- total_count: 102 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [makecindy/cindy/scripts/help.mjs](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/scripts/help.mjs) — CONFIRMED
    - `L34: log('    pnpm update:codex');`
    - `L35: log('    pnpm update:codex-package');`
    - `L42: log('    pnpm update:codex 0.144.1');`
    - `L43: log('    pnpm update:codex-package 0.145.0');`
  - [BenedictKing/ccx/desktop/frontend/src/components/agent/AgentTab.vue](https://github.com/BenedictKing/ccx/blob/19f31d8475632b90b25cbe6c2a4469c913938766/desktop/frontend/src/components/agent/AgentTab.vue) — CONFIRMED
    - `L192: @update:codex-mode="codexMode = $event"`
    - `L193: @update:codex-open-a-i-key="codexOpenAIKey = $event"`
    - `L194: @update:codex-open-a-i-use-own-key="codexOpenAIUseOwnKey = $event"`
  - [makecindy/cindy/package.json](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/package.json) — CONFIRMED
    - `L90: "update:codex": "node tools/codex/update.mjs",`
    - `L91: "update:codex-package": "node tools/codex-package/update.mjs",`
  - [makecindy/cindy/apps/desktop/src/main/agent-binaries/index.ts](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/apps/desktop/src/main/agent-binaries/index.ts) — CONFIRMED
    - `L22: *       dev: findDevBinary 短路, 缺失硬错 (开发者必须 pnpm update:codex-package)`
  - [archestra-ai/archestra/platform/backend/package.json](https://github.com/archestra-ai/archestra/blob/7ed976a182eaf7147f5623b76ba8f305e5d24ddb/platform/backend/package.json) — CONFIRMED
    - `L35: "update:codex-models-client-version": "node scripts/update-codex-models-client-version.mjs",`
  - [r1n7aro/Locus/src/components/SettingsView.vue](https://github.com/r1n7aro/Locus/blob/6074316c8cd9366e4cb92383a1661d5e7e20974e/src/components/SettingsView.vue) — CONFIRMED
    - `L347: @update:codex-transport="setCodexTransportMode"`
    - `L348: @update:codex-context-window="setCodexContextWindow"`
    - `L349: @update:codex-session-title-generation="setCodexSessionTitleGeneration"`
    - `L350: @update:codex-auto-review="setCodexAutoReview"`
  - [hashgraph-online/awesome-codex-plugins/plugins/sendbird/cc-plugin-codex/package.json](https://github.com/hashgraph-online/awesome-codex-plugins/blob/86167b0fa7bb91f8b5ce09db5dc20e134e7afc4c/plugins/sendbird/cc-plugin-codex/package.json) — CONFIRMED
    - `L58: "update:codex": "node scripts/installer-cli.mjs update",`
  - [vox-deorum/vox-deorum/docs/developers/vox-agents/codex.md](https://github.com/vox-deorum/vox-deorum/blob/60d5420a9ab090ca74a8d2486192d4b6a87a0f6c/docs/developers/vox-agents/codex.md) — CONFIRMED
    - `L38: npm run update:codex-proxy -- rc.12`
  - [vox-deorum/vox-deorum/docs/developers/operations.md](https://github.com/vox-deorum/vox-deorum/blob/60d5420a9ab090ca74a8d2486192d4b6a87a0f6c/docs/developers/operations.md) — CONFIRMED
    - `L45: This mirrors the invocation vox-agents builds. '--login device-code' forces the device-code sign-in flow, which the proxy would otherwise only pick when its std`
  - [sendbird/cc-plugin-codex/package.json](https://github.com/sendbird/cc-plugin-codex/blob/19e565151f35b328a5b9433df351bd8f3818fdc7/package.json) — CONFIRMED
    - `L58: "update:codex": "node scripts/installer-cli.mjs update",`

### task update:claude

- query: `"update:claude"`
- rc: 0
- total_count: 101 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [makecindy/cindy/scripts/help.mjs](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/scripts/help.mjs) — CONFIRMED
    - `L33: log('    pnpm update:claude');`
    - `L41: log('    pnpm update:claude 2.1.199');`
  - [BenedictKing/ccx/desktop/frontend/src/components/agent/AgentTab.vue](https://github.com/BenedictKing/ccx/blob/19f31d8475632b90b25cbe6c2a4469c913938766/desktop/frontend/src/components/agent/AgentTab.vue) — CONFIRMED
    - `L185: @update:claude-provider-keys="claudeProviderKeys = $event"`
    - `L186: @update:claude-mimo-base-url="claudeMimoBaseUrl = $event"`
  - [alirezarezvani/ClaudeForge/examples/integration-examples.md](https://github.com/alirezarezvani/ClaudeForge/blob/032c5e5a0f6844df7548426e2e04e68994f8f57d/examples/integration-examples.md) — CONFIRMED
    - `L91: "update:claude": "echo 'Run: /enhance-claude-md in Claude Code'",`
  - [makecindy/cindy/package.json](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/package.json) — CONFIRMED
    - `L89: "update:claude": "node tools/claude/update.mjs",`
  - [MemberJunction/MJ/templates/claude-pack/README.md](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/templates/claude-pack/README.md) — CONFIRMED
    - `L38: for what 'mj install' lays down at scaffold time and what 'mj update:claude' fetches over`
    - `L95: 'mj update:claude --refresh-commands' can detect drift on future bumps.`
    - `L117: without 'mj update:claude' overwriting their edits. To force a resync,`
  - [MemberJunction/MJ/templates/claude-pack/core/00-pack-header.md](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/templates/claude-pack/core/00-pack-header.md) — CONFIRMED
    - `L26: mj update:claude --check    # see if an update is available`
    - `L27: mj update:claude            # apply the update (managed block + .claude/mj/)`
    - `L43: Anything in that section is yours forever — 'mj update:claude' won't touch it.`
  - [MemberJunction/MJ/templates/claude-pack/core/18-getting-help.md](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/templates/claude-pack/core/18-getting-help.md) — CONFIRMED
    - `L83: mj update:claude            # apply the latest pack`
    - `L84: mj update:claude --check    # see if an update is available`
  - [MemberJunction/MJ/templates/claude-pack/versions/v5/CHANGELOG.md](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/templates/claude-pack/versions/v5/CHANGELOG.md) — CONFIRMED
    - `L62: 'mj install:claude' / 'mj update:claude' (added with this pack release).`
    - `L76: 'mj update:claude'. Use '--force' to overwrite (saves '.bak' files).`
  - [MemberJunction/MJ/templates/claude-pack/CLAUDE.md.template](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/templates/claude-pack/CLAUDE.md.template) — CONFIRMED
    - `L9: - Refresh with: mj update:claude`
    - `L11: overwritten on the next 'mj update:claude' run. Add your own instructions`
  - [MemberJunction/MJ/packages/MJCLI/src/commands/update/claude.ts](https://github.com/MemberJunction/MJ/blob/87e1223f9fd293d21039b88116a286af7c8e9734/packages/MJCLI/src/commands/update/claude.ts) — CONFIRMED
    - `L7: * 'mj update:claude' — refresh the Claude Code pack in the current directory.`
    - `L21: '<%= config.bin %> update:claude',`
    - `L22: '<%= config.bin %> update:claude --check',`
    - `L23: '<%= config.bin %> update:claude --refresh-commands',`

### task install:agy

- query: `"install:agy"`
- rc: 0
- total_count: 22 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [bad33ndj3/flow-slice-skill/README.md](https://github.com/bad33ndj3/flow-slice-skill/blob/331e00128d2a51c3960673757d3d02d5d1d66481/README.md) — CONFIRMED
    - `L15: task install:agy`
  - [RxAi-Aus/amp/CLAUDE.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/CLAUDE.md) — CONFIRMED
    - `L37: npm run hooks:install:agy                 # v2.9.1: agy PreInvocation/Stop hooks + skill into ~/.gemini/config`
  - [RxAi-Aus/amp/scripts/postinstall-hint.mjs](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/scripts/postinstall-hint.mjs) — CONFIRMED
    - `L36: missing.push(["agy / Antigravity CLI (L2)", "npm run hooks:install:agy"]);`
  - [RxAi-Aus/amp/AGENTS.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/AGENTS.md) — CONFIRMED
    - `L127: npm run hooks:install:agy                 # agy PreInvocation/Stop hooks + global skill into ~/.gemini/config`
  - [RxAi-Aus/amp/README.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/README.md) — CONFIRMED
    - `L228: | **agy (Antigravity CLI)** | No extra setup needed — 'cd' into the directory (agy will ask once to trust the workspace). For every-project access to the skill `
    - `L417: | **agy (Antigravity CLI)** | No MCP server needed — agy talks to GitHub through the 'gh' CLI ('gh auth login'). Its AMP customizations live in '~/.gemini/confi`
    - `L1078: 'adapters/agy/', installed with 'npm run hooks:install:agy'. A`
  - [RxAi-Aus/amp/adapters/agy/README.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/adapters/agy/README.md) — CONFIRMED
    - `L19: npm run hooks:install:agy            # add -- --dry-run to preview`
  - [RxAi-Aus/amp/fullInstallation.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/fullInstallation.md) — CONFIRMED
    - `L94: | **Installer** | 'npm run hooks:install:claude' | 'npm run hooks:install:agy' | 'npm run hooks:install:codex' | 'npm run hooks:install:openclaw' | 'npm run hoo`
    - `L254: npm run hooks:install:agy           # add -- --dry-run to preview`
    - `L517: | agy hooks never fire | hooks.json points at a moved checkout (absolute paths) → rerun 'npm run hooks:install:agy'; debug payloads with 'RXAI_AMP_DEBUG=1 agy -`
  - [RxAi-Aus/amp/adapters/README.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/adapters/README.md) — CONFIRMED
    - `L46: npm run hooks:install:agy             # add -- --dry-run to preview`
  - [RxAi-Aus/amp/PROTOCOL.md](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/PROTOCOL.md) — CONFIRMED
    - `L2035: | 2.9.1 | 2026-08-17 | **ADDITIVE:** 'agy' (Antigravity CLI) registered as the fifth participating agent (§2) at conformance L2, and §2 Requirements clarified: `
  - [RxAi-Aus/amp/scripts/setup.mjs](https://github.com/RxAi-Aus/amp/blob/67bfee69b5250a1fca7829c9ebc279f674496e43/scripts/setup.mjs) — CONFIRMED
    - `L487: if (others.includes("agy")) info("agy: run 'npm run hooks:install:agy' (offered in the lifecycle step) — no MCP registration needed, it uses the gh CLI");`

### task install:claude

- query: `"install:claude"`
- rc: 0
- total_count: 608 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [cloudflare/workers-mcp/src/cli.ts](https://github.com/cloudflare/workers-mcp/blob/e22d7c46c49f34e3f825d750c0c316f7aa9728dd/src/cli.ts) — CONFIRMED
    - `L32: } else if (cmd === 'install:claude') {`
  - [cloudflare/workers-mcp/src/scripts/help.ts](https://github.com/cloudflare/workers-mcp/blob/e22d7c46c49f34e3f825d750c0c316f7aa9728dd/src/scripts/help.ts) — CONFIRMED
    - `L45: ${chalk.yellow('npx workers-mcp install:claude <name-within-claude> <url-to-your-hosted-worker>')}`
  - [rullerzhou-afk/clawd-on-desk/AGENTS.md](https://github.com/rullerzhou-afk/clawd-on-desk/blob/244cec4e99031ee749390f8ca40bf7fa7ae9d9a3/AGENTS.md) — CONFIRMED
    - `L29: npm run install:claude-hooks`
    - `L30: npm run uninstall:claude-hooks`
  - [cloudflare/workers-mcp/README.md](https://github.com/cloudflare/workers-mcp/blob/e22d7c46c49f34e3f825d750c0c316f7aa9728dd/README.md) — CONFIRMED
    - `L69: You shouldn't ever need to rerun 'npx workers-mcp install:claude', but it's safe to do so if you want to rule out Claude config as a source of errors.`
  - [makecindy/cindy/scripts/help.mjs](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/scripts/help.mjs) — CONFIRMED
    - `L28: log('    pnpm install:claude');`
  - [cloudflare/workers-mcp/src/scripts/install-claude.ts](https://github.com/cloudflare/workers-mcp/blob/e22d7c46c49f34e3f825d750c0c316f7aa9728dd/src/scripts/install-claude.ts) — CONFIRMED
    - `L9: console.error('usage: npx workers-mcp install:claude <claude_name> <workers_url>')`
  - [rullerzhou-afk/clawd-on-desk/docs/guides/setup-guide.md](https://github.com/rullerzhou-afk/clawd-on-desk/blob/244cec4e99031ee749390f8ca40bf7fa7ae9d9a3/docs/guides/setup-guide.md) — CONFIRMED
    - `L78: Running 'npm run install:claude-hooks' for a local hook repair does not opt in. The explicit debug form 'npm run install:claude-hooks -- --statusline' can insta`
  - [volcengine/ai-app-lab/demohouse/car-decision-assistant/README.md](https://github.com/volcengine/ai-app-lab/blob/88c983d70a098110fc839f8cd05e29fa7715e6ce/demohouse/car-decision-assistant/README.md) — CONFIRMED
    - `L24: # 或 npm run skill:install:claude`
  - [rullerzhou-afk/clawd-on-desk/docs/guides/setup-guide.zh-CN.md](https://github.com/rullerzhou-afk/clawd-on-desk/blob/244cec4e99031ee749390f8ca40bf7fa7ae9d9a3/docs/guides/setup-guide.zh-CN.md) — CONFIRMED
    - `L41: 普通本机修复命令 'npm run install:claude-hooks' 不会开启采集。显式调试命令 'npm run install:claude-hooks -- --statusline' 可以安装并显示 Clawd 状态栏，但 Settings 开关关闭时，应用仍会把其本机 context/quota P`
  - [cloudflare/workers-mcp/src/scripts/setup.ts](https://github.com/cloudflare/workers-mcp/blob/e22d7c46c49f34e3f825d750c0c316f7aa9728dd/src/scripts/setup.ts) — CONFIRMED
    - `L217: 'Unable to determine which URL your worker was deployed to.\nPlease run ${chalk.yellow('npx workers-mcp install:claude <name-within-claude> <url-to-your-hosted-`
    - `L237: 'Skipping! Please run ${chalk.yellow('npx workers-mcp install:claude <name-within-claude> <url-to-your-hosted-worker>')} manually.',`

### task install:codex

- query: `"install:codex"`
- rc: 0
- total_count: 633 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [code-yeongyu/oh-my-openagent/packages/omo-codex/scripts/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/packages/omo-codex/scripts/AGENTS.md) — CONFIRMED
    - `L18: | Dev dogfood install | repo root 'bun run install:codex-dev' |`
  - [code-yeongyu/oh-my-openagent/script/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/script/AGENTS.md) — CONFIRMED
    - `L41: | 'install-codex-dev.ts' | Dev dogfood installer: uninstall current Codex Light, then install this repo's local build into the REAL '~/.codex' stamped as versio`
  - [code-yeongyu/oh-my-openagent/.agents/skills/codex-qa/SKILL.md](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/.agents/skills/codex-qa/SKILL.md) — CONFIRMED
    - `L74: To tell a dev dogfood build apart from a published one on a REAL '~/.codex' (NOT the isolated QA home), the repo ships 'bun run install:codex-dev', which stamps`
  - [code-yeongyu/oh-my-openagent/packages/omo-codex/README.md](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/packages/omo-codex/README.md) — CONFIRMED
    - `L51: bun run install:codex-dev            # uninstalls current, installs repo HEAD as version "dev"`
  - [code-yeongyu/oh-my-openagent/packages/omo-codex/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/packages/omo-codex/AGENTS.md) — CONFIRMED
    - `L28: 'bun run install:codex-dev' swaps your real install for this repo's local build stamped as version 'dev' (env 'LAZYCODEX_DEV_VERSION', default 'dev'). Everywher`
  - [code-yeongyu/oh-my-openagent/package.json](https://github.com/code-yeongyu/oh-my-openagent/blob/c5d4972f53421d31a2568f56ef1b2bc0a268fa2a/package.json) — CONFIRMED
    - `L118: "install:codex-dev": "bun run script/build-codex-install.ts && bun run script/install-codex-dev.ts",`
  - [rullerzhou-afk/clawd-on-desk/AGENTS.md](https://github.com/rullerzhou-afk/clawd-on-desk/blob/244cec4e99031ee749390f8ca40bf7fa7ae9d9a3/AGENTS.md) — CONFIRMED
    - `L61: npm run install:codex-hooks`
    - `L62: npm run uninstall:codex-hooks`
    - `L63: npm run install:codex-debug-hooks`
    - `L64: npm run uninstall:codex-debug-hooks`
  - [makecindy/cindy/scripts/help.mjs](https://github.com/makecindy/cindy/blob/297c8577f7fcec0afa64fb0a234aa90fe482fca5/scripts/help.mjs) — CONFIRMED
    - `L29: log('    pnpm install:codex');`
  - [rullerzhou-afk/clawd-on-desk/package.json](https://github.com/rullerzhou-afk/clawd-on-desk/blob/244cec4e99031ee749390f8ca40bf7fa7ae9d9a3/package.json) — CONFIRMED
    - `L50: "install:codex-hooks": "node hooks/codex-install.js",`
    - `L51: "uninstall:codex-hooks": "node hooks/codex-install.js --uninstall",`
    - `L52: "install:codex-debug-hooks": "node hooks/codex-debug-install.js",`
    - `L53: "uninstall:codex-debug-hooks": "node hooks/codex-debug-install.js --uninstall",`
  - [volcengine/ai-app-lab/demohouse/car-decision-assistant/README.md](https://github.com/volcengine/ai-app-lab/blob/88c983d70a098110fc839f8cd05e29fa7715e6ce/demohouse/car-decision-assistant/README.md) — CONFIRMED
    - `L23: npm run skill:install:codex`

### claude native installer in mise.toml

- query: `"claude.ai/install.sh" filename:mise.toml`
- rc: 0
- total_count: 17 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [bellini666/dotfiles/mise.toml](https://github.com/bellini666/dotfiles/blob/a8dfafaddf3350e8e80a8b1d267a7ec3ce419884/mise.toml) — CONFIRMED
    - `L55: curl -fsSL https://claude.ai/install.sh -o "$agent_install_dir/claude.sh"`
  - [naa0yama/devtool-wsl2/mise.toml](https://github.com/naa0yama/devtool-wsl2/blob/969a24d092b7dc7f8d1883d8e627765b104c546e/mise.toml) — CONFIRMED
    - `L68: curl -fsSL https://claude.ai/install.sh | bash`
  - [hiramekun/dotfiles/mise.toml](https://github.com/hiramekun/dotfiles/blob/d6176679abeedbc71e2fac82474294f877ceda82/mise.toml) — CONFIRMED
    - `L106: "curl -fsSL https://claude.ai/install.sh | bash",`
  - [kjgarza/snowyowl/.mise.toml](https://github.com/kjgarza/snowyowl/blob/2555bec0090f41a996ef6520514f891f0c939ec9/.mise.toml) — CONFIRMED
    - `L107: curl -fsSL https://claude.ai/install.sh | bash`
    - `L129: curl -fsSL https://claude.ai/install.sh | bash`
  - [advaypakhale/dotfiles/mise.toml](https://github.com/advaypakhale/dotfiles/blob/0dbf02c274fb158ab4657d5e3a3b2bb21fea3e81/mise.toml) — CONFIRMED
    - `L26: run = '[ -x "$HOME/.local/bin/claude" ] || curl -fsSL https://claude.ai/install.sh | bash'`
  - [kyosuke/dotfiles/mise.toml](https://github.com/kyosuke/dotfiles/blob/2cf683d387526f5ac75471cc0263628966847b25/mise.toml) — CONFIRMED
    - `L21: "command -v claude >/dev/null || { set -o pipefail; curl -fsSL https://claude.ai/install.sh | bash; }",`
  - [carljohan/dotfiles/mise.toml](https://github.com/carljohan/dotfiles/blob/6e65cce6935f418a55927440afd5c888be62d640/mise.toml) — CONFIRMED
    - `L24: curl -fsSL https://claude.ai/install.sh | bash -s latest`
  - [ericboehs/dotfiles/mise.toml](https://github.com/ericboehs/dotfiles/blob/0b2725c6bcfdaba1db6353e441d207e2d48235ec/mise.toml) — CONFIRMED
    - `L976: curl -fsSL https://claude.ai/install.sh | bash`
  - [dkimura/osx-setup/mise.toml](https://github.com/dkimura/osx-setup/blob/194febd9442c69bed054b6852631b2c01b06eaf2/mise.toml) — CONFIRMED
    - `L70: test -x ~/.local/bin/claude || curl -fsSL https://claude.ai/install.sh | bash`
  - [halkn/dotfiles/mise.toml](https://github.com/halkn/dotfiles/blob/717c2378c42e6c6847184d6b7e88f76acc05be8a/mise.toml) — CONFIRMED
    - `L70: run = "command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash"`

### claude native installer in Dockerfile

- query: `"claude.ai/install.sh" filename:Dockerfile`
- rc: 0
- total_count: 4864 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [rizsotto/Bear/.devcontainer/Dockerfile](https://github.com/rizsotto/Bear/blob/7238459f4d221e3a3ad1fff007ba78d6a04a10fd/.devcontainer/Dockerfile) — CONFIRMED
    - `L17: && curl -fsSL https://claude.ai/install.sh | sh \`
  - [near/nearcore/.devcontainer/Dockerfile](https://github.com/near/nearcore/blob/bb04d86378ef66bbc0573771dad7d5fced25b2eb/.devcontainer/Dockerfile) — CONFIRMED
    - `L121: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [NVIDIA-BioNeMo/bionemo-recipes/.devcontainer/Dockerfile](https://github.com/NVIDIA-BioNeMo/bionemo-recipes/blob/11701476b005ca7bc489df924a398b8f12453f0b/.devcontainer/Dockerfile) — CONFIRMED
    - `L23: RUN curl -fsSL https://claude.ai/install.sh | bash || true # Install Claude CLI tool`
  - [codebutler/farebot/.devcontainer/Dockerfile](https://github.com/codebutler/farebot/blob/dc09f6f014ea3675b64bcd38335b4b78d77fa374/.devcontainer/Dockerfile) — CONFIRMED
    - `L76: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [akash-network/awesome-akash/claude-code/Dockerfile](https://github.com/akash-network/awesome-akash/blob/01c20ced89788646f8df97c8669638a38a6487e1/claude-code/Dockerfile) — CONFIRMED
    - `L19: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [Accio-Lab/Dressage/docker/Dockerfile](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docker/Dockerfile) — CONFIRMED
    - `L39: RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_CODE_VERSION}" && \`
  - [mimo-x/Code-Review-GPT-Gitlab/docker/backend/Dockerfile](https://github.com/mimo-x/Code-Review-GPT-Gitlab/blob/aff1e87be8d8cc0dd7679b1300157c55600cf187/docker/backend/Dockerfile) — CONFIRMED
    - `L15: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [joinly-ai/joinly/.devcontainer/Dockerfile](https://github.com/joinly-ai/joinly/blob/4ea1259de329aa6965d9fdb806db64a7cdeeb683/.devcontainer/Dockerfile) — CONFIRMED
    - `L31: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [matter-js/matter.js/.devcontainer/Dockerfile](https://github.com/matter-js/matter.js/blob/cc1de5a9f2692d5927cf5d9d91c5c5f6e863d4e2/.devcontainer/Dockerfile) — CONFIRMED
    - `L97: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [NandaScott/Scrython/.sandcastle/Dockerfile](https://github.com/NandaScott/Scrython/blob/3dd6d789b60b5df1304b46d29d02b0e9aab70daa/.sandcastle/Dockerfile) — CONFIRMED
    - `L34: RUN curl -fsSL https://claude.ai/install.sh | bash`

### claude native installer in devcontainer.json

- query: `"claude.ai/install.sh" filename:devcontainer.json`
- rc: 0
- total_count: 204 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [icloud-photos-downloader/icloud_photos_downloader/.devcontainer/python/devcontainer.json](https://github.com/icloud-photos-downloader/icloud_photos_downloader/blob/879c561240d993d748ddb4546f935090502b16d3/.devcontainer/python/devcontainer.json) — CONFIRMED
    - `L10: "postCreateCommand": "sudo apt-get update && sudo apt-get install -y locales-all && (curl -fsSL https://claude.ai/install.sh | bash)"`
  - [amd/gaia/.devcontainer/devcontainer.json](https://github.com/amd/gaia/blob/c5df3128f7f5eab4dd97723274d4dbb4b1c1347b/.devcontainer/devcontainer.json) — CONFIRMED
    - `L90: "postStartCommand": "mkdir -p /home/gaia/.cache && sudo chown -R gaia:gaia /home/gaia/.cache /home/gaia/.claude; if [ ! -f ~/.local/bin/uv ]; then curl -LsSf ht`
  - [PLC-lang/rusty/.devcontainer/devcontainer.json](https://github.com/PLC-lang/rusty/blob/9413775181e45607fc0f545dfbb07b4f5bd23c41/.devcontainer/devcontainer.json) — CONFIRMED
    - `L27: "postCreateCommand": "command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash",`
  - [pypose/bae/.devcontainer/devcontainer.json](https://github.com/pypose/bae/blob/b881f90802407f14a02c1b16c66617f8eefe7a43/.devcontainer/devcontainer.json) — CONFIRMED
    - `L19: "postCreateCommand": "curl -fsSL https://chatgpt.com/codex/install.sh | sh && curl -fsSL https://claude.ai/install.sh | bash && pip install nvidia-cudss-cu12==0`
  - [mendixlabs/mxcli/.devcontainer/devcontainer.json](https://github.com/mendixlabs/mxcli/blob/e1ef0c9e34bc35e31870e643540314063dcc7f24/.devcontainer/devcontainer.json) — CONFIRMED
    - `L34: "postCreateCommand": "curl -fsSL https://claude.ai/install.sh | bash && go mod download",`
  - [mendixlabs/mxcli/.devcontainer/podman/devcontainer.json](https://github.com/mendixlabs/mxcli/blob/e1ef0c9e34bc35e31870e643540314063dcc7f24/.devcontainer/podman/devcontainer.json) — CONFIRMED
    - `L37: "postCreateCommand": "curl -fsSL https://claude.ai/install.sh | bash && go mod download",`
  - [Sendspin/aiosendspin/.devcontainer/devcontainer.json](https://github.com/Sendspin/aiosendspin/blob/83209af414e1950dbbd0ebf60a9c0567b2c5f0c8/.devcontainer/devcontainer.json) — CONFIRMED
    - `L18: "postCreateCommand": "git config --global --add safe.directory ${containerWorkspaceFolder} && ./scripts/setup.sh && curl -fsSL https://claude.ai/install.sh | ba`
  - [jenkinsci/explain-error-plugin/.devcontainer/devcontainer.json](https://github.com/jenkinsci/explain-error-plugin/blob/4323971c7900d49874fb0064caed721dc5c047ef/.devcontainer/devcontainer.json) — CONFIRMED
    - `L24: "postCreateCommand": "bash -c 'curl -fsSL https://gh.io/copilot-install | bash && curl -fsSL https://claude.ai/install.sh | bash && mvn clean verify -DskipTests`
  - [ironsheep/P2-HUB75-LED-Matrix-Driver/.devcontainer/devcontainer.json](https://github.com/ironsheep/P2-HUB75-LED-Matrix-Driver/blob/84a1236d9ae676ebf732d7299524fca21c8651fe/.devcontainer/devcontainer.json) — CONFIRMED
    - `L26: "postCreateCommand": "sudo mkdir -p /Users/stephen && sudo ln -sfn /opt/container-tools /Users/stephen/container-tools; sudo chown -R vscode:vscode /home/vscode`
  - [byt3bl33d3r/figaro/.devcontainer/devcontainer.json](https://github.com/byt3bl33d3r/figaro/blob/591e17392ded6d5fdae86bc4f293feacbb066e55/.devcontainer/devcontainer.json) — CONFIRMED
    - `L49: "postCreateCommand": "mkdir -p ~/.claude && cp /tmp/.host-credentials.json ~/.claude/.credentials.json && cp /tmp/.host-claude.json ~/.claude.json && curl -fsSL`

### claude native installer in chezmoi scripts

- query: `"claude.ai/install.sh" path:.chezmoiscripts`
- rc: 0
- total_count: 49 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [claytron/dotfiles/.chezmoiscripts/run_after_claude_install.sh](https://github.com/claytron/dotfiles/blob/5d067c73b9260076242a088c2e81cf211d61bbd6/.chezmoiscripts/run_after_claude_install.sh) — CONFIRMED
    - `L2: curl -fsSL https://claude.ai/install.sh | bash`
  - [liby/dotfiles/.chezmoiscripts/run_once_after_install-agent-clis.sh](https://github.com/liby/dotfiles/blob/2edfc619826543778d266442fcd44a8204900ac6/.chezmoiscripts/run_once_after_install-agent-clis.sh) — CONFIRMED
    - `L11: curl -fsSL https://claude.ai/install.sh | bash`
  - [mimikun/dotfiles/.chezmoiscripts/linux/run_onchange_after-install-claude-code.sh.tmpl](https://github.com/mimikun/dotfiles/blob/48ca197d488e46e45c4b6c86bb571759515c5100/.chezmoiscripts/linux/run_onchange_after-install-claude-code.sh.tmpl) — CONFIRMED
    - `L5: base_url="https://claude.ai/install.sh"`
  - [kevinold/dotfiles/.chezmoiscripts/run_once_03-install-tools.sh](https://github.com/kevinold/dotfiles/blob/1c8178632fbec178d950d8857b03e4c3516655fa/.chezmoiscripts/run_once_03-install-tools.sh) — CONFIRMED
    - `L15: curl -fsSL https://claude.ai/install.sh | bash`
  - [azlekov/dotfiles/.chezmoiscripts/run_once_after_02-install-claude-code.sh.tmpl](https://github.com/azlekov/dotfiles/blob/9b9ac85659bb7edcb3883d3906172401682906a4/.chezmoiscripts/run_once_after_02-install-claude-code.sh.tmpl) — CONFIRMED
    - `L5: curl -fsSL https://claude.ai/install.sh | bash`
  - [cloudartisan/dotfiles/.chezmoiscripts/run_once_install-claude-code.sh.tmpl](https://github.com/cloudartisan/dotfiles/blob/829b78a79593ab26c094ca5be4d95cf1c4a5aa78/.chezmoiscripts/run_once_install-claude-code.sh.tmpl) — CONFIRMED
    - `L33: if curl -fsSL http://claude.ai/install.sh | bash; then`
  - [maxclax/dotfiles/.chezmoiscripts/darwin/run_onchange_after_11-ai-tools.sh.tmpl](https://github.com/maxclax/dotfiles/blob/6e7523fa070fb8fd8e3cc334009f57b7a7a9c4ba/.chezmoiscripts/darwin/run_onchange_after_11-ai-tools.sh.tmpl) — CONFIRMED
    - `L17: curl -fsSL https://claude.ai/install.sh | sh`
  - [edge2992/dotfiles/.chezmoiscripts/run_once_install-claude.sh.tmpl](https://github.com/edge2992/dotfiles/blob/d2bbd25b2c0d165adec39a3de7026e636fd6a6d4/.chezmoiscripts/run_once_install-claude.sh.tmpl) — CONFIRMED
    - `L13: curl -fsSL https://claude.ai/install.sh | bash`
  - [ahal/chezmoi/.chezmoiscripts/run_once_05-claude.sh.tmpl](https://github.com/ahal/chezmoi/blob/14d2e022b0110f715b169577f1c65b69653bb49c/.chezmoiscripts/run_once_05-claude.sh.tmpl) — CONFIRMED
    - `L6: curl -fsSL https://claude.ai/install.sh | bash`
  - [ppcamp/dotfiles/.chezmoiscripts/run_once_ai.tmpl](https://github.com/ppcamp/dotfiles/blob/b309d991d66fc6946c000624c9daa5ab028cef4c/.chezmoiscripts/run_once_ai.tmpl) — CONFIRMED
    - `L16: curl -fsSL https://claude.ai/install.sh | bash &>/dev/null`

### claude native installer in dotfiles (any)

- query: `"claude.ai/install.sh" dotfiles`
- rc: 0
- total_count: 1900 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [coffebar/dotfiles/dotfiles-restore.sh](https://github.com/coffebar/dotfiles/blob/36442fe0e39ed853a5ff35fafce76596526b493d/dotfiles-restore.sh) — CONFIRMED
    - `L151: curl -fsSL https://claude.ai/install.sh | bash`
  - [cengebretson/dotfiles/.config/setup.sh](https://github.com/cengebretson/dotfiles/blob/b48b3f0f7ed97b9118f3ad015e9549376f36be56/.config/setup.sh) — CONFIRMED
    - `L88: curl -fsSL https://claude.ai/install.sh | bash`
  - [treuille/dotfiles/setup/setup_dotfiles.py](https://github.com/treuille/dotfiles/blob/511a1e1165c03e9751523ccfe35ea53e7894c20d/setup/setup_dotfiles.py) — CONFIRMED
    - `L220: "curl -fsSL https://claude.ai/install.sh | bash",`
  - [freekmurze/dotfiles/bin/install-claude-code](https://github.com/freekmurze/dotfiles/blob/50345d32c2671662b1c74cc0873e9d4e0dc5ba02/bin/install-claude-code) — CONFIRMED
    - `L36: curl -fsSL https://claude.ai/install.sh | bash || warn "Claude Code installation failed"`
  - [wincent/wincent/aspects/vm/index.ts](https://github.com/wincent/wincent/blob/8b169efa526a76e28e4ebe9f8a84a88c65c88ca0/aspects/vm/index.ts) — CONFIRMED
    - `L103: url: 'https://claude.ai/install.sh',`
  - [A7med7x7/dotfiles/DOTFILES_BUILD.md](https://github.com/A7med7x7/dotfiles/blob/ba27fcb9b2f8e7839988ca19b78597669cc3ed35/DOTFILES_BUILD.md) — CONFIRMED
    - `L310: curl -fsSL https://claude.ai/install.sh | bash`
  - [Olical/dotfiles/README.md](https://github.com/Olical/dotfiles/blob/f81435dceb6434e87f528fa1ec55431816f8bf9a/README.md) — CONFIRMED
    - `L82: curl -fsSL https://claude.ai/install.sh | bash`
  - [RowanMcDonald/dotfiles/.bin/setup_dotfiles](https://github.com/RowanMcDonald/dotfiles/blob/a1fac1e1ad5b76b532161ffa77615dcf945591b7/.bin/setup_dotfiles) — CONFIRMED
    - `L93: curl -fsSL https://claude.ai/install.sh | bash`
  - [feldera/feldera/.devcontainer/Dockerfile](https://github.com/feldera/feldera/blob/6ad7a1868227cd1777172a9ad73b9ab4b22d8ee7/.devcontainer/Dockerfile) — CONFIRMED
    - `L103: RUN curl -fsSL https://claude.ai/install.sh | bash`
  - [memorysaver/dotfiles/docs/plans/2026-03-19-dotfiles-redesign-implementation.md](https://github.com/memorysaver/dotfiles/blob/70b3a198b7e0d0ee03e9831a7eb7a53a60bb2e58/docs/plans/2026-03-19-dotfiles-redesign-implementation.md) — CONFIRMED
    - `L474: curl -fsSL https://claude.ai/install.sh | bash`
    - `L774: curl -fsSL https://claude.ai/install.sh | bash || { echo "Claude Code failed"; failed=$((failed+1)); }`

### claude-code npm pin in mise.toml

- query: `"npm:@anthropic-ai/claude-code" filename:mise.toml`
- rc: 0
- total_count: 105 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [PSU3D0/formualizer/mise.toml](https://github.com/PSU3D0/formualizer/blob/7ec3b5f14e846c46e46e0586e8f506dcc4456959/mise.toml) — CONFIRMED
    - `L6: "npm:@anthropic-ai/claude-code" = "latest"`
  - [bdmorin/eyelet/.mise.toml.2](https://github.com/bdmorin/eyelet/blob/25ab72effffc243ef89515478e2e2ef6e10c27bc/.mise.toml.2) — CONFIRMED
    - `L16: "npm:@anthropic-ai/claude-code" = "latest"`
    - `L82: run = "bunx @anthropic-ai/claude-code --dangerously-skip-permissions"`
  - [lucaconlaq/drizzle-zod-to-code/mise.toml](https://github.com/lucaconlaq/drizzle-zod-to-code/blob/80c5d6d34eca5611f5785e9d5c29206c9eeb7517/mise.toml) — CONFIRMED
    - `L9: claude = "npm:@anthropic-ai/claude-code"`
  - [vinnie357/claude-skills/plugins/tools/agent-sandboxing/templates/mise.toml.claude-code](https://github.com/vinnie357/claude-skills/blob/4e974d538df003ec2edca4380fcc7de580141312/plugins/tools/agent-sandboxing/templates/mise.toml.claude-code) — CONFIRMED
    - `L4: # 'npm:@anthropic-ai/claude-code' backend prefix). The registry maps the short`
  - [Shakeskeyboarde/vite-live-preview/mise.toml](https://github.com/Shakeskeyboarde/vite-live-preview/blob/d54b5cec13e23f74cbd785c5d893f8b6162c7199/mise.toml) — CONFIRMED
    - `L5: 'npm:@anthropic-ai/claude-code' = "latest"`
  - [codemountains/mountix/mise.toml](https://github.com/codemountains/mountix/blob/1325247de2465c10b5b01f71496dc26c96b2b240/mise.toml) — CONFIRMED
    - `L4: "npm:@anthropic-ai/claude-code" = "latest"`
  - [getMoreBrain/bitmark-playground/.mise.toml](https://github.com/getMoreBrain/bitmark-playground/blob/ecf601b7ccafcf681fc7b2dda69d5dba1d6d293d/.mise.toml) — CONFIRMED
    - `L8: "npm:@anthropic-ai/claude-code" = { version = "latest", npm_args = "--ignore-scripts=false" }`
  - [The-Focus-AI/claude-marketplace/mise.toml](https://github.com/The-Focus-AI/claude-marketplace/blob/054a9a6dbe8e5b6a918807d53413c2e6596ccd62/mise.toml) — CONFIRMED
    - `L3: "npm:@anthropic-ai/claude-code" = "latest"`
  - [getMoreBrain/bitmark-parser-generator/.mise.toml](https://github.com/getMoreBrain/bitmark-parser-generator/blob/32bff5239820b0171b3f5c52f7a0ffc99384449a/.mise.toml) — CONFIRMED
    - `L4: "npm:@anthropic-ai/claude-code" = { version = "latest", npm_args = "--ignore-scripts=false" }`
  - [Kotaro7750/dotfiles/chezmoi/mise.toml.tmpl](https://github.com/Kotaro7750/dotfiles/blob/44d73718c076bc0c00278cfbf56669520c381d0a/chezmoi/mise.toml.tmpl) — CONFIRMED
    - `L18: "npm:@anthropic-ai/claude-code" = { version = "latest", allow_builds = true }`

### claude-code npm in Dockerfile

- query: `"@anthropic-ai/claude-code" filename:Dockerfile`
- rc: 0
- total_count: 9792 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [GreenSheep01201/claw-empire/Dockerfile](https://github.com/GreenSheep01201/claw-empire/blob/66a24ea7df2435ef897c48c147deb7ec572c01c2/Dockerfile) — CONFIRMED
    - `L16: @anthropic-ai/claude-code \`
  - [quoroom-ai/room/Dockerfile](https://github.com/quoroom-ai/room/blob/678d309247f500a92b2c8fab312adfeb8189f23f/Dockerfile) — CONFIRMED
    - `L12: RUN npm install -g @openai/codex @anthropic-ai/claude-code`
  - [opslane/opslane_old/Dockerfile](https://github.com/opslane/opslane_old/blob/ea95765c82113445cb64c4475de15ab8233afc0d/Dockerfile) — CONFIRMED
    - `L29: RUN npm install -g @anthropic-ai/claude-code@2.0.19`
  - [xvirobotics/metabot/Dockerfile](https://github.com/xvirobotics/metabot/blob/916637eccb68fd79a0850a02dff390580cedce4a/Dockerfile) — CONFIRMED
    - `L33: RUN npm install -g @anthropic-ai/claude-code`
  - [jonesphillip/weft/Dockerfile](https://github.com/jonesphillip/weft/blob/93efd90d3c68a1a2906e9f09184a6adb651c5ab8/Dockerfile) — CONFIRMED
    - `L4: RUN npm install -g @anthropic-ai/claude-code`
  - [LF-Decentralized-Trust-labs/gitmesh/Dockerfile](https://github.com/LF-Decentralized-Trust-labs/gitmesh/blob/4e57c58bcb8e7ae083721ba8f4e4969c90a0072b/Dockerfile) — CONFIRMED
    - `L38: RUN npm install --global --omit=dev @anthropic-ai/claude-code@latest @openai/codex@latest opencode-ai`
  - [Utopai-Research/pai-code/Dockerfile](https://github.com/Utopai-Research/pai-code/blob/825bca2f9cc41904c2955897599c7dd5eaf4847e/Dockerfile) — CONFIRMED
    - `L128: (npm install -g "@anthropic-ai/claude-code@${CLAUDE_VERSION}" --no-audit --no-fund && \`
  - [Lin-jun-xiang/agent-line-bot/Dockerfile](https://github.com/Lin-jun-xiang/agent-line-bot/blob/ad442447a941968e9c8ee4c979178a9809f524c6/Dockerfile) — CONFIRMED
    - `L15: && npm install -g @anthropic-ai/claude-code \`
  - [ninehills/PatentWriterAgent/Dockerfile](https://github.com/ninehills/PatentWriterAgent/blob/8d741be7c13271f5f0bac5fc78823d4fb3087935/Dockerfile) — CONFIRMED
    - `L88: RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}`
  - [VishalJ99/claude-docker/Dockerfile](https://github.com/VishalJ99/claude-docker/blob/2d59004220f554f30c8520187fc9697745e786c9/Dockerfile) — CONFIRMED
    - `L52: npm install -g @anthropic-ai/claude-code@$CC_VERSION; \`
    - `L55: npm install -g @anthropic-ai/claude-code; \`

### claude-code devcontainer feature

- query: `"ghcr.io/anthropics/devcontainer-features/claude-code" filename:devcontainer.json`
- rc: 0
- total_count: 1150 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [elastic/kibana/.ona/devcontainer.json](https://github.com/elastic/kibana/blob/5b99fc1e4ee312d88eb573e41ce51979286223b0/.ona/devcontainer.json) — CONFIRMED
    - `L51: "ghcr.io/anthropics/devcontainer-features/claude-code:1": {}`
  - [hacs/integration/.devcontainer.json](https://github.com/hacs/integration/blob/adb7d83e33d24325535fb43b8226572405143757/.devcontainer.json) — CONFIRMED
    - `L59: "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {},`
  - [oxc-project/oxc/.devcontainer/devcontainer.json](https://github.com/oxc-project/oxc/blob/7c61ebe1beec424f5b257e2899d47b9bcbfa9ed9/.devcontainer/devcontainer.json) — CONFIRMED
    - `L14: "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}`
  - [zammad/zammad/.devcontainer/with-ldap/devcontainer.json](https://github.com/zammad/zammad/blob/480ca9d4feba9b67142254e6eaafc5fc79545881/.devcontainer/with-ldap/devcontainer.json) — CONFIRMED
    - `L22: "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {},`
  - [zammad/zammad/.devcontainer/with-ollama/devcontainer.json](https://github.com/zammad/zammad/blob/480ca9d4feba9b67142254e6eaafc5fc79545881/.devcontainer/with-ollama/devcontainer.json) — CONFIRMED
    - `L22: "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {},`
  - [github/gh-aw/.devcontainer/devcontainer.json](https://github.com/github/gh-aw/blob/856e7fa3ca4f1597f9adbd519eec415ce92320e2/.devcontainer/devcontainer.json) — CONFIRMED
    - `L42: "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {},`
  - [zammad/zammad/.devcontainer/with-selenium/devcontainer.json](https://github.com/zammad/zammad/blob/480ca9d4feba9b67142254e6eaafc5fc79545881/.devcontainer/with-selenium/devcontainer.json) — CONFIRMED
    - `L22: "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {},`
  - [zammad/zammad/.devcontainer/with-mailserver/devcontainer.json](https://github.com/zammad/zammad/blob/480ca9d4feba9b67142254e6eaafc5fc79545881/.devcontainer/with-mailserver/devcontainer.json) — CONFIRMED
    - `L22: "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {},`
  - [postaljs/postal.js/.devcontainer/devcontainer.json](https://github.com/postaljs/postal.js/blob/664738f347e95c4f09dbb4a27c14df1510cf196a/.devcontainer/devcontainer.json) — CONFIRMED
    - `L57: "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}`
  - [tambo-ai/tambo/.devcontainer/devcontainer.json](https://github.com/tambo-ai/tambo/blob/0c84ae09499bc9e18fd0bd49f6abe53b526026f3/.devcontainer/devcontainer.json) — CONFIRMED
    - `L94: "ghcr.io/anthropics/devcontainer-features/claude-code:1": {}`

### codex npm pin in mise.toml

- query: `"npm:@openai/codex" filename:mise.toml`
- rc: 0
- total_count: 82 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [PSU3D0/formualizer/mise.toml](https://github.com/PSU3D0/formualizer/blob/7ec3b5f14e846c46e46e0586e8f506dcc4456959/mise.toml) — CONFIRMED
    - `L7: "npm:@openai/codex" = "latest"`
  - [matchai/dotfiles/home/mise.toml](https://github.com/matchai/dotfiles/blob/c7a8618803e9015fc5b763a205d3b6e6ec684dd0/home/mise.toml) — CONFIRMED
    - `L20: "npm:@openai/codex" = "latest"`
  - [yuki-yano/dotfiles/mise.toml](https://github.com/yuki-yano/dotfiles/blob/e6c9868b09958b3947c15afc0c6edc50dfc5af2d/mise.toml) — CONFIRMED
    - `L2: "npm:@openai/codex" = "latest"`
  - [golemfactory/ya-runtime-wasi/mise.toml](https://github.com/golemfactory/ya-runtime-wasi/blob/511b1c00a868426d3f031edcec36946677e764cf/mise.toml) — CONFIRMED
    - `L10: "npm:@openai/codex-security" = "latest"`
  - [akua-dev/agentos/mise.toml](https://github.com/akua-dev/agentos/blob/a30d855b06853c98477c6121238e4202e3b0b26a/mise.toml) — CONFIRMED
    - `L14: "npm:@openai/codex" = "0.144.5"`
  - [kulesh/dotfiles/dev/dev/.mise.toml](https://github.com/kulesh/dotfiles/blob/b2695f7fff9445953f12e5f7fbe2514c1e6d6c8b/dev/dev/.mise.toml) — CONFIRMED
    - `L10: "npm:@openai/codex" = "latest"`
  - [Kotaro7750/dotfiles/chezmoi/mise.toml.tmpl](https://github.com/Kotaro7750/dotfiles/blob/44d73718c076bc0c00278cfbf56669520c381d0a/chezmoi/mise.toml.tmpl) — CONFIRMED
    - `L17: "npm:@openai/codex" = "latest"`
  - [kossnocorp/alwaysly/mise.toml](https://github.com/kossnocorp/alwaysly/blob/badd0289d6139f77d69779b69b11ec1c29e657ec/mise.toml) — CONFIRMED
    - `L6: "npm:@openai/codex" = "latest"`
  - [KenosInc/dwf-mcp-server/.mise.toml](https://github.com/KenosInc/dwf-mcp-server/blob/4724e4621050da17958299c421a89b7f26ff071a/.mise.toml) — CONFIRMED
    - `L2: "npm:@openai/codex" = "0.130.0"`
  - [harshalbhatia/dotfiles/mise.toml](https://github.com/harshalbhatia/dotfiles/blob/1d58a9693de29a8090ba7bb3322a4b755f303f0d/mise.toml) — CONFIRMED
    - `L6: "npm:@openai/codex" = "latest"`

### codex github backend in mise.toml

- query: `"github:openai/codex" filename:mise.toml`
- rc: 0
- total_count: 1 (incomplete_results=False); re-fetched first 1 (per_page=10)
  - [FaintGhost/dotfiles/dot_config/mise/mise.toml.tmpl](https://github.com/FaintGhost/dotfiles/blob/55e680a954e5c0bea8558284553725121e310d04/dot_config/mise/mise.toml.tmpl) — CONFIRMED
    - `L22: [tools."github:openai/codex"]`

### codex npm in Dockerfile

- query: `"@openai/codex" filename:Dockerfile`
- rc: 0
- total_count: 6984 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [bugbasesecurity/pentest-copilot/backend/Dockerfile](https://github.com/bugbasesecurity/pentest-copilot/blob/cd512edd037a32ddb1df3caf2672915bd555daec/backend/Dockerfile) — CONFIRMED
    - `L27: RUN npm install --global "@openai/codex@${CODEX_CLI_VERSION}" \`
  - [GreenSheep01201/claw-empire/Dockerfile](https://github.com/GreenSheep01201/claw-empire/blob/66a24ea7df2435ef897c48c147deb7ec572c01c2/Dockerfile) — CONFIRMED
    - `L17: @openai/codex \`
  - [quoroom-ai/room/Dockerfile](https://github.com/quoroom-ai/room/blob/678d309247f500a92b2c8fab312adfeb8189f23f/Dockerfile) — CONFIRMED
    - `L12: RUN npm install -g @openai/codex @anthropic-ai/claude-code`
  - [heymrun/heym/backend/Dockerfile](https://github.com/heymrun/heym/blob/22c04ba08ff379de43ffb0eed0abcab1ced3abb6/backend/Dockerfile) — CONFIRMED
    - `L53: RUN npm install -g @openai/codex@${HEYM_CODEX_CLI_VERSION}`
  - [strongdm/leash/Dockerfile.coder](https://github.com/strongdm/leash/blob/fd8e0c1deb978d1871e080cd09a7f9e9c394c406/Dockerfile.coder) — CONFIRMED
    - `L26: @openai/codex \`
  - [johannesjo/parallel-code/docker/Dockerfile](https://github.com/johannesjo/parallel-code/blob/8c09c4c7a76f3265492e342b57df3847737b1cce/docker/Dockerfile) — CONFIRMED
    - `L53: RUN npm install -g @anthropic-ai/claude-code @openai/codex @google/gemini-cli opencode-ai`
  - [LF-Decentralized-Trust-labs/gitmesh/Dockerfile](https://github.com/LF-Decentralized-Trust-labs/gitmesh/blob/4e57c58bcb8e7ae083721ba8f4e4969c90a0072b/Dockerfile) — CONFIRMED
    - `L38: RUN npm install --global --omit=dev @anthropic-ai/claude-code@latest @openai/codex@latest opencode-ai`
  - [Utopai-Research/pai-code/Dockerfile](https://github.com/Utopai-Research/pai-code/blob/825bca2f9cc41904c2955897599c7dd5eaf4847e/Dockerfile) — CONFIRMED
    - `L139: (npm install -g "@openai/codex@${CODEX_VERSION}" --no-audit --no-fund && \`
  - [nikvdp/cco/Dockerfile](https://github.com/nikvdp/cco/blob/658e99ce3ef90963b0a7d4443af16f4de983ea2c/Dockerfile) — CONFIRMED
    - `L124: @openai/codex@latest \`
  - [PacificStudio/openase/Dockerfile](https://github.com/PacificStudio/openase/blob/e530faf137e764337d5beaaf68af3be159eb17aa/Dockerfile) — CONFIRMED
    - `L36: "@openai/codex@${CODEX_VERSION}" \`

### codex npm in devcontainer.json

- query: `"@openai/codex" filename:devcontainer.json`
- rc: 0
- total_count: 185 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [cre185/InstantSfM/.devcontainer/devcontainer.json](https://github.com/cre185/InstantSfM/blob/d3e599e1a42b4c5a806a84d9f383e1005d25f61b/.devcontainer/devcontainer.json) — CONFIRMED
    - `L21: "postCreateCommand": ". ${NVM_DIR}/nvm.sh && nvm install --lts && npm install -g @openai/codex oh-my-codex @anthropic-ai/claude-code opencode-ai && pip install `
  - [wechaty/docusaurus/.devcontainer/devcontainer.json](https://github.com/wechaty/docusaurus/blob/c4c8549eff7cf89be6b1ca3e3922ab789386d781/.devcontainer/devcontainer.json) — CONFIRMED
    - `L45: "npm:@openai/codex",`
  - [nizos/probity/.devcontainer/devcontainer.json](https://github.com/nizos/probity/blob/fabb04968f259416645f91f3c62bc12147e714b5/.devcontainer/devcontainer.json) — CONFIRMED
    - `L18: "postCreateCommand": "npm install -g @anthropic-ai/claude-code@latest @openai/codex@latest @github/copilot@latest @google/gemini-cli@latest"`
  - [obra/packnplay/.devcontainer/devcontainer.json](https://github.com/obra/packnplay/blob/a6e978ea71fcb67b5c2104161a542c050a4af95d/.devcontainer/devcontainer.json) — CONFIRMED
    - `L69: "npm install -g @openai/codex",`
  - [1c-neurofish/onec-client-mcp-devkit/.devcontainer/devcontainer.json](https://github.com/1c-neurofish/onec-client-mcp-devkit/blob/3f6a066913057c2d6f2d61c0b429fd0707ab271b/.devcontainer/devcontainer.json) — CONFIRMED
    - `L23: "postCreateCommand": "bash -lc 'mkdir -p /home/vscode/.codex /home/vscode/.npm-global && npm config set prefix /home/vscode/.npm-global && npm install -g --no-f`
  - [alkoleft/v8-runner-rust/.devcontainer/devcontainer.json](https://github.com/alkoleft/v8-runner-rust/blob/7ce1b062843d86644fe55741dbe0ee79f7ca767d/.devcontainer/devcontainer.json) — CONFIRMED
    - `L29: "postCreateCommand": "bash -lc 'sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkg-config libssl-dev && cargo install --locked ca`
  - [huan/mailbox/.devcontainer/devcontainer.json](https://github.com/huan/mailbox/blob/bedf1e1899a6cf7d1e7f56d2bd1c374fcdbe1981/.devcontainer/devcontainer.json) — CONFIRMED
    - `L45: "npm:@openai/codex",`
  - [MathieuDutSik/polyhedral_common/.devcontainer/devcontainer.json](https://github.com/MathieuDutSik/polyhedral_common/blob/2ba3f051c18dde2a5d3ea92f9d941d89f256ff78/.devcontainer/devcontainer.json) — CONFIRMED
    - `L93: "postCreateCommand": "npm install -g --silent @anthropic-ai/claude-code @openai/codex @modelcontextprotocol/server-sequential-thinking @modelcontextprotocol/ser`
  - [robince/parqview/.devcontainer/devcontainer.json](https://github.com/robince/parqview/blob/f92b087a64c6964ec6f3b7570607f1883b050785/.devcontainer/devcontainer.json) — CONFIRMED
    - `L35: "postCreateCommand": "go mod download && go install golang.org/x/tools/gopls@latest && go install github.com/go-delve/delve/cmd/dlv@latest && go install golang.`
  - [wechaty/redux/.devcontainer/devcontainer.json](https://github.com/wechaty/redux/blob/1c8be7441be4fd5c4914ad0eca8fe4d15480899e/.devcontainer/devcontainer.json) — CONFIRMED
    - `L45: "npm:@openai/codex",`

### codex release download in Dockerfile

- query: `"openai/codex/releases" filename:Dockerfile`
- rc: 0
- total_count: 205 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [raine/workmux/docker/Dockerfile.codex](https://github.com/raine/workmux/blob/e6500921408063d000ab1474fa34e6728533cbd2/docker/Dockerfile.codex) — CONFIRMED
    - `L19: curl -fsSL "https://github.com/openai/codex/releases/latest/download/codex-${ARCH}-unknown-linux-musl.tar.gz" | \`
  - [kagent-dev/kagent/go/harness/codex/Dockerfile](https://github.com/kagent-dev/kagent/blob/ccd68ccadb5241eb7e1382abf065661fec00d2ab/go/harness/codex/Dockerfile) — CONFIRMED
    - `L36: "https://github.com/openai/codex/releases/download/rust-v${CODEX_CLI_VERSION}/codex-package-${platform}.tar.gz" \`
  - [Accio-Lab/Dressage/docker/Dockerfile](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docker/Dockerfile) — CONFIRMED
    - `L52: RUN curl -fsSL "https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/install.sh" | \`
  - [openai/frontier-evals/project/evmbench/evmbench/Dockerfile](https://github.com/openai/frontier-evals/blob/51052cede8cc608f95bb00346635e03759013e5a/project/evmbench/evmbench/Dockerfile) — CONFIRMED
    - `L48: ENV CODEX_URL=https://github.com/openai/codex/releases/download/${CODEX_VERSION}/codex-${ARCH}-unknown-linux-gnu.tar.gz`
  - [ai/env/devcontainer/Dockerfile](https://github.com/ai/env/blob/03223aa19a94b5d4d48b7412823e5b9ad9aff59c/devcontainer/Dockerfile) — CONFIRMED
    - `L39: ADD https://github.com/openai/codex/releases/latest/download/codex-x86_64-unknown-linux-musl.tar.gz /codex.tar.gz`
    - `L40: ADD https://github.com/openai/codex/releases/latest/download/codex-code-mode-host-x86_64-unknown-linux-musl.tar.gz /codex-code-mode-host.tar.gz`
  - [zitongbai/legged_lab/docker/Dockerfile](https://github.com/zitongbai/legged_lab/blob/69b7f73d912a9d5695a60b5bed41d0785c8b302e/docker/Dockerfile) — CONFIRMED
    - `L23: codex_install_url=https://github.com/openai/codex/releases/latest/download/install.sh; \`
  - [mattolson/agent-sandbox/images/agents/codex/Dockerfile](https://github.com/mattolson/agent-sandbox/blob/c5b65e7cbd8f5b3bbf4e3ea40900c0014eedfa04/images/agents/codex/Dockerfile) — CONFIRMED
    - `L54: BASE_URL="https://github.com/openai/codex/releases/latest/download"; \`
    - `L56: BASE_URL="https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}"; \`
  - [dyoshikawa/rulesync/.devcontainer/Dockerfile](https://github.com/dyoshikawa/rulesync/blob/b222afe08de132f43907b9580be6e0e2a02bd951/.devcontainer/Dockerfile) — CONFIRMED
    - `L134: RUN curl -fsSL "https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/install.sh" -o /tmp/codex-install.sh && \`
  - [stacklok/brood-box/images/codex/Dockerfile](https://github.com/stacklok/brood-box/blob/6f7c156416025018674dbbd1d568b471268b9fc0/images/codex/Dockerfile) — CONFIRMED
    - `L13: "https://github.com/openai/codex/releases/latest/download/codex-${ARCH}-unknown-linux-musl.tar.gz" && \`
  - [sortie-ai/sortie/examples/docker/codex.Dockerfile](https://github.com/sortie-ai/sortie/blob/9763d87be1470758827721e0b659ff4d402b693c/examples/docker/codex.Dockerfile) — CONFIRMED
    - `L37: curl -fsSL "https://github.com/openai/codex/releases/latest/download/codex-${codex_arch}.tar.gz" \`

### antigravity-cli in mise.toml

- query: `"antigravity-cli" filename:mise.toml`
- rc: 0
- total_count: 15 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [binaryn3xus/HomeOps/.mise.toml](https://github.com/binaryn3xus/HomeOps/blob/3948efa291ef0419c052f404cbb9d86336bf35ae/.mise.toml) — CONFIRMED
    - `L32: antigravity-cli = "1.2.14"`
  - [dceoy/docker-ai-coder/mise.toml](https://github.com/dceoy/docker-ai-coder/blob/1d95f1f2f15f43439a9d2f19ab6fb3e21bbd53b8/mise.toml) — CONFIRMED
    - `L18: "github:google-antigravity/antigravity-cli" = { version = "latest", matching = "agy_cli", rename_exe = { antigravity = "agy" } }`
  - [zawa-kyo/dotfiles/mise.toml](https://github.com/zawa-kyo/dotfiles/blob/c040219946aa1f4112ec3ca17cc4d360e562345f/mise.toml) — CONFIRMED
    - `L11: antigravity-cli = "latest"`
  - [jamierumbelow/agentfiles/workspace/mise.toml](https://github.com/jamierumbelow/agentfiles/blob/cf44cae8eb7831ed6e6115b4bb3c8061cbbdfcdb/workspace/mise.toml) — CONFIRMED
    - `L23: # https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/<platform>.json`
    - `L32: macos-arm64 = { url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.1.19-4894004681244672/darwin-arm/cli_mac_arm64.tar.gz", checksum = "s`
    - `L33: macos-x64 = { url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.1.19-4894004681244672/darwin-x64/cli_mac_x64.tar.gz", checksum = "sha51`
    - `L34: linux-x64 = { url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.1.19-4894004681244672/linux-x64/cli_linux_x64.tar.gz", checksum = "sha5`
  - [damiansan239/onedead/mise.toml](https://github.com/damiansan239/onedead/blob/dca02fcde669b3c0bf178d77da91c10e377bb2e1/mise.toml) — CONFIRMED
    - `L8: url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/{version}/linux-x64/cli_linux_x64.tar.gz"`
  - [romainPrignon/neodotfiles/mise/mise.toml](https://github.com/romainPrignon/neodotfiles/blob/08be95bddf0e3b850eca36cd51a831f2c24bd79b/mise/mise.toml) — CONFIRMED
    - `L30: antigravity-cli = "latest"`
  - [anorneto/simple-machine-setup/configs/dotfiles/mise.toml](https://github.com/anorneto/simple-machine-setup/blob/47dd7dc9100e7c6c9112552e0b28270665494d22/configs/dotfiles/mise.toml) — CONFIRMED
    - `L43: antigravity-cli = "latest" # Google's terminal AI agent for code editing`
  - [cebrusfs/dotfiles/mise.toml](https://github.com/cebrusfs/dotfiles/blob/815ece5cf69653ae8ef064511284203f3f8b8fc1/mise.toml) — CONFIRMED
    - `L103: description = "Sync stable Antigravity CLI settings into ~/.gemini/antigravity-cli/settings.json"`
  - [Marketingtool-pro/AiMarketingtool-pro-fbaf2fad/mise.toml](https://github.com/Marketingtool-pro/AiMarketingtool-pro-fbaf2fad/blob/41022dd4dfabf8e275323634732aa66511368ece/mise.toml) — CONFIRMED
    - `L56: antigravity-cli = "latest"`
  - [hidekitux/skills/mise.toml](https://github.com/hidekitux/skills/blob/549cbd4637dbecf6765b5219a285d9964a48d71f/mise.toml) — CONFIRMED
    - `L11: "aqua:google-antigravity/antigravity-cli" = "1.1.19"`

### antigravity in Dockerfile

- query: `"antigravity" filename:Dockerfile`
- rc: 0
- total_count: 876 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [openabdev/openab/Dockerfile.antigravity](https://github.com/openabdev/openab/blob/739c344d3604840283abd3ea9021d5129524a17d/Dockerfile.antigravity) — CONFIRMED
    - `L33: # Install agy (Google Antigravity CLI) — pinned version`
    - `L43: curl -fsSL "https://github.com/google-antigravity/antigravity-cli/releases/download/${AGY_VERSION}/${ASSET}" \`
    - `L48: mv /usr/local/bin/antigravity /usr/local/bin/agy && \`
  - [GoogleCloudPlatform/scion/harnesses/antigravity/Dockerfile](https://github.com/GoogleCloudPlatform/scion/blob/73ebd022b1c60c54e42d9aea275e99f076e49c13/harnesses/antigravity/Dockerfile) — CONFIRMED
    - `L23: RUN mkdir -p /home/scion/.gemini/antigravity-cli \`
    - `L32: "https://github.com/google-antigravity/antigravity-cli/releases/download/${AGY_VERSION}/agy_cli_linux_${ARCH}.tar.gz" \`
    - `L33: && tar -xzf /tmp/cli.tar.gz -C /tmp antigravity \`
    - `L34: && mv /tmp/antigravity /usr/local/bin/agy \`
  - [google-gemini/gemini-cli/tools/caretaker-agent/cloudrun/pr-generator/Dockerfile](https://github.com/google-gemini/gemini-cli/blob/38700b4b38bf387dafded6c97c3f190d084b49e9/tools/caretaker-agent/cloudrun/pr-generator/Dockerfile) — CONFIRMED
    - `L1: # Dockerfile for Jetski/Antigravity Worker Job using the Python SDK`
    - `L3: # the code generation and evaluation in-process using google-antigravity and Firestore synchronization.`
  - [lbjlaq/Antigravity-Manager/docker/Dockerfile](https://github.com/lbjlaq/Antigravity-Manager/blob/45fc6d37db64689b50e42b38fd59a8d2dd627740/docker/Dockerfile) — CONFIRMED
    - `L86: cargo build --release --bin antigravity-tools && \`
    - `L87: cp target/release/antigravity-tools /tmp/antigravity-tools`
    - `L116: COPY --from=backend-builder /tmp/antigravity-tools /app/antigravity-tools`
    - `L134: ENTRYPOINT ["/app/antigravity-tools", "--headless"]`
  - [lbjlaq/Antigravity-Manager/docker/Dockerfile.backend](https://github.com/lbjlaq/Antigravity-Manager/blob/45fc6d37db64689b50e42b38fd59a8d2dd627740/docker/Dockerfile.backend) — CONFIRMED
    - `L2: ARG FRONTEND_IMAGE=antigravity-manager:latest`
    - `L59: cargo build --release --bin antigravity-tools && \`
    - `L60: cp target/release/antigravity-tools /tmp/antigravity-tools`
    - `L63: ARG FRONTEND_IMAGE=antigravity-manager:latest`
  - [lbjlaq/Antigravity-Manager/docker/Dockerfile.backend.localdist](https://github.com/lbjlaq/Antigravity-Manager/blob/45fc6d37db64689b50e42b38fd59a8d2dd627740/docker/Dockerfile.backend.localdist) — CONFIRMED
    - `L60: cargo build --release --bin antigravity-tools && \`
    - `L61: cp target/release/antigravity-tools /tmp/antigravity-tools`
    - `L90: COPY --from=backend-builder /tmp/antigravity-tools /app/antigravity-tools`
    - `L108: ENTRYPOINT ["/app/antigravity-tools", "--headless"]`
  - [linuxserver/proot-apps/apps/antigravity/Dockerfile](https://github.com/linuxserver/proot-apps/blob/4ee3ab4df63731a8e73a16072f61e6c96448dfea/apps/antigravity/Dockerfile) — CONFIRMED
    - `L43: "https://antigravity-ide-auto-updater-974169037036.us-central1.run.app/api/update/${ARCH}/stable/latest" \`
    - `L46: /tmp/antigravity.tar.gz -L \`
    - `L48: mkdir -p /tmp/antigravity && \`
    - `L50: /tmp/antigravity.tar.gz -C \`
  - [google/ax/Dockerfile.task-runner](https://github.com/google/ax/blob/ac2332829f22360ff97b0ba34d94dd0dd782f17e/Dockerfile.task-runner) — CONFIRMED
    - `L26: RUN pip install --no-cache-dir google-antigravity`
    - `L29: COPY cmd/ax-task-runner/antigravity_bootstrap.py /usr/local/bin/antigravity_bootstrap.py`
  - [Bitterbot-AI/bitterbot-desktop/Dockerfile](https://github.com/Bitterbot-AI/bitterbot-desktop/blob/b38a7f146271d95f9b5d348283e1abacd89467ef/Dockerfile) — CONFIRMED
    - `L30: COPY extensions/google-antigravity-auth/package.json ./extensions/google-antigravity-auth/`
  - [prettysmartdev/awman/templates/Dockerfile.antigravity](https://github.com/prettysmartdev/awman/blob/e86ddde0e0e9ef70fd4bdf774a6dcc42062e9635/templates/Dockerfile.antigravity) — CONFIRMED
    - `L31: https://antigravity.google/cli/install.sh | bash \`

### agy in mise.toml

- query: `"agy" filename:mise.toml`
- rc: 0
- total_count: 20 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [mkobit/chezmoi-skills/.mise.toml](https://github.com/mkobit/chezmoi-skills/blob/a846e16983dd9698c16b57b8c438e7e2d8ecab7a/.mise.toml) — CONFIRMED
    - `L14: run = "sbx env plan .sbx/sbxenv.yaml && sbx env plan .sbx/sbxenv.agy.yaml && sbx env plan .sbx/sbxenv.claude.yaml"`
  - [dceoy/docker-ai-coder/mise.toml](https://github.com/dceoy/docker-ai-coder/blob/1d95f1f2f15f43439a9d2f19ab6fb3e21bbd53b8/mise.toml) — CONFIRMED
    - `L18: "github:google-antigravity/antigravity-cli" = { version = "latest", matching = "agy_cli", rename_exe = { antigravity = "agy" } }`
  - [kaybenleroll/ai_assisted_research/mise.toml](https://github.com/kaybenleroll/ai_assisted_research/blob/b411da6f607d50e1cd4a0698c4c459ff8f2d7084/mise.toml) — CONFIRMED
    - `L2: agy = "latest"`
  - [simonepri/openplex/mise.toml](https://github.com/simonepri/openplex/blob/d4cd8b7abd6f572ea3ec108920d15ca30aa3147f/mise.toml) — CONFIRMED
    - `L28: agy = "1.2.13"`
    - `L104: description = "Review changes in the repository using an AI agent (claude, codex, agy)"`
  - [SlashNephy/surasura-roppou/.mise.toml](https://github.com/SlashNephy/surasura-roppou/blob/4a0a8c8023beb862e111271b5bf77591430664a4/.mise.toml) — CONFIRMED
    - `L2: agy = "1.2.8"`
  - [vamsiramakrishnan/pixelpitch-slidegen/mise.toml](https://github.com/vamsiramakrishnan/pixelpitch-slidegen/blob/e9f5475f257df7ee73ba7b16cf9c08e4e9377662/mise.toml) — CONFIRMED
    - `L52: uv sync --project agy-worker --frozen --no-install-project`
    - `L53: uv run python scripts/prepare_agy_skills.py`
    - `L54: uv run python scripts/prepare_agy_skills.py --check`
    - `L176: uv run python scripts/prepare_agy_skills.py`
  - [fmind/dot/mise.toml](https://github.com/fmind/dot/blob/3e8124a1a66cf843d8a0fbe3160eabfb98369fb7/mise.toml) — CONFIRMED
    - `L32: python_sources = "dot dot_config/ptpython/config.py skills/gws/scripts skills/agy/scripts skills/deleguate-tasks/scripts"`
    - `L167: "uv run --frozen --directory dot ty check src dot_tasks tests ../skills/gws/scripts ../skills/agy/scripts ../skills/deleguate-tasks/scripts",`
  - [jamierumbelow/agentfiles/workspace/mise.toml](https://github.com/jamierumbelow/agentfiles/blob/cf44cae8eb7831ed6e6115b4bb3c8061cbbdfcdb/workspace/mise.toml) — CONFIRMED
    - `L21: # Antigravity CLI ('agy'). No package-manager distribution — Google ships it via`
    - `L27: [tools."http:agy"]`
    - `L29: rename_exe = "agy"`
    - `L31: [tools."http:agy".platforms]`
  - [damiansan239/onedead/mise.toml](https://github.com/damiansan239/onedead/blob/dca02fcde669b3c0bf178d77da91c10e377bb2e1/mise.toml) — CONFIRMED
    - `L6: [tools."http:agy"]`
    - `L9: rename_exe = "agy"`
  - [Hashory/dotfiles/mise.toml](https://github.com/Hashory/dotfiles/blob/5a3e18634f3cf20e5b73b224d63bef375636afa7/mise.toml) — CONFIRMED
    - `L72: # agy を常に --dangerously-skip-permissions で起動する`
    - `L73: function agy {`
    - `L74: command agy --dangerously-skip-permissions "$@"`

### claude install cmd in postCreate

- query: `"claude.ai/install.sh" "postCreateCommand"`
- rc: 0
- total_count: 435 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [near/nearcore/.devcontainer/Dockerfile](https://github.com/near/nearcore/blob/bb04d86378ef66bbc0573771dad7d5fced25b2eb/.devcontainer/Dockerfile) — CONFIRMED
    - `L109: # Pytest venv (created here; packages installed by postCreateCommand)`
  - [ChilliCream/graphql-platform/.devcontainer/dockerfile](https://github.com/ChilliCream/graphql-platform/blob/a82bf33860e8bd8fce0c8ae640a2933da95b9797/.devcontainer/dockerfile) — CONFIRMED
    - `L50: # The browser binary itself is downloaded in postCreateCommand so it matches the`
  - [icloud-photos-downloader/icloud_photos_downloader/.devcontainer/python/devcontainer.json](https://github.com/icloud-photos-downloader/icloud_photos_downloader/blob/879c561240d993d748ddb4546f935090502b16d3/.devcontainer/python/devcontainer.json) — CONFIRMED
    - `L10: "postCreateCommand": "sudo apt-get update && sudo apt-get install -y locales-all && (curl -fsSL https://claude.ai/install.sh | bash)"`
    - `L18: // Use 'postCreateCommand' to run commands after the container is created.`
    - `L19: // "postCreateCommand": "pip3 install --user -r requirements.txt",`
  - [amd/gaia/.devcontainer/README.md](https://github.com/amd/gaia/blob/c5df3128f7f5eab4dd97723274d4dbb4b1c1347b/.devcontainer/README.md) — CONFIRMED
    - `L20: 3. Wait for 'postCreateCommand' to finish (pip install + initial setup)`
  - [tractorjuice/arc-kit/scripts/create-sdg-repo.py](https://github.com/tractorjuice/arc-kit/blob/98c113537217f0075109bc3fb669abbf93c8f91b/scripts/create-sdg-repo.py) — CONFIRMED
    - `L298: "postCreateCommand": "curl -fsSL https://claude.ai/install.sh | bash",`
  - [Konilo/retrospect/.devcontainer/postCreateCommand.sh](https://github.com/Konilo/retrospect/blob/4d2cbd48b6187f588bcee6a4c8649f65c8fa14c9/.devcontainer/postCreateCommand.sh) — CONFIRMED
    - `L6: echo 'Running postCreateCommand.sh'`
  - [Konilo/sandbox/.devcontainer/postCreateCommand.sh](https://github.com/Konilo/sandbox/blob/1756cb611f0005d563fb3915a0eef679a5788ec6/.devcontainer/postCreateCommand.sh) — CONFIRMED
    - `L6: echo 'Running postCreateCommand.sh'`
  - [Konilo/signals/.devcontainer/postCreateCommand.sh](https://github.com/Konilo/signals/blob/b759f1f2d0c1137857af01f83126c33660d87997/.devcontainer/postCreateCommand.sh) — CONFIRMED
    - `L6: echo 'Running postCreateCommand.sh'`
  - [amd/gaia/.devcontainer/devcontainer.json](https://github.com/amd/gaia/blob/c5df3128f7f5eab4dd97723274d4dbb4b1c1347b/.devcontainer/devcontainer.json) — CONFIRMED
    - `L89: "postCreateCommand": "pip install -e \".[dev,mcp,eval,rag]\" && cp /workspace/.devcontainer/.mcp.json /workspace/.mcp.json",`
    - `L91: "waitFor": "postCreateCommand"`
  - [PLC-lang/rusty/.devcontainer/devcontainer.json](https://github.com/PLC-lang/rusty/blob/9413775181e45607fc0f545dfbb07b4f5bd23c41/.devcontainer/devcontainer.json) — CONFIRMED
    - `L27: "postCreateCommand": "command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash",`

### claude update in mise.toml

- query: `"claude update" filename:mise.toml`
- rc: 0
- total_count: 2 (incomplete_results=False); re-fetched first 2 (per_page=10)
  - [bellini666/dotfiles/mise.toml](https://github.com/bellini666/dotfiles/blob/a8dfafaddf3350e8e80a8b1d267a7ec3ce419884/mise.toml) — CONFIRMED
    - `L53: claude update`
  - [halkn/dotfiles/mise.toml](https://github.com/halkn/dotfiles/blob/717c2378c42e6c6847184d6b7e88f76acc05be8a/mise.toml) — CONFIRMED
    - `L67: # Claude Code is in the mise registry, but 'claude update' (run by 'mise run update') replaces it`

## Round 2 (native-installer URLs discovered in round 1)

### R2 codex native installer in mise.toml

- query: `"chatgpt.com/codex/install.sh" filename:mise.toml`
- rc: 0
- total_count: 5 (incomplete_results=False); re-fetched first 5 (per_page=10)
  - [bellini666/dotfiles/mise.toml](https://github.com/bellini666/dotfiles/blob/a8dfafaddf3350e8e80a8b1d267a7ec3ce419884/mise.toml) — CONFIRMED
    - `L59: curl -fsSL https://chatgpt.com/codex/install.sh -o "$agent_install_dir/codex.sh"`
  - [hiramekun/dotfiles/mise.toml](https://github.com/hiramekun/dotfiles/blob/d6176679abeedbc71e2fac82474294f877ceda82/mise.toml) — CONFIRMED
    - `L107: "curl -fsSL https://chatgpt.com/codex/install.sh | sh",`
  - [simonrw/dotfiles/mise.toml](https://github.com/simonrw/dotfiles/blob/f12be3291d1d5c9c49393812ee091dc7af4a6240/mise.toml) — CONFIRMED
    - `L187: command -v codex >/dev/null || curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [dkimura/osx-setup/mise.toml](https://github.com/dkimura/osx-setup/blob/194febd9442c69bed054b6852631b2c01b06eaf2/mise.toml) — CONFIRMED
    - `L71: test -x ~/.local/bin/codex || curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [fuyutarow/dotfiles/mise.toml](https://github.com/fuyutarow/dotfiles/blob/16b5bec3b0621e207d956018c21f5e9e1e133b07/mise.toml) — CONFIRMED
    - `L501: description = "Install the AI coding-agent CLIs through each vendor's self-updating installer: Claude Code native (claude.ai/install.sh), Codex standalone (chat`
    - `L504: "curl -fsSL https://chatgpt.com/codex/install.sh | sh",`

### R2 codex native installer in Dockerfile

- query: `"chatgpt.com/codex/install.sh" filename:Dockerfile`
- rc: 0
- total_count: 206 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [tursodatabase/turso/.devcontainer/Dockerfile](https://github.com/tursodatabase/turso/blob/f399ab30a337896f32f917ef525c70b395797c3f/.devcontainer/Dockerfile) — CONFIRMED
    - `L169: RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [asterinas/asterinas/tools/dev_env/docker/Dockerfile](https://github.com/asterinas/asterinas/blob/a5238eb6a965a4616ce07a48f5dfbc8042c4cd44/tools/dev_env/docker/Dockerfile) — CONFIRMED
    - `L31: RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh \`
  - [annict/annict/Dockerfile.dev](https://github.com/annict/annict/blob/dc88faad976d54930a488bfa900dda067b0fa0b1/Dockerfile.dev) — CONFIRMED
    - `L225: RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [caarmen/poet-assistant/.docker/codex/Dockerfile](https://github.com/caarmen/poet-assistant/blob/15c0e9703cd89bef3dc42d57f4f8f4936a6764fb/.docker/codex/Dockerfile) — CONFIRMED
    - `L5: RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [aws/agentcore-cli/src/assets/python/http/bma/base/Dockerfile](https://github.com/aws/agentcore-cli/blob/e02995ea76e39cf0b3c6125289bb6f9905a1d48f/src/assets/python/http/bma/base/Dockerfile) — CONFIRMED
    - `L9: RUN curl -fsSL https://chatgpt.com/codex/install.sh -o /tmp/install-codex.sh \`
  - [rennf93/roboco/docker/agent-codex.Dockerfile](https://github.com/rennf93/roboco/blob/b7f65132e6e0651cbb9a8d9d58999cbf748f21a4/docker/agent-codex.Dockerfile) — CONFIRMED
    - `L24: # kimi). The npm route (not chatgpt.com/codex/install.sh, which the CDN denies`
  - [E3SM-Project/containers/ghci/dev/Dockerfile](https://github.com/E3SM-Project/containers/blob/fc822782926e29a5bc2ee93bb158ede2ea4867c9/ghci/dev/Dockerfile) — CONFIRMED
    - `L134: RUN set -o pipefail && curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [imbue-ai/catalyst/openhost/Dockerfile](https://github.com/imbue-ai/catalyst/blob/a2ee48c34741df5d4549d97b22aa44589d9eaa6a/openhost/Dockerfile) — CONFIRMED
    - `L47: && curl -fsSL https://chatgpt.com/codex/install.sh | sh \`
  - [docker/sbx-kits-contrib/codex/Dockerfile](https://github.com/docker/sbx-kits-contrib/blob/c7a99a0b4b61a666661714e859609087c3880624/codex/Dockerfile) — CONFIRMED
    - `L81: RUN CODEX_NON_INTERACTIVE=true sh -c "$(curl -fsSL https://chatgpt.com/codex/install.sh)" \`
  - [jgmontoya/shaka/dockerfile-codex](https://github.com/jgmontoya/shaka/blob/ac8760023b280d91217f3c6abd88aa944dd90598/dockerfile-codex) — CONFIRMED
    - `L29: https://chatgpt.com/codex/install.sh && \`

### R2 codex native installer in devcontainer.json

- query: `"chatgpt.com/codex/install.sh" filename:devcontainer.json`
- rc: 0
- total_count: 10 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [pypose/bae/.devcontainer/devcontainer.json](https://github.com/pypose/bae/blob/b881f90802407f14a02c1b16c66617f8eefe7a43/.devcontainer/devcontainer.json) — CONFIRMED
    - `L19: "postCreateCommand": "curl -fsSL https://chatgpt.com/codex/install.sh | sh && curl -fsSL https://claude.ai/install.sh | bash && pip install nvidia-cudss-cu12==0`
  - [BNLNPPS/simphony/.devcontainer/devcontainer.json](https://github.com/BNLNPPS/simphony/blob/2b74a7206d4969fe6ea7b019a06daebc7ac02969/.devcontainer/devcontainer.json) — CONFIRMED
    - `L22: "postCreateCommand": "curl -fsSL --output /tmp/codex-install.sh https://chatgpt.com/codex/install.sh && CODEX_NON_INTERACTIVE=1 sh /tmp/codex-install.sh; status`
  - [ryo8000/http-playground-server/.devcontainer/devcontainer.json](https://github.com/ryo8000/http-playground-server/blob/3337fe8c1aef2d54a0c5db5354b94d4a9a15ea15/.devcontainer/devcontainer.json) — CONFIRMED
    - `L21: "install-codex": "curl -fsSL https://chatgpt.com/codex/install.sh | sh",`
  - [marcingurbisz/idea-execution-framework/.devcontainer/devcontainer.json](https://github.com/marcingurbisz/idea-execution-framework/blob/cdd743eb836dbe7909851fc6e8b35f4eded31a64/.devcontainer/devcontainer.json) — CONFIRMED
    - `L33: "postCreateCommand": "sudo chown vscode:vscode /home/vscode/.cache/ms-playwright && curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh`
  - [enzo2/gray-oak-academy/.devcontainer/devcontainer.json](https://github.com/enzo2/gray-oak-academy/blob/18d4cb123ec8e866ff494585a6ae516f869ca41e/.devcontainer/devcontainer.json) — CONFIRMED
    - `L51: "codex": "curl -fsSL https://chatgpt.com/codex/install.sh | sh"`
  - [kabuto412rock/blog/.devcontainer/devcontainer.json](https://github.com/kabuto412rock/blog/blob/151d747b6930fb2fdb637f51c4fa6860b41a6aba/.devcontainer/devcontainer.json) — CONFIRMED
    - `L10: "sudo apt-get update && sudo apt-get install -y wget && wget -q https://github.com/gohugoio/hugo/releases/download/v0.151.0/hugo_extended_0.151.0_linux-amd64.de`
  - [evgobmm/schubert-lieder/.devcontainer/devcontainer.json](https://github.com/evgobmm/schubert-lieder/blob/2a55ec1938fa148205b738f8557d36c2ff1bc195/.devcontainer/devcontainer.json) — CONFIRMED
    - `L6: "postCreateCommand": "mkdir -p /home/vscode/.local/bin /home/vscode/.claude /home/vscode/.codex && curl -fsSL https://claude.ai/install.sh | bash && curl -fsSL `
  - [KevMendesDev/mercadinho-sao-francisco/.devcontainer/devcontainer.json](https://github.com/KevMendesDev/mercadinho-sao-francisco/blob/61be76dee4b271cb1886ae67f689c4d043bc61fb/.devcontainer/devcontainer.json) — CONFIRMED
    - `L34: "postCreateCommand": "curl -fsSL https://chatgpt.com/codex/install.sh | sh && sudo chown -R node:node /workspaces/mercadinho-sao-francisco/node_modules && npm c`
  - [sncollective/snc-platform/.devcontainer/devcontainer.json](https://github.com/sncollective/snc-platform/blob/004c866dd042df90e91485172616d0927fe737ea/.devcontainer/devcontainer.json) — CONFIRMED
    - `L21: "postCreateCommand": "sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg && npm install -g pm2 bun@1.3.12 && curl -fsSL https://chatgpt.com/codex/ins`
  - [hlxie22/OncoTwin-backup/.devcontainer/devcontainer.json](https://github.com/hlxie22/OncoTwin-backup/blob/9bc2168b9eaa3bca8508bd9cc0e6da4f4e694c3f/.devcontainer/devcontainer.json) — CONFIRMED
    - `L2: "postCreateCommand": "curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh"`

### R2 codex native installer in chezmoi scripts

- query: `"chatgpt.com/codex/install.sh" path:.chezmoiscripts`
- rc: 0
- total_count: 7 (incomplete_results=False); re-fetched first 7 (per_page=10)
  - [coreyjadams/dotfiles/.chezmoiscripts/run_after_04-install-codex.sh](https://github.com/coreyjadams/dotfiles/blob/58adcb63d41c81c0f50457db859411f29db12841/.chezmoiscripts/run_after_04-install-codex.sh) — CONFIRMED
    - `L10: curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=true sh`
  - [cellfusion/dotfiles/.chezmoiscripts/run_onchange_after_40-ai-clis.sh.tmpl](https://github.com/cellfusion/dotfiles/blob/c145775a3a749bf8878a14dddf78e4890704f340/.chezmoiscripts/run_onchange_after_40-ai-clis.sh.tmpl) — CONFIRMED
    - `L26: curl -fsSL https://chatgpt.com/codex/install.sh | sh || die 'codex の導入に失敗した'`
  - [peloeil/dotfiles/.chezmoiscripts/run_once_after_12_install_codex_standalone.sh.tmpl](https://github.com/peloeil/dotfiles/blob/4f5a68ed46aa74a9c0a3983c35837fce6d0965b6/.chezmoiscripts/run_once_after_12_install_codex_standalone.sh.tmpl) — CONFIRMED
    - `L7: curl -fsSL https://chatgpt.com/codex/install.sh |`
  - [Idanbot/.dotfiles/.chezmoiscripts/run_once_08-install-ai-tools.sh.tmpl](https://github.com/Idanbot/.dotfiles/blob/97ba371938454ab5928a5be994d5cb614dcbdfef/.chezmoiscripts/run_once_08-install-ai-tools.sh.tmpl) — CONFIRMED
    - `L34: https://chatgpt.com/codex/install.sh "$tmpdir/codex-install.sh" \`
  - [AkashiSN/dotfiles/.chezmoiscripts/run_onchange_after_40-ai-assistants.sh.tmpl](https://github.com/AkashiSN/dotfiles/blob/b739941bb67e4eb1081a6c1d09b45d186f5b30ab/.chezmoiscripts/run_onchange_after_40-ai-assistants.sh.tmpl) — CONFIRMED
    - `L21: # --- OpenAI Codex (chatgpt.com/codex/install.sh) ---`
    - `L24: curl -fsSL https://chatgpt.com/codex/install.sh | \`
  - [max-miller1204/dotfiles/.chezmoiscripts/run_once_before_10-install-packages.sh.tmpl](https://github.com/max-miller1204/dotfiles/blob/a0e7db41b4c38497fac4e3f3191f7ce2d0ccdf34/.chezmoiscripts/run_once_before_10-install-packages.sh.tmpl) — CONFIRMED
    - `L152: curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh`
  - [fx/dotfiles/.chezmoiscripts/run_onchange_after_install-codex.sh.tmpl](https://github.com/fx/dotfiles/blob/1f6cbfdd75e2a767fa80786e8f8ea1178bc64194/.chezmoiscripts/run_onchange_after_install-codex.sh.tmpl) — CONFIRMED
    - `L96: if CODEX_NON_INTERACTIVE=1 curl -fsSL https://chatgpt.com/codex/install.sh | sh; then`

### R2 codex native installer anywhere

- query: `"chatgpt.com/codex/install.sh"`
- rc: 0
- total_count: 3736 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [openai/codex/codex-rs/app-server-daemon/README.md](https://github.com/openai/codex/blob/596ae94fb00f8325d6bf835a9ebdc90baab4ad33/codex-rs/app-server-daemon/README.md) — CONFIRMED
    - `L81: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [openinterpreter/openinterpreter/codex-rs/app-server-daemon/README.md](https://github.com/openinterpreter/openinterpreter/blob/43e8b55ad4fa4aaa53a5e2b00a88cc14d297a404/codex-rs/app-server-daemon/README.md) — CONFIRMED
    - `L81: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [Alishahryar1/free-claude-code/scripts/install.sh](https://github.com/Alishahryar1/free-claude-code/blob/7195cefd5d0c197a9809e851a65b4a940918cee8/scripts/install.sh) — CONFIRMED
    - `L7: CODEX_INSTALL_URL="https://chatgpt.com/codex/install.sh"`
  - [digoal/blog/202607/20260730_02.md](https://github.com/digoal/blog/blob/69fb7934d82bf9489e42082d418476db6814fe4a/202607/20260730_02.md) — CONFIRMED
    - `L812: #    HTTP_PROXY=$ALL_PROXY HTTPS_PROXY=$ALL_PROXY ALL_PROXY=$ALL_PROXY all_proxy=$ALL_PROXY http_proxy=$ALL_PROXY https_proxy=$ALL_PROXY NO_PROXY="$NO_PROXY" no`
  - [tradecatlabs/vibe-coding-cn/research/openai-codex/raw/github-readme.raw.md.txt](https://github.com/tradecatlabs/vibe-coding-cn/blob/0ae243674325527dbfa9761c1660406a85151b6d/research/openai-codex/raw/github-readme.raw.md.txt) — CONFIRMED
    - `L19: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
    - `L31: curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_INSTALLER_USE_RELEASES_OPENAI_COM=false sh`
  - [stormzhang/ai-coding-guide/codex/03-install.md](https://github.com/stormzhang/ai-coding-guide/blob/d187dbdb83fa1be051a850074eb518e30e2eb47c/codex/03-install.md) — CONFIRMED
    - `L116: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
    - `L124: curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh`
    - `L216: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [FlashML-org/FreeToken/python/freetoken/launch.py](https://github.com/FlashML-org/FreeToken/blob/eba7120eabde70c7414e0e14c551e1caa3b0f174/python/freetoken/launch.py) — CONFIRMED
    - `L94: argv=("sh", "-c", "curl -fsSL https://chatgpt.com/codex/install.sh | sh"),`
  - [stormzhang/ai-coding-guide/codex/33-windows.md](https://github.com/stormzhang/ai-coding-guide/blob/d187dbdb83fa1be051a850074eb518e30e2eb47c/codex/33-windows.md) — CONFIRMED
    - `L131: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
  - [chaitanyagiri/munder-difflin/blog/src/posts/how-to-install-codex-cli.md](https://github.com/chaitanyagiri/munder-difflin/blob/2a5a5858ddf11885fe9c3980df0b9b1dfdace9a8/blog/src/posts/how-to-install-codex-cli.md) — CONFIRMED
    - `L25: Codex CLI is OpenAI's open source coding agent for the terminal, and you install it with one command: 'curl -fsSL https://chatgpt.com/codex/install.sh | sh' on `
    - `L61: curl -fsSL https://chatgpt.com/codex/install.sh | sh`
    - `L67: curl -fsSL https://chatgpt.com/codex/install.sh | sh -s -- --release 0.157.1`
  - [stormzhang/ai-coding-guide/codex/01-what-is-codex.md](https://github.com/stormzhang/ai-coding-guide/blob/d187dbdb83fa1be051a850074eb518e30e2eb47c/codex/01-what-is-codex.md) — CONFIRMED
    - `L177: curl -fsSL https://chatgpt.com/codex/install.sh | sh`

### R2 agy native installer in mise.toml

- query: `"antigravity.google/cli/install.sh" filename:mise.toml`
- rc: 0
- total_count: 0 (incomplete_results=False); re-fetched first 0 (per_page=10)

### R2 agy native installer in Dockerfile

- query: `"antigravity.google/cli/install.sh" filename:Dockerfile`
- rc: 0
- total_count: 282 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [agent-of-empires/agent-of-empires/docker/Dockerfile](https://github.com/agent-of-empires/agent-of-empires/blob/1d687df1b341368d583adcfde80ab455af85e23b/docker/Dockerfile) — CONFIRMED
    - `L54: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [johannesjo/parallel-code/docker/Dockerfile](https://github.com/johannesjo/parallel-code/blob/8c09c4c7a76f3265492e342b57df3847737b1cce/docker/Dockerfile) — CONFIRMED
    - `L60: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash -s -- --dir /usr/local/bin \`
  - [flutter/cocoon/cloud_build/flutter_agy_docker/Dockerfile](https://github.com/flutter/cocoon/blob/1421420a5270db1d536b5ef1346b07913f3b9ec6/cloud_build/flutter_agy_docker/Dockerfile) — CONFIRMED
    - `L53: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [jbcoe/value_types/docker/Dockerfile](https://github.com/jbcoe/value_types/blob/57f2e7a81aea38fd9cf29b4c0cd1f45c9ce2d415/docker/Dockerfile) — CONFIRMED
    - `L59: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [finbarr/yolobox/Dockerfile](https://github.com/finbarr/yolobox/blob/3a650d0d213c5f18d32151d1b741fd1830509e34/Dockerfile) — CONFIRMED
    - `L876: curl -fsSL https://antigravity.google/cli/install.sh -o "$installer"; \`
  - [docker/sbx-kits-contrib/antigravity/Dockerfile](https://github.com/docker/sbx-kits-contrib/blob/c7a99a0b4b61a666661714e859609087c3880624/antigravity/Dockerfile) — CONFIRMED
    - `L9: RUN curl -fsSL https://antigravity.google/cli/install.sh -o /tmp/install-antigravity.sh && \`
  - [vesaias/JobNavigator/Dockerfile.backend](https://github.com/vesaias/JobNavigator/blob/b06fb31d6f0ab4a9e9a4415be7b8e754508d0130/Dockerfile.backend) — CONFIRMED
    - `L35: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash \`
  - [ucb-bar/chia/dockerfiles/AntigravityDockerfile](https://github.com/ucb-bar/chia/blob/f1182bf429990d921d66e0f6818b1741aa664fa3/dockerfiles/AntigravityDockerfile) — CONFIRMED
    - `L55: # curl -fsSL https://antigravity.google/cli/install.sh | bash`
    - `L58: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [simion/termic/docs/docker-sandbox/Dockerfile](https://github.com/simion/termic/blob/cd56e6534df9966d2be8b5d03b4280dfef20dd27/docs/docker-sandbox/Dockerfile) — CONFIRMED
    - `L50: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [TwiTech-LAB/devchain/apps/local-app/Dockerfile](https://github.com/TwiTech-LAB/devchain/blob/7821ba17e80cc36ecaf115a9d0d19b1619d8e44f/apps/local-app/Dockerfile) — CONFIRMED
    - `L60: # script (https://antigravity.google/cli/install.sh), which drops 'agy' into ~/.local/bin. That`
    - `L109: RUN su - node -c "curl -fsSL https://antigravity.google/cli/install.sh | bash && agy --version"`

### R2 agy native installer in devcontainer.json

- query: `"antigravity.google/cli/install.sh" filename:devcontainer.json`
- rc: 0
- total_count: 21 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [memes/home/.devcontainer/devcontainer.json](https://github.com/memes/home/blob/afd3303ba2fc6537136b6d2aa82236922e006e14/.devcontainer/devcontainer.json) — CONFIRMED
    - `L23: "install-antigravity": "curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [r-carroll/code-adventure/.devcontainer/devcontainer.json](https://github.com/r-carroll/code-adventure/blob/db03f32d65afdcd4f91f5132250485cf4c19c74a/.devcontainer/devcontainer.json) — CONFIRMED
    - `L12: "postCreateCommand": "npm install -g @anthropic-ai/claude-code && curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [benjamin-aicheler/SynapseAdmin.NET/.devcontainer/devcontainer.json](https://github.com/benjamin-aicheler/SynapseAdmin.NET/blob/265619fc653695476696864dce7b44fdf89e57a6/.devcontainer/devcontainer.json) — CONFIRMED
    - `L13: "postCreateCommand": "curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [stageMatch/stageMatch/.devcontainer/devcontainer.json](https://github.com/stageMatch/stageMatch/blob/23a11a45b273f0b0f404f93c108f3cc0652e4786/.devcontainer/devcontainer.json) — CONFIRMED
    - `L28: "postCreateCommand": "curl -fsSL https://antigravity.google/cli/install.sh | bash && curl -fsSL https://claude.ai/install.sh | bash"`
  - [tianhaoz95/meowtrix/.devcontainer/devcontainer.json](https://github.com/tianhaoz95/meowtrix/blob/7941f0c02f53a5f48507faf1152af9fb06090a01/.devcontainer/devcontainer.json) — CONFIRMED
    - `L31: "postCreateCommand": "npm install && mkdir -p ~/.local/bin && curl -fsSL https://claude.ai/install.sh | bash && curl -fsSL https://antigravity.google/cli/instal`
  - [wjhorne/AllVibesDemo/.devcontainer/gemini/devcontainer.json](https://github.com/wjhorne/AllVibesDemo/blob/8f386e496199d8a3f9eeccdddf0e5ef3b501d4ad/.devcontainer/gemini/devcontainer.json) — CONFIRMED
    - `L10: "postCreateCommand": "sudo apt-get update && sudo apt-get install -y vim curl && curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [Zuul86/WeatherStation/.devcontainer/devcontainer.json](https://github.com/Zuul86/WeatherStation/blob/b84c2da830e9afc7f554c5ac9cea27b0dfcf3b12/.devcontainer/devcontainer.json) — CONFIRMED
    - `L19: "postCreateCommand": "wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash && dotnet dev-certs https --trust && wget -q`
  - [ric866/bitwarden-hardware-bridge/.devcontainer/devcontainer.json](https://github.com/ric866/bitwarden-hardware-bridge/blob/d1462c6d27635bfa5121d439d52b077e085f5f93/.devcontainer/devcontainer.json) — CONFIRMED
    - `L30: "postCreateCommand": "curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [Nucklan/CodeSearch/.devcontainer/devcontainer.json](https://github.com/Nucklan/CodeSearch/blob/15063f4cffa9acb709b8a06bd44d7e440d724580/.devcontainer/devcontainer.json) — CONFIRMED
    - `L17: "postCreateCommand": "curl -fsSL https://antigravity.google/cli/install.sh | bash",`
  - [iona-compagnia/compagnia/.devcontainer/devcontainer.json](https://github.com/iona-compagnia/compagnia/blob/851474d55f2cd0c03492c3a925dfb3786cea5629/.devcontainer/devcontainer.json) — CONFIRMED
    - `L31: "postCreateCommand": "npm install && curl -fsSL https://antigravity.google/cli/install.sh | bash && echo 'source ${containerWorkspaceFolder}/.devcontainer/welco`

### R2 agy native installer in chezmoi scripts

- query: `"antigravity.google/cli/install.sh" path:.chezmoiscripts`
- rc: 0
- total_count: 6 (incomplete_results=False); re-fetched first 6 (per_page=10)
  - [rnwolfe/.dotfiles/.chezmoiscripts/run_onchange_after_30_manual.sh.tmpl](https://github.com/rnwolfe/.dotfiles/blob/71af591a4883dbf8278c6b2fb8626e1299dd0ecf/.chezmoiscripts/run_onchange_after_30_manual.sh.tmpl) — CONFIRMED
    - `L20: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [p3aga/dotfiles/.chezmoiscripts/run_once_after_40-install-antigravity-cli.sh.tmpl](https://github.com/p3aga/dotfiles/blob/c1cf0049bd40eb2e38ecc48dff14de3ed08e699c/.chezmoiscripts/run_once_after_40-install-antigravity-cli.sh.tmpl) — CONFIRMED
    - `L10: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [timvink/dotfiles/.chezmoiscripts/run_onchange_setup_packages_darwin.sh](https://github.com/timvink/dotfiles/blob/c4c04c9d1d3f4546befe714e22e517907d5c4fe3/.chezmoiscripts/run_onchange_setup_packages_darwin.sh) — CONFIRMED
    - `L144: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [Idanbot/.dotfiles/.chezmoiscripts/run_once_08-install-ai-tools.sh.tmpl](https://github.com/Idanbot/.dotfiles/blob/97ba371938454ab5928a5be994d5cb614dcbdfef/.chezmoiscripts/run_once_08-install-ai-tools.sh.tmpl) — CONFIRMED
    - `L60: https://antigravity.google/cli/install.sh "$tmpdir/antigravity-install.sh" \`
  - [Raina-Hardik/dotfiles/.chezmoiscripts/run_onchange_after_install-tools.sh](https://github.com/Raina-Hardik/dotfiles/blob/f45f7c917b7e683d7ae2860855e576609d31748c/.chezmoiscripts/run_onchange_after_install-tools.sh) — CONFIRMED
    - `L92: "agy|https://antigravity.google/cli/install.sh"`
  - [yordycg/dotfiles-universal/.chezmoiscripts/run_once_after_20-install-mise.sh.tmpl](https://github.com/yordycg/dotfiles-universal/blob/afb07a1e4c5d4a95445e73b4dc978b5e480a9eba/.chezmoiscripts/run_once_after_20-install-mise.sh.tmpl) — CONFIRMED
    - `L85: curl -fsSL https://antigravity.google/cli/install.sh | bash`

### R2 agy native installer anywhere

- query: `"antigravity.google/cli/install.sh"`
- rc: 0
- total_count: 3960 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [digoal/blog/202607/20260722_01.md](https://github.com/digoal/blog/blob/69fb7934d82bf9489e42082d418476db6814fe4a/202607/20260722_01.md) — CONFIRMED
    - `L51: ALL_PROXY=http://127.0.0.1:22222 curl -fsSL https://antigravity.google/cli/install.sh | ALL_PROXY=http://127.0.0.1:22222 bash`
  - [freebsd/freebsd-ports/misc/antigravity-cli/Makefile](https://github.com/freebsd/freebsd-ports/blob/dc93ca6279f66e356b18ae0e0d017888a9d508ea/misc/antigravity-cli/Makefile) — CONFIRMED
    - `L29: install_sh=$$(fetch -q -o - https://antigravity.google/cli/install.sh); \`
  - [open-gsd/gsd-core/docs/zh-CN/how-to/set-up-cross-ai-review.md](https://github.com/open-gsd/gsd-core/blob/651a960f09bd99cf82d5993ed63b1286a8743f78/docs/zh-CN/how-to/set-up-cross-ai-review.md) — CONFIRMED
    - `L19: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [open-gsd/gsd-core/docs/ko-KR/how-to/set-up-cross-ai-review.md](https://github.com/open-gsd/gsd-core/blob/651a960f09bd99cf82d5993ed63b1286a8743f78/docs/ko-KR/how-to/set-up-cross-ai-review.md) — CONFIRMED
    - `L19: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [Tracer-Cloud/opensre/integrations/llm_cli/antigravity_cli.py](https://github.com/Tracer-Cloud/opensre/blob/e81c88df134e883088a6ad48afad6d806f8b61ce/integrations/llm_cli/antigravity_cli.py) — CONFIRMED
    - `L141: install_hint = "curl -fsSL https://antigravity.google/cli/install.sh | bash"`
  - [agent-of-empires/agent-of-empires/docker/Dockerfile](https://github.com/agent-of-empires/agent-of-empires/blob/1d687df1b341368d583adcfde80ab455af85e23b/docker/Dockerfile) — CONFIRMED
    - `L54: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [massgen/MassGen/docs/announcements/archive/v0.1.88.md](https://github.com/massgen/MassGen/blob/007bd8579298d7dc3ff2a43c378e27a284902f22/docs/announcements/archive/v0.1.88.md) — CONFIRMED
    - `L21: curl -fsSL https://antigravity.google/cli/install.sh | bash`
    - `L74: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [massgen/MassGen/docs/announcements/archive/v0.1.89.md](https://github.com/massgen/MassGen/blob/007bd8579298d7dc3ff2a43c378e27a284902f22/docs/announcements/archive/v0.1.89.md) — CONFIRMED
    - `L21: curl -fsSL https://antigravity.google/cli/install.sh | bash`
    - `L80: curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - [johannesjo/parallel-code/docker/Dockerfile](https://github.com/johannesjo/parallel-code/blob/8c09c4c7a76f3265492e342b57df3847737b1cce/docker/Dockerfile) — CONFIRMED
    - `L60: RUN curl -fsSL https://antigravity.google/cli/install.sh | bash -s -- --dir /usr/local/bin \`
  - [hardbeat920/monocode/CONTRIBUTING.md](https://github.com/hardbeat920/monocode/blob/7ce63cb80e2afc48a170358f1d86381da238d802/CONTRIBUTING.md) — CONFIRMED
    - `L16: - [Antigravity](https://antigravity.google/docs/cli-install) (macOS/Linux) - 'curl -fsSL https://antigravity.google/cli/install.sh | bash', then run 'agy' once `

### R2 codex update in mise.toml

- query: `"codex update" filename:mise.toml`
- rc: 0
- total_count: 0 (incomplete_results=False); re-fetched first 0 (per_page=10)

### R2 agy update in mise.toml

- query: `"agy update" filename:mise.toml`
- rc: 0
- total_count: 0 (incomplete_results=False); re-fetched first 0 (per_page=10)

### R2 disable_tools naming codex

- query: `"disable_tools" "codex" language:TOML`
- rc: 0
- total_count: 19 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [jefftriplett/dotfiles/home/.config/mise/config.toml](https://github.com/jefftriplett/dotfiles/blob/90c6e95c6921252d7ca73d0d21d4893d029d1117/home/.config/mise/config.toml) — CONFIRMED
    - `L41: [tasks.codex]`
    - `L42: description = "Run Codex with bypass-approvals-and-sandbox and resume fallback"`
    - `L43: run = "cd $MISE_ORIGINAL_CWD && codex --dangerously-bypass-approvals-and-sandbox resume || codex --dangerously-bypass-approvals-and-sandbox"`
  - [megalithic/dotfiles/config/mise/config.toml](https://github.com/megalithic/dotfiles/blob/729f0c49c7f510321a87c64e7de0bc7bdb88e0d5/config/mise/config.toml) — CONFIRMED
    - `L29: "npm:@openai/codex",`
    - `L236: "aqua:openai/codex" = "latest"`
  - [eugeniojimenes/dotfiles/mise/.config/mise/config.toml](https://github.com/eugeniojimenes/dotfiles/blob/55517df5e9ed18c4686acd2ce4dcaa7c243c7282/mise/.config/mise/config.toml) — CONFIRMED
    - `L16: codex = "latest"`
  - [musher-dev/specifications/.config/mise/config.toml](https://github.com/musher-dev/specifications/blob/83c6170778376bd52f8a735bd5431238eb2bcd65/.config/mise/config.toml) — CONFIRMED
    - `L43: # @openai/codex is pinned here but NOT installed by default: it is opt-in via`
    - `L44: # MUSHER_INSTALL_CODEX=1 in .devcontainer/.env, which the setup scripts turn`
    - `L47: "npm:@openai/codex" = "0.143.0"`
  - [ErebusBat/chezmoi/dot_config/mise/config.local.toml](https://github.com/ErebusBat/chezmoi/blob/fb6b3f509d8898e66da56cf2f845b7a6e2b7220f/dot_config/mise/config.local.toml) — CONFIRMED
    - `L6: # calls and rate-limit warnings. Codex explicitly uses aqua:openai/codex, so`
    - `L7: # disabling npm here keeps prompts fast without disabling codex.`
  - [moniquelive/dotfiles/.config/mise/config.freebsd.toml](https://github.com/moniquelive/dotfiles/blob/a73ea7d349d8ab51bd9259fc2b87bbef4e778a78/.config/mise/config.freebsd.toml) — CONFIRMED
    - `L61: "codex",`
  - [ssiumha/dots/config/mise/config.toml](https://github.com/ssiumha/dots/blob/b59bf28416779b5a4e336e5f2301d80da001c8b3/config/mise/config.toml) — CONFIRMED
    - `L55: codex = "npm:@openai/codex"`
  - [jarv/dotfiles/dotfile.mise/config.toml](https://github.com/jarv/dotfiles/blob/433ca1ff68646cb5c47a9a08be14d8c7b274548b/dotfile.mise/config.toml) — CONFIRMED
    - `L35: codex = "latest"`
  - [ray-manaloto/dotfiles/mise.toml](https://github.com/ray-manaloto/dotfiles/blob/a5a9f786b1a953148ae1624d581f2a71f02359d9/mise.toml) — CONFIRMED
    - `L109: # Cross-vendor executor-lane CLIs: codex (this repo's own codex-* lanes) and`
    - `L116: # executor lanes only. Auth is per-user (codex login / Google account).`
    - `L118: # 'codex' (the orchestrator's executor lane here, and separately the #613`
    - `L119: # in-container review lane's 'npm:@openai/codex' in mise-runtime.toml) moved`
  - [mattdepaula/dotfiles/config/mise/config.toml](https://github.com/mattdepaula/dotfiles/blob/dde55542137146257d956c1c43f40e110836fdb7/config/mise/config.toml) — CONFIRMED
    - `L9: "npm:@openai/codex" = "latest"`

### R2 disable_tools naming claude

- query: `"disable_tools" "claude" language:TOML`
- rc: 0
- total_count: 47 (incomplete_results=False); re-fetched first 10 (per_page=10)
  - [jdx/mise/settings.toml](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/settings.toml) — CONFIRMED
    - `L3116: default = ".claude/skills"`
  - [jefftriplett/dotfiles/home/.config/mise/config.toml](https://github.com/jefftriplett/dotfiles/blob/90c6e95c6921252d7ca73d0d21d4893d029d1117/home/.config/mise/config.toml) — CONFIRMED
    - `L29: [tasks.claude]`
    - `L30: description = "Run Claude with skip-permissions and continue fallback"`
    - `L31: run = "cd $MISE_ORIGINAL_CWD && command claude --allow-dangerously-skip-permissions --dangerously-skip-permissions --continue || command claude --allow-dangerou`
    - `L33: [tasks.claude-agents]`
  - [djensenius/dotfiles/mise/config.toml](https://github.com/djensenius/dotfiles/blob/2234f84b203682c6a3b415b8aae8fbaa4518eefd/mise/config.toml) — CONFIRMED
    - `L21: "npm:@anthropic-ai/claude-code" = "latest"`
  - [samhvw8/dotfiles/mise/config.toml](https://github.com/samhvw8/dotfiles/blob/cd1f6f1bb78ec04cfecf8be032db34b0ae65dbac/mise/config.toml) — CONFIRMED
    - `L42: "github:samhvw8/claude-code-profile" = { version = "latest", minimum_release_age = "0s" }`
    - `L49: claude = { version = "latest", minimum_release_age = "0s" }`
    - `L94: # ~/.claude belongs to ccp ('ccp use -g' repoints it), so it is not a`
    - `L97: "mise exec -- bash $HOME/.dotfiles/mise/scripts/setup-claude-mcp.sh",`
  - [megalithic/dotfiles/config/mise/config.toml](https://github.com/megalithic/dotfiles/blob/729f0c49c7f510321a87c64e7de0bc7bdb88e0d5/config/mise/config.toml) — CONFIRMED
    - `L30: "claude-code",`
    - `L301: claude = "latest"`
  - [eugeniojimenes/dotfiles/mise/.config/mise/config.toml](https://github.com/eugeniojimenes/dotfiles/blob/55517df5e9ed18c4686acd2ce4dcaa7c243c7282/mise/.config/mise/config.toml) — CONFIRMED
    - `L15: claude = "latest"`
  - [mattdepaula/dotfiles/config/mise/config.toml](https://github.com/mattdepaula/dotfiles/blob/dde55542137146257d956c1c43f40e110836fdb7/config/mise/config.toml) — CONFIRMED
    - `L25: disable_tools = ["npm:@anthropic-ai/claude-code"]`
  - [ssiumha/dots/config/mise/config.toml](https://github.com/ssiumha/dots/blob/b59bf28416779b5a4e336e5f2301d80da001c8b3/config/mise/config.toml) — CONFIRMED
    - `L53: claude = "npm:@anthropic-ai/claude-code"`
    - `L54: claude_swarm = "gem:claude_swarm"`
  - [hallelujah/dotfiles/config/mise/config.nixos.toml](https://github.com/hallelujah/dotfiles/blob/e4b303f0c48eb45f8256baff730429467a0aed6c/config/mise/config.nixos.toml) — CONFIRMED
    - `L10: "npm:@agentclientprotocol/claude-agent-acp",`
  - [j5ik2o/dotfiles/config/mise/mise.toml](https://github.com/j5ik2o/dotfiles/blob/ad6377f347148836ec5805538b97b130d74dd1e3/config/mise/mise.toml) — CONFIRMED
    - `L23: claude = "2.1.285"`

## Exemplar excerpts (re-fetched from default branch 2026-09-30)

- **bellini666/dotfiles `mise.toml` L44-60** — `[tasks."agents:install"]` "Install or update Claude Code and Codex": `claude update` if present else download `claude.ai/install.sh` to a mktemp dir and run it; then `CODEX_NON_INTERACTIVE=1 sh codex.sh` from `chatgpt.com/codex/install.sh`. Closest match to an `update:claude`/`update:codex` task pair.
- **fuyutarow/dotfiles `mise.toml` L500-505** — `[tasks."install:ai-clis"]`, run list `curl -fsSL https://claude.ai/install.sh | bash` + `curl -fsSL https://chatgpt.com/codex/install.sh | sh`; comment: "Never bun/npm — an npm claude cannot self-update"; agy reached separately.
- **halkn/dotfiles `mise.toml` L67-69** — comment: "Claude Code is in the mise registry, but `claude update` ... replaces it in place and would drift from the lockfile, so it stays on its own installer"; guarded `command -v claude || curl … | bash` in `[bootstrap.hooks.final]`.
- **simonrw/dotfiles `mise.toml` L186-187**, **dkimura/osx-setup `mise.toml` L70-71**, **advaypakhale/dotfiles `mise.toml` L26** — idempotent `command -v X || curl … | sh` / `test -x ~/.local/bin/X ||` guards.
- **mattdepaula/dotfiles `config/mise/config.toml` L25** — `disable_tools = ["npm:@anthropic-ai/claude-code"]`: exact precedent for disabling a vendor CLI's mise entry by full backend id.
- **jdx/mise `settings.toml` L559-562** — `[disable_tools]` setting, env `MISE_DISABLE_TOOLS` (the upstream definition).
- **dceoy/docker-ai-coder `mise.toml` L18**, **hidekitux/skills** (`aqua:google-antigravity/antigravity-cli`), **jamierumbelow/agentfiles** (`http:agy` with per-platform GCS URLs + sha512) — the mise-managed agy alternatives people use instead of the native installer.

## Synthesis

1. **Native installers are the dominant real-world pattern for all three CLIs.** Official one-liners, each confirmed across mise.toml / Dockerfile / devcontainer.json / chezmoi hits:
   - claude: `curl -fsSL https://claude.ai/install.sh | bash` (mise.toml 17, Dockerfile 4864, devcontainer.json 204, .chezmoiscripts 49)
   - codex: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`, non-interactive via `CODEX_NON_INTERACTIVE=1`, version via `sh -s -- --release <v>` (mise.toml 5, Dockerfile 206, devcontainer.json 10, .chezmoiscripts 7). Also `github.com/openai/codex/releases/download/rust-v<v>/install.sh` and raw musl tarballs (205 Dockerfile hits).
   - agy: `curl -fsSL https://antigravity.google/cli/install.sh | bash`, `-s -- --dir /usr/local/bin` supported (Dockerfile 282, devcontainer.json 21, .chezmoiscripts 6). Release tarballs also at `github.com/google-antigravity/antigravity-cli/releases/download/<v>/agy_cli_linux_<arch>.tar.gz` (GoogleCloudPlatform/scion, openabdev/openab).
2. **Image/devcontainer installs are in the Dockerfile at build time far more than postCreateCommand** (claude Dockerfile 4864 vs devcontainer.json 204), and pinned-version Dockerfiles pass the version to the installer (`bash -s "${CLAUDE_CODE_VERSION}"`, codex `rust-v${CODEX_VERSION}/install.sh`, agy `${AGY_VERSION}` release asset). This is the IMAGE-side replacement shape if the IMAGE pins are retired — it must still be proven in this repo's image before any IMAGE/CI pin is removed.
3. **mise-task shape**: no exact `update:codex` / `update:claude` / `install:agy` mise task exists in the sample — those literal names hit only npm/pnpm scripts and unrelated CLIs (makecindy/cindy `package.json`, MemberJunction `mj update:claude`, sendbird cc-plugin-codex). Real mise precedents use `agents:install` (bellini666) and `install:ai-clis` (fuyutarow), or `bootstrap` hooks (halkn, simonrw).
4. **`disable_tools` is widely used (116 mise.toml, 20 under .config/mise, 269 TOML)** and one dotfiles repo disables a Claude npm backend by full id. Hits that named codex/claude alongside `disable_tools` were mostly co-occurrence, not disabling them.
5. **Negatives (with control arms)**: `"antigravity.google/cli/install.sh" filename:mise.toml` = 0, `"codex update" filename:mise.toml` = 0, `"agy update" filename:mise.toml` = 0. Control: the same query shape `"claude.ai/install.sh" filename:mise.toml` = 17 and `"chatgpt.com/codex/install.sh" filename:mise.toml` = 5, and a fresh nonsense token = 0 while `"[tools]" filename:mise.toml` = 25280 — so the probe discriminates. Bounds: GitHub code search indexes default branches only and excludes some large/fork repos; only the first 10 hits per query were re-fetched.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `disable_tools` setting definition
- [bellini666/dotfiles](https://github.com/bellini666/dotfiles) — mise `agents:install` task (claude update / codex native)
- [fuyutarow/dotfiles](https://github.com/fuyutarow/dotfiles) — mise `install:ai-clis` task
- [halkn/dotfiles](https://github.com/halkn/dotfiles) — claude kept off mise registry because `claude update` drifts the lock
- [simonrw/dotfiles](https://github.com/simonrw/dotfiles) — guarded codex native install in mise
- [dkimura/osx-setup](https://github.com/dkimura/osx-setup) — guarded claude + codex native installs in mise
- [hiramekun/dotfiles](https://github.com/hiramekun/dotfiles) — claude + codex native installs in mise
- [advaypakhale/dotfiles](https://github.com/advaypakhale/dotfiles) — guarded claude install task
- [mattdepaula/dotfiles](https://github.com/mattdepaula/dotfiles) — `disable_tools` for claude npm backend
- [megalithic/dotfiles](https://github.com/megalithic/dotfiles) — codex/claude in mise config
- [dceoy/docker-ai-coder](https://github.com/dceoy/docker-ai-coder) — agy via mise github backend
- [jamierumbelow/agentfiles](https://github.com/jamierumbelow/agentfiles) — agy via mise http backend
- [GoogleCloudPlatform/scion](https://github.com/GoogleCloudPlatform/scion) — agy release-tarball Dockerfile install
- [openabdev/openab](https://github.com/openabdev/openab) — pinned agy Dockerfile install
- [johannesjo/parallel-code](https://github.com/johannesjo/parallel-code) — agy installer `--dir` in Dockerfile
- [docker/sbx-kits-contrib](https://github.com/docker/sbx-kits-contrib) — codex + agy native installers in Dockerfiles
- [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) — pinned codex `rust-v<v>/install.sh` in devcontainer Dockerfile
- [Accio-Lab/Dressage](https://github.com/Accio-Lab/Dressage) — pinned claude + codex installers in Dockerfile
- [near/nearcore](https://github.com/near/nearcore) — claude native install in devcontainer Dockerfile
- [PLC-lang/rusty](https://github.com/PLC-lang/rusty) — guarded claude install in postCreateCommand
- [pypose/bae](https://github.com/pypose/bae) — codex + claude in postCreateCommand
- [openai/codex](https://github.com/openai/codex) — upstream README of the codex installer
- plus every other repo listed in the raw query log above (first-10 hits per query).
