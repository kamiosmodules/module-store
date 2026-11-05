#!/usr/bin/env python3
"""Build the KamiOS module index and release ZIPs.

Each module lives in modules/<id>/ and contains module.json or module.prop.
Store artwork (root thumbnail.* and the root screenshots/ directory) stays
in the repository for the website, but is excluded from installable ZIPs.

Usage:
    python3 scripts/build.py
    python3 scripts/build.py --refresh-counts
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

BRANCH = os.environ.get("STORE_BRANCH", "main")
REPO = os.environ.get("GITHUB_REPOSITORY", "USER/module-store")
TAG = os.environ.get("RELEASE_TAG", "latest")
OUT = Path("out")
STATE = Path("downloads.json")
IMG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SOUND_EXTENSIONS = {".wav", ".mp3", ".ogg", ".opus", ".m4a", ".aac", ".flac"}
REQUIRED = ("id", "name", "version", "author", "description")
DEFAULT_VERSION = "1.0"

CATEGORIES = (
    "theme", "launcher", "tweak", "sounds", "bootanimation", "emoji",
    "fonts", "wallpaper", "icons", "apps", "quicksettings", "pill",
    "volume", "lockscreen",
)

# Root-level fields that represent a single style component. Combining one of
# these with unrelated module behaviour makes the module a theme.
STYLE_FIELDS = {
    "fonts": "fonts",
    "wallpaper": "wallpaper",
    "accent": "accent",
    "accent_style": "accent",
    "icons": "icons",
    "icon_pack": "icons",
    "sounds": "sounds",
    "bootanimation": "bootanimation",
    "emoji": "emoji",
}
STYLE_LABELS = {
    "fonts": "fonts",
    "wallpaper": "wallpaper",
    "accent": "accent",
    "icons": "icons",
    "sounds": "sounds",
    "bootanimation": "bootanimation",
    "emoji": "emoji",
}
METADATA_FIELDS = {
    "format", "version", "id", "name", "author", "description",
    "module_version", "category", "group", "restart", "min_rom_version",
    "max_rom_version", "devices", "roms", "compatibility",
}
FEATURE_CONFIG_FIELDS = {"targets", "overlays", "settings", "_knobs"}
THEME_STYLE_PARTS = {"fonts", "wallpaper", "accent", "icons", "sounds", "bootanimation"}


def read_prop(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open(encoding="utf-8") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def read_meta(folder: Path) -> dict[str, Any] | None:
    """Read module.json first, with module.prop as a metadata/category fallback."""
    json_path = folder / "module.json"
    prop_path = folder / "module.prop"

    prop = read_prop(prop_path) if prop_path.is_file() else {}

    if json_path.is_file():
        with json_path.open(encoding="utf-8") as stream:
            manifest = json.load(stream)
        if not isinstance(manifest, dict):
            raise ValueError(f"{json_path} must contain a JSON object")

        category_value = manifest.get("category")
        if category_value is None or not str(category_value).strip():
            category_value = prop.get("category")

        return {
            "id": str(manifest.get("id", "")).strip(),
            "name": str(manifest.get("name", "")).strip(),
            "author": str(manifest.get("author", "")).strip(),
            "description": str(manifest.get("description", "")).strip(),
            "version": str(manifest.get("module_version", "")).strip() or DEFAULT_VERSION,
            "category": category_value,
            "_manifest": manifest,
            "_has_explicit_category": category_value not in (None, ""),
        }

    if prop_path.is_file():
        prop.setdefault("version", DEFAULT_VERSION)
        return {
            "id": prop.get("id", "").strip(),
            "name": prop.get("name", "").strip(),
            "author": prop.get("author", "").strip(),
            "description": prop.get("description", "").strip(),
            "version": prop.get("version", DEFAULT_VERSION).strip() or DEFAULT_VERSION,
            "category": prop.get("category"),
            "_manifest": {},
            "_has_explicit_category": bool(prop.get("category", "").strip()),
        }

    return None


def clean_category(value: Any) -> str | None:
    value = str(value).strip().lower() if value is not None else ""
    return value if value in CATEGORIES else None


def module_files(folder: Path) -> list[str]:
    return [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]


def infer_category(meta: dict[str, Any], folder: Path) -> str:
    """Infer a category from the KamiOS manifest and the module's files.

    The manifest's target-resource names are used for pill, volume, quick
    settings and lock-screen modules. Explicit categories are handled by
    resolve_category() and always take precedence over this inference.
    """
    manifest = meta.get("_manifest") or {}
    all_paths = module_files(folder)
    paths = [path.lower() for path in all_paths]
    path_parts = {part for path in paths for part in path.split("/")}
    basenames = {Path(path).name for path in paths}

    style_parts: set[str] = set()
    for field, category in STYLE_FIELDS.items():
        if field in manifest and manifest.get(field) not in (None, "", {}, []):
            style_parts.add(category)

    # File-layout fallback for modules whose manifests point at assets without
    # declaring a corresponding top-level style field.
    if (
        "sounds" in path_parts
        or any("/audio/" in f for f in paths)
        or any(Path(path).suffix.lower() in SOUND_EXTENSIONS for path in all_paths)
    ):
        style_parts.add("sounds")
    if "bootanimation.zip" in basenames or "bootanimation" in path_parts:
        style_parts.add("bootanimation")
    emoji_files = any("emoji" in Path(path).name or "emoji" in path_parts for path in paths)
    has_non_emoji_font = any(
        Path(path).suffix in {".ttf", ".otf", ".ttc"} and "emoji" not in Path(path).name
        for path in paths
    )
    if (
        ("fonts" in manifest and (not emoji_files or has_non_emoji_font))
        or has_non_emoji_font
        or ("fonts" in path_parts and not emoji_files)
    ):
        style_parts.add("fonts")
    if "wallpaper" in path_parts or any(Path(path).name.startswith("wallpaper.") for path in paths):
        style_parts.add("wallpaper")
    if "icons" in path_parts or "icon_pack" in manifest:
        style_parts.add("icons")
    if emoji_files:
        style_parts.add("emoji")
    options = manifest.get("options")
    if isinstance(options, dict) and "accent" in options and options.get("accent") not in (None, "", {}, []):
        style_parts.add("accent")

    # Count distinct Android package targets. Three or more means this is a
    # cross-app theme, regardless of which individual resources are touched.
    packages: set[str] = set()
    targets = manifest.get("targets")
    if isinstance(targets, dict):
        target_packages = targets.keys()
    elif isinstance(targets, list):
        target_packages = targets
    else:
        target_packages = ()
    for package in target_packages:
        if isinstance(package, str) and "." in package and package.lower() != "android":
            packages.add(package)

    apps = manifest.get("apps")
    if isinstance(apps, list):
        for app in apps:
            if isinstance(app, str):
                package = app
            elif isinstance(app, dict):
                package = app.get("package") or app.get("packageName") or app.get("id")
            else:
                package = None
            if isinstance(package, str) and "." in package and package.lower() != "android":
                packages.add(package)
    if len(packages) >= 3:
        return "theme"

    # A home app is a Launcher unless it also brings fonts or wallpaper. Check
    # common manifest fields and app records; filename hints cover simple APK
    # bundles where the manifest does not identify the home app explicitly.
    has_home_app = bool(manifest.get("home_app")) or bool(manifest.get("launcher"))
    if not has_home_app and isinstance(apps, list):
        for app in apps:
            if isinstance(app, str):
                app_role = app.lower()
                is_home = "launcher" in app_role or "home" in app_role
            elif isinstance(app, dict):
                app_role = " ".join(
                    str(app.get(key, ""))
                    for key in ("type", "role", "category", "name", "package", "packageName")
                ).lower()
                is_home = bool(app.get("is_home_app") or app.get("is_launcher") or "launcher" in app_role)
            else:
                is_home = False
            if is_home:
                has_home_app = True
                break
    if not has_home_app:
        has_home_app = any(
            Path(path).suffix == ".apk"
            and any(token in Path(path).name.lower() for token in ("launcher", "home"))
            for path in all_paths
        )
    if has_home_app:
        if "fonts" in style_parts or "wallpaper" in style_parts:
            return "theme"
        return "launcher"

    # Recognise narrow KamiOS areas from resource/setting names in targets,
    # overlays, settings and _knobs. Unrecognised resource keys are evidence
    # that the module does more than that one narrow feature.
    resource_names: list[str] = []
    knob_groups: list[str] = []

    def collect_resource_names(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key).lower()
                if "/" in key_text or key_text.startswith("kami_"):
                    resource_names.append(key_text)
                collect_resource_names(child)
        elif isinstance(value, list):
            for child in value:
                collect_resource_names(child)

    for key in ("targets", "overlays", "settings", "options"):
        collect_resource_names(manifest.get(key))
    knobs = manifest.get("_knobs")
    if isinstance(knobs, list):
        for knob in knobs:
            if not isinstance(knob, dict):
                continue
            if knob.get("resource"):
                resource_names.append(str(knob["resource"]).lower())
            if knob.get("group"):
                knob_groups.append(str(knob["group"]).lower())

    feature_categories: set[str] = set()
    unclassified_resource = False
    for resource in resource_names:
        matched: set[str] = set()
        if re.search(r"pill", resource):
            matched.add("pill")
        if re.search(r"volume_(dialog|slider|ringer|panel)|volume_panel|kami_volume", resource):
            matched.add("volume")
        if re.search(r"keyguard|lock.?screen|lockscreen", resource):
            matched.add("lockscreen")
        if re.search(r"quick.?settings|qs_|common_tile|brightness_slider|footer_button|shade_panel|tile_", resource):
            matched.add("quicksettings")
        feature_categories.update(matched)
        if not matched and re.match(r"(bool|color|dimen|drawable|font|integer|layout|mipmap|raw|string|style|xml|system)/", resource):
            unclassified_resource = True
    for group in knob_groups:
        if "pill" in group:
            feature_categories.add("pill")
        if "volume" in group:
            feature_categories.add("volume")
        if "lock" in group:
            feature_categories.add("lockscreen")
        if "quick setting" in group or "quicksettings" in group or group == "qs":
            feature_categories.add("quicksettings")

    # Recognise resource-named asset folders as a fallback.
    for part in path_parts:
        if part in {"pill", "volume", "lockscreen", "quicksettings", "quick_settings"}:
            feature_categories.add("quicksettings" if part == "quick_settings" else part)

    non_feature_fields = set(manifest) - METADATA_FIELDS - set(STYLE_FIELDS) - FEATURE_CONFIG_FIELDS - {"home_app", "launcher"}
    has_non_feature_behaviour = any(
        manifest.get(key) not in (None, "", {}, [], False) for key in non_feature_fields
    )

    if len(feature_categories) > 1:
        return "theme"
    if feature_categories:
        feature_category = next(iter(feature_categories))
        if style_parts or unclassified_resource or has_non_feature_behaviour:
            return "theme"
        return feature_category

    # A style component plus other module behaviour is a theme. Emoji is a
    # dedicated category, but is not by itself one of the style-part signals
    # specified for this rule.
    theme_style_parts = style_parts & THEME_STYLE_PARTS
    if len(theme_style_parts) > 1:
        return "theme"

    # targets/settings/overlays count as additional behaviour for a style
    # module; descriptive metadata and the style field itself do not.
    other_fields = set(manifest) - METADATA_FIELDS - set(STYLE_FIELDS) - {"home_app", "launcher"}
    has_other_behaviour = any(
        manifest.get(key) not in (None, "", {}, [], False) for key in other_fields
    )
    if theme_style_parts and (len(style_parts) > 1 or has_other_behaviour):
        return "theme"

    if len(style_parts) == 1:
        return next(iter(style_parts))

    # The store's default is Tweaks. Apps remains an available explicit
    # category, but app-only modules are not inferred as Apps automatically.
    return "tweak"

def resolve_category(meta: dict[str, Any], folder: Path) -> str | None:
    raw_category = meta.get("category")
    if raw_category is not None and str(raw_category).strip():
        category = clean_category(raw_category)
        if category is None:
            print(
                f"WARNING {folder.name}: unsupported category {raw_category!r}; "
                "ignoring it and listing the module under Other"
            )
        return category
    return infer_category(meta, folder)


def raw(module_id: str, relative_path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/modules/"
        f"{module_id}/{relative_path}"
    )


def find_media(folder: Path, module_id: str) -> tuple[str | None, list[str]]:
    thumbnail: str | None = None
    screenshots: list[str] = []

    for path in folder.iterdir():
        if not path.is_file():
            continue
        if path.stem.lower() == "thumbnail" and path.suffix.lower() in IMG_EXTENSIONS:
            thumbnail = raw(module_id, path.name)

    screenshots_dir = folder / "screenshots"
    if screenshots_dir.is_dir():
        for path in sorted(screenshots_dir.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file() and path.suffix.lower() in IMG_EXTENSIONS:
                screenshots.append(raw(module_id, f"screenshots/{path.name}"))

    return thumbnail, screenshots


def is_store_media(relative_path: str) -> bool:
    """Exclude only root thumbnail.* and the root screenshots/ directory."""
    normalized = relative_path.replace("\\", "/")
    lowered = normalized.lower()
    if lowered == "screenshots" or lowered.startswith("screenshots/"):
        return True
    if "/" not in normalized:
        stem = Path(normalized).stem.lower()
        suffix = Path(normalized).suffix.lower()
        return stem == "thumbnail" and suffix in IMG_EXTENSIONS
    return False


def last_changed(folder: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(folder)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def load_state() -> dict[str, Any]:
    try:
        with STATE.open(encoding="utf-8") as stream:
            value = json.load(stream)
            return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: dict[str, Any]) -> None:
    with STATE.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2, sort_keys=True)
        stream.write("\n")


def live_assets() -> dict[str, tuple[int, int]] | None:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "module-store-build"},
    )
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            assets = json.load(response).get("assets", [])
    except (OSError, ValueError) as error:
        print(f"note: could not read download counts ({error}); keeping previous numbers")
        return None
    return {
        asset["name"][:-4]: (asset["id"], int(asset.get("download_count", 0)))
        for asset in assets
        if asset.get("name", "").endswith(".zip")
    }


def update_counts(state: dict[str, Any], live: dict[str, tuple[int, int]] | None) -> None:
    for module_id, (asset_id, count) in (live or {}).items():
        record = state.setdefault(module_id, {"base": 0, "asset": asset_id, "count": 0})
        if record.get("asset") == asset_id:
            record["count"] = max(int(record.get("count", 0)), count)
        else:
            record["base"] = int(record.get("base", 0)) + int(record.get("count", 0))
            record["asset"] = asset_id
            record["count"] = count


def total_downloads(state: dict[str, Any], module_id: str) -> int:
    record = state.get(module_id)
    return int(record.get("base", 0)) + int(record.get("count", 0)) if record else 0


def refresh_counts() -> None:
    state = load_state()
    update_counts(state, live_assets())
    with Path("modules.json").open(encoding="utf-8") as stream:
        index = json.load(stream)
    for module in index.get("modules", []):
        module["downloads"] = total_downloads(state, module["id"])
    save_state(state)
    with Path("modules.json").open("w", encoding="utf-8") as stream:
        json.dump(index, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(f"updated download numbers for {len(index.get('modules', []))} module(s)")


def main() -> None:
    modules_dir = Path("modules")
    if not modules_dir.is_dir():
        raise SystemExit("ERROR: modules/ directory does not exist")

    OUT.mkdir(parents=True, exist_ok=True)
    for old_zip in OUT.glob("*.zip"):
        old_zip.unlink()

    modules: list[dict[str, Any]] = []
    errors: list[str] = []
    state = load_state()
    update_counts(state, live_assets())

    for folder in sorted(modules_dir.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        try:
            meta = read_meta(folder)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{folder.name}: cannot read metadata ({error})")
            continue

        if meta is None:
            errors.append(f"{folder.name}: needs module.json or module.prop")
            continue

        missing = [key for key in REQUIRED if not meta.get(key)]
        if missing:
            errors.append(f"{folder.name}: missing {', '.join(missing)}")
            continue
        if meta["id"] != folder.name:
            errors.append(f"{folder.name}: id {meta['id']!r} must match the folder name")
            continue

        archive_path = OUT / f"{folder.name}.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"{path}: symbolic links are not allowed in modules")
                if not path.is_file():
                    continue
                relative = path.relative_to(folder).as_posix()
                if is_store_media(relative):
                    continue
                archive.write(path, relative)

        category = resolve_category(meta, folder)
        entry = {key: meta[key] for key in REQUIRED}
        if category:
            entry["category"] = category
        changed = last_changed(folder)
        if changed:
            entry["updated"] = changed
        entry["download"] = f"https://github.com/{REPO}/releases/download/{TAG}/{folder.name}.zip"
        thumbnail, screenshots = find_media(folder, folder.name)
        entry["downloads"] = total_downloads(state, folder.name)
        entry["thumbnail"] = thumbnail
        entry["screenshots"] = screenshots
        modules.append(entry)
        print(f"ok  {folder.name} v{meta['version']} [{category or 'Other'}]")

    if errors:
        print("\n".join("ERROR " + error for error in errors))
        raise SystemExit(1)

    save_state(state)
    index = {"updated": datetime.date.today().isoformat(), "modules": modules}
    with Path("modules.json").open("w", encoding="utf-8") as stream:
        json.dump(index, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(f"wrote modules.json with {len(modules)} module(s)")


if __name__ == "__main__":
    if "--refresh-counts" in sys.argv[1:]:
        refresh_counts()
    else:
        main()
