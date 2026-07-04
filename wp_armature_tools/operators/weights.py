# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

from ..core.utils import get_armature_object


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

    blend_width: bpy.props.FloatProperty(
        name="Blend Width",
        description=(
            "Width of the soft transition zone at the split point, as a fraction of the "
            "combined bone axis length. 0 = hard cut."
        ),
        min=0.0, max=0.5, default=0.05, subtype='FACTOR',
    )
    smooth_iterations: bpy.props.IntProperty(
        name="Smooth Iterations",
        description=(
            "Edge-topology-aware smoothing passes applied to the split boundary. "
            "0 = off. Uses the same uniform Laplacian as Blender's Weight Paint smooth."
        ),
        min=0, max=10, default=0,
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

        layout.separator(factor=0.5)
        layout.prop(self, "blend_width")
        layout.prop(self, "smooth_iterations")

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_chain(bone_chain_str):
        """Return the list of stripped, non-empty bone name strings."""
        return [n.strip() for n in bone_chain_str.split(",") if n.strip()]

    def _do_split_chain(self, obj, arm_obj, source_vg_name, bone_names, blend_width=0.0):
        """Distribute source_vg_name's weights across N bones along their shared axis.

        Bones are sorted by their head position along the axis so the caller
        does not need to supply them in a particular order.  For each vertex
        in the source group the function finds the bone segment whose
        [head … tail] interval (projected onto the axis) contains the vertex
        and assigns the weight to that bone's vertex group.  The source group
        is cleared of any vertex that was redistributed.

        blend_width controls the half-width of a smoothstep transition zone at each
        internal split threshold (as a fraction of the total axis length), splitting
        a vertex's weight smoothly between the two bones on either side. 0 = hard cut.
        Assumes each segment is wider than blend_width; thinner segments may not blend
        against both neighbours correctly.

        Returns (counts, sorted_bone_names) on success — counts is a dict
        {bone_name: vertex_count} and sorted_bone_names is bone_names reordered along
        the axis (needed by the caller to smooth adjacent boundaries in order).
        Returns None when prerequisites are missing (silent — used for the mirrored
        pass).
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

        # Classify every vertex that belongs to the source group into a hard
        # segment bucket, keeping its axis position (t) for the blend pass below.
        classified = []   # [(vert_idx, weight, seg, t), ...]

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

            classified.append((vert.index, w, seg, t))

        # Distribute weights per segment, splitting across an internal threshold's
        # smoothstep blend zone when the vertex falls within half_w of it.
        half_w = blend_width / 2.0
        vg_weights = [{} for _ in bones_sorted]   # vg_weights[seg][vert_idx] = weight

        for idx, w, seg, t in classified:
            blended = False
            if half_w > 0.0:
                # Right boundary of this segment (toward seg + 1).
                if seg < len(split_ts):
                    delta = t - split_ts[seg]              # <= 0 within this bucket
                    if delta > -half_w:
                        zone_t = (delta + half_w) / (2.0 * half_w)
                        blend  = zone_t * zone_t * (3.0 - 2.0 * zone_t)
                        vg_weights[seg][idx]     = vg_weights[seg].get(idx, 0.0)     + w * (1.0 - blend)
                        vg_weights[seg + 1][idx] = vg_weights[seg + 1].get(idx, 0.0) + w * blend
                        blended = True
                # Left boundary of this segment (toward seg - 1).
                if not blended and seg > 0:
                    delta = t - split_ts[seg - 1]          # > 0 within this bucket
                    if delta < half_w:
                        zone_t = (delta + half_w) / (2.0 * half_w)
                        blend  = zone_t * zone_t * (3.0 - 2.0 * zone_t)
                        vg_weights[seg][idx]     = vg_weights[seg].get(idx, 0.0)     + w * blend
                        vg_weights[seg - 1][idx] = vg_weights[seg - 1].get(idx, 0.0) + w * (1.0 - blend)
                        blended = True
            if not blended:
                vg_weights[seg][idx] = vg_weights[seg].get(idx, 0.0) + w

        # Flush all classified vertices from the source group first, then
        # write them into the correct destination groups.
        all_indices = [idx for idx, _, _, _ in classified]
        if all_indices:
            source_vg.remove(all_indices)

        counts = {}
        for bone, vg, weights in zip(bones_sorted, dest_vgs, vg_weights):
            n = 0
            for idx, w in weights.items():
                if w >= 1e-6:
                    vg.add([idx], w, 'REPLACE')
                    n += 1
            counts[bone.name] = n

        return counts, [b.name for b in bones_sorted]

    # ------------------------------------------------------------------

    @staticmethod
    def _smooth_boundaries(obj, vg_a, vg_b, iterations, factor=0.5):
        """Uniform graph Laplacian smooth over the boundary vertices of vg_a and vg_b.

        Only vertices that have non-zero weight in BOTH groups are smoothed (the blend
        zone at the split boundary). Each iteration blends each boundary vertex toward
        its edge-neighbour average, then renormalises a+b to preserve the combined
        total weight — no weight is created or destroyed.

        Uses the same algorithm as Blender's vertex_group_smooth operator
        (vgroup_smooth_subset in object_vgroup.cc): uniform graph Laplacian with
        adjacency built from mesh.edges.
        """
        if iterations < 1:
            return

        mesh = obj.data
        idx_a = vg_a.index
        idx_b = vg_b.index

        # Build edge adjacency map  {vert_index: [neighbour_indices, ...]}
        adj = {}
        for edge in mesh.edges:
            v0, v1 = edge.vertices[0], edge.vertices[1]
            adj.setdefault(v0, []).append(v1)
            adj.setdefault(v1, []).append(v0)

        ifac = 1.0 - factor

        for _ in range(iterations):
            # Snapshot current weights for both groups
            wa = {}
            wb = {}
            for vert in mesh.vertices:
                for g in vert.groups:
                    if g.group == idx_a:
                        wa[vert.index] = g.weight
                    elif g.group == idx_b:
                        wb[vert.index] = g.weight

            # Only smooth vertices present in BOTH groups (the boundary zone)
            boundary = set(wa) & set(wb)
            if not boundary:
                break

            new_wa = dict(wa)
            new_wb = dict(wb)

            for vi in boundary:
                neighbours = adj.get(vi, [])
                if not neighbours:
                    continue
                n = len(neighbours)
                avg_a = sum(wa.get(nb, 0.0) for nb in neighbours) / n
                avg_b = sum(wb.get(nb, 0.0) for nb in neighbours) / n

                new_wa[vi] = ifac * wa[vi] + factor * avg_a
                new_wb[vi] = ifac * wb[vi] + factor * avg_b

                # Renormalise to preserve combined total (a + b = constant)
                total_before = wa[vi]     + wb[vi]
                total_after  = new_wa[vi] + new_wb[vi]
                if total_after > 1e-6:
                    scale = total_before / total_after
                    new_wa[vi] *= scale
                    new_wb[vi] *= scale

            # Write back, pruning near-zero entries
            for vi in boundary:
                w = new_wa[vi]
                if w < 1e-6:
                    vg_a.remove([vi])
                else:
                    vg_a.add([vi], w, 'REPLACE')

                w = new_wb[vi]
                if w < 1e-6:
                    vg_b.remove([vi])
                else:
                    vg_b.add([vi], w, 'REPLACE')

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

        result = self._do_split_chain(obj, arm_obj, self.source_vg, bone_names, self.blend_width)
        if result is None:
            self.report({'ERROR'}, "Bones are co-located — cannot determine a split axis")
            return {'CANCELLED'}
        counts, sorted_names = result

        summary = ", ".join(f"{n}: {c}v" for n, c in counts.items())
        msg = f"Split '{self.source_vg}' → {summary}"

        mesh = obj.data
        mirror_axes_active = obj.use_mesh_mirror_x or obj.use_mesh_mirror_y or obj.use_mesh_mirror_z
        mir_sorted_names = None
        if mesh.use_mirror_vertex_groups and mirror_axes_active:
            mir_source = bpy.utils.flip_name(self.source_vg)
            if mir_source != self.source_vg:
                mir_bones  = [bpy.utils.flip_name(n) for n in bone_names]
                mir_result = self._do_split_chain(obj, arm_obj, mir_source, mir_bones, self.blend_width)
                if mir_result is not None:
                    mir_counts, mir_sorted_names = mir_result
                    mir_summary = ", ".join(f"{n}: {c}v" for n, c in mir_counts.items())
                    msg += f" | mirror → {mir_summary}"

        # Post-split boundary smooth (Laplacian) — only if requested. Smooths every
        # adjacent pair of bones along the chain, one boundary at a time.
        if self.smooth_iterations > 0:
            for a, b in zip(sorted_names, sorted_names[1:]):
                if a in obj.vertex_groups and b in obj.vertex_groups:
                    self._smooth_boundaries(
                        obj, obj.vertex_groups[a], obj.vertex_groups[b], self.smooth_iterations
                    )

            if mir_sorted_names is not None:
                for a, b in zip(mir_sorted_names, mir_sorted_names[1:]):
                    if a in obj.vertex_groups and b in obj.vertex_groups:
                        self._smooth_boundaries(
                            obj, obj.vertex_groups[a], obj.vertex_groups[b], self.smooth_iterations
                        )

        self.report({'INFO'}, msg)
        return {'FINISHED'}
