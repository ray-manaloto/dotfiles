---
name: local-preflight
description: Run the smallest useful local validation set for this repo before pushing or after a failed CI run. Use when you need fast local checks for Docker, devcontainer, mise, hk, or Python workflow regressions. Supports standard, tool-specific, and image-specific modes.
---

# Local Preflight

## Overview

Use the plugin script to run the repo-local validation stack.

## Commands

Standard preflight:

```bash
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh
```

Tool admission check:

```bash
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh tool <tool-name>
```

Image-aware preflight:

```bash
IMAGE_REF=ghcr.io/ray-manaloto/dotfiles-devcontainer:dev \
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh image
```

## Included Checks

- `hk validate`
- `hk run pre-commit --all`
- `dotfiles-setup verify`
- `mise doctor`
- optional `mise test-tool`
- optional image smoke and benchmark
---
name: local-preflight
description: Run the smallest useful local validation set for this repo before pushing or after a failed CI run. Use when you need fast local checks for Docker, devcontainer, mise, hk, or Python workflow regressions. Supports standard, tool-specific, and image-specific modes.
---

# Local Preflight

## Overview

Use the plugin script to run the repo-local validation stack.

## Commands

Standard preflight:

```bash
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh
```

Tool admission check:

```bash
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh tool <tool-name>
```

Image-aware preflight:

```bash
IMAGE_REF=ghcr.io/ray-manaloto/dotfiles-devcontainer:dev \
plugins/dotfiles-build-optimizer/scripts/local_preflight.sh image
```

## Included Checks

- `hk validate`
- `hk run pre-commit --all`
- `dotfiles-setup verify`
- `mise doctor`
- optional `mise test-tool`
- optional image smoke and benchmark
