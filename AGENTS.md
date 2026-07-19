# Weight Paint Armature Tools — Agent Guidelines

Blender add-on exposing armature operators and bone layer/collection controls
inside Weight Paint mode. All source code lives in `wp_armature_tools/`.

See `../AGENTS.md` for workspace-wide conventions (hot-reload pattern, the
`bpy.ops` rules, package-layout diagram, and where the local Blender docs/source
live). This file only covers what's specific to *this* repo.

## Hard constraints (from ../AGENTS.md, section on `bpy.ops`)

- No `bpy.ops` for data-level manipulation (mesh/object/collection edits go
  through `bpy.data`/`bmesh` directly).
- Bmesh vertex deletion is vertex-first, not face-delete-then-cleanup.
- Diagnostics never assume a console — use a `bpy.data.texts` block, not
  `print()`. (Not currently needed here: this add-on has no debug/report
  output beyond `self.report(...)`, which is already console-independent.)

## Package layout

Split into the standard four-subpackage layout:

```
wp_armature_tools/
├── __init__.py          # orchestration only — hot-reload guard, register/unregister
├── blender_manifest.toml
├── core/
│   ├── utils.py          # get_armature_object, is_cloudrig, tag_redraw_all, _any_solo_active
│   └── geonodes.py        # ensure_combine_vertex_groups_node_group() — procedural GN node groups
├── operators/
│   ├── bone_chain.py     # Select/Extend Bone Chain
│   ├── bone_layers.py    # WPAT_OT_clear_solo, WPAT_OT_bone_layers_popup
│   ├── combine_weights.py # Combine Vertex Groups (destructive + Geometry Nodes variant)
│   ├── pose.py           # toggle/clear pose operators
│   └── weights.py        # normalize + split-coaxial-weights operators
├── properties/preferences.py  # WPATPreferences (keymap UI)
└── ui/panel.py            # WPAT_PT_armature_panel
```

`operators/__init__.py` owns the M-key "3D View" keymap registration (not
top-level `__init__.py`) because the shortcut is tied one-to-one to
`WPAT_OT_bone_layers_popup`, which lives in that subpackage. Register order is
`properties → operators → ui` (reversed for unregister), matching each
subpackage's internal class-registration order.

## Key design decisions

- **`bl_info` is retained and is load-bearing, not legacy cruft.**
  `blender_manifest.toml` is only read by Blender's Extensions platform
  (4.2+). This add-on declares `blender_version_min = "3.0.0"` in the
  manifest, and pre-4.2 Blender has no concept of that file — it discovers
  add-ons exclusively via the `bl_info` dict in `__init__.py`. Don't remove
  `bl_info` while the minimum stays below 4.2, even though newer scaffolded
  projects in this workspace skip it.
- **Blender 3.0–4.x compatibility gate**: `core/utils._USE_BONE_COLLECTIONS`
  detects whether the running Blender has named `BoneCollection`s (4.0+,
  with native `is_visible`/`is_solo`) or only legacy 32-bit armature layers
  (3.x). Every UI/operator branch that touches bone visibility checks this
  flag — don't assume `BoneCollection` exists.
- **CloudRig interop**: `is_cloudrig()` checks both a structural marker
  (`hasattr(arm, "cloudrig")`, present while CloudRig is installed) and a data
  marker (a `"cloudrig"` custom property baked into generated rigs, present
  even without CloudRig installed) so detection survives CloudRig being
  uninstalled after rig generation.
- **M-key registered on the "3D View" keymap, not "Weight Paint"** — the
  mode-specific keymap swallows key events (CloudRig hit the same bug; see
  their own changelog entry for it). Registering broadly and gating with
  `poll()` lets the addon's item run first, and fall through to CloudRig's own
  handler when `poll()` returns `False` on a CloudRig rig.
- **Deliberate `bpy.ops` exceptions** in `operators/pose.py` and
  `operators/weights.py` (`object.mode_set`, `pose.transforms_clear`,
  `object.vertex_group_normalize_all`): these are
  used inside `execute()`, which the workspace rule generally forbids. Kept
  as-is because `object.mode_set` has no data-API equivalent at all (`Object.mode`
  is read-only outside operators), and reimplementing transform-clear via `bmesh`
  would mean re-deriving Blender's own pose-transform math — a large, risky
  rewrite of stable, already-shipped behavior that nobody asked for. Each call
  site sets `view_layer.objects.active` immediately before the
  matching `mode_set`, so context is never ambiguous at the call site.
- **Split Coaxial Weights** (`operators/weights.py`) generalizes a hard 2-bone
  cut into an N-bone chain: each internal boundary gets its own smoothstep
  blend zone (`blend_width`) and, optionally, a Laplacian boundary smooth
  (`smooth_iterations`) run pairwise across every adjacent bone in the sorted
  chain. See the class docstrings for the exact math — worth reading before
  changing either the blend or smoothing logic, since both assume segments are
  wider than `blend_width`.
