# Directory Update Log

## 2026-11-04
* **Decision**: the upgrade automation is dropped. Upgrades stay manual (`upgrades.md`); ADR 0001 is
  superseded and spec #412's tickets are closed as wontfix.
* **Design**: the upgrade automation is agreed (ADR 0001) after a grill with the owner and an adversarial Codex
  review over five revisions: a PR that touches nothing live (check, trial, review, accept, prepare), then a
  separate apply PR.
* **Correction**: `install --skip-binary --reset-indexes -y` keeps every index; the earlier note said it deletes
  them. Only a successful reset install without `--skip-binary` deletes them (cli.c:11192-11195 return
  before the deletion at :11222-11229).

## 2026-11-03
* **Creation**: CBM 0.12.1 installed at user scope for Claude Code and Codex through mise and the new `//cbm:install`
  task, after three adversarial Codex reviews (install proposal, upgrade automation, completed install). The old
  0.11.0 setup of another repository was retired. Research covered the v0.12.1 source, mise 2026.11.0 source,
  public setups found by 73 GitHub searches (75 saved; 2 are watch rows for later runs), and web reports on token cost.
* **Deferred**: the hook token A/B test, upgrade automation (its own PR), and Antigravity and OpenCode setup.
