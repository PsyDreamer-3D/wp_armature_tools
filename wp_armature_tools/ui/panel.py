# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.icons import get_icon
from ..core.utils import _any_solo_active, _USE_BONE_COLLECTIONS, get_armature_object, is_cloudrig


class WPAT_PT_armature_panel(bpy.types.Panel):
    bl_label = "Armature"
    bl_idname = "WPAT_PT_armature_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature"
    bl_context = "weightpaint"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        arm_obj = get_armature_object(context)

        if arm_obj is None:
            layout.label(text="No Armature modifier found", icon='ERROR')
            return

        arm      = arm_obj.data
        is_pose  = arm.pose_position == 'POSE'
        cloudrig = is_cloudrig(arm_obj)

        # ── Armature identity ──────────────────────────────────────────────
        box = layout.box()
        row = box.row()
        row.label(text=arm_obj.name, icon='ARMATURE_DATA')
        if cloudrig:
            row.label(text="CloudRig", icon='FUND')

        # ── Pose Position ─────────────────────────────────────────────────
        col = layout.column(align=True)
        col.label(text="Pose Position:")
        row = col.row(align=True)
        row.prop_enum(arm, "pose_position", 'POSE')
        row.prop_enum(arm, "pose_position", 'REST')

        toggle_label = "→ Switch to Rest" if is_pose else "→ Switch to Pose"
        toggle_icon  = 'OUTLINER_DATA_ARMATURE' if is_pose else 'POSE_HLT'
        col.operator("wpat.toggle_pose_position", text=toggle_label, icon=toggle_icon)

        layout.separator()

        # ── Bone layers / collections (skipped for CloudRig rigs) ─────────
        if not cloudrig:
            col = layout.column(align=True)
            col.label(text="Bone Layers / Collections:")
            row = col.row(align=True)
            row.operator("wpat.bone_layers_popup", text="Show Layers  [M]", icon='BONE_DATA')
            if _USE_BONE_COLLECTIONS:
                clear = row.row(align=True)
                clear.enabled = _any_solo_active(arm)
                clear.operator("wpat.clear_solo", text="", icon='X')
            layout.separator()

        # ── Pose utilities ────────────────────────────────────────────────
        col = layout.column(align=True)
        col.label(text="Pose Utilities:")
        sub = col.column(align=True)
        sub.enabled = is_pose
        sub.operator("wpat.clear_bone_transforms", icon='LOOP_BACK')
        sub.operator("wpat.apply_pose_as_rest", icon='ARMATURE_DATA')

        layout.separator()

        # ── Weight utilities ──────────────────────────────────────────────
        col = layout.column(align=True)
        col.label(text="Weight Utilities:")
        col.operator("wpat.assign_automatic_from_bones", icon='ARMATURE_DATA')
        col.operator("wpat.assign_automatic_from_envelopes", icon_value=get_icon("assign_automatic_from_envelopes"))
        col.operator("wpat.normalize_all_weights",  icon='MOD_VERTEX_WEIGHT')
        col.operator("wpat.split_coaxial_weights",  icon='BONE_DATA')

        layout.separator()

        # ── Viewport display ──────────────────────────────────────────────
        col = layout.column(align=True)
        col.label(text="Viewport Display:")

        col.prop(arm, "display_type", text="Display As")

        sub = col.column(align=True)
        sub.prop(arm, "show_names",              text="Names")
        sub.prop(arm, "show_bone_custom_shapes", text="Shapes")
        if _USE_BONE_COLLECTIONS:
            sub.prop(arm, "show_bone_colors",    text="Bone Colors")
        sub.prop(arm_obj, "show_in_front",       text="In Front")

        axes_row = col.row(align=True)
        axes_row.prop(arm, "show_axes", text="Axes")
        if _USE_BONE_COLLECTIONS:
            sub_axes = axes_row.row(align=True)
            sub_axes.active = arm.show_axes
            sub_axes.prop(arm, "axes_position", text="Position", slider=True)

        if _USE_BONE_COLLECTIONS:
            col.row(align=True).prop(arm, "relation_line_position", text="Relations", expand=True)
