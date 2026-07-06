# SPDX-License-Identifier: GPL-2.0-or-later

"""Custom icon loading.

Blender's UI only accepts built-in icon enum identifiers for the `icon=`
argument; custom icons must be pre-rendered PNGs loaded through
bpy.utils.previews and referenced by `icon_value=`. SVGs (e.g. the ones in
icons/) are the design source and are not loaded directly — export a PNG
alongside each SVG (32x32 matches Blender's own icon size).

Usage:
    from ..core.icons import get_icon
    col.operator("wpat.foo", icon_value=get_icon("foo"))
"""

from pathlib import Path

import bpy.utils.previews

_ICONS_DIR = Path(__file__).parent.parent / "icons"
_preview_collection = None


def register():
    global _preview_collection
    _preview_collection = bpy.utils.previews.new()
    for path in _ICONS_DIR.glob("*.png"):
        _preview_collection.load(path.stem, str(path), 'IMAGE')


def unregister():
    global _preview_collection
    if _preview_collection is not None:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None


def get_icon(name: str) -> int:
    """Return the icon_id of icons/<name>.png for use as icon_value=.

    Returns 0 (Blender's "no icon") if *name* has no matching loaded PNG.
    """
    if _preview_collection is None or name not in _preview_collection:
        return 0
    return _preview_collection[name].icon_id
