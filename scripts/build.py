#!/usr/bin/env python3
"""Zip every folder in modules/ and regenerate modules.json.

Each module folder needs a module.json (KamiOS format) or a module.prop with
id, name, author and description. version defaults to 1.0.

    build.py                  zip the modules, write modules.json (run before the zips are uploaded)
    build.py --refresh-counts only update the download numbers in modules.json (no zips, run on a schedule)
"""
import json, os, subprocess, sys, urllib.request, zipfile, datetime

BRANCH = os.environ.get("STORE_BRANCH", "main")
IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif")

REPO = os.environ.get("GITHUB_REPOSITORY", "USER/module-store")
TAG = os.environ.get("RELEASE_TAG", "latest")
OUT = "out"
REQUIRED = ["id", "name", "version", "author", "description"]
DEFAULT_VERSION = "1.0"

def read_prop(path):
    prop = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                prop[k.strip()] = v.strip()
    return prop

# The categories the phone knows (the filter of the store). A module names one in its module.json ("category") or in
# module.prop (category=). A missing or unknown one is left out of the index and the phone lists the module under "Other".
CATEGORIES = ("theme", "launcher", "tweak", "sounds", "bootanimation", "emoji", "fonts", "wallpaper", "icons", "apps",
              "quicksettings", "pill", "volume", "lockscreen")

def clean_category(value):
    value = str(value).strip().lower() if value else ""
    return value if value in CATEGORIES else None

def last_changed(folder):
    """The date (YYYY-MM-DD) of the last commit that touched the folder; needs the whole history (fetch-depth: 0)."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", folder], capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None

def read_meta(folder):
    """KamiOS module.json first, module.prop as a fallback."""
    jpath = os.path.join(folder, "module.json")
    if os.path.isfile(jpath):
        with open(jpath, encoding="utf-8") as f:
            j = json.load(f)
        # In module.json, "version" is the file-format version (a number),
        # so the module's own version comes from "module_version" if present.
        meta = {k: str(j.get(k, "")).strip() for k in ("id", "name", "author", "description")}
        meta["version"] = str(j.get("module_version", "")).strip() or DEFAULT_VERSION
        meta["category"] = j.get("category")
        if not meta["category"]:
            # a store-only category in module.prop: a phone that does not know the new ids yet rejects them in module.json
            ppath = os.path.join(folder, "module.prop")
            if os.path.isfile(ppath):
                meta["category"] = read_prop(ppath).get("category")
        return meta
    ppath = os.path.join(folder, "module.prop")
    if os.path.isfile(ppath):
        prop = read_prop(ppath)
        prop.setdefault("version", DEFAULT_VERSION)
        return prop
    return None

def raw(d, rel):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/modules/{d}/{rel}"

def find_media(folder, d):
    """Optional: thumbnail.(png|jpg|webp) and a screenshots/ folder. No config needed."""
    thumb, shots = None, []
    for fn in sorted(os.listdir(folder)):
        name, ext = os.path.splitext(fn.lower())
        if name == "thumbnail" and ext in IMG:
            thumb = raw(d, fn)
    sdir = os.path.join(folder, "screenshots")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            if os.path.splitext(fn.lower())[1] in IMG:
                shots.append(raw(d, "screenshots/" + fn))
    return thumb, shots

def is_media(rel):
    rel = rel.replace("\\", "/")
    name, ext = os.path.splitext(rel.lower())
    return rel.startswith("screenshots/") or (name == "thumbnail" and ext in IMG)

# Download numbers. GitHub counts the downloads of a release file, but the workflow uploads fresh zips on every build and a new
# file starts at 0. So downloads.json keeps, for each module, "base" (what the retired files had) plus the file that is online now
# ("asset" is its id, "count" the highest number seen for it). Seeing the same file twice never counts twice; the last look at an old
# file happens right before the build replaces it, so only the downloads of the last minutes are lost.
STATE = "downloads.json"

def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")

def live_assets():
    """{module id: (asset id, download count)} of the files on the release, or None when GitHub cannot be asked."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "module-store-build"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            assets = json.load(r).get("assets", [])
    except (OSError, ValueError) as e:
        print(f"note: could not read the download counts ({e}); keeping the numbers from the last run")
        return None
    return {a["name"][:-4]: (a["id"], int(a.get("download_count", 0))) for a in assets if a.get("name", "").endswith(".zip")}

def update_counts(state, live):
    """Fold what GitHub reports now into the state."""
    for d, (asset, count) in (live or {}).items():
        s = state.setdefault(d, {"base": 0, "asset": asset, "count": 0})
        if s["asset"] == asset:
            s["count"] = max(s["count"], count)
        else:                       # the file was replaced: the old one is final
            s["base"] += s["count"]
            s["asset"], s["count"] = asset, count

def total(state, d):
    s = state.get(d)
    return s["base"] + s["count"] if s else 0

def refresh_counts():
    """Only the numbers: take modules.json as it is and update `downloads` in it."""
    state = load_state()
    update_counts(state, live_assets())
    with open("modules.json", encoding="utf-8") as f:
        index = json.load(f)
    for m in index["modules"]:
        m["downloads"] = total(state, m["id"])
    save_state(state)
    with open("modules.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"updated the download numbers of {len(index['modules'])} module(s)")

def main():
    os.makedirs(OUT, exist_ok=True)
    modules, errors = [], []
    state = load_state()
    update_counts(state, live_assets())     # the files online now are replaced by this build: count them one last time
    for d in sorted(os.listdir("modules")):
        folder = os.path.join("modules", d)
        if not os.path.isdir(folder):
            continue
        prop = read_meta(folder)
        if prop is None:
            errors.append(f"{d}: needs a module.json (or module.prop)")
            continue
        missing = [k for k in REQUIRED if not prop.get(k)]
        if missing:
            errors.append(f"{d}: missing {', '.join(missing)}")
            continue
        if prop["id"] != d:
            errors.append(f"{d}: id '{prop['id']}' must match the folder name")
            continue
        zip_path = os.path.join(OUT, f"{d}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(folder):
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, folder)
                    if is_media(rel):
                        continue  # store art stays out of the module zip
                    z.write(full, rel)
        entry = {k: prop[k] for k in REQUIRED}
        category = clean_category(prop.get("category"))
        if category:
            entry["category"] = category
        changed = last_changed(folder)
        if changed:
            entry["updated"] = changed
        entry["download"] = f"https://github.com/{REPO}/releases/download/{TAG}/{d}.zip"
        thumb, shots = find_media(folder, d)
        entry["downloads"] = total(state, d)
        entry["thumbnail"] = thumb      # null when the module has none
        entry["screenshots"] = shots    # empty list when the module has none
        modules.append(entry)
        print(f"ok  {d} v{prop['version']}")
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    save_state(state)
    index = {"updated": datetime.date.today().isoformat(), "modules": modules}
    with open("modules.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote modules.json with {len(modules)} module(s)")

if __name__ == "__main__":
    if "--refresh-counts" in sys.argv[1:]:
        refresh_counts()
    else:
        main()
