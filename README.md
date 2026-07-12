# Weight Paint Armature Tools

A Blender add-on that surfaces common armature operators inside Weight Paint
mode, so you can adjust rig state without switching context.

---

## Features

### Sidebar Panel

Located in the **N-panel → Armature** tab while in Weight Paint mode.

| Section | Controls |
|---|---|
| **Armature** | Displays the name of the linked armature. Shows a *CloudRig* badge when a CloudRig-managed rig is detected. |
| **Pose Position** | `POSE` / `REST` enum buttons and a quick-toggle operator, wired directly to `armature.data.pose_position`. |
| **Bone Layers / Collections** | Opens the bone layer popup. Shows a *Clear Solo* button when a solo is active. Hidden for CloudRig rigs. |
| **Pose** | **Auto IK**, **X-Axis Mirror**, **Relative Mirror**, and **Affect Only Locations** toggles — the same controls Blender exposes only in Pose Mode's header, wired directly to `pose.use_auto_ik` / `pose.use_mirror_x` / `pose.use_mirror_relative` and `tool_settings.use_transform_pivot_point_align`. **Clear Bone Transforms** — clears location, rotation, and scale on the selected bones (`pose.transforms_clear`), disabled when the armature is in Rest Position. |
| **Weight Utilities** | **Normalize All Weights** — normalizes all vertex groups so weights sum to 1. |

### Bone Layer / Collection Popup

Press **M** in the 3D viewport while in Weight Paint mode to open a popup
showing all bone layers (Blender 3.x) or bone collections (Blender 4.0+).

- **Visibility toggles** — show or hide each layer / collection.
- **Solo** — click the radio button next to any collection to isolate it.
  Uses the native `BoneCollection.is_solo` property (Blender 4.0+).
- **Clear Solo** — restores all collections; visible in both the popup
  header and the sidebar panel while a solo is active.

The shortcut is configurable under **Edit → Preferences → Add-ons →
Weight Paint Armature Tools**.

### CloudRig Compatibility

When the active armature is detected as a CloudRig rig, the add-on:

- Hides the Bone Layers section from the panel (CloudRig provides its
  own interface).
- Returns `False` from the popup `poll()`, allowing the **M** keypress to
  fall through to CloudRig's own handler.
- Shows a *CloudRig* badge in the armature identity box so the distinction
  is visible at a glance.

Detection uses two checks in order: a structural check for the
`cloudrig` PropertyGroup registered on `bpy.types.Armature` while the
CloudRig add-on is active, and a data check for the `cloudrig` custom
property that CloudRig bakes into generated rigs.

---

## Compatibility

| Blender | Support |
|---|---|
| 3.0 – 3.6 | Bone **layers** (32-bit grid) |
| 4.0+ | Bone **collections** with native `is_solo` |

The `blender_manifest.toml` targets Blender 4.2+ for installation via the
Extensions platform. For Blender 3.x, install manually using the legacy
zip method described below.

---

## Installation

### Blender 4.2+ (Extensions)

1. Download `wp_armature_tools.py` and `blender_manifest.toml` and place
   them in a folder named `wp_armature_tools`.
2. Zip the folder.
3. Open Blender and go to **Edit → Preferences → Get Extensions**.
4. Click **Install from Disk** and select the zip file.

### Blender 3.x (Legacy)

1. Download `wp_armature_tools.py`.
2. Open Blender and go to **Edit → Preferences → Add-ons**.
3. Click **Install**, select the `.py` file, and enable the add-on.

---

## Usage

### Typical workflow

1. Select your mesh and enter **Weight Paint** mode.
2. Open the **N-panel** and switch to the **Armature** tab.
3. Use the **Pose Position** controls to toggle the rig between Pose and
   Rest without leaving Weight Paint mode.
4. Press **M** to open the bone layer / collection popup. Click the radio
   button next to a collection to solo it while painting; click again or
   press *Clear Solo* to restore all.
5. Select bones in the viewport (Ctrl-click for multiple), then use
   **Clear Bone Transforms** to reset their pose without changing mode.

### Keymap

The **M** shortcut is registered in the `3D View` keymap (broader than the
`Weight Paint` keymap, which does not reliably receive general key events).
The `poll()` restricts it to Weight Paint mode on a mesh with a non-CloudRig
armature modifier, so it does not interfere with other modes.

To change the key: **Edit → Preferences → Add-ons → Weight Paint Armature
Tools → Keymap**.

---

## License

GNU General Public License v2.0 or later.
See [SPDX:GPL-2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later.html).
