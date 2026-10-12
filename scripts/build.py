#!/usr/bin/env python3
"""Zip every folder in modules/ and regenerate modules.json.

Each module folder needs a module.json (KamiOS format) or a module.prop with
id, name, author and description. version defaults to 1.0.
"""
import json, os, sys, zipfile, datetime

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

def main():
    os.makedirs(OUT, exist_ok=True)
    modules, errors = [], []
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
        entry["download"] = f"https://github.com/{REPO}/releases/download/{TAG}/{d}.zip"
        thumb, shots = find_media(folder, d)
        entry["thumbnail"] = thumb      # null when the module has none
        entry["screenshots"] = shots    # empty list when the module has none
        modules.append(entry)
        print(f"ok  {d} v{prop['version']}")
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    index = {"updated": datetime.date.today().isoformat(), "modules": modules}
    with open("modules.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote modules.json with {len(modules)} module(s)")

if __name__ == "__main__":
    main()
