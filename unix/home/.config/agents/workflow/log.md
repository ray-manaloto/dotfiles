# Directory Update Log

## 2026-11-04
* **Creation**: a generic rewrite of the agent workflow protocol (v1.9) for user scope: the rules,
  the chain, shipping, cross-review and the skill table. Nothing project-specific is kept.

## 2026-11-07
* **Added**: cross-review's "Waiting on the pane" section. It says to wait with `hc wait` or
  `hc send --wait`, not with a sleep loop over `hc read`, which can miss the answer. It also says to
  word a brief's limits so the pane's read-only shell stays allowed.
