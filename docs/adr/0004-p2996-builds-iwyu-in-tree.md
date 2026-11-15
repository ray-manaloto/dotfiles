---
status: accepted
---

# p2996 builds include-what-you-use in the LLVM tree, at a pinned commit

Every p2996 build also builds include-what-you-use (IWYU) as an LLVM external project
(`LLVM_EXTERNAL_PROJECTS=iwyu`), from a checkout at `P2996_IWYU_COMMIT`. The install puts it in the
prefix, and the view links it as `include-what-you-use-p2996`, `fix_includes.py-p2996` and
`iwyu_tool.py-p2996`. The owner asked for this through the cpp-standard lead on 2026-11-15: a hand
install into one prefix is lost at the next build.

IWYU has a branch per LLVM major (`clang_21` for p2996's LLVM 21), and its source is not hashed by the
build id: its folder sits in the cache, which the id leaves out. So the id counts the commit itself,
and the commit is pinned rather than read from a branch head, so a push to `clang_21` cannot change
what a build id means.

Move the pin when `P2996_BRANCH` reaches a new LLVM major: point it at the head of that `clang_NN`
branch. Until then a build fails, the previous install stays active, and the error names both
commits.

## Considered options

- **Out-of-tree after each install**, against the prefix's CMake exports. A second build and install
  step outside the id, and the prefix changes after verify. Rejected.
- **Homebrew's include-what-you-use.** Built against Homebrew's LLVM, so it cannot parse p2996's
  reflection syntax (`^^`, splices). The global mise config keeps it for other projects.
- **In-tree, as chosen.** One configure, one install, and Skia builds its clang the same way
  (`infra/bots/assets/clang_ubuntu_noble/Dockerfile`, `LLVM_EXTERNAL_PROJECTS=iwyu`). The cost: an IWYU
  that no longer compiles stops the p2996 build until the pin moves.
