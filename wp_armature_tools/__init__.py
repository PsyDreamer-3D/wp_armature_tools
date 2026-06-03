bl_info = {
    "name": "Weight Paint Armature Tools",
    "author": "Jess G.",
    "version": (1, 7, 0),
    "blender": (3, 0, 0),
    "location": "Weight Paint > Sidebar > Armature  |  M → Bone Layers popup",
    "description": (
        "Exposes armature operators and properties in Weight Paint mode. "
        "M opens a bone layer/collection visibility popup with solo support. "
        "Automatically defers to CloudRig on CloudRig-managed rigs. "
        "Shortcut is configurable under Add-on Preferences."
    ),
    "category": "Rigging",
}

import bpy
import rna_keymap_ui

# Blender 4.0 replaced per-armature layer bits with named BoneCollections.
# BoneCollection has native is_visible and is_solo properties.
_USE_BONE_COLLECTIONS = bpy.app.version >= (4, 0, 0)

# Accumulated keymap entries for clean unregister.
_addon_keymaps: list = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_armature_object(context):
    """Return the first armature object linked to the active mesh via an
    Armature modifier, or None if not found."""
    obj = context.active_object
    if obj and obj.type == 'MESH':
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                return mod.object
    return None


def is_cloudrig(arm_obj) -> bool:
    """Return True if this armature is managed by CloudRig.

    Two checks:
    - Structural: CloudRig registers a PropertyGroup named 'cloudrig' on
      bpy.types.Armature while the add-on is active.
    - Data: generated rigs carry a 'cloudrig' custom property on arm.data
      even when the add-on is no longer installed.
    """
    arm = arm_obj.data
    return hasattr(arm, "cloudrig") or (arm.get("cloudrig") is not None)


def tag_redraw_all(context):
    for area in context.screen.areas:
        area.tag_redraw()


def _any_solo_active(arm) -> bool:
    """Return True if any bone collection on *arm* has is_solo enabled."""
    if not _USE_BONE_COLLECTIONS:
        return False
    return any(coll.is_solo for coll in arm.collections_all)


# ---------------------------------------------------------------------------
# Add-on preferences
# ---------------------------------------------------------------------------

class WPATPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.label(text="Keymap:")

        wm = context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            layout.label(text="Keyconfig not available.", icon='ERROR')
            return

        # The keymap is registered under "3D View" (see register()).
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


# ---------------------------------------------------------------------------
# Clear-all-solo operator
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Bone layer / collection popup
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Existing operators
# ---------------------------------------------------------------------------

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


class WPAT_OT_apply_pose_as_rest(bpy.types.Operator):
    """Apply the current pose as the new rest pose on the linked armature"""
    bl_idname = "wpat.apply_pose_as_rest"
    bl_label = "Apply Pose as Rest Pose"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        arm_obj = get_armature_object(context)
        return arm_obj is not None and arm_obj.data.pose_position == 'POSE'

    def execute(self, context):
        arm_obj = get_armature_object(context)
        mesh_obj = context.active_object

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

        tag_redraw_all(context)
        self.report({'INFO'}, "Pose applied as rest pose.")
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


class WPAT_OT_normalize_all_weights(bpy.types.Operator):
    """Normalize all vertex groups on the active mesh so they sum to 1"""
    bl_idname = "wpat.normalize_all_weights"
    bl_label = "Normalize All Weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and len(obj.vertex_groups) > 0

    def execute(self, context):
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        self.report({'INFO'}, "All vertex groups normalized.")
        return {'FINISHED'}

