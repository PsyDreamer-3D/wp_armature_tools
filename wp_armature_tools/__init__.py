# SPDX-License-Identifier: GPL-2.0-or-later

# Legacy bl_info: still load-bearing, not just informational. blender_manifest.toml
# is only read by Blender's Extensions platform (4.2+); this add-on's declared
# blender_version_min is 3.0.0, and pre-4.2 Blender only recognizes add-ons via
# this dict. Do not remove it while that minimum stays below 4.2.
bl_info = {
    "name": "Weight Paint Armature Tools",
    "author": "Jess G.",
    "version": (1, 9, 0),
    "blender": (3, 0, 0),
    "location": "Weight Paint > Sidebar > Armature  |  M → Bone Layers popup",
    "description": (
        "Exposes armature operators and properties in Weight Paint mode. "
        "M opens a bone layer/collection visibility popup with solo support. "
        "Automatically defers to CloudRig on CloudRig-managed rigs. "
        "Shortcut is configurable under Add-on Preferences."
    ),
    "category": "Rigging",
}

# START — workflow remove
_needs_reload = "bpy" in locals()
# END — workflow remove

import bpy

from . import core, properties, operators, ui

# START — workflow remove
if _needs_reload:
    import sys, importlib

    all_modules = dict(sorted(sys.modules.items(), key=lambda x: x[0]))

    for k, v in all_modules.items():
        if v is not None and (k == __name__ or k.startswith(__name__ + ".")):
            importlib.reload(v)

del _needs_reload
# END — workflow remove


def register():
    core.register()
    properties.register()
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()
    core.unregister()


if __name__ == "__main__":
    register()
