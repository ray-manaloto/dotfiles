---
name: secrets
description: Add, update, delete or list Doppler secrets in dotfiles/dev_personal, and check the Keychain, fnox and Doppler setup, through the mise secret tasks. Use for any Doppler secret change, never the web dashboard.
---

Global mise tasks, from any folder. Each is a one-line doppler CLI call on dotfiles/dev_personal; none prints a
value.

- `pbpaste | mise run secret:set NAME`: adds NAME from stdin. It refuses a name Doppler already has;
  `secret:set --replace NAME` changes an existing one.
- `secret:delete NAME...`: deletes those names. Ask the owner for a yes on the exact names first.
- `secret:list`: the names in dotfiles/dev_personal.
- `secret:doctor`: the fnox and Doppler checks (dotfiles doctor/mise.toml), each pass or fail.

Never `fnox set` on the doppler provider, and never put a value in an argument.
