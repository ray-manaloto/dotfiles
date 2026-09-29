# Proposal: give every Omarchy user a declarative "my machine" file with `mise bootstrap`

- URL: https://github.com/jdx/mise/discussions/12709
- author: jdx created: 2026-09-02T15:46:56Z

## Body

Omarchy already ships mise, and as of the lazy-tools change it declares its default agent CLIs (Claude Code, Codex, gh, opencode, and the rest) as lazy tools in a system-level mise config at `/etc/mise/config.toml`. That file is already a small "Omarchy layer": it says what the distro wants on the machine, and a user's own `~/.config/mise/config.toml` layers on top of it, so pinning `claude` to a version in the global config already overrides Omarchy's `latest`.

mise has a second half that Omarchy is not using yet: `mise bootstrap`, which converges a machine to a declared state. Packages, system files, systemd services, firewall rules, dotfiles, and the tools it already handles. It uses the same config files and the same layering. I maintain mise, and I am willing to make broad changes to bootstrap to fit Omarchy. This post is about what extending that existing layer would give Omarchy users that they do not have today.

## The user problem

Omarchy makes a fresh machine beautiful in twenty minutes. Then people spend the next month making it *theirs*: `pacman -S` a dozen things, remove the preinstalls they never open, flip a service, tweak a Hyprland file, install their language toolchains. None of that is recorded anywhere. When they get a second machine, reinstall after a bad experiment, or move from the laptop to a desktop, they do it all again from memory.

The current answer is "keep notes" or "write a shell script". Neither is Omarchy-grade.

## This is opt-in

Nothing here is required to set up or use an Omarchy machine. The installer, `omarchy update`, and every existing command keep working exactly as they do for someone who never touches a mise config. Bootstrap is one way to make a setup trackable and shareable for the people who want that. Users who prefer to `pacman -S` things by hand lose nothing.

## What it would look like

The user's global mise config, `~/.config/mise/config.toml`, becomes the one file that describes their machine. `~/.config/mise` is a git checkout, so that file and the dotfiles next to it live in a repo. Roughly:

```toml
# ~/.config/mise/config.toml

# Extra packages on top of Omarchy
[bootstrap.packages]
"pacman:helix" = "latest"
"pacman:zathura" = "latest"
"pacman:libreoffice-fresh" = { state = "absent" }   # a preinstall, gone (not in mise yet, see below)

# Flip an Omarchy default
[bootstrap.services.cups]
enabled = false
state = "stopped"

# Dev toolchains. This is the same [tools] table `mise use -g` already writes to,
# and the same table Omarchy's /etc/mise/config.toml uses for its lazy agent CLIs.
[tools]
node = "lts"
ruby = "latest"
rust = "latest"
claude = "2.1"          # overrides Omarchy's lazy `latest`, works today

# Their own config files, kept in the same repo and symlinked into place
[dotfiles]
"~/.config/hypr/bindings.lua" = "hypr/bindings.lua"
"~/.config/alacritty/alacritty.toml" = "alacritty/alacritty.toml"
"~/.gitconfig" = "gitconfig"
```

On a fresh Omarchy machine:

```sh
omarchy setup dotfiles git@github.com:me/omarchy-setup.git
```

which checks the repo out as `~/.config/mise` and runs `mise bootstrap`. Ten minutes later it is their machine. From then on `omarchy update` runs plain `mise bootstrap`, so declared packages and files stay applied over time. There is no separate dotfiles repo path for Omarchy to remember, because the global config *is* the repo.

## What users get that they do not have today

**Their setup gets recorded without them doing anything new.** Because the repo is the global config, every `mise use -g node` a user already runs today lands in the repo. Omarchy's own dev-env installer writes there too. Add `omarchy pkg add` delegating to `mise bootstrap packages use -g pacman:...` and installing a package records it as well. The declared file stays true because the tools people already use write to it.

**Reinstall stops being scary.** A fresh Omarchy install plus one command gets someone back to their exact setup. That makes people far more willing to try things, wipe, and start over, which is the mindset Omarchy wants to encourage.

