# SPDX-License-Identifier: GPL-2.0-or-later

from .preferences import WPATPreferences

classes = (
    WPATPreferences,
)


def register():
    import bpy
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
