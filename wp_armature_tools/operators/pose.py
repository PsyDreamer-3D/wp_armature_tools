# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.utils import get_armature_object, tag_redraw_all


class WPAT_OT_toggle_pose_position(bpy.types.Operator):
    """Toggle the linked armature between Rest Position and Pose Position"""
    bl_idname = "wpat.toggle_pose_position"
    bl_label = "Toggle Rest / Pose Position"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_armature_object(context) is not None

    def execute(self, context):
        arm_obj = get_armature_object(context)
        arm = arm_obj.data
        arm.pose_position = 'REST' if arm.pose_position == 'POSE' else 'POSE'
        tag_redraw_all(context)
        self.report({'INFO'}, f"Armature '{arm_obj.name}': {arm.pose_position.title()} Position")
        return {'FINISHED'}


class WPAT_OT_clear_bone_transforms(bpy.types.Operator):
    """Clear location, rotation, and scale on selected bones (pose.transforms_clear)"""
    bl_idname = "wpat.clear_bone_transforms"
    bl_label = "Clear Bone Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        arm_obj = get_armature_object(context)
        return arm_obj is not None and arm_obj.data.pose_position == 'POSE'

    def execute(self, context):
        arm_obj  = get_armature_object(context)
        mesh_obj = context.active_object

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.transforms_clear()
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

        tag_redraw_all(context)
        self.report({'INFO'}, "Bone transforms cleared.")
        return {'FINISHED'}
