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
        col.operator("wpat.normalize_all_weights", icon='MOD_VERTEX_WEIGHT')

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