**Many machines, one source of truth.** Laptop and desktop share the repo. mise environments (`-E work`, `-E home`) handle the differences from one config.

**Customizing Omarchy by declaring, not by fighting it.** Today the only Omarchy default a user can override declaratively is a tool version. Removing a preinstall or disabling a default service is a manual action Omarchy might undo on the next refresh, and the preinstalls toggle works by deleting and reinstalling the whole system mise file. With bootstrap, the same override mechanism that already works for tools covers packages, services, and files. I verified this week that a user config overriding a system-level declaration works today: the plan showed the union of both, the user's entries won on shared keys, and each line named the config that declared it.

**A machine that can tell you what changed.** `mise bootstrap plan` and `mise bootstrap status --missing` are a drift report. "Why is my machine different from my other one" has an answer.

**Shareable setups.** "Omarchy, but set up for Rails work" or "Omarchy for a Framework 13 in a design shop" becomes a repo someone can fork. That is a community surface Omarchy does not have.

**Fleets, later.** The same config applies to other machines with `mise bootstrap remote`, which stages the project over plain OpenSSH and runs bootstrap there. Hosts live in an inventory with tags, and `-E` environments give a host its profile, so this is the Ansible shape without Python on the target. Nobody needs this to set up one laptop. It matters when a team, a classroom, or a company wants ten Omarchy machines to match one repo, and it means Omarchy would not have to build its own fleet story when that comes up.

**Agents can edit TOML safely.** Omarchy's pitch is Beautiful, Fun and Agentic. An agent adding a package by editing one declared file and running `plan` is a much safer loop than an agent running `sudo pacman -S`. The desired state is reviewable in a diff before anything happens, and it is already in git.

## What Omarchy itself gets

This is secondary, but real. A good share of `install/config/` and of the migrations are hand-written versions of "ensure this service is enabled", "ensure this file is in `/etc` with these permissions", "ensure this package is present". Those become `[bootstrap.*]` sections next to the `[tools]` table Omarchy already ships in `/etc/mise/config.toml` (or a sibling file in `/etc/mise/conf.d/`), converged on every update, with no marker files and no bespoke idempotency logic per script. The user's global config layers on top of that system file, which is exactly why the user story above works and why the tool-version override works already.

## What does not work yet, and what I will build

I want to be straight about the gaps, because they are mine to fix.

- **Declarative package removal.** Today `state = "absent"` for a pacman package does not exist. It is the most common customization after "add these", so it is first.
- **AUR.** The pacman backend does not build AUR packages. Omarchy has AUR packages, and users will ask.
- **Checking a repo out as the global config.** `mise bootstrap --from <url>` exists but clones to a side directory. It should be able to make the checkout `~/.config/mise` itself, with sane handling of an existing config there.
- **An enable-only mode for services and firewall.** The Omarchy installer runs in a chroot with no live systemd and must not enable UFW live. Bootstrap needs a mode that writes enable symlinks and rules without starting anything, so the same declarations can run at install time and on the installed system.
- **Anything else Omarchy needs.** If adopting this surfaces a rough edge in mise, I would rather change mise than have Omarchy work around it in bash.

On the Omarchy side the main thing to sort out is `omarchy-refresh-config`, which copies onto the target and would write through a symlink into a user's repo. That is a small change once the model is agreed.

## Proposed order

1. Add `[bootstrap.services]` and `[bootstrap.files]` declarations beside the existing lazy `[tools]` in Omarchy's system mise config, and apply them from `omarchy update` and `omarchy-migrate`. No user-facing surface yet. This proves the model on the file that already exists.
2. Add `omarchy setup dotfiles`, run `mise bootstrap` from `omarchy update`, and point `omarchy pkg add` at the declared config. Small once step 1 exists.
3. Land package removal, AUR, global-config checkout, and enable-only mode in mise in parallel, then extend the installer to use the same declarations.

