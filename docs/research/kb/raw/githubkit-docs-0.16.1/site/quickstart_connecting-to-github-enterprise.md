[Skip to content](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/#connecting-to-github-enterprise)

# Connecting to GitHub Enterprise [¶](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/\#connecting-to-github-enterprise "Permanent link")

Connecting to GitHub Enterprise is similar to using the public GitHub API, but requires two specific configurations. Each is explained below with brief guidance and examples.

## Provide the server API endpoint [¶](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/\#provide-the-server-api-endpoint "Permanent link")

When connecting to a GitHub Enterprise Server (GHES or GHEC), you must set the server's REST API endpoint via the `base_url` parameter when creating the client. Use the full API base URL for your instance (for example `https://example.ghe.com/api/v3/`). githubkit will ensure the trailing slash is present.

This tells the client where to send REST and GraphQL requests rather than the public GitHub endpoints.

```
from githubkit import GitHub
from githubkit_schemas.latest.models import PublicUser, PrivateUser

github = GitHub("<your_token_here>", base_url="https://example.ghe.com/api/v3/")
```

## Switch the REST API schema version [¶](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/\#switch-the-rest-api-schema-version "Permanent link")

GitHub Enterprise Server may require a different REST API schema/version than the public API. Use the `rest("<schema-version>")` selector on the client to choose the correct REST schema for your server (for example `ghec-2022-11-28`). Picking the right schema ensures endpoint signatures match your server version and provides autocompletion support in your IDE.

The examples below demonstrate how to use both REST API and GraphQL API calls:

[Sync](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/#switch-the-rest-api-schema-version-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/connecting-to-github-enterprise/#switch-the-rest-api-schema-version-async)

```
# Call the GitHub REST API with a specific schema version
resp = github.rest("ghec-2022-11-28").users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# Call the GitHub GraphQL API
data: dict = github.graphql("{ viewer { login } }")
```

```
# Call the GitHub REST API with a specific schema version
resp = await github.rest("ghec-2022-11-28").users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# Call the GitHub GraphQL API
data: dict = await github.async_graphql("{ viewer { login } }")
```

For more information, see [REST API Versioning](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-versioning).

Back to top