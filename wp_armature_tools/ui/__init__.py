# SPDX-License-Identifier: GPL-2.0-or-later

from .panel import WPAT_PT_armature_panel

classes = (
    WPAT_PT_armature_panel,
)


def register():
    import bpy
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
