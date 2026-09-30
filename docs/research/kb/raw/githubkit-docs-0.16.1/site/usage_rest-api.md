[Skip to content](https://yanyongyu.github.io/githubkit/usage/rest-api/#calling-rest-api)

# Calling REST API [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#calling-rest-api "Permanent link")

GitHub's REST API enables you to build automation processes, integrate with GitHub and extend GitHub. See the [GitHub REST API documentation](https://docs.github.com/en/rest) for more information.

> APIs are fully typed. Type hints in the following examples are just for reference only.

## The Basics [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#the-basics "Permanent link")

Calling REST API is simple with githubkit. You just need to create a `GitHub` instance with your authentication strategy and call the REST API methods in categories. For example, to get a repository:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-sync)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-async)

```
from githubkit import GitHub, Response
from githubkit_schemas.latest.models import FullRepository

github = GitHub("<your_token_here>")
resp: Response[FullRepository] = github.rest.repos.get("owner", "repo")
repo: FullRepository = resp.parsed_data
```

```
from githubkit import Response
from githubkit_schemas.latest.models import FullRepository

github = GitHub("<your_token_here>")
resp: Response[FullRepository] = await github.rest.repos.async_get("owner", "repo")
repo: FullRepository = resp.parsed_data
```

If you are calling an API that requires request body parameters, you can pass the request body as a keyword argument:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-sync_1)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-async_1)

```
from githubkit import GitHub, Response
from githubkit_schemas.latest.models import Issue

github = GitHub("<your_token_here>")
resp: Response[Issue] = github.rest.issues.create(
    "owner",
    "repo",
    title="New Issue",
    body="This is issue body",
)
issue: Issue = resp.parsed_data
```

```
from githubkit import GitHub, Response
from githubkit_schemas.latest.models import Issue

github = GitHub("<your_token_here>")
resp: Response[Issue] = await github.rest.issues.async_create(
    "owner",
    "repo",
    title="New Issue",
    body="This is issue body",
)
issue: Issue = resp.parsed_data
```

Tip

By default, githubkit will validate the request body against the API schema. If you want to skip the validation, you can set the client config `rest_api_validate_body` to `False`. See [Configuration](https://yanyongyu.github.io/githubkit/usage/getting-started/configuration/#rest_api_validate_body) for more information.

Or you can pass the json request body as a dictionary:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-sync_2)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-async_2)

```
from githubkit import GitHub, Response
from githubkit_schemas.latest.models import Issue

github = GitHub("<your_token_here>")
resp: Response[Issue] = github.rest.issues.create(
    "owner",
    "repo",
    data={"title": "New Issue", "body": "This is issue body"},
)
issue: Issue = resp.parsed_data
```

```
from githubkit import GitHub, Response
from githubkit_schemas.latest.models import Issue

github = GitHub("<your_token_here>")
resp: Response[Issue] = await github.rest.issues.async_create(
    "owner",
    "repo",
    data={"title": "New Issue", "body": "This is issue body"},
)
issue: Issue = resp.parsed_data
```

For some APIs, the request body may be raw data. You can pass the raw data directly to the `data` parameter:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-sync_3)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#the-basics-async_3)

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = github.rest.markdown.render_raw(
    data="Hello **world**",
)
rendered_html = resp.text
```

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = await github.rest.markdown.async_render_raw(
    data="Hello **world**",
)
rendered_html = resp.text
```

Danger

Note that you should hold a **strong reference** to the githubkit client instance. Otherwise, githubkit client will fail to call the request.
For example, you should not do this:

```
from githubkit import GitHub

def get_client() -> GitHub:
    return GitHub()

# This will cause error
get_client().rest.repos.get("owner", "repo")

# This is ok
client = get_client()
client.rest.repos.get("owner", "repo")
```

## Custom Headers [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#custom-headers "Permanent link")

