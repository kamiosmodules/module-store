# KamiOS Module Store

A public module store for KamiOS. Modules are kept in `modules/`, indexed in
`modules.json`, and published as installable ZIP files in the GitHub Release
named `latest`.

- Website: <https://kamiosmodules.github.io/module-store/>
- Repository: <https://github.com/kamiosmodules/module-store>
- ROM/app index: <https://raw.githubusercontent.com/kamiosmodules/module-store/main/modules.json>

## How the store is built

1. Each module lives in `modules/<module-id>/`.
2. A module contains a root-level `module.json` or `module.prop`.
3. GitHub Actions validates the module folders, creates one installable ZIP per
   module and regenerates `modules.json`.
4. The ZIPs are published to the `latest` release. The website and the ROM read
   `modules.json` and use the release URLs for downloads.

The release ZIP includes the module's installation files, but excludes the
root-level `thumbnail.png` (and the other supported `thumbnail.*` image types)
and the root `screenshots/` directory. Those images remain in the repository
and are used by the website.

## Module layout

```text
modules/
└── my-module/                 # folder name must equal module.json id
    ├── module.json           # required, or use module.prop instead
    ├── module.prop           # optional; supports store-only category metadata
    ├── assets/               # module's own install files
    ├── thumbnail.png         # optional store artwork
    └── screenshots/          # optional store screenshots
        ├── 1.png
        └── 2.png
```

Required metadata:

- `id`: must exactly match the folder name.
- `name`, `author` and `description`: must be filled in with real values.
- `module.json` must be at the module folder root. Older modules may use a
  root-level `module.prop` with `id`, `name`, `author`, `description`, and
  optionally `version`.

For `module.json`, the module's own version is `module_version`. The JSON
`version` field is the manifest format version. If `module_version` is absent,
the store displays `1.0`.

## Categories

`category` is optional. Supported values are:

```text
theme, launcher, tweak, sounds, bootanimation, emoji, fonts, wallpaper,
icons, apps, quicksettings, pill, volume, lockscreen
```

You may put the category in `module.json` as `"category": "pill"`, or in
`module.prop` as `category=pill`. For the newer values `quicksettings`, `pill`,
`volume`, and `lockscreen`, use `module.prop` when compatibility with older
KamiOS builds matters; older phones may reject those values when they appear
inside `module.json`.

A missing category is inferred during the build:

- A module that only changes sounds, boot animation, emoji, fonts, wallpaper,
  or icons gets that category.
- A home app without fonts or wallpaper is a launcher. A home app combined
  with fonts or wallpaper is a theme.
- A module that combines a style component (font, wallpaper, accent, icons,
  sounds, boot animation or emoji) with other module behaviour is a theme.
- A module that targets three or more Android app packages is a theme.
- App-only installers do not become Apps automatically: use an explicit
  `"category": "apps"` when that is the best fit. Anything else that does not
  match the rules above defaults to Tweaks.

An explicitly supplied category always takes precedence. An unrecognised value
(for example, a typo or a category from a newer ROM) is **not a build error**:
the value is ignored, the module appears under **Other**, and
`scripts/validate.py` prints a warning. The website groups modules by category
and provides category filters; absent or unknown values are shown under Other.

## Submit a module from the website

The website has a **Submit a module ZIP** section. A contributor selects a ZIP
with the same layout described above. The browser extracts it, checks the
metadata and file paths, and submits the extracted files to a new branch in the
contributor's fork. It then opens a pull request against this repository.

A maintainer must review and merge that pull request. The existing GitHub
Actions workflow then builds the installable ZIP and updates the website index.
The browser uploader does not write directly to the official `main` branch.

### One-time maintainer setup for the website uploader

The store is hosted on GitHub Pages, which is static and cannot safely hold a
GitHub OAuth client secret or repository write token. The uploader therefore
uses GitHub's Device Flow and a small Cloudflare Worker proxy. The proxy only
forwards device-code/token requests; the user's token is held in browser memory
and is not stored by the Worker.

