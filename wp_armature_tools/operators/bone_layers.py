# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.utils import (
    _any_solo_active,
    _USE_BONE_COLLECTIONS,
    _USE_BONE_COLLECTION_HIERARCHY,
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


class WPAT_UL_bone_collections(bpy.types.UIList):
    """Bone collection list with visibility/solo toggles, indented and
    collapsible into a parent/child tree on Blender 4.1+ (which added
    BoneCollection.parent/.children/.is_expanded). Falls back to a flat,
    still-scrollable list on exactly 4.0.x, where those fields don't exist."""
    bl_idname = "WPAT_UL_bone_collections"

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index, flt_flag):
        coll = item
        row = layout.row(align=True)

        if _USE_BONE_COLLECTION_HIERARCHY:
            # Depth was stashed in the low nibble of flt_flag by filter_items()
            # below - bitflag_filter_item is a single high bit, so this never
            # collides with it.
            depth = flt_flag & 0xF
            for _ in range(depth):
                row.separator()
            if len(coll.children) > 0:
                icon_name = 'TRIA_DOWN' if coll.is_expanded else 'TRIA_RIGHT'
                row.prop(coll, "is_expanded", text="", icon=icon_name, emboss=False)
            else:
                row.label(text="", icon='BLANK1')

        vis_icon = 'HIDE_OFF' if coll.is_visible else 'HIDE_ON'
        row.prop(coll, "is_visible", text=coll.name, toggle=True, icon=vis_icon)
        solo_icon = 'RADIOBUT_ON' if coll.is_solo else 'RADIOBUT_OFF'
        row.prop(coll, "is_solo", text="", toggle=True, icon=solo_icon)

    def filter_items(self, context, data, propname):
        colls = getattr(data, propname)
        helper = bpy.types.UI_UL_list
        n = len(colls)
        flt_flags = [self.bitflag_filter_item] * n
        flt_neworder = list(range(n))
        if n == 0:
            return flt_flags, flt_neworder

        if not _USE_BONE_COLLECTION_HIERARCHY:
            # No parent/children/is_expanded on 4.0.x - flat list, natural
            # order is already fine, just apply the name filter.
            if self.filter_name:
                name_flags = helper.filter_items_by_name(
                    self.filter_name, self.bitflag_filter_item, colls, "name",
                    reverse=self.use_filter_name_reverse)
                if name_flags:
                    flt_flags = name_flags
            return flt_flags, flt_neworder

        # collections_all groups each parent's children contiguously, but
        # interleaves separate subtrees in creation order, not nesting order -
        # a real depth-first walk from the roots is needed for correct nested
        # display, plus per-row depth for indentation.
        index_of = {c.as_pointer(): i for i, c in enumerate(colls)}
        depth_of = [0] * n
        parent_of = [-1] * n
        collapsed_by_ancestor = [False] * n
        order = []

        def visit(coll, depth, parent_idx, ancestor_collapsed):
            idx = index_of[coll.as_pointer()]
            depth_of[idx] = depth
            parent_of[idx] = parent_idx
            collapsed_by_ancestor[idx] = ancestor_collapsed
            order.append(idx)
            child_ancestor_collapsed = ancestor_collapsed or not coll.is_expanded
            for child in coll.children:
                visit(child, depth + 1, idx, child_ancestor_collapsed)

        for root in data.collections:
            visit(root, 0, -1, False)

        if self.filter_name:
            name_flags = helper.filter_items_by_name(
                self.filter_name, self.bitflag_filter_item, colls, "name",
                reverse=self.use_filter_name_reverse)
            if name_flags:
                match = list(name_flags)
                # Every descendant of a node precedes it in reversed(order)
                # (pre-order property), so a child's match has already been
                # propagated by the time we reach its parent.
                for idx in reversed(order):
                    if match[idx] & self.bitflag_filter_item:
                        p = parent_of[idx]
                        if p != -1:
                            match[p] |= self.bitflag_filter_item
                flt_flags = match

        for idx in range(n):
            if collapsed_by_ancestor[idx]:
                flt_flags[idx] &= ~self.bitflag_filter_item
            flt_flags[idx] |= (depth_of[idx] & 0xF)

        for new_idx, org_idx in enumerate(order):
            flt_neworder[org_idx] = new_idx

        return flt_flags, flt_neworder


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

    # Required by template_list() below to track the highlighted row; pure UI
    # state, not a meaningful action argument.
    active_collection_index: bpy.props.IntProperty(
        name="Active Bone Collection",
        default=0,
        options={'SKIP_SAVE', 'HIDDEN'},
    )

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
        return context.window_manager.invoke_popup(self, width=340)

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
            colls = arm.collections_all
            if not colls:
                layout.label(text="(no collections)", icon='INFO')
                return
            layout.template_list(
                "WPAT_UL_bone_collections", "",
                arm, "collections_all",
                self, "active_collection_index",
                rows=10 if colls else 1,
            )
        else:
            self._draw_layers_3x(layout, arm)

    def execute(self, context):
        return {'FINISHED'}
