[Skip to content](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#develop-an-oauth-app-github-app-with-web-flow)

# Develop an OAuth APP (GitHub APP) with Web Flow [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/\#develop-an-oauth-app-github-app-with-web-flow "Permanent link")

OAuth web flow allows you to authenticate as a user and act on behalf of the user.

To authenticate as a user, you need to redirect the user to the [GitHub OAuth Authorization Page](https://github.com/login/oauth/authorize) with the `client_id` and `redirect_uri` (See [GitHub Docs - Web application flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#web-application-flow) for more information). After the user authorizes your app, GitHub will redirect the user back to your `redirect_uri` with a `code`. You can exchange the `code` for an access token.

Note that the `code` is **one-time use** and only valid for a short period of time. If you want to auth as the user later again, you need to store the user token in a database.

If you are developing a GitHub APP, you may opt-in / opt-out of the **user-to-server token expiration** feature. If you opt-in, the user-to-server token will **expire** after a certain period of time, and you need to use the **refresh token** to generate a new token. In this case, you need to do more work to handle the token refresh. See [GitHub Docs - Refreshing user access tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens) for more information.

## One-Time Usage [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/\#one-time-usage "Permanent link")

To use the `code` once, replace `<code>` with the code you get from the callback:

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#one-time-usage-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#one-time-usage-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

user_github = github.with_auth(github.auth.as_web_user("<code>"))

# now you can act as the user
resp = user_github.rest.users.get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

user_github = github.with_auth(github.auth.as_web_user("<code>"))

# now you can act as the user
resp = await user_github.rest.users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

## Store token without expiration [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/\#store-token-without-expiration "Permanent link")

If you are developing an OAuth APP or a GitHub APP without user-to-server token expiration, you just need to exchange the `code` for an access token.

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#store-token-without-expiration-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#store-token-without-expiration-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

auth: OAuthTokenAuthStrategy = github.auth.as_web_user("<code>").exchange_token(
    github
)
access_token = auth.token

user_github = github.with_auth(
    OAuthTokenAuthStrategy("<client_id>", "<client_secret>", token=access_token)
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
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

auth: OAuthTokenAuthStrategy = await github.auth.as_web_user(
    "<code>"
).async_exchange_token(github)
access_token = auth.token

user_github = github.with_auth(
    OAuthTokenAuthStrategy("<client_id>", "<client_secret>", token=access_token)
)

# now you can act as the user
resp = await user_github.rest.users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

## Store token with expiration [¶](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/\#store-token-with-expiration "Permanent link")

If you are developing a GitHub APP with user-to-server token expiration, you need to handle the token refresh with the `refresh_token`.

[Sync](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#store-token-with-expiration-sync)[Async](https://yanyongyu.github.io/githubkit/quickstart/oauth-web-flow/#store-token-with-expiration-async)

```
from githubkit_schemas.latest.models import PublicUser, PrivateUser
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

auth: OAuthTokenAuthStrategy = github.auth.as_web_user("<code>").exchange_token(
    github
)
refresh_token = auth.refresh_token

auth = OAuthTokenAuthStrategy(
    "<client_id>", "<client_secret>", refresh_token=refresh_token
)
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
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy

github = GitHub(OAuthAppAuthStrategy("<client_id>", "<client_secret>"))

# redirect user to github oauth page and get the code from callback

auth: OAuthTokenAuthStrategy = await github.auth.as_web_user(
    "<code>"
).async_exchange_token(github)
refresh_token = auth.refresh_token

auth = OAuthTokenAuthStrategy(
    "<client_id>", "<client_secret>", refresh_token=refresh_token
)
await auth.async_refresh(github)
refresh_token = auth.refresh_token

user_github = github.with_auth(auth)

# now you can act as the user
resp = await user_github.rest.users.async_get_authenticated()
user: PublicUser | PrivateUser = resp.parsed_data

# you can get the user name and id now
username = user.login
user_id = user.id
```

Back to top