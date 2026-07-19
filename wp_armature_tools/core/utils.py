# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

# Blender 4.0 replaced per-armature layer bits with named BoneCollections.
# BoneCollection has native is_visible and is_solo properties.
_USE_BONE_COLLECTIONS = bpy.app.version >= (4, 0, 0)

# Blender 4.1 added real parent/child bone collection hierarchy (.parent,
# .children, .is_expanded). On exactly 4.0.x, collections exist but are flat.
_USE_BONE_COLLECTION_HIERARCHY = bpy.app.version >= (4, 1, 0)

# Blender 4.0 replaced the legacy inputs.new()/outputs.new() node-group
# socket API with node_tree.interface, and is where the Fields-based
# GeometryNodeInputNamedAttribute/GeometryNodeStoreNamedAttribute nodes this
# add-on's Combine Vertex Groups (Geometry Nodes) feature needs are stable.
_USE_GEOMETRY_NODES = bpy.app.version >= (4, 0, 0)


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
