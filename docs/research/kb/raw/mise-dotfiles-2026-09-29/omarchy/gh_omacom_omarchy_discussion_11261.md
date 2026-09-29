# May be `vcsh` is a good framework for dots.

- URL: https://github.com/omacom/omarchy/discussions/11261
- author: eloyesp (NONE) created: 2026-09-11T02:39:15Z upvotes: 1
- fetched: 2026-09-29 via gh api graphql (lane X)

## Body

I've just been reading the [dots](/omacom/omarchy/blob/quattro/plans/dots.md) plan, and made me read about the usage of bare git repositories for dotfiles. While reading that I've found [vcsh](https://github.com/RichiH/vcsh) that I think might be a good "framework" to implement dots, but adding more flexibility.

I can think on the following example, one user have both a desktop and a [server](/omacom/omarchy/blob/quattro/plans/server.md), `vcsh` makes it possible to sync the sharable parts of the dotfiles between both like bash aliases, while ignoring the rest.

Also, this allows thinking omarchy as a pack of plugins that work well together (like an omakase menu), but making it possible to replace parts, so a user might replace one dot with an alternative dot, making the plugin easier to maintain.

Hope this helps.

## Comments

