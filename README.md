# Module Store

A simple module repository. The ROM's settings app (or the website) reads
`modules.json`, shows each module with its description, and the Download
button links straight to the module zip on GitHub.

## How it works

1. Each module is a folder in `modules/` with a `module.prop`.
2. On every push, a GitHub Action zips each module, attaches the zips to the
   `latest` release, and rewrites `modules.json`.
3. The ROM app and the website read `modules.json`.

## Set it up

1. Create a new GitHub repo and push these files to `main`.
2. Settings > Actions > General > Workflow permissions: choose **Read and write permissions**.
3. Settings > Pages: deploy from branch `main`, folder `/ (root)`.
4. Push once (or run the workflow from the Actions tab). `modules.json` and the release get created.

Your links will be:

- Index for the ROM app: `https://raw.githubusercontent.com/OWNER/REPO/main/modules.json`
- Website: `https://OWNER.github.io/REPO/`
- A module zip: `https://github.com/OWNER/REPO/releases/download/latest/<id>.zip`

## Add a module

1. Copy `modules/hello-module` to `modules/<your-id>`.
2. Edit `module.prop` and add your files.
3. Commit and push. Done. Wait about a minute for the Action.

`module.prop` fields (all required):

```
id=my-module          # must match the folder name
name=My Module
version=1.0
author=yourname
description=One line on what it does.
```

Update a module by changing its files and bumping `version`.

## Thumbnail and screenshots (optional)

Drop images into the module folder. No config, the build detects them:

```
modules/my-module/
├── module.prop
├── thumbnail.png          # square icon, shown next to the name
└── screenshots/
    ├── 1.png
    └── 2.png
```

They show up in `modules.json` as `thumbnail` (a URL, or `null`) and
`screenshots` (a list of URLs, empty if none). They are left out of the module zip.

## Contributing

Fork, add your folder under `modules/`, open a pull request. Every module is
reviewed before merging because users install these on their phones.

## modules.json format

```json
{
  "updated": "2026-10-12",
  "modules": [
    {
      "id": "my-module",
      "name": "My Module",
      "version": "1.0",
      "author": "yourname",
      "description": "One line on what it does.",
      "download": "https://github.com/OWNER/REPO/releases/download/latest/my-module.zip",
      "thumbnail": "https://raw.githubusercontent.com/OWNER/REPO/main/modules/my-module/thumbnail.png",
      "screenshots": ["https://raw.githubusercontent.com/OWNER/REPO/main/modules/my-module/screenshots/1.png"]
    }
  ]
}
```
