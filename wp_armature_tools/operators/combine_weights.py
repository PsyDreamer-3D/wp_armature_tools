# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.geonodes import ensure_combine_vertex_groups_node_group
from ..core.utils import _USE_GEOMETRY_NODES


def _read_group_weights(obj, vg_name):
    """Return {vert_index: weight} for vg_name, or {} if it doesn't exist."""
    if vg_name not in obj.vertex_groups:
        return {}
    idx = obj.vertex_groups[vg_name].index
    out = {}
    for vert in obj.data.vertices:
        for g in vert.groups:
            if g.group == idx:
                out[vert.index] = g.weight
                break
    return out


def _clear_or_create_vg(obj, name):
    """Return name's vertex group, cleared of any existing weights, creating
    it (empty) if it doesn't exist yet."""
    if name in obj.vertex_groups:
        vg = obj.vertex_groups[name]
        idx = vg.index
        existing = [v.index for v in obj.data.vertices for g in v.groups if g.group == idx]
        if existing:
            vg.remove(existing)
        return vg
    return obj.vertex_groups.new(name=name)


class _CombineVertexGroupsMixin:
    """Shared properties/poll/dialog for the destructive and Geometry Nodes
    Combine Vertex Groups operators."""

    group_a: bpy.props.StringProperty(name="Group A")
    group_b: bpy.props.StringProperty(name="Group B")
    target_vg: bpy.props.StringProperty(name="Target Group", default="Combined")
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('SUM', "Sum", "Add both groups' weights, capped at 1.0"),
            ('AVERAGE', "Average", "Blend both groups' weights 50/50"),
        ],
        default='AVERAGE',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and len(obj.vertex_groups) >= 2

    def invoke(self, context, event):
        obj = context.active_object
        active_vg = obj.vertex_groups.active
        self.group_a = active_vg.name if active_vg else ""
        self.group_b = ""
        self.target_vg = f"{self.group_a}_Combined" if self.group_a else "Combined"
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        obj = context.active_object
        layout = self.layout

        layout.prop_search(self, "group_a", obj, "vertex_groups", text="Group A")
        layout.prop_search(self, "group_b", obj, "vertex_groups", text="Group B")
        layout.separator(factor=0.5)
        layout.prop(self, "target_vg", text="Target Group")
        if self.target_vg in obj.vertex_groups:
            layout.label(text="Target exists — will be overwritten", icon='ERROR')
        layout.separator(factor=0.5)
        row = layout.row(align=True)
        row.prop_enum(self, "mode", 'SUM')
        row.prop_enum(self, "mode", 'AVERAGE')

    def _validate(self, obj):
        """Return an error message, or None if the current inputs are valid."""
        if self.group_a not in obj.vertex_groups or self.group_b not in obj.vertex_groups:
            return "Both source groups must exist"
        if self.group_a == self.group_b:
            return "Group A and Group B must be different"
        if not self.target_vg.strip():
            return "Target group name cannot be empty"
        if self.target_vg in (self.group_a, self.group_b):
            return "Target group must differ from both source groups"
        return None


class WPAT_OT_combine_vertex_groups(_CombineVertexGroupsMixin, bpy.types.Operator):
    """Sum or average two vertex groups' normalized weights into a new or
    existing target group, leaving both source groups untouched"""
    bl_idname = "wpat.combine_vertex_groups"
    bl_label = "Combine Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def _combine_and_write(self, obj, wa, wb, target_name):
        target = _clear_or_create_vg(obj, target_name)
        n = 0
        for idx in set(wa) | set(wb):
            a = wa.get(idx, 0.0)
            b = wb.get(idx, 0.0)
            w = (a + b) if self.mode == 'SUM' else (a + b) / 2.0
            if self.mode == 'SUM':
                w = min(w, 1.0)
            if w >= 1e-6:
                target.add([idx], w, 'REPLACE')
                n += 1
        return n

    def execute(self, context):
        obj = context.active_object
        error = self._validate(obj)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        wa = _read_group_weights(obj, self.group_a)
        wb = _read_group_weights(obj, self.group_b)
        n = self._combine_and_write(obj, wa, wb, self.target_vg)
        msg = f"Combined '{self.group_a}' + '{self.group_b}' → '{self.target_vg}' ({n}v)"

        # Mirror pass: only meaningful if the TARGET has a distinct mirrored
        # name (e.g. "Combined.L") - sources can be asymmetric (e.g. Group B
        # a shared, non-side-specific group), so it's the target's name that
        # decides whether a second, independent write is needed.
        mesh = obj.data
        mirror_axes_active = obj.use_mesh_mirror_x or obj.use_mesh_mirror_y or obj.use_mesh_mirror_z
        if mesh.use_mirror_vertex_groups and mirror_axes_active:
            mir_target = bpy.utils.flip_name(self.target_vg)
            if mir_target != self.target_vg:
                mir_a = bpy.utils.flip_name(self.group_a)
                mir_b = bpy.utils.flip_name(self.group_b)
                if mir_a in obj.vertex_groups and mir_b in obj.vertex_groups:
                    mwa = _read_group_weights(obj, mir_a)
                    mwb = _read_group_weights(obj, mir_b)
                    mn = self._combine_and_write(obj, mwa, mwb, mir_target)
                    msg += f" | mirror → '{mir_target}' ({mn}v)"

        self.report({'INFO'}, msg)
        return {'FINISHED'}


class WPAT_OT_combine_vertex_groups_geonodes(_CombineVertexGroupsMixin, bpy.types.Operator):
    """Non-destructive equivalent of Combine Vertex Groups: adds a Geometry
    Nodes modifier that combines the two source groups into the target group
    without touching mesh data"""
    bl_idname = "wpat.combine_vertex_groups_geonodes"
    bl_label = "Combine Vertex Groups (Geometry Nodes)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not _USE_GEOMETRY_NODES:
            return False
        return super().poll(context)

    def draw(self, context):
        super().draw(context)
        self.layout.separator(factor=0.5)
        self.layout.label(
            text="Weight Paint overlay won't show this — check deformed shape",
            icon='INFO',
        )

    def execute(self, context):
        obj = context.active_object
        error = self._validate(obj)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        # GeometryNodeStoreNamedAttribute cannot create a new vertex group by
        # name - Blender only recognizes the write as vertex-group data if
        # that name already exists in obj.vertex_groups.
        if self.target_vg not in obj.vertex_groups:
            obj.vertex_groups.new(name=self.target_vg)

        node_group = ensure_combine_vertex_groups_node_group(self.mode)
        mod = obj.modifiers.new(name="Combine Vertex Groups", type='NODES')
        mod.node_group = node_group
        # Input_2/3/4 follow the Group A/B/Target socket declaration order in
        # core/geonodes.py (Geometry is the implicit Input_1).
        mod["Input_2"] = self.group_a
        mod["Input_3"] = self.group_b
        mod["Input_4"] = self.target_vg

        # Modifiers evaluate top-to-bottom - if this sits below the Armature
        # modifier, Armature deforms using the target group's pre-combine
        # (empty) state, so the combine would have zero visible effect.
        for i, m in enumerate(obj.modifiers):
            if m.type == 'ARMATURE':
                obj.modifiers.move(obj.modifiers.find(mod.name), i)
                break

        self.report({'INFO'}, f"Added Combine Vertex Groups modifier → '{self.target_vg}'")
        return {'FINISHED'}
