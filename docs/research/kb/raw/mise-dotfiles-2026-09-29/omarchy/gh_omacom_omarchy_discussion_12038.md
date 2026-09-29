# Preference sharing: a manual first slice of the dots plan

https://github.com/omacom/omarchy/discussions/12038

I use several Omarchy machines and want to share preferences without copying hardware configuration or making my home directory a Git worktree.

I have separated preference sharing from session restoration and file backup. [PR #12037](https://github.com/omacom/omarchy/pull/12037) is a concrete first slice of `plans/dots.md`: an audited shared/local manifest, a private bare repository, local recovery history, and explicit publish/pull through Setup > Preferences and System > Preferences. Automatic timer snapshots and update hooks are deferred.

There is one design choice on which I would especially appreciate maintainer direction: the plan describes a remote-wins fallback for conflicting changes. This implementation keeps a persistent pending update and asks the user to choose between this machine and the shared version before continuing. It preserves both sides and refuses to overwrite edits made during review, at the cost of another interaction.

Would you prefer that explicit conflict choice for the first version, or the plan's remote-wins behavior with the local version preserved in recovery history? The PR includes real two-machine Git tests and screenshots from the exercised conflict picker, so the behavior is reviewable.

The separate [session PR #10353](https://github.com/omacom/omarchy/pull/10353) is now opt-in and limited to supported applications and numbered workspaces. For backups, I am building on [#7814](https://github.com/omacom/omarchy/pull/7814) and contributing recovery/setup fixes to its author's branch instead of proposing another backend. The integrated preview remains available in [my fork](https://github.com/jordanhubbard/omarchy).


## Comments

