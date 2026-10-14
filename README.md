# KamiOS Module Store

A public store of modules for KamiOS. Browse them on the website, or in the
ROM's settings. Every module has a description, optional screenshots, and a
one-tap download straight from GitHub.

- Website: https://kamiosmodules.github.io/module-store/
- Index for apps: https://raw.githubusercontent.com/kamiosmodules/module-store/main/modules.json

## How it works

1. Each module is a folder inside `modules/`.
2. When something is added to `main`, a GitHub Action zips every module,
   publishes the zips to the **latest** release, and rewrites `modules.json`.
3. The website and the ROM read `modules.json`, so a new module appears by
   itself. Nobody has to update the app.


## Contributors

We would love seeing what you build and want to make it as easy as possible to share your creations, making the experience available to everyone in the community.

Maintainers: Can push directly to the main branch.
Contributors: Fork the repository and open a Pull Request.


What to Expect Next

• Review: A maintainer will look over your Pull Request as soon as possible to help review and merge your changes.
• Deployment: Once merged, your module will automatically go live within just 1–2 minutes.

## What a module looks like

```
modules/
└── my-module/              <- folder name = the module's id
    ├── module.json         <- required (exported from the ROM)
    ├── assets/ ...         <- the module's own files
    ├── thumbnail.png       <- optional, square icon for the store
    └── screenshots/        <- optional
        ├── 1.png
        └── 2.png
```

**Required**
- `module.json` at the top level of the folder (not inside another folder).
- The folder name must be **exactly** the `id` written inside `module.json`.
  For example `"id": "nyan-cat-pill"` means the folder is `modules/nyan-cat-pill`.
- `name`, `author` and `description` filled in. Write a real one-line
  description, not a placeholder like "What it does".

**Optional**
- `"category"` in `module.json`: where the store lists the module. One of `theme`, `launcher`,
  `tweak`, `sounds`, `bootanimation`, `emoji`, `fonts`, `wallpaper`, `icons`, `apps`, `quicksettings`,
  `pill`, `volume`, `lockscreen`. A missing or unknown one lands under "Other".
  The newest ids (`quicksettings`, `pill`, `volume`, `lockscreen`) are rejected by phones on an older
  ROM when they sit in `module.json`. For those, put `category=pill` (for example) in a `module.prop`
  next to it instead; the store reads it and the phone ignores that file.
- `"module_version"` in `module.json` (like `1.2`): the module's own version. The store compares it to
  the installed one for the "Updates" list. Raise it with every change you want phones to pick up.
- `thumbnail.png` (or `.jpg`, `.webp`, `.gif`): a small square icon shown next to the name.
- `screenshots/`: images (PNG, JPG, WebP or GIF) directly inside this folder.
  Sub-folders are not read. Files show in number order (1, 2, 10).

Thumbnail and screenshots are for the store only. They are left out of the
module's download zip.

Older modules can use a `module.prop` file instead of `module.json`
(`id`, `name`, `author`, `description`, and optionally `version`).

**Download numbers:** `modules.json` has a `downloads` number per module, shown in the store and used by
"Popular". GitHub restarts a file's counter whenever the workflow uploads the zips again, so
`downloads.json` keeps the running total (do not edit it by hand). A scheduled run refreshes the numbers
every six hours without touching the zips.

**Version note:** the `"version"` number inside `module.json` is the file-format version, not the
module's own version. The store shows `module_version` and falls back to `1.0` when it is not set.

## How to contribute

### 1. Fork the repo
Open https://github.com/kamiosmodules/module-store and click **Fork**.
This gives you your own copy.

### 2. Add your module to your fork
Pick whichever method suits you.

**A. In the browser (easiest, nothing to install)**
1. Open your fork on GitHub and go into the `modules` folder.
2. Click **Add file → Upload files**.
3. Drag in your whole module folder (named after the module id).
4. Click **Commit changes**.

Browser uploads allow roughly 100 files at a time and 25 MB per file. For a
bigger module, upload in two batches or use method B or C.

**B. GitHub Desktop (buttons, no commands)**
1. Install GitHub Desktop and sign in.
2. **File → Clone repository**, and pick your fork.
3. Copy your module folder into the `modules` folder.
4. Type a message, click **Commit to main**, then **Push origin**.

**C. Git commands**
```
git clone https://github.com/YOURNAME/module-store.git
cd module-store
git checkout -b add-my-module
# copy your module folder into modules/
git add .
git commit -m "Add My Module"
git push -u origin add-my-module
```

**D. github.dev (browser editor)**
Open your fork and press the **.** key. Drag your folder into the file list,
then use the Source Control tab to commit.

### 3. Open a pull request
On your fork's page, click **Contribute → Open pull request** (or
**Compare & pull request**). Check that it targets `kamiosmodules/module-store`
on `main`, then click **Create pull request**. Put the module's name and a
short line about what it does in the title or description.

### 4. Wait for review
An owner will look at your module. They may ask for changes, for example a
better description or a missing field. Make the change in your fork and push
again, and the pull request updates itself. Once it is merged, your module
appears in the store after about a minute or two.

### Updating your module later
Change the files in your module's folder, open a pull request again, and the
store rebuilds the zip when it is merged.

## Rules

- Only add or change **your own** module folder. Don't edit other people's modules.
- **Don't edit `modules.json`.** It is generated automatically.
- Everything must be safe to install. No hidden or harmful code, and don't
  upload anything you don't have the right to share.
- Use clear names and a real description so people know what the module does.
- Keep the module small. Large unnecessary files slow down downloads for everyone.

## Testing before you submit 

You must test your module in your own phone before pushing it

______________________________________________________________________________________________________________________________________________________________________________________________________________

Made with care by the KamiOS Team.

Join the community on Telegram: https://t.me/kamiosmodules | https://t.me/kamiosofficial

KamiOS. Released under open-source terms.


