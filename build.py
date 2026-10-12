#!/usr/bin/env python3
"""Zip every folder in modules/ and regenerate modules.json.

Each module folder needs a module.prop with at least id, name, version,
author and description (key=value, one per line).
"""
import json, os, sys, zipfile, datetime

BRANCH = os.environ.get("STORE_BRANCH", "main")
IMG = (".png", ".jpg", ".jpeg", ".webp")

REPO = os.environ.get("GITHUB_REPOSITORY", "USER/module-store")
TAG = os.environ.get("RELEASE_TAG", "latest")
OUT = "out"
REQUIRED = ["id", "name", "version", "author", "description"]

def read_prop(path):
    prop = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                prop[k.strip()] = v.strip()
    return prop

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
        prop_path = os.path.join(folder, "module.prop")
        if not os.path.isdir(folder):
            continue
        if not os.path.isfile(prop_path):
            errors.append(f"{d}: missing module.prop")
            continue
        prop = read_prop(prop_path)
        missing = [k for k in REQUIRED if not prop.get(k)]
        if missing:
            errors.append(f"{d}: module.prop missing {', '.join(missing)}")
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
