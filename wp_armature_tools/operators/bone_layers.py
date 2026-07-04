# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.utils import (
    _any_solo_active,
    _USE_BONE_COLLECTIONS,
    get_armature_object,
    is_cloudrig,
    tag_redraw_all,
)


class WPAT_OT_clear_solo(bpy.types.Operator):
    """Disable solo on all bone collections"""
    bl_idname = "wpat.clear_solo"
    bl_label = "Clear Solo"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        arm_obj = get_armature_object(context)
        if arm_obj is None:
            return False
        return _any_solo_active(arm_obj.data)

    def execute(self, context):
        arm = get_armature_object(context).data
        for coll in arm.collections_all:
            coll.is_solo = False
        tag_redraw_all(context)
        return {'FINISHED'}


class WPAT_OT_bone_layers_popup(bpy.types.Operator):
    """Show bone layer/collection visibility + solo toggles.

    Registered on M in the "3D View" keymap.  The "Weight Paint" keymap is
    too narrow and misses some events; the broader "3D View" keymap fires in
    all modes.  poll() restricts execution to Weight Paint mode on a mesh
    that has a non-CloudRig armature modifier.

    Because addon keymaps run before built-in keymaps, returning False from
    poll() lets Blender fall through to CloudRig's handler (if present) or
    the default Move to Collection.
    """
    bl_idname = "wpat.bone_layers_popup"
    bl_label = "Bone Layers"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Only activate in Weight Paint mode.
        if context.mode != 'PAINT_WEIGHT':
            return False
        arm_obj = get_armature_object(context)
        if arm_obj is None:
            return False
        # Defer to CloudRig's own handler.
        if is_cloudrig(arm_obj):
            return False
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)

    # --- draw helpers -------------------------------------------------------

    @staticmethod
    def _draw_layers_3x(layout, arm):
        """32-layer bit grid for Blender < 4.0 (no native solo support)."""
        layout.label(text="Bone Layers:")
        col = layout.column(align=True)
        for row_start in range(0, 32, 8):
            row = col.row(align=True)
            for offset in range(8):
                idx = row_start + offset
                row.prop(arm, "layers", index=idx, text=str(idx + 1), toggle=True)

    @staticmethod
    def _draw_collections_4x(layout, arm):
        """Named BoneCollection list with native is_visible / is_solo toggles."""
        colls = arm.collections_all
        if not colls:
            layout.label(text="(no collections)", icon='INFO')
            return
        for coll in colls:
            row = layout.row(align=True)
            # Visibility toggle
            vis_icon = 'HIDE_OFF' if coll.is_visible else 'HIDE_ON'
            row.prop(coll, "is_visible", text=coll.name, toggle=True, icon=vis_icon)
            # Solo toggle — native is_solo property
            solo_icon = 'RADIOBUT_ON' if coll.is_solo else 'RADIOBUT_OFF'
            row.prop(coll, "is_solo", text="", toggle=True, icon=solo_icon)

    # --- draw / execute -----------------------------------------------------

    def draw(self, context):
        layout = self.layout
        arm_obj = get_armature_object(context)
        if arm_obj is None:
            layout.label(text="No armature found", icon='ERROR')
            return

        arm = arm_obj.data

        # Header: armature name + Clear Solo button
        header = layout.row(align=True)
        header.label(text=arm_obj.name, icon='ARMATURE_DATA')
        if _USE_BONE_COLLECTIONS:
            clear = header.row(align=True)
            clear.enabled = _any_solo_active(arm)
            clear.operator("wpat.clear_solo", text="Clear Solo", icon='X')

        layout.separator(factor=0.5)

        if _USE_BONE_COLLECTIONS:
            header_row = layout.row(align=True)
            header_row.label(text="Collection")
            header_row.label(text="S", icon='BLANK1')
            self._draw_collections_4x(layout, arm)
        else:
            self._draw_layers_3x(layout, arm)

    def execute(self, context):
        return {'FINISHED'}
