---
okf_version: "0.2"
type: "report"
title: "Private names in a public dotfiles repo"
description: "How names we do not want public (machine names, addresses) live in Doppler and reach mise templates through fnox, what other dotfiles repos do, Tailscale tips, and the gaps."
---

# Private names in a public dotfiles repo

Research of 2026-11-12, for the owner's ruling that names we do not want public (machine names, addresses,
tailnet names) live in Doppler and never in a tracked file, commit, PR or issue. Add to this page instead of
repeating the research.

## What we use (MVP)

- Each name is a Doppler secret in the existing `dotfiles/dev_personal` config, added with
  `pbpaste | mise run secret:set NAME`.
- The one global fnox file (`unix/home/.config/fnox/config.toml`) reads it with `env = "exec"`.
- A mise `[bootstrap.secrets]` entry in the root `mise.toml` names the variable, and a `[dotfiles]` entry with
  `mode = "template"` renders it with `{{ secret(name="...") }}` (mise `docs/bootstrap/secrets.md` at v2026.11.7).
- The owner applies with the real value in the environment:
  `fnox exec -- mise dot apply <targets>`. Agents cannot: the rule guard blocks `fnox exec`, and
  `fnox proxy run` gives a command placeholders only (fnox `docs/cli/proxy.md:13` at v1.48.0), so a template
  rendered under the proxy would hold the placeholder text.
- First user: `~/.ssh/config.d/tailnet.conf`: the PC over Tailscale from `PC_HOST`, and the break-glass
  `pc-lan` host over the home LAN from `PC_LAN_HOST`.

Left for later (owner: MVP first): a separate names-only Doppler config with its own read-only service token, a
fnox profile for it, and a mise task that applies under that profile so an agent can run it without a token that
reads API keys.

## Doppler

Primary sources: docs.doppler.com and the DopplerHQ/cli source.

- Visibility. *Unmasked* is "always displayed" and "retrievable via any token type"; Doppler names it for
  non-sensitive values such as database ports. *Masked* hides the value in the dashboard only. *Restricted* is
  readable only through non-user tokens, so the owner's own login could not read a restricted name: never use it
  for names.
- A service token gives "read-only secrets access to a specific config within a project", with optional write
  access and expiry (docs.doppler.com/docs/service-tokens). That is the scope for a later names-only token.
- `doppler secrets substitute <file>` renders a Go template with secrets and `--output` writes it 0600;
  `doppler run --mount` is an ephemeral FIFO. mise already renders templates, so neither is needed.
- Offline: the doppler CLI has encrypted fallback files (`--fallback`, `--offline`), used only when the API
  status is not 401, 403 or 404. fnox's doppler provider probably does not use them (not verified). The owner
  accepted that an apply needs the network.
- No Doppler doc or blog covers dotfiles, ssh config, hostnames or Tailscale.

## What other dotfiles repos do

Line numbers are from each default branch on 2026-11-12.

- ahstn/dotfiles, the same mechanism: `mise.toml:116-118` declares `[bootstrap.secrets]`
  (`tern_tailscale_email`, `tern_ssh_fingerprint`), and `.config/tern/access.toml.tera:26` renders
  `{{ secret(name="tern_tailscale_email") | json_encode }}`. Values come from fnox backed by 1Password. Docs use
  placeholders such as `<host>.<tailnet>.ts.net` (`README.md:98`).
- WeixuanZ/dotfiles: `misc/.ssh/config:3-5` includes an untracked `~/.ssh/config.local` first ("ssh uses the first
  value it finds for each option"); `README.md:51-53` keeps machine-specific values in such local files. The most
  common pattern overall, but nothing syncs it between machines.
- Xevion/dotfiles (chezmoi, Doppler, age): a private domain from Doppler
  (`home/run_onchange_install-packages.sh.tmpl:59`, `dopplerProjectJson.PRIVATE_DOMAIN`) and the whole ssh config
  age-encrypted (`ARCHITECTURE.md:143,156`).
- rios0rios0/dotfiles (chezmoi, 1Password): `dot_ssh/config.tmpl` builds hosts from per-device vault items.
- divaltor/.dotfiles: reads tailnet names at run time from `tailscale status --json`
  (`homelab/ansible/inventory/tailscale.yml:1-9`), so none is stored.
- risu729/dotfiles commits its hostnames (`unix/home/.ssh/config:1-2`): not a precedent here. jdx's dotfiles are
  not public.

Other mise options (v2026.11.7), not used for the MVP:

- `mode = "fnox"` deploys a whole file stored encrypted in fnox (`docs/dotfiles/managed.md:243-262`). Its
  ciphertext would sit in the public global fnox file and its git history.
- `[vars]` with `prompt` asks once per machine and keeps the answer in `$MISE_STATE_DIR/vars.toml` (mise PR
  #14190), outside the repo, but not in Doppler.
- `merge = "missing"` seeds a file once with `secret()` values (`docs/dotfiles/edits.md:198,223-252`).

No mise or fnox issue, PR or discussion covers hostnames or Tailscale names in dotfiles.

## Tailscale tips from those repos

- A tracked `Host *.ts.net` block with `StrictHostKeyChecking accept-new` and `UpdateHostKeys yes`
  (WeixuanZ `misc/.ssh/config:20-22`): policy for every tailnet host without naming one.
- Use the system ssh over MagicDNS, not `tailscale ssh` (WeixuanZ `misc/.ssh/config:18-19`), as this repo does.
- Keep Tailscale settings in mise tasks, not files: ahstn `mise.toml:137-155` runs
  `sudo tailscale set --accept-dns=true --shields-up=false --ssh --operator="$USER"` on a Linux server and
  `tailscale set --accept-dns=true` on a client.
- Scripts can take the tailnet name from `tailscale status --json` (`DNSName`) and connect with
  `ProxyCommand tailscale nc %h %p` (divaltor).

## Gaps and failures

- `/last30days` (engine 3.36.0) on "Doppler secrets dotfiles hostnames non-secret config" returned only two
  unrelated Hacker News items. Its own `doctor --postmortem`:
  - Web search failed with `CERTIFICATE_VERIFY_FAILED ... Missing Authority Key Identifier`. Cause, reproduced:
    fnox 1.48.0's proxy signs its own certificate for each host in its rules (here Serper), and that certificate
    lacks the Authority Key Identifier that Python 3.13+ requires in its default strict mode. A host outside the
    rules passes. Fixed upstream in jdx/fnox PR #1162 (issue #1160), not yet released; rerun after the fnox bump.
  - Reddit answered `HTTP 403: Blocked`: Reddit refuses the scripted request.
- Not verified: whether fnox's doppler provider uses Doppler's offline fallback; which pattern is most common
  (a handful of repos, no survey).