In some cases, you may need to pass additional headers to the API request. You can pass the headers through the `headers` parameter. For example:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#custom-headers-sync)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#custom-headers-async)

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = github.rest.repos.get_content(
    "owner",
    "repo",
    "/path/to/file",
    headers={"Accept": "application/vnd.github.raw+json"},
)
content = resp.text
```

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = await github.rest.repos.async_get_content(
    "owner",
    "repo",
    "/path/to/file",
    headers={"Accept": "application/vnd.github.raw+json"},
)
content = resp.text
```

## Data Validation [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#data-validation "Permanent link")

As shown above, the response data is parsed and validated by accessing the `response.parsed_data` property. This ensures that the data type returned by the API is as expected and your code is safe to use it (with static type checking). But sometimes you may want to get the raw data returned by the API, such as when the schema is not correct. You can use the `response.text` property or `response.json()` method to get the raw data. The loaded json data is also typed but not validated. For example:

```
from typing import Any
from githubkit import Response
from githubkit_schemas.latest.models import FullRepository
from githubkit_schemas.latest.types import FullRepositoryType

resp: Response[FullRepository, FullRepositoryType] = github.rest.repos.get(
    "owner", "repo"
)
repo: FullRepositoryType = resp.json()
```

[Pydantic v1](https://yanyongyu.github.io/githubkit/usage/rest-api/#data-validation-pydantic-v1)[Pydantic v2](https://yanyongyu.github.io/githubkit/usage/rest-api/#data-validation-pydantic-v2)

If you have already got the parsed data and want to dump it into a dict object or JSON string, you can use the pydantic model's `dict` or `json` method:

```
from typing import Any
from githubkit import Response
from githubkit_schemas.latest.models import FullRepository

resp: Response[FullRepository] = github.rest.repos.get("owner", "repo")
repo: FullRepository = resp.parsed_data

repo_dict: dict[str, Any] = repo.dict(by_alias=True, exclude_unset=True)
repo_json: str = repo.json(by_alias=True, exclude_unset=True)
```

If you have already got the parsed data and want to dump it into a dict object or JSON string, you can use the pydantic model's `model_dump` or `model_dump_json` method:

```
from typing import Any
from githubkit import Response
from githubkit_schemas.latest.models import FullRepository

resp: Response[FullRepository] = github.rest.repos.get("owner", "repo")
repo: FullRepository = resp.parsed_data

repo_dict: dict[str, Any] = repo.model_dump(
    mode="json", by_alias=True, exclude_unset=True
)
repo_json: str = repo.model_dump_json(by_alias=True, exclude_unset=True)
```

## Data Streaming [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#data-streaming "Permanent link")

Some APIs may return large amounts of data, such as downloading the repository archive. In this case, you can use the `stream` parameter to enable streaming mode and iterate over the response data in chunks. For example, to download a repository archive:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#data-streaming-sync)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#data-streaming-async)

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = github.rest.repos.download_tarball_archive(
    "owner", "repo", "branch", stream=True
)
for chunk in resp.iter_bytes(chunk_size=8192):
    # do something with the chunk
    print(f"Received {len(chunk)} bytes")
```

```
from githubkit import GitHub

github = GitHub("<your_token_here>")
resp = await github.rest.repos.async_download_tarball_archive(
    "owner", "repo", "branch", stream=True
)
async for chunk in resp.aiter_bytes(chunk_size=8192):
    # do something with the chunk
    print(f"Received {len(chunk)} bytes")
```

## REST API Versioning [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#rest-api-versioning "Permanent link")

githubkit supports multiple versions of GitHub API, you can switch between versions as follows:

```
github.rest("2022-11-28").repos.get("owner", "repo")
```

The code above uses the `2022-11-28` version of the GitHub API.

Besides the REST API methods, the versioned models can also be imported from `githubkit_schemas.<version>.models` module. For example:

```
from githubkit_schemas.v2022_11_28.models import FullRepository
```

Specially, the `latest` module is always linked to the latest version of GitHub API:

```
from githubkit_schemas.latest.models import FullRepository
```

Note

For backward compatibility, the `githubkit.rest` module is linked to the models of `latest` version by default.

```
from githubkit.rest import FullRepository
```

You can also get the latest version name of GitHub API and version-module mapping of GitHub API:

```
from githubkit_schemas import LATEST_VERSION, VERSIONS
```

Current supported versions are: (you can also find it in the section `[[descriptions]]` of the `githubkit/versions/versions.lock` file)

- 2026-03-10 (latest)
- ghec-2026-03-10
- 2022-11-28
- ghec-2022-11-28

Installing extra schema versions

Only the `latest` schema is installed by default. To use a non-default version such as `2022-11-28` or `ghec-2026-03-10`, install the corresponding extra first. See [Install Extra Schema Versions](https://yanyongyu.github.io/githubkit/installation/#install-extra-schema-versions) for instructions.

## REST API Pagination [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#rest-api-pagination "Permanent link")

When a response from the REST API would include many results, GitHub will paginate the results and return a subset of the results. In this case, some APIs provide `page` and `per_page` parameters to control the pagination. See [GitHub Docs - Using pagination in the REST API](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api) for more information.

githubkit provides a built-in pagination feature to handle this. You can use the `github.rest.paginate` method to iterate over all the results:

> Pagination typing is checked with Pylance ( [Pyright](https://github.com/microsoft/pyright)).

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-pagination-sync)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-pagination-async)

```
from githubkit_schemas.latest.models import Issue

for issue in github.rest.paginate(
    github.rest.issues.list_for_repo, owner="owner", repo="repo", state="open"
):
    issue: Issue
    print(issue.number)
```

```
from githubkit_schemas.latest.models import Issue

async for issue in github.rest.paginate(
    github.rest.issues.async_list_for_repo, owner="owner", repo="repo", state="open"
):
    issue: Issue
    print(issue.number)
```

You can also provide a custom map function to handle complex pagination (such as when the API returns data in a nested field):

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-pagination-sync_1)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#rest-api-pagination-async_1)

```
from githubkit_schemas.latest.models import Repository

for accessible_repo in github.rest.paginate(
    github.rest.apps.list_installation_repos_for_authenticated_user,
    map_func=lambda r: r.parsed_data.repositories,
    installation_id=1,
):
    accessible_repo: Repository
    print(accessible_repo.full_name)
```

```
from githubkit_schemas.latest.models import Repository

async for accessible_repo in github.rest.paginate(
    github.rest.apps.async_list_installation_repos_for_authenticated_user,
    map_func=lambda r: r.parsed_data.repositories,
    installation_id=1,
):
    accessible_repo: Repository
    print(accessible_repo.full_name)
```

## Calling API Directly [¶](https://yanyongyu.github.io/githubkit/usage/rest-api/\#calling-api-directly "Permanent link")

In some cases, you may want to call the API directly without using the generated methods. You can use the `github.request` / `github.arequest` method to make a raw request.

For example, to upload a release asset:

[Sync](https://yanyongyu.github.io/githubkit/usage/rest-api/#calling-api-directly-sync)[Async](https://yanyongyu.github.io/githubkit/usage/rest-api/#calling-api-directly-async)

```
from githubkit import GitHub
from githubkit_schemas.latest.models import Release, ReleaseAsset

github = GitHub()

resp = github.rest.repos.get_release_by_tag("owner", "repo", "tag_name")
release: Release = resp.parsed_data

resp = github.request(
    "POST",
    release.upload_url.split("{?")[0],
    params={"name": "test", "label": "description"},
    content=b"file content",
    headers={"Content-Type": "application/zip"},
    response_model=ReleaseAsset,
)
asset: ReleaseAsset = resp.parsed_data
```

```
from githubkit import GitHub
from githubkit_schemas.latest.models import Release, ReleaseAsset

github = GitHub()

resp = await github.rest.repos.async_get_release_by_tag("owner", "repo", "tag_name")
release: Release = resp.parsed_data

resp = await github.arequest(
    "POST",
    release.upload_url.split("{?")[0],
    params={"name": "test", "label": "description"},
    content=b"file content",
    headers={"Content-Type": "application/zip"},
    response_model=ReleaseAsset,
)
asset: ReleaseAsset = resp.parsed_data
```

Back to top