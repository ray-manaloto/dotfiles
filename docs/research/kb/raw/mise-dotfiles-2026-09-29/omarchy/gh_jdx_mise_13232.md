# docs(dotfiles): explain encryption key setup and first-adoption conflicts

- URL: https://github.com/jdx/mise/pull/13232
- state: closed | author: jdx | created: 2026-09-15T14:03:53Z | closed: 2026-09-15T15:48:07Z | merged_pr: 2026-09-15T15:48:06Z
- labels: 

## Body

Setting up encryption for shared dotfiles meant guessing. The configuration
example was all placeholders:

```toml
[history.encryption]
recipients = ["<age-or-plugin-public-recipient>", "<recovery-public-recipient>"]
```

Nothing said what a recipient string looks like, how to produce one, or what
the "recovery" one is for — and `dotfiles.md` pointed at that section "for key
setup" that was not there. This came up in
[an Omarchy discussion](https://github.com/omacom/omarchy/discussions/11029#discussioncomment-18450136)
from someone who had just set up desktop↔laptop sync with an encrypted file and
worked it out the hard way.

## Encryption key setup

A new **Choose recipients** section documents the recipient forms mise already
accepts, then walks through each way to get one:

- **An existing SSH public key works as a recipient**, and mise already reads
  `~/.ssh/id_ed25519` as the matching identity. For most people this is the
  whole setup, and it was previously undocumented.
- Generating a dedicated age key with `age-keygen`, including installing the
  age CLI through mise.
- Generating a recovery recipient, storing it in a password manager, and
  removing the local copy.

Two failure modes that are easy to hit get explicit warnings:

- **A passphrase-protected SSH key cannot decrypt history.** mise does not
  prompt for the passphrase, and an SSH agent does not help — which is
  surprising next to the repository-authentication guidance, where a
  passphrase-protected key in an agent is the recommended choice.
- **A plugin-only recipient list (`age1yubikey1...`) stops automatic saving.**
  Plugin recipients need an interactive terminal and the watcher runs in the
  background.

It also states what changing `recipients` does: files are re-encrypted on their
next save, while commits already in history keep the recipients they were
written with, so a machine added later cannot read older versions.

## Adopting onto a machine that already has the files

A second machine usually already has a `~/.bashrc`. mise holds each file that
differs for a decision and stops the adoption — deliberately, so nothing is
overwritten — but the guide only described conflicts as "if two machines change
the same lines", which is the *ongoing sync* case, not this one.

`Set up another machine` now covers it: what the paused message means, how to
resolve it, that moving files aside beforehand avoids the decisions entirely,
and that `--replace-history` and `--force-dotfiles` are not the fix (the first
replaces history rather than differing files; the second applies to `[dotfiles]`
link and copy targets).

## Any Git host

Sharing works with any Git URL, but every example was GitHub, which reads as a
requirement. Added a self-hosted example for `mise dot origin set` and
`mise bootstrap --adopt`, and noted that `OWNER/REPO` is GitHub shorthand while
credentials belong in an SSH agent or a credential helper rather than the URL.

Documentation only; no behavior changes.

*AI-assisted — Tool: Claude Code; model: Anthropic/claude-opus-5; version: unavailable.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)

<!-- CURSOR_SUMMARY -->
---

