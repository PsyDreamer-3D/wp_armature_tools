# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import rna_keymap_ui

from ..operators.bone_layers import WPAT_OT_bone_layers_popup


class WPATPreferences(bpy.types.AddonPreferences):
    # bl_idname must be the top-level add-on package name, not this submodule's
    # __name__ — __package__ here is "wp_armature_tools.properties", so take
    # its first component regardless of nesting depth.
    bl_idname = __package__.split(".")[0]

    def draw(self, context):
        layout = self.layout
        layout.label(text="Keymap:")

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            layout.label(text="Keyconfig not available.", icon='ERROR')
            return

        # The keymap is registered under "3D View" (see operators/__init__.py).
        km = kc.keymaps.get("3D View")
        if not km:
            layout.label(text="3D View keymap not registered yet.", icon='INFO')
            return

        col = layout.column()
        for kmi in km.keymap_items:
            if kmi.idname == WPAT_OT_bone_layers_popup.bl_idname:
                rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

        layout.separator()
        layout.label(
            text=(
                "When the active rig is a CloudRig rig, this shortcut passes "
                "through to CloudRig's own handler automatically."
            ),
            icon='INFO',
        )
