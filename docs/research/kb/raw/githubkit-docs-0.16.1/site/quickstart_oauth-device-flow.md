[Skip to content](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#develop-an-oauth-app-github-app-with-device-flow)

# Develop an OAuth APP (GitHub APP) with device flow [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/\#develop-an-oauth-app-github-app-with-device-flow "Permanent link")

OAuth device flow also allows you to authenticate as a user and act on behalf of the user. It is suitable for headless application like CLI tools.

To authenticate as a user, you need to display a `user_code` to the user and ask the user to visit the [GitHub OAuth Device Verification Page](https://github.com/login/device) to enter the code. After the user authorizes your app, the client application will get the user token.

Note that the `user_code` is **one-time use** and only valid for a short period of time. If you want to auth as the user later again, you need to store the user token in a database.

Like OAuth web flow, you can opt-in / opt-out of the **user-to-server token expiration** feature.

## One-Time Usage [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/\#one-time-usage "Permanent link")

If you just want to temporarily act as the user, you can simply call the API directly with the `OAuthDeviceAuthStrategy` and a callback function.

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#one-time-usage-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#one-time-usage-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
def callback(data: dict):
    print(data["user_code"])

user_github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

# now you can act as the user
resp = user_github.rest.users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
def callback(data: dict):
    print(data["user_code"])

user_github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

# now you can act as the user
resp = await user_github.rest.users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

## Store token without expiration [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/\#store-token-without-expiration "Permanent link")

If you are developing an OAuth APP or a GitHub APP without user-to-server token expiration, you just need to exchange the `code` for an access token.

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#store-token-without-expiration-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#store-token-without-expiration-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
def callback(data: dict):
    print(data["user_code"])

github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

auth: OAuthTokenAuthStrategy = github.auth.exchange_token(github)
access_token = auth.token

user_github = github.with_auth(
    OAuthTokenAuthStrategy("<client_id>", token=access_token)
)

# now you can act as the user
resp = user_github.rest.users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
async def callback(data: dict):
    print(data["user_code"])

github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

auth: OAuthTokenAuthStrategy = await github.auth.async_exchange_token(github)
access_token = auth.token

user_github = github.with_auth(
    OAuthTokenAuthStrategy("<client_id>", token=access_token)
)

# now you can act as the user
resp = await user_github.rest.users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

## Store token with expiration [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/\#store-token-with-expiration "Permanent link")

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#store-token-with-expiration-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-device-flow/#store-token-with-expiration-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
def callback(data: dict):
    print(data["user_code"])

github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

auth: OAuthTokenAuthStrategy = github.auth.exchange_token(github)
refresh_token = auth.refresh_token

auth = OAuthTokenAuthStrategy("<client_id>", refresh_token=refresh_token)
auth.refresh(github)
refresh_token = auth.refresh_token

user_github = github.with_auth(auth)

# now you can act as the user
resp = user_github.rest.users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthDeviceAuthStrategy, OAuthTokenAuthStrategy

# sync/async func for displaying user code to user
async def callback(data: dict):
    print(data["user_code"])

github = GitHub(OAuthDeviceAuthStrategy("<client_id>", callback))

auth: OAuthTokenAuthStrategy = await github.auth.async_exchange_token(github)
refresh_token = auth.refresh_token

auth = OAuthTokenAuthStrategy("<client_id>", refresh_token=refresh_token)
await auth.async_refresh(github)
refresh_token = auth.refresh_token

user_github = github.with_auth(auth)

# now you can act as the user
resp = user_github.rest.users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

Back to top