> [!NOTE]
> **Low Risk**
> Markdown documentation updates only; no application code or configuration defaults changed.
> 
> **Overview**
> **Documentation-only** expansion for dotfile history, bootstrap adoption, and encryption setup—no runtime behavior changes.
> 
> **Encrypted shared files:** Adds a **Choose recipients** section in `history.md` that documents accepted recipient forms (age, SSH public key, tagged age, plugins), default identity discovery paths, and step-by-step flows for reusing a passphrase-free SSH key, generating `age-keygen` keys via mise, and adding an offline recovery recipient. It calls out that passphrase-protected SSH keys cannot decrypt history (unlike Git SSH auth), that missing recipients fail pulls with `cannot unlock`, how changing `recipients` re-encrypts on next save while old commits keep prior recipients, and that plugin/YubiKey recipients break background watcher saves. `dotfiles.md` now links to this section for key setup.
> 
> **Second-machine bootstrap:** `setup.md` explains that `mise bootstrap --adopt` pauses when existing paths differ (expected, not failure), how to resolve with `mise dot status` / `pull --take-remote` or `save` + `--keep-local`, finishing with `mise bootstrap`, and a tip to move conflicting files aside to skip decisions. It clarifies `--replace-history` and `--force-dotfiles` do not resolve this case.
> 
> **Remotes:** Examples and notes that any Git URL works (e.g. Gitea SSH), `OWNER/REPO` is GitHub shorthand, and credentials must not be embedded in the URL.
> 
> <sup>Reviewed by [Cursor Bugbot](https://cursor.com/bugbot) for commit fd382510c27873b3df547b5cfa674fcea6577ac4. Bugbot is set up for automated code reviews on this repo. Configure [here](https://www.cursor.com/dashboard/bugbot).</sup>
<!-- /CURSOR_SUMMARY -->

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

* **Documentation**
  * Clarified setup steps for machines that already contain dotfiles, including how to handle matching and conflicting files.
  * Documented supported Git URL formats and authentication requirements across hosting providers.
  * Expanded encrypted shared-file guidance with recipient types, key discovery, key generation, recovery recipients, multi-machine examples, and re-encryption behavior.
  * Added clearer references for configuring encryption keys and understanding plaintext history limitations.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

## Comments

### coderabbitai[bot] @ 2026-09-15T14:04:18Z

<!-- This is an auto-generated comment: summarize by coderabbit.ai -->
<!-- review_stack_entry_start -->

<a href="https://app.coderabbit.ai/change-stack/jdx/mise/pull/13232#gh-light-mode-only"><img src="https://storage.googleapis.com/coderabbit_public_assets/review-stack-in-coderabbit-ui.svg" alt="Review Change Stack" width="202" height="32"></a><a href="https://app.coderabbit.ai/change-stack/jdx/mise/pull/13232#gh-dark-mode-only"><img src="https://storage.googleapis.com/coderabbit_public_assets/review-stack-in-coderabbit-ui-dark.svg" alt="Review Change Stack" width="202" height="32"></a>

<!-- review_stack_entry_end -->
<!-- This is an auto-generated comment: rate limited by coderabbit.ai -->

> [!WARNING]
> ## Review limit reached
> 
> **Next included review available in 9 minutes.**
> 
> [Check out review usage here](https://app.coderabbit.ai/dashboard/review-capacity?orgId=c3e7bb69-7173-4487-8370-853f882286f8).
> 
> <details>
> <summary>View limit details</summary>
> 
> **Limit details:** You’ve used all 10 included reviews currently available.
> 
> You've used all free OSS reviews for now. Wait for the free limit to reset to keep reviewing this public repository.
> 
> [Learn how review limits work](https://docs.coderabbit.ai/management/plans#rate-limits).
> 
> **Review configuration:**
> 
> <details>
> <summary>⚙️ Run configuration</summary>
> 
> **Configuration used**: Repository YAML (base), Central YAML (inherited), Organization UI (inherited)
> 
> **Review profile**: CHILL
> 
> **Plan**: Advanced
> 
> **Run ID**: `c2e77a91-0ffb-4b76-bbab-16d02bd6b1b2`
> 
> </details>
> 
> <details>
> <summary>📥 Commits</summary>
> 
> Reviewing files that changed from the base of the PR and between c9a9edee4c27a15e6fdecf87dcbf681f55cf8496 and fd382510c27873b3df547b5cfa674fcea6577ac4.
> 
> </details>
> 
> <details>
> <summary>📒 Files selected for processing (1)</summary>
> 
> * `docs/history.md`
> 
> </details>
> 
> </details>

<!-- end of auto-generated comment: rate limited by coderabbit.ai -->

<!-- recent_review_start -->

No actionable comments were generated in the recent review. 🎉

<details>
<summary>ℹ️ Recent review info</summary>

<details>
<summary>⚙️ Run configuration</summary>

**Configuration used**: Repository YAML (base), Central YAML (inherited), Organization UI (inherited)

**Review profile**: CHILL

**Plan**: Advanced

**Run ID**: `c1ad4585-8935-44a1-9cbd-e64ce53718ed`

</details>

<details>
<summary>📥 Commits</summary>

Reviewing files that changed from the base of the PR and between 204aadc1d1ac7d9103711da7ec7f5e96fd5e0bbe and c9a9edee4c27a15e6fdecf87dcbf681f55cf8496.

</details>

<details>
<summary>📒 Files selected for processing (3)</summary>

* `docs/bootstrap/setup.md`
* `docs/dotfiles.md`
* `docs/history.md`

</details>

**Included review availability:** Your plan provides up to 10 included reviews per hour; 0 remain after this review.

</details>

---



<!-- recent_review_end -->
<!-- walkthrough_start -->

<details>
<summary>📝 Walkthrough</summary>

## Walkthrough

The documentation updates define Git remote requirements, describe existing-file adoption and conflict resolution, and expand encrypted dotfiles guidance for recipient selection, key discovery, recovery, and re-encryption.

### Changes

**Dotfiles documentation**

|Layer / File(s)|Summary|
|---|---|
|**Remote and existing-file guidance** <br> `docs/bootstrap/setup.md`, `docs/history.md`|The documentation supports Git URLs from self-hosted hosts without embedded credentials, query strings, or fragments. It explains matching-file adoption, differing-file stops, and the `mise dot pull` resolution options.|
|**Encryption recipient guidance** <br> `docs/dotfiles.md`, `docs/history.md`|The documentation separates key generation from plaintext-history limits and adds recipient formats, private-key locations, overrides, recovery recipients, multi-machine configuration, re-encryption, and plugin-only recipient behavior.|

<!-- change_assessment_start -->
**Priority:** ⚪ Pending latest changes





**Estimated code review effort:** 1 (Trivial) | ~5 minutes

<!-- change_assessment_commit:"c9a9edee4c27a15e6fdecf87dcbf681f55cf8496" -->
**Change:** Other
<!-- change_assessment_end -->

</details>

<!-- walkthrough_end -->
<!-- final_review_risk_start -->
**Merge Risk:** _⚪ Minimal_ · up to `c9a9e`
<!-- final_review_risk_coverage:{"sourceCommitId":"c9a9edee4c27a15e6fdecf87dcbf681f55cf8496","coveredCommitId":"c9a9edee4c27a15e6fdecf87dcbf681f55cf8496","kind":"reviewed"} -->

This documentation-only change matches the supplied CLI and encryption contracts, with no concrete merge-blocking risk remaining.
<!-- final_review_risk_end -->
<!-- pre_merge_checks_walkthrough_start -->

<details>
<summary>🚥 Pre-merge checks | ✅ 5</summary>

<details>
<summary>✅ Passed checks (5 passed)</summary>

|         Check name         | Status   | Explanation                                                                                                                                                                                               |
| :------------------------: | :------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|      Description Check     | ✅ Passed | Check skipped - CodeRabbit’s high-level summary is enabled.                                                                                                                                               |
|         Title check        | ✅ Passed | The title clearly summarizes the two main documentation changes: encryption key setup and conflicts during first adoption of dotfiles.                                                                    |
|     Docstring Coverage     | ✅ Passed | No functions found in the changed files to evaluate docstring coverage. Skipping docstring coverage check. Docstring coverage is scoped to functions touched by this diff. Analyzed 0 functions across 0… |
|     Linked Issues check    | ✅ Passed | Check skipped because no linked issues were found for this pull request.                                                                                                                                  |
| Out of Scope Changes check | ✅ Passed | Check skipped because no linked issues were found for this pull request.                                                                                                                                  |

</details>

</details>

<!-- pre_merge_checks_walkthrough_end -->
<!-- tips_start -->

---

Thanks for using [CodeRabbit](https://coderabbit.ai?utm_source=oss&utm_medium=github&utm_campaign=jdx/mise&utm_content=13232)! It's free for OSS, and your support helps us grow. If you like it, consider giving us a shout-out.

<details>
<summary>❤️ Share</summary>

- [X](https://twitter.com/intent/tweet?text=I%20just%20used%20%40coderabbitai%20for%20my%20code%20review%2C%20and%20it%27s%20fantastic%21%20It%27s%20free%20for%20OSS%20and%20offers%20a%20free%20trial%20for%20the%20proprietary%20code.%20Check%20it%20out%3A&url=https%3A//coderabbit.ai)
- [Mastodon](https://mastodon.social/share?text=I%20just%20used%20%40coderabbitai%20for%20my%20code%20review%2C%20and%20it%27s%20fantastic%21%20It%27s%20free%20for%20OSS%20and%20offers%20a%20free%20trial%20for%20the%20proprietary%20code.%20Check%20it%20out%3A%20https%3A%2F%2Fcoderabbit.ai)
- [Reddit](https://www.reddit.com/submit?title=Great%20tool%20for%20code%20review%20-%20CodeRabbit&text=I%20just%20used%20CodeRabbit%20for%20my%20code%20review%2C%20and%20it%27s%20fantastic%21%20It%27s%20free%20for%20OSS%20and%20offers%20a%20free%20trial%20for%20proprietary%20code.%20Check%20it%20out%3A%20https%3A//coderabbit.ai)
- [LinkedIn](https://www.linkedin.com/sharing/share-offsite/?url=https%3A%2F%2Fcoderabbit.ai&mini=true&title=Great%20tool%20for%20code%20review%20-%20CodeRabbit&summary=I%20just%20used%20CodeRabbit%20for%20my%20code%20review%2C%20and%20it%27s%20fantastic%21%20It%27s%20free%20for%20OSS%20and%20offers%20a%20free%20trial%20for%20proprietary%20code)

</details>


<sub>Comment `@coderabbitai help` to get the list of available commands.</sub>

<!-- tips_end -->

### greptile-apps[bot] @ 2026-09-15T14:07:21Z

<!-- greptile_summary -->

<h2><a href="https://app.greptile.com/api/retrigger?id=64465956"><picture><source media="(prefers-color-scheme: dark)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/RetriggerDark.svg?v=2"><source media="(prefers-color-scheme: light)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2"><img alt="Retrigger" src="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2" align="right"></picture></a>Confidence Score: 5/5</h2>

The documentation-only PR appears safe to merge, with both previous findings fully addressed and no new actionable issues identified.

<h3>Summary</h3>

Expands the shared-dotfiles documentation with:
- Encryption recipient setup, identity discovery, recovery keys, and watcher limitations.
- Conflict-resolution guidance when adopting history on a machine with existing files.
- Examples and authentication guidance for non-GitHub Git remotes.
- Follow-up wording that fully addresses both previous review findings.

<sub>Reviews (2) · Last reviewed commit: ["docs(dotfiles): correct two encryption c..."](https://github.com/jdx/mise/commit/fd382510c27873b3df547b5cfa674fcea6577ac4)</sub>

## Review comments

### greptile-apps[bot] @ docs/history.md:621

<a href="#"><img alt="P2" src="https://greptile-static-assets.s3.amazonaws.com/badges/p2.svg?v=9" align="top"></a> Adding one native age or SSH recipient does not make a mixed recipient list safe for the background watcher. Noninteractive encryption parses every recipient and rejects any plugin recipient, so a list that also contains `age1yubikey1...` still stops automatic saving. The warning should make clear that watcher encryption cannot include plugin-dependent recipients.

```suggestion
::: warning
Plugin recipients such as `age1yubikey1...` require an interactive terminal.
The history watcher runs in the background, so any recipient list containing a
plugin recipient stops automatic saving with `plugin-dependent age recipients
require interactive synchronization`. Use only age or SSH recipients for files
saved by the watcher.
:::
```

**Knowledge Base Used:** [Dotfile lifecycle and synchronization](https://app.greptile.com/jdx-org/-/custom-context/knowledge-base/jdx/mise/-/docs/dotfile-lifecycle-and-synchronization.md)

<a href="https://app.greptile.com/ide/claude-code?prompt=This%20is%20a%20comment%20left%20during%20a%20code%20review.%0APath%3A%20docs%2Fhistory.md%0ALine%3A%20613-618%0A%0AComment%3A%0AAdding%20one%20native%20age%20or%20SSH%20recipient%20does%20not%20make%20a%20mixed%20recipient%20list%20safe%20for%20the%20background%20watcher.%20Noninteractive%20encryption%20parses%20every%20recipient%20and%20rejects%20any%20plugin%20recipient%2C%20so%20a%20list%20that%20also%20contains%20%60age1yubikey1...%60%20still%20stops%20automatic%20saving.%20The%20warning%20should%20make%20clear%20that%20watcher%20encryption%20cannot%20include%20plugin-dependent%20recipients.%0A%0A%60%60%60suggestion%0A%3A%3A%3A%20warning%0APlugin%20recipients%20such%20as%20%60age1yubikey1...%60%20require%20an%20interactive%20terminal.%0AThe%20history%20watcher%20runs%20in%20the%20background%2C%20so%20any%20recipient%20list%20containing%20a%0Aplugin%20recipient%20stops%20automatic%20saving%20with%20%60plugin-dependent%20age%20recipients%0Arequire%20interactive%20synchronization%60.%20Use%20only%20age%20or%20SSH%20recipients%20for%20files%0Asaved%20by%20the%20watcher.%0A%3A%3A%3A%0A%60%60%60%0A%0A**Knowledge%20Base%20Used%3A**%20%5BDotfile%20lifecycle%20and%20synchronization%5D%28https%3A%2F%2Fapp.greptile.com%2Fjdx-org%2F-%2Fcustom-context%2Fknowledge-base%2Fjdx%2Fmise%2F-%2Fdocs%2Fdotfile-lifecycle-and-synchronization.md%29%0A%0A---%0A%0AFor%20each%20issue%20above%2C%20determine%20whether%20it%20is%20valid%20and%20should%20be%20fixed.%20If%20so%2C%20fix%20it%20directly.&repo=jdx%2Fmise&pr=13232&platform=github"><picture><source media="(prefers-color-scheme: dark)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaudeDark.svg?v=7"><source media="(prefers-color-scheme: light)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaude.svg?v=7"><img alt="Fix in Claude Code" src="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaude.svg?v=7"></picture></a>

### greptile-apps[bot] @ docs/history.md:0

<a href="#"><img alt="P2" src="https://greptile-static-assets.s3.amazonaws.com/badges/p2.svg?v=9" align="top"></a> A machine without a matching identity can transfer encrypted Git objects, but it cannot necessarily complete `mise dot pull`. Pull reconciliation and application decrypt encrypted files and fail when no identity can unlock them, so describing the machine as still able to “push and pull” may lead users to expect synchronization or adoption to complete.

```suggestion
Repeat this on each machine and add every public key to `recipients`. A machine
whose recipient is missing can still transfer the encrypted Git history, but it
cannot read the encrypted files or complete a pull that must inspect or apply
them.
```

**Knowledge Base Used:** [Dotfile lifecycle and synchronization](https://app.greptile.com/jdx-org/-/custom-context/knowledge-base/jdx/mise/-/docs/dotfile-lifecycle-and-synchronization.md)

Note: If this suggestion doesn't match your team's coding style, reply to this and let me know. I'll remember it for next time!

<a href="https://app.greptile.com/ide/claude-code?prompt=This%20is%20a%20comment%20left%20during%20a%20code%20review.%0APath%3A%20docs%2Fhistory.md%0ALine%3A%20570-572%0A%0AComment%3A%0AA%20machine%20without%20a%20matching%20identity%20can%20transfer%20encrypted%20Git%20objects%2C%20but%20it%20cannot%20necessarily%20complete%20%60mise%20dot%20pull%60.%20Pull%20reconciliation%20and%20application%20decrypt%20encrypted%20files%20and%20fail%20when%20no%20identity%20can%20unlock%20them%2C%20so%20describing%20the%20machine%20as%20still%20able%20to%20%E2%80%9Cpush%20and%20pull%E2%80%9D%20may%20lead%20users%20to%20expect%20synchronization%20or%20adoption%20to%20complete.%0A%0A%60%60%60suggestion%0ARepeat%20this%20on%20each%20machine%20and%20add%20every%20public%20key%20to%20%60recipients%60.%20A%20machine%0Awhose%20recipient%20is%20missing%20can%20still%20transfer%20the%20encrypted%20Git%20history%2C%20but%20it%0Acannot%20read%20the%20encrypted%20files%20or%20complete%20a%20pull%20that%20must%20inspect%20or%20apply%0Athem.%0A%60%60%60%0A%0A**Knowledge%20Base%20Used%3A**%20%5BDotfile%20lifecycle%20and%20synchronization%5D%28https%3A%2F%2Fapp.greptile.com%2Fjdx-org%2F-%2Fcustom-context%2Fknowledge-base%2Fjdx%2Fmise%2F-%2Fdocs%2Fdotfile-lifecycle-and-synchronization.md%29%0A%0A---%0A%0AFor%20each%20issue%20above%2C%20determine%20whether%20it%20is%20valid%20and%20should%20be%20fixed.%20If%20so%2C%20fix%20it%20directly.&repo=jdx%2Fmise&pr=13232&platform=github"><picture><source media="(prefers-color-scheme: dark)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaudeDark.svg?v=7"><source media="(prefers-color-scheme: light)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaude.svg?v=7"><img alt="Fix in Claude Code" src="https://greptile-static-assets.s3.amazonaws.com/badges/FixInClaude.svg?v=7"></picture></a>

### jdx @ docs/history.md:621

Correct, and the wording was wrong: `preimages.rs` collects the parsed recipients with `collect::<Result<Vec<_>>>()?`, so one plugin recipient fails the whole list non-interactively. Reworded to say any plugin recipient stops the watcher and that adding a native recipient alongside it does not help.

_🤖 Addressed by [Claude Code](https://claude.com/claude-code)_

### jdx @ docs/history.md:0

Agreed — `files::decrypt` propagates `cannot unlock <path>` up through reconciliation rather than skipping the file. Reworded to say such a machine can transfer the encrypted history but a pull that must inspect or apply one of those files fails.

_🤖 Addressed by [Claude Code](https://claude.com/claude-code)_

## Reviews

### greptile-apps[bot] APPROVED

<!-- greptile-auto-approve {"codeReviewId":"24479858","correlationId":"f5fc3247-6d51-4150-ad21-19b33dfad864","headSha":"fd382510c27873b3df547b5cfa674fcea6577ac4"} -->

## Files
- docs/bootstrap/setup.md +55/-2
- docs/dotfiles.md +3/-2
- docs/history.md +120/-3
