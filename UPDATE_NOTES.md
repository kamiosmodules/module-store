# Module Store update overlay

This archive contains only the files added or changed for the requested
features. Extract it into the root of the existing
`kamiosmodules/module-store` checkout and preserve all existing `modules/`,
`modules.json`, `downloads.json`, `.gitignore`, and other repository assets.

## Included files

- `index.html` — category headings/filters and the ZIP uploader.
- `scripts/build.py` — category inference, index generation and release ZIP
  packaging that omits root store artwork.
- `scripts/validate.py` — metadata/category validation and warning-only
  handling for unsupported categories.
- `.github/workflows/build.yml` — PR validation and main-branch build/release.
- `oauth-proxy/worker.js`, `wrangler.toml`, `README.md` — GitHub OAuth Device
  Flow proxy and deployment instructions.
- `README.md` — updated repository and uploader documentation.

## Required setup before enabling website uploads

1. Create a GitHub OAuth App and enable Device Flow.
2. Deploy the Cloudflare Worker as documented in `oauth-proxy/README.md`.
3. Set `OAUTH_PROXY_URL` in `index.html` to the deployed Worker URL.
4. Push the overlay to the repository.
5. Test submission with a non-maintainer GitHub account.

The contributor authorizes the uploader with the `public_repo` OAuth scope. The
browser writes the extracted module into a new branch in that contributor's
fork and opens a pull request. A maintainer must review and merge that PR. The
website does not push unreviewed uploads directly to the official `main`
branch. No maintainer PAT or OAuth client secret is embedded in the page.

## Checks performed

- Python syntax compilation for `scripts/build.py` and `scripts/validate.py`.
- JavaScript syntax checks for the page's inline script and the Worker.
- Build/validation fixture tests for dedicated categories, themes, launchers,
  tweaks, explicit categories and unsupported categories.
- Archive test confirming root `thumbnail.*` and root `screenshots/` are left
  out, while nested module assets with similar names remain included.
- Mocked Worker tests for OAuth form encoding and the origin allowlist.

The live GitHub OAuth flow, Cloudflare deployment and actual pull-request
creation still require the repository maintainer's credentials and have not
been exercised from this environment.
