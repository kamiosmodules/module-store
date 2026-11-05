# GitHub OAuth Device Flow proxy

The static GitHub Pages site cannot keep a GitHub OAuth secret or a repository
write token private. This small Cloudflare Worker forwards only the two GitHub
OAuth Device Flow requests used by the module uploader. It does not store
access tokens. The contributor's access token stays in the browser's memory
and is cleared when they sign out or leave the page.

## 1. Create the OAuth App

In GitHub, open **Settings → Developer settings → OAuth Apps → New OAuth App**.
Use these values:

- Homepage URL: `https://kamiosmodules.github.io/module-store/`
- Authorization callback URL: `https://kamiosmodules.github.io/module-store/`
- Enable **Device Flow** in the OAuth App settings.

Copy the OAuth App's **Client ID**. The Worker uses the Client ID, not the
OAuth client secret. Do not put a client secret or personal access token in
`index.html`.

The uploader requests the `public_repo` scope so the contributor can create a
fork, commit their module there, and open a pull request. That scope grants
write access to the contributor's public repositories, not only this store.
The contributor can revoke the app later from GitHub's authorized OAuth Apps
settings.

## 2. Deploy the Worker

Install Wrangler and authenticate with Cloudflare, then run these commands
from the repository root:

```sh
cd oauth-proxy
npx wrangler secret put GITHUB_CLIENT_ID
npx wrangler deploy
```

When prompted for `GITHUB_CLIENT_ID`, paste the OAuth App Client ID. The
included `wrangler.toml` already sets `ALLOWED_ORIGINS` to the production
GitHub Pages origin:

```text
https://kamiosmodules.github.io
```

For local testing, add the exact local origin (for example,
`http://localhost:8000`) to `ALLOWED_ORIGINS` in `wrangler.toml`, then deploy
again. Remove the local origin before production use.

## 3. Configure the website

After deployment, copy the Worker URL (for example,
`https://kamios-module-store-oauth.<your-subdomain>.workers.dev`) into the
`OAUTH_PROXY_URL` constant near the beginning of the script in `index.html`.
Commit and push the updated page.

## 4. Test

Use a non-maintainer GitHub account to sign in, select a valid module ZIP, and
submit it. The expected result is a fork containing a new branch and a pull
request against `kamiosmodules/module-store`. Review and merge the pull request;
the repository's existing Actions workflow then builds the release ZIP and
updates `modules.json`.

The Worker is a small public OAuth relay. Its Origin allowlist restricts normal
browser use; it is not a substitute for rate limiting if the endpoint is
heavily abused. No repository write token is stored in the Worker or website.
