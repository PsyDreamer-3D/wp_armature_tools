# Changelog

All notable changes to Weight Paint Armature Tools are documented here.

## [Unreleased]

### Added
- **Split Coaxial Weights** operator (Weight Utilities section): splits a single vertex group across N co-axial bones by projecting each vertex onto the combined bone axis. The bone chain is auto-detected from the active vertex group name (`.001`, `.002`, … suffix convention) and displayed per-bone in the dialog with validity indicators. Bones can be entered manually as a comma-separated list to support non-standard naming. Respects the active Weight Paint mirror settings — when Mirror Vertex Groups is enabled, the full mirrored chain is split automatically.
- **Blend Width** and **Smooth Iterations** options on Split Coaxial Weights: Blend Width feathers each internal split boundary with a smoothstep transition instead of a hard cut, splitting a vertex's weight between the two adjacent bones; Smooth Iterations runs an edge-topology-aware Laplacian smooth (matching Blender's own vertex group smooth) across every boundary in the chain afterward.
- Release workflow and build scripts for automated packaging.

### Changed
- Repo structure updated to match project conventions.

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
