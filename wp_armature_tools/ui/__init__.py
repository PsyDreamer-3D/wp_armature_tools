# SPDX-License-Identifier: GPL-2.0-or-later

from .panel import WPAT_PT_armature_panel, WPAT_PT_bone_chain_pose, WPAT_PT_bone_chain_edit

classes = (
    WPAT_PT_armature_panel,
    WPAT_PT_bone_chain_pose,
    WPAT_PT_bone_chain_edit,
)


def register():
    import bpy
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