- **Combine Vertex Groups (Geometry Nodes variant)**: `GeometryNodeStoreNamedAttribute`
  cannot create a new vertex group by name — Blender's attribute layer for
  vertex groups only writes if the name already exists in `obj.vertex_groups`.
  The GN operator therefore always pre-creates the (empty) target vertex group
  via the data API before adding the modifier. The modifier is also moved
  (via `obj.modifiers.move()`, a data-API method — no `bpy.ops` exception
  needed here) to sit immediately above the first Armature modifier found:
  because modifiers evaluate top-to-bottom, an Armature modifier below a
  stale (un-combined) target group would deform using zero weight there,
  silently discarding the combine's effect. The Geometry Nodes result is
  **not** visible in Weight Paint mode's paint/weight overlay — that always
  reflects `obj.data`'s base-mesh weights, never modifier-evaluated data — so
  verify the GN variant via deformed shape (toggle Pose Position), not the
  paint overlay. `core/geonodes.py`'s node group is gated behind
  `core.utils._USE_GEOMETRY_NODES` (Blender 4.0+, where the modern
  `node_tree.interface` socket API and the Fields-based Named Attribute nodes
  it needs are stable) — this is a separate concern from
  `_USE_BONE_COLLECTIONS`, even though both thresholds happen to be 4.0.

## Building & Releasing

Follows the workspace-wide convention in `../AGENTS.md` ("Versioning &
Release") — nothing project-specific here. Cut a release with
`scripts/prepare_release.sh <version>` on `main`; for a local sanity-check
build without tagging anything, use `scripts/build_dev.sh`.

## Testing

No automated test suite — Blender's `bpy` API isn't meaningfully mockable for
this add-on's geometry-heavy operators. Manual regression checklist:

1. Install via Blender Preferences → Extensions → Install from Disk, pointing
   at `wp_armature_tools/` (or build with `scripts/build_dev.sh` and install
   the zip from `dist/`).
2. On a mesh with an Armature modifier, enter Weight Paint mode and confirm
   the **Armature** tab appears in the N-panel.
3. Press **M** — the Bone Layers/Collections popup should open (32-layer grid
   on Blender <4.0, named collections with solo toggles on 4.0+). Confirm it
   does *not* open on a CloudRig-managed rig (CloudRig's own popup should fire
   instead, or nothing if CloudRig isn't installed). On Blender 4.1+, on an
   armature with nested bone collections, confirm children are indented under
   their parent, the expand arrow collapses/expands that branch, and
   `is_visible`/`is_solo` toggles still work per row. On an armature with many
   flat (sibling-only) collections, confirm the list has a fixed height with a
   scrollbar instead of an unbounded wall of rows, and that the funnel/search
   icon keeps a matched child's ancestor chain visible instead of filtering it
   out. On Blender 4.0.x, confirm the same popup still works as a flat,
   non-indented, scrollable list with no errors.
4. Toggle Pose/Rest position, run Clear Bone Transforms in Pose position;
   confirm it re-enters Weight Paint mode afterward.
5. Run Normalize All Weights on a mesh with multiple vertex groups.
6. Run Split Coaxial Weights on a 2+ bone chain (e.g. `thigh`, `thigh.001`):
   verify with `blend_width = 0` it's a hard cut, with `blend_width > 0` the
   boundary blends smoothly, and `smooth_iterations > 0` further softens it
   without changing total per-vertex weight. Repeat with Mirror Vertex Groups
   enabled on a mirrored mesh and confirm the mirrored chain splits too.
7. In Edit Armature mode, select a bone with a connected chain (some
   `use_connect` children/parent) and a branch point; run **Select Bone
   Chain** from the new "Bone Chain" sidebar panel and confirm it selects the
   full connected run and stops at the branch. Repeat in Pose mode and in
   Weight Paint bone-select mode. Then select a bone outside the chain and
   confirm **Extend Bone Chain** adds the chain to the existing selection
   instead of replacing it.
8. Run **Combine Vertex Groups** with two overlapping normalized groups: Sum
   should clamp at vertices where both groups have weight (no vertex exceeds
   1.0 total), Average should read as a smooth 50/50 blend with no seam at
   the boundary of either source group. Re-run into an existing target and
   confirm it's fully overwritten, not additively merged. Repeat with Mirror
   Vertex Groups enabled and a `.L`/`.R`-suffixed target, confirming the
   mirrored pair combines into the mirrored target; confirm a non-suffixed
   target name skips the mirrored pass instead of double-writing. Then run
   **Combine Vertex Groups (Geometry Nodes)**: confirm the modifier appears
   positioned above the Armature modifier, confirm the target vertex group is
   created (empty) in the Vertex Groups list, and confirm the deformed mesh
   in Pose Position visibly reflects the combined weights even though Weight
   Paint's paint overlay still shows the target group as empty (expected —
   see the design notes above).
