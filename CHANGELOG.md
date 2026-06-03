# Changelog

All notable changes to Weight Paint Armature Tools are documented here.

## [Unreleased]

### Added
- **Split Coaxial Weights** operator (Weight Utilities section): splits a single vertex group between two co-axial bones by projecting each vertex onto the combined bone axis. Respects the active Weight Paint mirror settings — when Mirror Vertex Groups is enabled, the mirrored bone pair is split automatically.
- **Fill Bone from Region** operator (Weight Utilities section): populates a bone's vertex group by blending weights from neighbouring groups, analogous to the Vertex Weight Mix modifier. Auto-detects source VGs from the target bone's parent and children. Respects Mirror Vertex Groups.
  - **Blend Mode** (Minimum / Average / Maximum / Sum): controls how source weights are combined. Default is *Minimum* — the target receives weight only where all sources overlap, naturally scoping the fill to the transition zone without requiring a strict spatial filter. Ideal for inserting a bone between two existing weighted bones.
  - **Limit to Bone Region** (default on): additionally clips filled vertices to the target bone's physical extent via axis projection.
  - **Normalise Overlap** (default on): after writing each target weight, scales all involved groups (sources + target) so their combined total equals the pre-fill source total. No weight is created or destroyed; it is redistributed. Prevents over-weighted vertices that corrupt blur and other Weight Paint brush behaviour.
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
