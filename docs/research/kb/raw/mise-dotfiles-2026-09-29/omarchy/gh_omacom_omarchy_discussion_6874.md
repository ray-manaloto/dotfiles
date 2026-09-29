# [Suggestion] Have omarchy-mise-install check for already-installed tools

- URL: https://github.com/omacom/omarchy/discussions/6874
- author: rholak created: 2026-08-14T15:51:52Z

## Body

When I installed Quattro, the `omarchy-mise-install` tool forced all my currently installed agents to be replaced with mise-managed versions, some of which were out of date due to mise's release-lag policy. I stopped using mise a while back to manage agents specifically because of this. 
Right now I can partially fix it via something in my mise config.toml like:

```toml
[tools.pi]
version = "latest"
minimum_release_age = "0s"
```
But it would have been nice if `omarchy-mise-install` had an option to check for manually installed packages and prompt to replace them with mise management. Or just skip replacing already-installed tools to avoid too many interactive prompts during install.
It could also add a --force option to bypass this check.

## Comments
### rholak @ 2026-08-14T16:01:58Z

I do see that `omarchy update` and the `mup` alias partially help by reducing the mise release lag time, but that still relies on the mise infrastructure to be up to date.

