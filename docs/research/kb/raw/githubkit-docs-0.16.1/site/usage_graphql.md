[Skip to content](https://yanyongyu.github.io/githubkit/usage/graphql/#calling-graphql-api)

# Calling GraphQL API [¶](https://yanyongyu.github.io/githubkit/usage/graphql/\#calling-graphql-api "Permanent link")

The GitHub GraphQL API offers flexibility and the ability to define precisely the data you want to fetch. See the [GitHub GraphQL API documentation](https://docs.github.com/en/graphql) for more information.

## The Basics [¶](https://yanyongyu.github.io/githubkit/usage/graphql/\#the-basics "Permanent link")

Before calling the GraphQL API, you could create your query from the [GitHub GraphQL Explorer](https://docs.github.com/en/graphql/overview/explorer). For example, to get current login user:

```
query = """
{
  viewer {
    login
  }
}
"""
```

Then, you can call the GraphQL API with the query:

[Sync](https://yanyongyu.github.io/githubkit/usage/graphql/#the-basics-sync)[Async](https://yanyongyu.github.io/githubkit/usage/graphql/#the-basics-async)

```
data: dict[str, Any] = github.graphql(query)
user_login: str = data["viewer"]["login"]
```

```
data: dict[str, Any] = await github.async_graphql(query)
user_login: str = data["viewer"]["login"]
```

Calling GraphQL API with variables:

[Sync](https://yanyongyu.github.io/githubkit/usage/graphql/#the-basics-sync_1)[Async](https://yanyongyu.github.io/githubkit/usage/graphql/#the-basics-async_1)

```
query = """
query ($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    name
  }
}
"""

data: dict[str, Any] = github.graphql(
    query, variables={"owner": "owner", "repo": "repo"}
)
repo_name: str = data["repository"]["name"]
```

```
query = """
query ($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    name
  }
}
"""

data: dict[str, Any] = await github.async_graphql(
    query, variables={"owner": "owner", "repo": "repo"}
)
repo_name: str = data["repository"]["name"]
```

## GraphQL Pagination [¶](https://yanyongyu.github.io/githubkit/usage/graphql/\#graphql-pagination "Permanent link")

githubkit also provides a helper function to paginate the GraphQL API.

First, You must accept a `cursor` parameter and return a `pageInfo` object in your query. For example:

```
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 10, after: $cursor) {
      nodes {
        number
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

The `pageInfo` object in your query must be one of the following types depending on the direction of the pagination:

For forward pagination, use:

```
pageInfo {
  hasNextPage
  endCursor
}
```

For backward pagination, use:

```
pageInfo {
  hasPreviousPage
  startCursor
}
```

If you provide all 4 properties in a `pageInfo`, githubkit will default to **forward pagination**.

Then, you can iterate over the paginated results by using the graphql `paginate` method:

[Sync](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-sync)[Async](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-async)

```
for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo"}
):
    print(result)
```

```
async for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo"}
):
    print(result)
```

Note that the `result` is a dict containing the list of nodes/edges for each page and the `pageInfo` object. You should iterate over the `nodes` or `edges` list to get the actual data. For example:

[Sync](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-sync_1)[Async](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-async_1)

```
for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo"}
):
    for issue in result["repository"]["issues"]["nodes"]:
        print(issue)
```

```
async for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo"}
):
    for issue in result["repository"]["issues"]["nodes"]:
        print(issue)
```

You can also provide a initial cursor value to start pagination from a specific point:

[Sync](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-sync_2)[Async](https://yanyongyu.github.io/githubkit/usage/graphql/#graphql-pagination-async_2)

```
for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo", "cursor": "initial_cursor"}
):
    print(result)
```

```
async for result in github.graphql.paginate(
    query, variables={"owner": "owner", "repo": "repo", "cursor": "initial_cursor"}
):
    print(result)
```

Tips

Nested pagination is not supported.

Back to top