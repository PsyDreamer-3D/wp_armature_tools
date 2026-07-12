# SPDX-License-Identifier: GPL-2.0-or-later

from .bone_layers import WPAT_OT_clear_solo, WPAT_OT_bone_layers_popup
from .pose import (
    WPAT_OT_toggle_pose_position,
    WPAT_OT_clear_bone_transforms,
)
from .weights import WPAT_OT_normalize_all_weights, WPAT_OT_split_coaxial_weights, WPAT_OT_assign_automatic_from_bones, WPAT_OT_assign_automatic_from_envelopes

classes = (
    WPAT_OT_clear_solo,
    WPAT_OT_bone_layers_popup,
    WPAT_OT_toggle_pose_position,
    WPAT_OT_clear_bone_transforms,
    WPAT_OT_assign_automatic_from_bones,
    WPAT_OT_assign_automatic_from_envelopes,
    WPAT_OT_normalize_all_weights,
    WPAT_OT_split_coaxial_weights,
)

# Accumulated keymap entries for clean unregister.
_addon_keymaps: list = []


def register():
    import bpy

    for cls in classes:
        bpy.utils.register_class(cls)

    # Register M in the "3D View" keymap, NOT the mode-specific "Weight Paint"
    # keymap.  The "Weight Paint" keymap is limited to paint-tool events and
    # swallows/ignores many key presses (CloudRig had the same issue, see
    # their changelog: "Fix Bone Collections pop-up (Shift+M) not working
    # in Weight Paint mode").
    #
    # Using "3D View" means the shortcut fires in any mode; poll() restricts
    # it to Weight Paint on a non-CloudRig mesh.  When poll() returns False,
    # Blender falls through to CloudRig's handler or the built-in default.
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            WPAT_OT_bone_layers_popup.bl_idname,
            type='M',
            value='PRESS',
        )
        _addon_keymaps.append((km, kmi))


def unregister():
    import bpy

    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