I am happy to do the mise work and to help with the Omarchy side. Interested in whether this direction appeals before writing any code.

## Comments
### nettlesh @ 2026-09-02T19:54:23Z

I know this as an Omarchy focused post, but all of your suggested additions to mise would be 100% applicable to my CachyOS bootstrap too. I'm currently fully using mise bootstrap to one-touch setup all my machines atm via my dotfiles repo, which contains both arch and macOS mise configs. The absent state and AUR backend would be especially helpful as those are both gaps I've had to work around in my current dots. Definitely looking forward to those
#### reply jdx @ 2026-09-02T20:24:08Z

that's even better, I actually didn't realize that we couldn't do AUR packages so we could definitely improve some AUR-related things. I posted this here instead of omarchy since I wanted to refine this a bit more before presenting it to them and probably close some gaps like that.

if you have some specific feedback on any of the details I'd appreciate it, it would also be nice if once I close some of these gaps we could try to make a poc in both distros. A lot of this also isn't specific to arch either.

#### reply airtonix @ 2026-09-03T00:48:54Z

also bazzite. lamenting that DHH used arch instead of [Fedora Atomic](https://fedoraproject.org/atomic-desktops/)

#### reply airtonix @ 2026-09-03T00:58:24Z

and i feel like `mise bootstrap` and `mise oci` could work together to help users making trivial atomic oci images https://docs.bazzite.gg/Advanced/creating_custom_image/

#### reply nettlesh @ 2026-09-03T01:33:43Z

Definitely down to poc it out on the CachyOS side, as soon absent lands (which looks like soon) I'll try it out on my dots and attempt to remove a few packages it ships with. Cachy isn't nearly as opinionated as Omarchy but they certainly have _some_ opinions

For AUR in the bootstrap so far I've resorted to pulling paru from a Cachy repo via pacman declaratively, and then shoving the AUR piece into a mise bootstrap task. I've also tried adding it to the post-packages hook, which I actually prefer since that honors --skip packages. However, the one thing that's bitten me on bootstrap hooks is that the Tera templating doesn't render ({{ xdg_config_home }} in a hook has got me a couple times now because I keep forgetting) but I don't know how addressable that actually is. In general, I've been preferring to leverage the bootstrap hooks over tasks for this kind of automation.

The AUR backend would definitely solve this, but since mise is very supply chain focused it might be worth adding a note in the docs about being careful when it comes to the AUR, since we've been getting repeated malware attacks this summer. I don't think that's necessarily mise's responsibility to do anything about from a technical perspective but figured I'd flag that for the less security-conscious user

As for feedback on all of your other suggestions for the Omarchy side of the house, like I said I don't use it but they all seem great. Since mise ships with it, it makes sense that the the bootstrap mechanism should converge on mise entirely. Making Omarchy "yours" would be far far easier to accomplish, and then you can check your declarative OS config right into git. 

#### reply jdx @ 2026-09-03T02:17:06Z

> The AUR backend would definitely solve this, but since mise is very supply chain focused it might be worth adding a note in the docs about being careful when it comes to the AUR, since we've been getting repeated malware attacks this summer. I don't think that's necessarily mise's responsibility to do anything about from a technical perspective but figured I'd flag that for the less security-conscious user

the good thing is that if omarchy were to be successful and stick with arch they would have to solve this somehow. I'm thinking by replacing AUR with an alternative store and also having an improved package manager or perhaps a wrapper around pacman with some preflight checks might be sufficient. Perhaps mise could at least be a poc for some of these checks since it's already wrapping pacman/yay/paru and we could decorate the repository somehow with the right metadata for things like minimum release age (which as I understand it isn't possible with how stuff is structured right now).

you're not the first person to bring this up to me recently, it's probably worth my time to do a bit of a spike and learn more about how the AUR internals work and see what could be done. If you have any suggestions/pointers I'd appreciate it. I don't know much about AUR but of course I do know package managers generally.

> However, the one thing that's bitten me on bootstrap hooks is that the Tera templating doesn't render ({{ xdg_config_home }} in a hook has got me a couple times now because I keep forgetting) but I don't know how addressable that actually is.

that's easy to fix, I'll put a pr up

#### reply nettlesh @ 2026-09-04T04:08:12Z

really happy with how https://github.com/jdx/mise/pull/12692 is looking. Modified my dots locally and everything is looking good to go. Glad we're keeping it distinct from pacman and offloading most of the work to yay/paru (and thanks for the paru fallback). Also like the decisions on package provenance and how you're handling --aur

As for AUR internals, my understanding is there isn't really much of a package "store" to replace since its essentially just the PKGBUILD/source metadata, and most of the heavy lifting is done by yay and paru to resolve the deps, building via makepkg, and then handing results to pacman. So tbh just leaning on an existing AUR helper is probably already the right call here.

The issue is really the trust model of the AUR itself and if you're looking to replace it we'd need to totally change that. stuff like curated admissions, signed provenance and attestation, and a whole lot of scanning. We can't just mirror the PKGBUILDs somewhere else since they're hiding malicious logic in them or accompanying scripts. Tbh I think if you had genuine interest in pursuing a safer alternative to the AUR I'd be in full support but it would need reimagining from the ground up. Trying to make PKGBUILDs safe is a losing battle like trying to make every bash script safe. Maybe explore if there is a way to separate declarative package metadata from all of the unsafe and arbitrary scripting a PKGBUILD allows you to do. The registry should distribute built ALPM packages, not the recipe imo. Like the right solution might be to just publish packages into an ordinary pacman compatible repo. The whole problem is execution on the client

this feels like alot of work though. If its something you want to pursue happy to help out in any way



#### reply jdx @ 2026-09-04T11:50:22Z

> Trying to make PKGBUILDs safe is a losing battle like trying to make every bash script safe.

it might be a pipe dream but I am exploring using seccomp/landlock to do exactly this, not sure how well it will work in practice though

replacing AUR isn't something I can do on my own, but I do have ideas around it that I plan to at least pitch to omarchy to see if we could work together on it. I am admittedly a bit new but I feel like one improvement would be to more natively support a tumbleweed model for tested batches of releases like OpenSUSE and NixOS do—in addition to the supply chain stuff

#### reply nettlesh @ 2026-09-04T19:01:33Z

@jdx just dropped jdx/mise#12785, in my testing of https://github.com/jdx/mise/pull/12692 I noticed it failed my hk pipeline due to the schema being outdated. Feel free to cherry-pick it for the release branch if you're good with it

Also listen, if you want to replace the AUR I'm in full support. seccomp/landlock is a good direction and absolutely worth exploring imo. Even if the isolation isn't perfect

I saw you made pacvamp but haven't gotten through all of it yet, gonna take a look today. If you can leverage some community support from Omarchy I think you could hit the ground running with this. Replacing the AUR is obviously way too big for one person but this seems like exactly the kind of thing a distro/community could realistically accomplish

Liking the tumbleweed idea, its relatively low hanging fruit and should complement the secure supply chain work nicely

#### reply jdx @ 2026-09-04T19:08:19Z

oh I would ignore pacvamp for now, I might get to it this weekend but what is there is basically just what claude came up with after I gave it a gigantic PLAN.md, I haven't looked at the code or docs much at all

### jdx @ 2026-09-09T18:43:42Z

I've opened a focused follow-up on dotfiles: [automatic history, easy restore, and optional sync for Omarchy](https://github.com/jdx/mise/discussions/13022).

It builds on the Dots plan and my [introduction to mise's dotfile history](https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/), with a concrete first step: save personal config edits automatically and let users inspect and restore them from Omarchy's config menu. It also separates what mise already does from the remaining integration and sharing decisions.

That part can move independently of the broader packages/services proposal here. Please bring dotfiles-specific feedback to the new discussion.

*AI-assisted — Tool: Codex; model: OpenAI/GPT-6; version: unavailable.*


