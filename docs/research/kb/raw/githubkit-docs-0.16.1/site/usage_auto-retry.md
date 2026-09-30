[Skip to content](https://yanyongyu.github.io/githubkit/usage/auto-retry/#auto-retry)

# Auto Retry [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#auto-retry "Permanent link")

By default, githubkit will retry the request when specific exception encountered. When rate limit exceeded, githubkit will retry **once** after GitHub suggested waiting time. When server error encountered (http status >= 500), githubkit will retry **max three times**.

## Disable Auto Retry [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#disable-auto-retry "Permanent link")

You can disable this feature by set the `auto_retry` option to `False`:

```
github = GitHub(
    ...
    auto_retry=False
)
```

## Customize Retry Decision [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#customize-retry-decision "Permanent link")

You can also customize the retry decision by passing a callable. The callable should accept two arguments: the exception raised `exc` and the current retry count `retry_count`. The callable should return a `RetryOption` object. `RetryOption` is a named tuple with two fields: `do_retry` and `retry_after`. If `do_retry` is `True`, the request will be retried after `retry_after` time. Otherwise, the exception will be raised.

```
from datetime import timedelta

from githubkit.retry import RetryOption
from githubkit.exception import GitHubException

def retry_decision_func(exc: GitHubException, retry_count: int) -> RetryOption:
    if retry_count < 1:
        return RetryOption(True, timedelta(seconds=60))
    return RetryOption(False)

github = GitHub(
    ...
    auto_retry=retry_decision_func
)
```

## Builtin Retry Decision [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#builtin-retry-decision "Permanent link")

githubkit also provides some builtin retry decision function.

### Rate Limit Exceeded [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#rate-limit-exceeded "Permanent link")

```
from githubkit.retry import RETRY_RATE_LIMIT, RetryRateLimit

github = GitHub(
  ...
  auto_retry=RETRY_RATE_LIMIT
)

github = GitHub(
  ...
  auto_retry=RetryRateLimit(max_retry=1)
)
```

### Server Error [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#server-error "Permanent link")

```
from githubkit.retry import RETRY_SERVER_ERROR, RetryServerError

github = GitHub(
   ...
   auto_retry=RETRY_SERVER_ERROR
)
github = GitHub(
   ...
   auto_retry=RetryServerError(max_retry=1)
)
```

### Chain Retry Decision Functions [¶](https://yanyongyu.github.io/githubkit/usage/auto-retry/\#chain-retry-decision-functions "Permanent link")

You can chain multiple retry decision functions by using `RetryChainDecision`. The request will be retried if **any** of the decision functions return `True`. For example:

```
from githubkit.retry import RETRY_RATE_LIMIT, RETRY_SERVER_ERROR, RetryChainDecision

github = GitHub(
   ...
   auto_retry=RetryChainDecision(RETRY_RATE_LIMIT, RETRY_SERVER_ERROR)
)
```

Back to top