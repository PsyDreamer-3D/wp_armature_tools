# SPDX-License-Identifier: GPL-2.0-or-later

import bpy


def _walk_chain(active_bone):
    """Return the set of bones forming the connected chain through
    active_bone. Works for both Bone (pose/weight paint) and EditBone
    (edit mode) since both expose .parent, .children, .use_connect."""
    chain = {active_bone}

    # Root-ward: always a single path - a bone has exactly one parent,
    # so there's no branching to worry about in this direction.
    current = active_bone
    while current.use_connect and current.parent is not None:
        current = current.parent
        chain.add(current)

    # Tip-ward: only continue through an unambiguous single connected
    # child. Two or more connected children means we've hit a branch -
    # stop there rather than guessing which side to follow.
    current = active_bone
    while True:
        connected_children = [
            c for c in current.children
            if c.use_connect and c.parent == current
        ]
        if len(connected_children) != 1:
            break
        current = connected_children[0]
        chain.add(current)

    return chain


def _set_selected(bone, value):
    bone.select = value
    bone.select_head = value
    bone.select_tail = value


class WPAT_OT_select_bone_chain(bpy.types.Operator):
    """Select the connected bone chain through the active bone (stops at
    branches or unconnected joins)"""
    bl_idname = "wpat.select_bone_chain"
    bl_label = "Select Bone Chain"
    bl_options = {'REGISTER', 'UNDO'}

    extend: bpy.props.BoolProperty(
        name="Extend",
        description="Extend the current selection instead of replacing it",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_ARMATURE':
            return context.active_bone is not None
        if context.mode == 'POSE':
            return context.active_pose_bone is not None
        if context.mode == 'PAINT_WEIGHT':
            # context.pose_object is only populated when weight paint's
            # bone-select mode is active against a deforming armature.
            # active_pose_bone (not active_bone) is what's actually kept in
            # sync with click-selection in Pose/weight-paint bone-select -
            # it's also what backs PoseBone.select, which is what execute()
            # mutates for these two modes.
            return context.pose_object is not None and context.active_pose_bone is not None
        return False

    def execute(self, context):
        # EditBone exposes select/select_head/select_tail directly, so the
        # Edit Armature branch can walk and mutate the same Bone-like object.
        # Bone (the Pose/weight-paint data-block) has no selection attributes
        # at all - only its corresponding PoseBone.select does - so those two
        # modes walk the chain via Bone (for .parent/.children/.use_connect)
        # but write selection through the matching PoseBone by name instead.
        if context.mode == 'EDIT_ARMATURE':
            active = context.active_bone
        else:
            active_pose_bone = context.active_pose_bone
            active = active_pose_bone.bone if active_pose_bone else None

        if active is None:
            self.report({'WARNING'}, "No active bone")
            return {'CANCELLED'}

        chain = _walk_chain(active)

        if context.mode == 'EDIT_ARMATURE':
            bone_pool = context.object.data.edit_bones

            if not self.extend:
                for b in bone_pool:
                    _set_selected(b, False)
            for b in chain:
                _set_selected(b, True)

            # Preserve the original active bone - walking the chain
            # shouldn't change what subsequent operators (e.g. transform)
            # act on as active.
            bone_pool.active = active
        else:
            arm_obj = context.pose_object if context.mode == 'PAINT_WEIGHT' else context.object
            pose_bones = arm_obj.pose.bones

            if not self.extend:
                for pb in pose_bones:
                    pb.select = False
            for b in chain:
                pose_bones[b.name].select = True

            arm_obj.data.bones.active = active

        return {'FINISHED'}
