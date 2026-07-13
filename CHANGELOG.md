# Changelog

All notable changes to Weight Paint Armature Tools are documented here.

## [Unreleased]

### Added
- **Select Bone Chain** / **Extend Bone Chain** operators (new "Bone Chain" panel in the Pose Mode and Edit Armature Mode sidebar, plus a Bone Selection section in the Weight Paint Armature panel): selects the connected bone chain through the active bone by walking `use_connect` parent/child links, stopping at branches (multiple connected children) or disconnected joins. Works identically across Edit Armature, Pose, and Weight Paint (bone-select) modes. **Extend Bone Chain** adds the chain to the current selection instead of replacing it.

## [1.8.0] — 2026-07-12

### Added
- **Assign Automatic Weights** and **Assign Envelope Weights** operators (Weight Utilities section): one-click wrappers around Blender's `paint.weight_from_bones` for the active mesh's linked armature, using its selected bones — automatic (distance-based) or bone-envelope weighting — without leaving Weight Paint mode. Each has a custom icon.
- **Pose Options** section in the Armature sidebar panel: Auto IK, X-Axis Mirror, and Relative Mirror toggles, plus an **Affect Only → Locations** toggle, wired directly to Blender's own `pose.use_auto_ik` / `pose.use_mirror_x` / `pose.use_mirror_relative` and `tool_settings.use_transform_pivot_point_align`. Normally these are only reachable from the header while in Pose Mode — surfacing them here lets you pre-configure pose-transform behavior before switching out of Weight Paint mode to test deformation.
- Custom operator icon support (`core/icons.py`): loads PNGs from `icons/` into a preview collection via `bpy.utils.previews`, exposed through `get_icon(name)` for `icon_value=` in any operator/panel draw call (falls back to `0`/no icon if missing). SVGs alongside each PNG are the vector design source.
- **Pose** section in the Armature sidebar panel: Auto IK, X-Axis Mirror, and Relative Mirror toggles, plus an **Affect Only Locations** toggle, wired directly to Blender's own `pose.use_auto_ik` / `pose.use_mirror_x` / `pose.use_mirror_relative` and `tool_settings.use_transform_pivot_point_align`. Normally these are only reachable from the header while in Pose Mode — surfacing them here lets you pre-configure pose-transform behavior before switching out of Weight Paint mode to test deformation. Grouped alongside Clear Bone Transforms in the same section.
- **Split Coaxial Weights** operator (Weight Utilities section): splits a single vertex group across N co-axial bones by projecting each vertex onto the combined bone axis. The bone chain is auto-detected from the active vertex group name (`.001`, `.002`, … suffix convention) and displayed per-bone in the dialog with validity indicators. Bones can be entered manually as a comma-separated list to support non-standard naming. Respects the active Weight Paint mirror settings — when Mirror Vertex Groups is enabled, the full mirrored chain is split automatically.
- **Blend Width** and **Smooth Iterations** options on Split Coaxial Weights: Blend Width feathers each internal split boundary with a smoothstep transition instead of a hard cut, splitting a vertex's weight between the two adjacent bones; Smooth Iterations runs an edge-topology-aware Laplacian smooth (matching Blender's own vertex group smooth) across every boundary in the chain afterward.
- Release workflow and build scripts for automated packaging.

### Removed
- **Apply Pose as Rest Pose** operator. It permanently rewrites the armature's rest pose — a rig-authoring action, not a weight-painting one — so offering a one-click way to trigger it from the Weight Paint panel risked an accidental, hard-to-notice rewrite of the rig's bind pose. Pose Position, Clear Bone Transforms, and the Pose Options toggles are unaffected.

### Changed
- Repo structure updated to match project conventions.
- Split the single `__init__.py` into `core/`, `operators/`, `properties/`, and `ui/` subpackages, each owning its own class registration; `__init__.py` is now orchestration-only (hot-reload guard + register/unregister). Added `AGENTS.md` documenting the layout and project-specific design decisions.
- `scripts/bump_version.py`, `scripts/build_dev.sh`, and `scripts/generate_index.py` now auto-detect the add-on package directory instead of hardcoding `wp_armature_tools`, matching the project-agnostic convention used elsewhere in the workspace. `.github/workflows/release.yml` updated to match (pinned Blender version moved to a single `env.BLENDER_VERSION`).
- Added `scripts/prepare_release.sh` and `scripts/update_changelog.py`, plus `.github/workflows/auto-tag-release.yml`: pushing a `Release vX.Y.Z` commit to `main` now dates the CHANGELOG's `Unreleased` section, bumps the manifest version, and auto-tags/publishes via the existing `release.yml` pipeline, instead of requiring a manually pushed tag.

---

## [1.7.0] — 2026-05-17

### Added
- **Viewport Display** section in the Armature sidebar panel, exposing armature display controls directly in Weight Paint mode:
  - Display type (Octahedral, Stick, B-Bone, Envelope, Wire)
  - Bone names, custom shapes, in-front
  - Bone Colors toggle (Blender 4.0+)
  - Axes toggle with position slider (Blender 4.0+)
  - Relation line position (Blender 4.0+)

---

## [1.6.0] — 2026-05-10

### Added
- Initial release of Weight Paint Armature Tools.
- **Armature identity** box showing the linked armature name, with CloudRig badge when detected.
- **Pose Position** toggle: enum buttons (Pose / Rest) and a one-click switch operator.
- **Bone Layers / Collections** popup on **M** (configurable shortcut):
  - Blender 3.x: 32-layer bit grid.
  - Blender 4.0+: named BoneCollection list with visibility and native solo (`is_solo`) toggles.
  - Clear Solo button to disable all active solos at once.
  - Defers to CloudRig's own handler on CloudRig-managed rigs.
- **Pose Utilities** (disabled in Rest position):
  - Clear Bone Transforms
  - Apply Pose as Rest Pose
- **Weight Utilities**:
  - Normalize All Weights
- Configurable keymap shortcut with preview in Add-on Preferences.
- CloudRig detection via PropertyGroup presence and custom property fallback.
