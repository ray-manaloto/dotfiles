# Post by @somi\_ai

Author: Somi \- @somi\_ai
Posted: 2026\-09\-11T01:08:47\.000Z
URL: [https://x\.com/somi\_ai/status/2098217156785893857](https://x.com/somi_ai/status/2098217156785893857)
Likes: 4 | Retweets: 1

## Post

36.7%. That's the best of four code-context tools at putting every file a fix needed into its top 10. Same 60 bugs, same scoring:

1) ripwire: 36.7%
2) codebase-memory-mcp: 26.7%
3) graphify: 21.7%
4) Aider repo-map: 13.3%

So the winner still misses a needed file 6 times out of 10. The "give your agent a map of the repo" pitch isn't done. Your agent is going to grep anyway.

What got me is the evals doc. The Red Hat team behind ripwire found their own retrieval eval had been skewed by file path order for over a year and published it instead of burying it. I'd trust that number set over any launch benchmark.

Numbers and method:

## Top Comments

### 1. @ParejaAldo
Author: aldo pareja
Posted: 2026\-09\-11T02:36:18\.000Z
URL: [https://x\.com/ParejaAldo/status/2098239180224774148](https://x.com/ParejaAldo/status/2098239180224774148)

> But, does it help on downstream tasks even if the map doesn’t contain ALL the details?

Likes: 0

### 2. @itsjustnikhil
Author: Nikhil Pareek
Posted: 2026\-09\-11T13:09:02\.000Z
URL: [https://x\.com/itsjustnikhil/status/2098398411104108838](https://x.com/itsjustnikhil/status/2098398411104108838)

> The ranking changes with the task set — 60 bugs from one repo skews toward its naming conventions. The Red Hat honesty about path-order skew is more useful than the score: a team that publishes its own bias is one you can trust on the next eval too.

Likes: 0

### 3. @kartikb753
Author: kartik bhardwaj
Posted: 2026\-09\-11T04:31:00\.000Z
URL: [https://x\.com/kartikb753/status/2098268043596189986](https://x.com/kartikb753/status/2098268043596189986)

> Sixty bugs is a narrow base for separating four tools, since a couple of unusual repos can reorder the middle of the list. The ranking gets believable if the gap between first and second survives a bug level bootstrap.

Likes: 0
