[Skip to content](https://yanyongyu.github.io/githubkit/installation/#installation)

# Installation [¶](https://yanyongyu.github.io/githubkit/installation/\#installation "Permanent link")

Tip

githubkit supports **both pydantic v1 and v2**, but pydantic v2 is recommended. If you have encountered any problems with pydantic v1/v2, please file an issue.

## Basic Installation [¶](https://yanyongyu.github.io/githubkit/installation/\#basic-installation "Permanent link")

[poetry](https://yanyongyu.github.io/githubkit/installation/#basic-installation-poetry)[pdm](https://yanyongyu.github.io/githubkit/installation/#basic-installation-pdm)[uv](https://yanyongyu.github.io/githubkit/installation/#basic-installation-uv)[pip](https://yanyongyu.github.io/githubkit/installation/#basic-installation-pip)

```
poetry add githubkit
```

```
pdm add githubkit
```

```
uv add githubkit
```

```
pip install githubkit
```

## GitHub Schema Versions Installation [¶](https://yanyongyu.github.io/githubkit/installation/\#github-schema-versions-installation "Permanent link")

githubkit provides versioned REST API definitions and models through the `githubkit-schemas` ecosystem.

By default, installing `githubkit` (or `githubkit-schemas`) gives you the latest stable schema version.

Calendar versioning

`githubkit-schemas` and its versioned packages follow [Calendar Versioning (CalVer)](https://calver.org/) in the format `YY.MM.PATCH` (e.g. `26.5.12`). Releases are issued whenever GitHub updates its API schemas, so the package version reflects when the schema was published rather than a semantic API stability guarantee.

### Pin Schema Versions [¶](https://yanyongyu.github.io/githubkit/installation/\#pin-schema-versions "Permanent link")

By default, `githubkit-schemas` always points to the latest stable schema, so a fresh install may pull in a newer schema than expected. Explicitly pinning the package ensures every environment uses the same schema version:

[poetry](https://yanyongyu.github.io/githubkit/installation/#pin-schema-versions-poetry)[pdm](https://yanyongyu.github.io/githubkit/installation/#pin-schema-versions-pdm)[uv](https://yanyongyu.github.io/githubkit/installation/#pin-schema-versions-uv)[pip](https://yanyongyu.github.io/githubkit/installation/#pin-schema-versions-pip)

```
poetry add 'githubkit-schemas==26.5.12'
```

```
pdm add 'githubkit-schemas==26.5.12'
```

```
uv add 'githubkit-schemas==26.5.12'
```

```
pip install 'githubkit-schemas==26.5.12'
```

### Install Extra Schema Versions [¶](https://yanyongyu.github.io/githubkit/installation/\#install-extra-schema-versions "Permanent link")

If you need an additional schema module, install the corresponding extra on `githubkit-schemas`.

- `githubkit-schemas` tracks the latest stable schema.
- `githubkit-schemas-<version>` is a concrete, version-specific package.
- `githubkit-schemas[<version>]` is a convenience extra that installs the matching `githubkit-schemas-<version>` package.

For example, to pin schema version `2022-11-28`:

[poetry](https://yanyongyu.github.io/githubkit/installation/#install-extra-schema-versions-poetry)[pdm](https://yanyongyu.github.io/githubkit/installation/#install-extra-schema-versions-pdm)[uv](https://yanyongyu.github.io/githubkit/installation/#install-extra-schema-versions-uv)[pip](https://yanyongyu.github.io/githubkit/installation/#install-extra-schema-versions-pip)

```
poetry add 'githubkit-schemas[2022-11-28]'
```

```
pdm add 'githubkit-schemas[2022-11-28]'
```

```
uv add 'githubkit-schemas[2022-11-28]'
```

```
pip install 'githubkit-schemas[2022-11-28]'
```

For GitHub Enterprise Cloud/Server compatibility schemas, use versions like `ghec-2022-11-28` in the same format.

After installation, select the schema in code with `github.rest("<schema-version>")`. See [REST API Versioning](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-versioning).

## Extra Dependencies [¶](https://yanyongyu.github.io/githubkit/installation/\#extra-dependencies "Permanent link")

If you want to auth as github app, you should install `auth-app` extra dependencies:

[poetry](https://yanyongyu.github.io/githubkit/installation/#extra-dependencies-poetry)[pdm](https://yanyongyu.github.io/githubkit/installation/#extra-dependencies-pdm)[uv](https://yanyongyu.github.io/githubkit/installation/#extra-dependencies-uv)[pip](https://yanyongyu.github.io/githubkit/installation/#extra-dependencies-pip)

```
poetry add 'githubkit[auth-app]'
```

```
pdm add 'githubkit[auth-app]'
```

```
uv add 'githubkit[auth-app]'
```

```
pip install 'githubkit[auth-app]'
```

## Full Installation [¶](https://yanyongyu.github.io/githubkit/installation/\#full-installation "Permanent link")

You can install fully featured githubkit with `all` extra dependencies:

[poetry](https://yanyongyu.github.io/githubkit/installation/#full-installation-poetry)[pdm](https://yanyongyu.github.io/githubkit/installation/#full-installation-pdm)[uv](https://yanyongyu.github.io/githubkit/installation/#full-installation-uv)[pip](https://yanyongyu.github.io/githubkit/installation/#full-installation-pip)

```
poetry add 'githubkit[all]'
```

```
pdm add 'githubkit[all]'
```

```
uv add 'githubkit[all]'
```

```
pip install 'githubkit[all]'
```

Back to top