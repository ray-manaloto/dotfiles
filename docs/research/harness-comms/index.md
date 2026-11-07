---
okf_version: "0.2"
---

# How Claude Code and Codex sessions talk to each other (2026-11-07)

How two Claude Code 2.1.319 sessions, two Codex 0.167.0 sessions, and a Claude session and a Codex session can
exchange messages and "done" signals through each harness's own protocol, instead of waiting on terminal screens.
Every mechanism is read from the installed version: Codex from its Rust source at tag `rust-v0.167.0` (`086ccc833b`),
Claude from the JavaScript embedded in the 2.1.319 binary. Claims are tagged VERIFIED-SOURCE, VERIFIED-LIVE or
REPORTED, and the live runs (P1, C1, C2) back the ones a design depends on.

* [Method](method.md) - how the sources were made offline and pinned, how the Claude binary was read, how the code was mapped, and how claims were confirmed live. Start here to re-run any of it.
* [Claude <-> Claude](claude-claude.md) - the inbox socket, registry, delivery policy, SendMessage, idle notices, ListAgents, teammates, `--bg`, Channels, Remote Control.
* [Codex <-> Codex](codex-codex.md) - the app-server, shared daemon and `--remote`, thread subscribers, turn start/steer/interrupt/completed, `codex queue`, hooks, multi-agent tools, exec and rollouts.
* [Dead-tab name fallthrough](dead-tab-fallthrough.md) - why a message to a closed Claude tab's name can reach its cloud copy, and how to address tabs so it can't.
* [Approval fan-out](approval-fanout.md) - why a client that joins a Codex thread also receives its approval requests, why an error reply counts as an answer, and the rules that keep the client from answering.
* [Claude <-> Codex proposals](claude-codex.md) - the options in each direction, visible tab and headless, with evidence and gaps, and the recommended pair.
* [Diagrams](diagrams.md) - components and their dependencies, and sequence diagrams for each proposal (Mermaid).
* [Update log](log.md) - what was added, corrected and left open, by date.
* [Critique](critique.md) - what the evidence does not cover, and which claims are weakest.