class WPAT_OT_split_coaxial_weights(bpy.types.Operator):
    """Split a vertex group across N co-axial bones by projecting each vertex onto the combined bone axis.
Auto-detects the bone chain from the active vertex group name (.001, .002, … suffixes)"""
    bl_idname = "wpat.split_coaxial_weights"
    bl_label = "Split Coaxial Weights"
    bl_options = {'REGISTER', 'UNDO'}

    source_vg: bpy.props.StringProperty(name="Source VG")
    bone_chain: bpy.props.StringProperty(
        name="Bone Chain",
        description="Comma-separated bone names in axis order (auto-detected from Source VG name)",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not (obj and obj.type == 'MESH' and obj.vertex_groups.active):
            return False
        return get_armature_object(context) is not None

    def invoke(self, context, event):
        obj     = context.active_object
        arm_obj = get_armature_object(context)
        arm     = arm_obj.data

        active_vg      = obj.vertex_groups.active
        self.source_vg = active_vg.name if active_vg else ""

        # Walk the .001 / .002 / … chain starting from the source VG name.
        chain = []
        if self.source_vg in arm.bones:
            chain.append(self.source_vg)
            i = 1
            while True:
                candidate = f"{self.source_vg}.{i:03d}"
                if candidate in arm.bones:
                    chain.append(candidate)
                    i += 1
                else:
                    break

        self.bone_chain = ", ".join(chain)
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        obj     = context.active_object
        arm_obj = get_armature_object(context)
        layout  = self.layout

        layout.prop_search(self, "source_vg", obj, "vertex_groups", text="Source VG")
        layout.prop(self, "bone_chain", text="Bone Chain")
        layout.label(text="Comma-separated, in axis order", icon='INFO')

        # Parse the current field and show per-bone validity at a glance.
        arm   = arm_obj.data
        names = [n.strip() for n in self.bone_chain.split(",") if n.strip()]
        if names:
            layout.separator(factor=0.5)
            col = layout.column(align=True)
            for name in names:
                row = col.row()
                if name in arm.bones:
                    row.label(text=name, icon='BONE_DATA')
                else:
                    row.label(text=f"{name}  (not found)", icon='ERROR')

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_chain(bone_chain_str):
        """Return the list of stripped, non-empty bone name strings."""
        return [n.strip() for n in bone_chain_str.split(",") if n.strip()]

    def _do_split_chain(self, obj, arm_obj, source_vg_name, bone_names):
        """Distribute source_vg_name's weights across N bones along their shared axis.

        Bones are sorted by their head position along the axis so the caller
        does not need to supply them in a particular order.  For each vertex
        in the source group the function finds the bone segment whose
        [head … tail] interval (projected onto the axis) contains the vertex
        and assigns the weight to that bone's vertex group.  The source group
        is cleared of any vertex that was redistributed.

        Returns a dict  {bone_name: vertex_count}  on success, or None when
        prerequisites are missing (silent — used for the mirrored pass).
        """
        arm = arm_obj.data

        if source_vg_name not in obj.vertex_groups:
            return None

        bones = []
        for name in bone_names:
            if name not in arm.bones:
                return None
            bones.append(arm.bones[name])

        if len(bones) < 2:
            return None

        # Combined axis: first-bone head → last-bone tail (in armature local space).
        # Bones are sorted by the projection of their head onto this direction so
        # the algorithm is independent of the order they were entered.
        p_start = bones[0].head_local.copy()
        p_end   = bones[-1].tail_local.copy()
        axis    = p_end - p_start
        axis_len_sq = axis.dot(axis)

        if axis_len_sq < 1e-10:
            return None

        def _head_t(bone):
            return (bone.head_local - p_start).dot(axis) / axis_len_sq

        bones_sorted = sorted(bones, key=_head_t)

        # Recompute axis endpoints from the sorted list (sorting may swap them).
        p_start = bones_sorted[0].head_local.copy()
        p_end   = bones_sorted[-1].tail_local.copy()
        axis    = p_end - p_start
        axis_len_sq = axis.dot(axis)

        # Split thresholds: t value at each bone's tail except the last.
        split_ts = [
            (bone.tail_local - p_start).dot(axis) / axis_len_sq
            for bone in bones_sorted[:-1]
        ]

        # Ensure destination VGs exist for every bone in the chain.
        dest_vgs = []
        for bone in bones_sorted:
            if bone.name in obj.vertex_groups:
                dest_vgs.append(obj.vertex_groups[bone.name])
            else:
                dest_vgs.append(obj.vertex_groups.new(name=bone.name))

        source_vg = obj.vertex_groups[source_vg_name]
        mesh_to_arm = arm_obj.matrix_world.inverted() @ obj.matrix_world
        vg_idx = source_vg.index

        # Classify every vertex that belongs to the source group.
        assignments = [[] for _ in bones_sorted]   # assignments[i] = [(vert_idx, weight), …]

        for vert in obj.data.vertices:
            w = None
            for g in vert.groups:
                if g.group == vg_idx:
                    w = g.weight
                    break
            if w is None or w == 0.0:
                continue

            v_arm = mesh_to_arm @ vert.co
            t     = (v_arm - p_start).dot(axis) / axis_len_sq

            # Walk the split thresholds to find the owning bone segment.
            seg = len(bones_sorted) - 1          # default: last bone
            for i, threshold in enumerate(split_ts):
                if t <= threshold:
                    seg = i
                    break

            assignments[seg].append((vert.index, w))

        # Flush all classified vertices from the source group first, then
        # write them into the correct destination groups.
        all_indices = [idx for seg in assignments for (idx, _) in seg]
        if all_indices:
            source_vg.remove(all_indices)

        counts = {}
        for bone, vg, seg in zip(bones_sorted, dest_vgs, assignments):
            for idx, w in seg:
                vg.add([idx], w, 'REPLACE')
            counts[bone.name] = len(seg)

        return counts

    # ------------------------------------------------------------------

    def execute(self, context):
        obj     = context.active_object
        arm_obj = get_armature_object(context)
        arm     = arm_obj.data

        if self.source_vg not in obj.vertex_groups:
            self.report({'ERROR'}, f"Vertex group '{self.source_vg}' not found")
            return {'CANCELLED'}

        bone_names = self._parse_chain(self.bone_chain)

        if len(bone_names) < 2:
            self.report({'ERROR'}, "At least two bones are required in the chain")
            return {'CANCELLED'}

        missing = [n for n in bone_names if n not in arm.bones]
        if missing:
            self.report({'ERROR'}, f"Bone(s) not found in armature: {', '.join(missing)}")
            return {'CANCELLED'}

        if len(bone_names) != len(set(bone_names)):
            self.report({'ERROR'}, "Bone chain contains duplicate names")
            return {'CANCELLED'}

        counts = self._do_split_chain(obj, arm_obj, self.source_vg, bone_names)
        if counts is None:
            self.report({'ERROR'}, "Bones are co-located — cannot determine a split axis")
            return {'CANCELLED'}

        summary = ", ".join(f"{n}: {c}v" for n, c in counts.items())
        msg = f"Split '{self.source_vg}' → {summary}"

        mesh = obj.data
        mirror_axes_active = obj.use_mesh_mirror_x or obj.use_mesh_mirror_y or obj.use_mesh_mirror_z
        if mesh.use_mirror_vertex_groups and mirror_axes_active:
            mir_source = bpy.utils.flip_name(self.source_vg)
            if mir_source != self.source_vg:
                mir_bones  = [bpy.utils.flip_name(n) for n in bone_names]
                mir_counts = self._do_split_chain(obj, arm_obj, mir_source, mir_bones)
                if mir_counts is not None:
                    mir_summary = ", ".join(f"{n}: {c}v" for n, c in mir_counts.items())
                    msg += f" | mirror → {mir_summary}"

        self.report({'INFO'}, msg)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Sidebar panel
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    WPATPreferences,
    WPAT_OT_clear_solo,
    WPAT_OT_bone_layers_popup,
    WPAT_OT_toggle_pose_position,
    WPAT_OT_clear_bone_transforms,
    WPAT_OT_apply_pose_as_rest,
    WPAT_OT_normalize_all_weights,
    WPAT_OT_split_coaxial_weights,
    WPAT_PT_armature_panel,
)


def register():
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
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
