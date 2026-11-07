---
okf_version: "0.2"
type: "glossary"
title: "Terms"
description: "The words this bundle and jbctl/jbax use for how an IDE is reached and named."
resource: "python/jbctl and swift/"
version: "2026-11-06"
timestamp: "2026-11-06T03:00:00Z"
status: "draft"
stale_after: "2026-12-06T00:00:00Z"
tags: [glossary, jbctl, jbax]
---

# Terms

**Headless run**:
A run in which no step brings the IDE forward or takes the front app from the person at the machine. The
IDE may show a window, but it stays behind. agent-desktop's `--headed` flag is a different, narrower thing.
_Avoid_: headless (for an IDE launched with no UI at all).

**Debug route**:
Opening Settings from the menu bar, which brings the IDE forward. It is only for debugging a failed
headless route, and only with `JETBRAINS_FOREGROUND=1` (mise `--foreground`).
_Avoid_: headed test, foreground test.

**Station route**:
Opening Settings in the background through the IDE's station socket, which leaves the front app as it was.

**Toolbox script name**:
How `--ide` names one install: the shell-script name Toolbox gives it (`clion`, `clion1`, `pycharm`). It
names an install, not a product: several installs of one product get numbered names.
_Avoid_: product name, app name.
