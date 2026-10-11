Before reporting “X does not exist,” you must:

- Run **the same probe against something known to exist**. For grep, use a known-present term in the same corpus with the same command shape.
- Remove search bounds or prove the target falls within them.
- Distinguish an actual negative from redirects, timeouts, or parsing failures.
- Report which control arm you ran and its result.
- Cross-check surprising results through a second route before reporting them.

Source: [.claude/rules/probes-need-a-control-arm.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/probes-need-a-control-arm.md:51), rules 1, 3, 4, 5, and 7.