1. Create a GitHub OAuth App under **GitHub Settings → Developer settings →
   OAuth Apps**. Set its homepage to
   `https://kamiosmodules.github.io/module-store/`, enable **Device Flow**, and
   note its Client ID. The callback URL can be the same website URL.
2. Deploy `oauth-proxy/worker.js` as a Cloudflare Worker. From the repository
   root, run:

   ```sh
   cd oauth-proxy
   npx wrangler secret put GITHUB_CLIENT_ID
   npx wrangler deploy
   ```

   Paste the OAuth App Client ID when prompted. The included
   `oauth-proxy/wrangler.toml` sets `ALLOWED_ORIGINS` to the production GitHub
   Pages origin. Add a local development origin only while testing.
3. Copy the deployed Worker URL into `OAUTH_PROXY_URL` near the top of the
   script section in `index.html`.
4. Commit and push `index.html` and the Worker configuration. Test with a
   non-maintainer GitHub account: it should create a fork, branch and pull
   request without asking for a maintainer token.

The uploader asks GitHub for the `public_repo` OAuth scope. This is a GitHub
permission that lets the signed-in contributor work with their public
repositories; it is broader than permission to this one fork. Contributors can
revoke the OAuth app at **GitHub Settings → Applications → Authorized OAuth
Apps**. Do not add a personal access token or OAuth client secret to `index.html`.

The browser uploader currently limits ZIPs to 100 files, 20 MB per file and
50 MB total extracted size. Larger modules can still be submitted using the
manual fork/PR process below.

## Manual contribution

The website uploader is the easiest method, but contributors can still use any
of the repository's normal GitHub contribution methods.

1. Fork this repository from <https://github.com/kamiosmodules/module-store>.
2. Add the complete module folder under `modules/<module-id>/` in your fork.
   The folder name must exactly match the `id` in its metadata.
3. Open a pull request targeting `kamiosmodules/module-store` on `main`.
4. A maintainer reviews and merges it. The store is rebuilt automatically.

Other ways to add the folder to your fork:

- **GitHub in the browser:** open the `modules/` folder in your fork, choose
  **Add file → Upload files**, and upload the complete module folder.
- **GitHub Desktop:** clone your fork, copy the module folder into `modules/`,
  commit the change and push your branch.
- **Git commands:**

  ```sh
  git clone https://github.com/YOURNAME/module-store.git
  cd module-store
  git checkout -b add-my-module
  # copy your module folder into modules/
  git add modules/my-module
  git commit -m "Add My Module"
  git push -u origin add-my-module
  ```

- **github.dev:** open your fork, press `.`, add the module folder in the file
  list, then commit and push from the Source Control tab.

To update a module later, change its existing folder in your fork and open a
pull request again. A maintainer must review and merge the change before the
new release ZIP is published.

## Contribution rules

- Only add or change module folders you are authorised to contribute. Do not
  modify another author's module.
- Do not edit `modules.json` or `downloads.json` manually; both are generated.
- Modules must be safe to install. Do not upload hidden or harmful code, or
  content you do not have permission to distribute.
- Use a clear name and a real description so users understand what the module
  changes. Keep unnecessary large files out of the module.
- Test the module on a device before submitting it.

## Local checks

```bash
python3 scripts/validate.py
python3 scripts/build.py
```

`validate.py` fails on missing/invalid required metadata and warns about
unsupported category values. It prints the inferred category for modules that
do not declare one. `build.py` creates installable ZIPs under `out/` and writes
`modules.json`.

## Download numbers

`modules.json` includes a `downloads` count used by the website. GitHub resets
an asset's download counter when a release asset is replaced, so
`downloads.json` carries the previous totals forward. A scheduled GitHub Action
refreshes the counts every six hours. Do not edit this file by hand.

Made with care by the KamiOS Team.

Join the community: <https://t.me/kamiosmodules> · <https://t.me/kamiosofficial>
