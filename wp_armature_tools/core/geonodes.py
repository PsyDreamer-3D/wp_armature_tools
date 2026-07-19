# SPDX-License-Identifier: GPL-2.0-or-later

"""Procedural Geometry Nodes group for Combine Vertex Groups.

Built in Python rather than bundled as a .blend asset: the graph is tiny
(two Named Attribute reads, a Math combine, one Store Named Attribute write)
and this keeps the add-on free of binary asset files. Sum and Average are
two separate node groups rather than one with a runtime switch, since the
mode is a one-time choice made when the operator runs, not something that
benefits from being live-tweakable in the modifier's Input panel.

Only call ensure_combine_vertex_groups_node_group() from inside an
operator's execute() (lazily), never at import/register() time - module
import happens with no guarantee of an active .blend.
"""

import bpy

_SUM_NAME = "WPAT_CombineVertexGroups_Sum"
_AVERAGE_NAME = "WPAT_CombineVertexGroups_Average"


def _build_combine_node_group(name: str, mode: str) -> bpy.types.GeometryNodeTree:
    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    # Guard against orphan-purge before any modifier references this group.
    tree.use_fake_user = True

    iface = tree.interface
    iface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    iface.new_socket("Group A", in_out='INPUT', socket_type='NodeSocketString')
    iface.new_socket("Group B", in_out='INPUT', socket_type='NodeSocketString')
    iface.new_socket("Target", in_out='INPUT', socket_type='NodeSocketString')
    iface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes, links = tree.nodes, tree.links
    n_in = nodes.new('NodeGroupInput')
    n_out = nodes.new('NodeGroupOutput')

    attr_a = nodes.new('GeometryNodeInputNamedAttribute')
    attr_a.data_type = 'FLOAT'
    attr_b = nodes.new('GeometryNodeInputNamedAttribute')
    attr_b.data_type = 'FLOAT'
    links.new(n_in.outputs["Group A"], attr_a.inputs["Name"])
    links.new(n_in.outputs["Group B"], attr_b.inputs["Name"])

    combine = nodes.new('ShaderNodeMath')
    combine.operation = 'ADD'
    links.new(attr_a.outputs["Attribute"], combine.inputs[0])
    links.new(attr_b.outputs["Attribute"], combine.inputs[1])

    if mode == 'AVERAGE':
        # Fixed 50/50 blend, not divide-by-count-of-present-groups - see
        # operators/combine_weights.py for why (avoids a seam at the
        # boundary between a vertex touched by one group vs. both).
        post = nodes.new('ShaderNodeMath')
        post.operation = 'MULTIPLY'
        post.inputs[1].default_value = 0.5
    else:  # SUM
        # Two independently-normalized groups can overlap and exceed 1.0.
        post = nodes.new('ShaderNodeMath')
        post.operation = 'MINIMUM'
        post.inputs[1].default_value = 1.0
    links.new(combine.outputs["Value"], post.inputs[0])

    store = nodes.new('GeometryNodeStoreNamedAttribute')
    store.data_type = 'FLOAT'
    store.domain = 'POINT'
    links.new(n_in.outputs["Geometry"], store.inputs["Geometry"])
    links.new(n_in.outputs["Target"], store.inputs["Name"])
    links.new(post.outputs["Value"], store.inputs["Value"])
    links.new(store.outputs["Geometry"], n_out.inputs["Geometry"])

    return tree


def ensure_combine_vertex_groups_node_group(mode: str = 'SUM') -> bpy.types.GeometryNodeTree:
    """Return the shared WPAT combine-vertex-groups node group for *mode*
    ('SUM' or 'AVERAGE'), building it once per .blend session if missing."""
    name = _AVERAGE_NAME if mode == 'AVERAGE' else _SUM_NAME
    existing = bpy.data.node_groups.get(name)
    if existing is not None:
        return existing
    return _build_combine_node_group(name, mode)
