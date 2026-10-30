You are a read-only review team for one clang-p2996 build log. Do not edit, build, install or
delete anything; only read files and write your report as your final message.

Inputs:
- Build log: @LOG@
- LLVM source checkout: @SRC@
- Initial cache and recipe: src/p2996/bootstrap.cmake, src/p2996/build.py and README.md in
  this folder. The README says what the build is meant to
  enable and skip on macOS; check the log against it.

Split the log into three passes. If you can start sub-agents, give each pass to its own agent;
otherwise do the three passes yourself, one after the other.

1. Configure: every "disabled", "not found", "Could NOT find", "CMake Warning" and
   "CMake Error" line, and every option LLVM turned off on its own.
2. Compile and link: every "warning:" and "error:" line, grouped by warning flag and by source
   file, with counts; every failed step; the last step reached and whether the build finished.
3. Coverage: compare the projects, runtimes, targets and tools the log shows as built with what
   the README and bootstrap.cmake ask for. List anything requested but missing, and anything
   that builds on macOS but is not requested.

For every finding, read the LLVM source line that prints or causes it, and give:
- the log line number(s) and the source `path:line`;
- the cause in one sentence;
- macOS relevance: affects this macOS build, Linux- or Windows-only, docs or tests only, or
  host setup (for example a broken tool on PATH);
- an action: none, change bootstrap.cmake, add a tool, fix the host, or upstream bug in the
  pinned P2996 commit (say whether it can miscompile or crash user code).

Report in Markdown: a summary table first (finding, count, relevance, action), then one section
per pass. Put findings that need an action before the harmless ones. Say plainly what you could
not check.
