[Skip to content](https://yanyongyu.github.io/githubkit/usage/unit-test/#unit-test)

# Unit Test [¶](https://yanyongyu.github.io/githubkit/usage/unit-test/\#unit-test "Permanent link")

If you are using githubkit in your business logic, you may want to mock the github API in your unit tests. There are two ways to reach this.

## Mocking the API Calls [¶](https://yanyongyu.github.io/githubkit/usage/unit-test/\#mocking-the-api-calls "Permanent link")

If you can't provide a githubkit test client to your business logic, you can mock the `request`/`arequest` method of the `GitHub` class to custom the response. Here is an example of how to mock githubkit's API calls:

[Sync](https://yanyongyu.github.io/githubkit/usage/unit-test/#mocking-the-api-calls-sync)[Async](https://yanyongyu.github.io/githubkit/usage/unit-test/#mocking-the-api-calls-async)

```
import json
from pathlib import Path
from typing import Any, Type

import httpx
import pytest

from githubkit import GitHub
from githubkit.utils import UNSET
from githubkit.response import Response
from githubkit.typing import URLTypes, UnsetType
from githubkit_schemas.latest.models import FullRepository

FAKE_RESPONSE = json.loads(Path("fake_response.json").read_text())

def target_sync_func() -> FullRepository:
    github = GitHub("xxxxx")
    resp = github.rest.repos.get("owner", "repo")
    return resp.parsed_data

def mock_request(
    g: GitHub,
    method: str,
    url: URLTypes,
    *,
    response_model: Type[Any] | UnsetType = UNSET,
    **kwargs: Any,
) -> Response[Any]:
    if method == "GET" and url == "/repos/owner/repo":
        return Response(
            httpx.Response(status_code=200, json=FAKE_RESPONSE),
            Any if response_model is UNSET else response_model,
        )
    raise RuntimeError(f"Unexpected request: {method} {url}")

# Test the target function
def test_sync_mock():
    with pytest.MonkeyPatch.context() as m:
        # Patch the request method with the mock
        m.setattr(GitHub, "request", mock_request)

        repo = target_sync_func()
        assert isinstance(repo, FullRepository)
```

```
import json
from pathlib import Path
from typing import Any, Type

import httpx
import pytest

from githubkit import GitHub
from githubkit.utils import UNSET
from githubkit.response import Response
from githubkit.typing import URLTypes, UnsetType
from githubkit_schemas.latest.models import FullRepository

FAKE_RESPONSE = json.loads(Path("fake_response.json").read_text())

async def target_async_func() -> FullRepository:
    async with GitHub("xxxxx") as github:
        resp = await github.rest.repos.get("owner", "repo")
        return resp.parsed_data

async def mock_arequest(
    g: GitHub,
    method: str,
    url: URLTypes,
    *,
    response_model: Type[Any] | UnsetType = UNSET,
    **kwargs: Any,
) -> Response[Any]:
    if method == "GET" and url == "/repos/owner/repo":
        return Response(
            httpx.Response(status_code=200, json=FAKE_RESPONSE),
            Any if response_model is UNSET else response_model,
        )
    raise RuntimeError(f"Unexpected request: {method} {url}")

# Test the target function
@pytest.mark.anyio
async def test_async_mock():
    with pytest.MonkeyPatch.context() as m:
        # Patch the request method with the mock
        m.setattr(GitHub, "arequest", mock_arequest)

        repo = await target_async_func()
        assert isinstance(repo, FullRepository)
```

## Using a Test Transport [¶](https://yanyongyu.github.io/githubkit/usage/unit-test/\#using-a-test-transport "Permanent link")

You can also create a test client with mock transport and provide it to your business logic. Here is an example:

[Sync](https://yanyongyu.github.io/githubkit/usage/unit-test/#using-a-test-transport-sync)[Async](https://yanyongyu.github.io/githubkit/usage/unit-test/#using-a-test-transport-async)

```
import json
from pathlib import Path

import httpx
import pytest

from githubkit import GitHub
from githubkit_schemas.latest.models import FullRepository

FAKE_RESPONSE = json.loads(Path("fake_response.json").read_text())

def target_sync_func(github: GitHub):
    resp = github.rest.repos.get("owner", "repo")
    return resp.parsed_data

def mock_transport_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/repos/owner/repo":
        return httpx.Response(status_code=200, json=FAKE_RESPONSE)
    raise RuntimeError(f"Unexpected request: {request.method} {request.url.path}")

def test_sync_mock():
    g = GitHub("xxxxx", transport=httpx.MockTransport(mock_transport_handler))
    repo = target_sync_func(g)
    assert isinstance(repo, FullRepository)
```

```
import json
from pathlib import Path

import httpx
import pytest

from githubkit import GitHub
from githubkit_schemas.latest.models import FullRepository

FAKE_RESPONSE = json.loads(Path("fake_response.json").read_text())

async def target_async_func(github: GitHub):
    resp = await github.rest.repos.async_get("owner", "repo")
    return resp.parsed_data

def mock_transport_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/repos/owner/repo":
        return httpx.Response(status_code=200, json=FAKE_RESPONSE)
    raise RuntimeError(f"Unexpected request: {request.method} {request.url.path}")

@pytest.mark.anyio
async def test_async_mock():
    g = GitHub("xxxxx", async_transport=httpx.MockTransport(mock_transport_handler))
    repo = await target_async_func(g)
    assert isinstance(repo, FullRepository)
```

Back to top