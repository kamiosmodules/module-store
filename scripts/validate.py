#!/usr/bin/env python3
"""Validate module folders before the store is built.

Unsupported category values are warnings, not errors: those modules are kept
and appear under Other. A missing category is inferred by build.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from build import CATEGORIES, infer_category, read_meta

MODULES = Path("modules")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REQUIRED = ("id", "name", "author", "description")
PLACEHOLDERS = {"what it does", "module description", "description", "todo", "tbd"}


def main() -> int:
    if not MODULES.is_dir():
        print("ERROR: modules/ directory does not exist")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    for folder in sorted(MODULES.iterdir(), key=lambda path: path.name.lower()):
        if not folder.is_dir():
            continue
        checked += 1
        try:
            meta = read_meta(folder)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{folder.name}: cannot read metadata ({error})")
            continue

        if meta is None:
            errors.append(f"{folder.name}: missing module.json or module.prop")
            continue

        symlinks = [path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_symlink()]
        for relative in symlinks:
            errors.append(f"{folder.name}: symbolic link is not allowed ({relative})")

        for key in REQUIRED:
            value = str(meta.get(key, "")).strip()
            if not value:
                errors.append(f"{folder.name}: missing {key}")
            elif key == "description" and value.lower() in PLACEHOLDERS:
                errors.append(f"{folder.name}: description is still a placeholder")

        module_id = str(meta.get("id", "")).strip()
        if module_id and not ID_PATTERN.fullmatch(module_id):
            errors.append(f"{folder.name}: invalid module id {module_id!r}")
        if module_id and module_id != folder.name:
            errors.append(f"{folder.name}: id {module_id!r} must match the folder name")

        raw_category = meta.get("category")
        if raw_category is not None and str(raw_category).strip():
            normalized = str(raw_category).strip().lower()
            if normalized not in CATEGORIES:
                warnings.append(
                    f"{folder.name}: unsupported category {raw_category!r}; ignored, module will appear under Other"
                )
            else:
                print(f"OK      {folder.name}: category={normalized}")
        else:
            inferred = infer_category(meta, folder)
            print(f"INFER   {folder.name}: category={inferred}")

    for warning in warnings:
        print("WARNING " + warning)
    for error in errors:
        print("ERROR   " + error)

    print(
        f"\nValidation complete: {checked} module(s), "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
