# Render Manager
**A Blender addon for managing render layers, passes, compositor node outputs, and collection visibility across view layers.**

Built for Blender 4.2+ · GNU GPL v3

---

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Layer Manager](#layer-manager)
  - [View Layer Visibility](#view-layer-visibility)
  - [Output Path Setup](#output-path-setup)
  - [Render Layer Settings](#render-layer-settings)
  - [Create Render Nodes](#create-render-nodes)
  - [Per-Pass Denoising](#per-pass-denoising)
  - [Combine Passes](#combine-passes)
  - [EXR Compression & Color Depth](#exr-compression--color-depth)
- [Collection Manager](#collection-manager)
- [Special Thanks](#special-thanks)
- [License](#license)

---

## Overview

Render Manager streamlines multi-layer render pipelines in Blender. It gives you a centralized panel to control view layer visibility, automate compositor file output node creation, manage render passes, and toggle collection visibility across all view layers at once — without diving into the node editor or hunting through scattered properties.

---

## Installation

1. Download the latest `.zip` release.
2. In Blender, go to **Edit → Preferences → Add-ons → Install from Disk**.
3. Select the downloaded `.zip` file.
4. Enable **Render Manager** in the add-on list.

The panel appears in **Properties → View Layer**.

---

## Layer Manager

### View Layer Visibility

The top section of the panel lists all view layers in your scene. From here you can:

- **Toggle render** — enable or disable each view layer for rendering using the eye icon on the right.
- **Rename** — edit the layer name directly in the list.
- **Reorder** — use the up/down arrows on the side to change the layer order.
- **Add / Remove** — create a new layer or delete the active one with the `+` / `-` buttons.
- **Copy / Paste settings** — duplicate render pass settings from one layer to another using the copy/paste icons on each row.

---

### Output Path Setup

Controls how compositor file output nodes are named and where they save their EXRs.

#### Use Native Output Filepath *(on by default)*

When enabled, the addon derives all output paths automatically from Blender's native render output path (**Output Properties → Output → File Path**).

For each active view layer the structure becomes:

```
{native_dir}/{LayerName}/{stem}_{LayerName}.####.exr
{native_dir}/{LayerName}/{stem}_{LayerName}_data.####.exr
```

**Example** — If your Blender file is named `Test_v002` and your native output path is set to `//renders/Test_v002/Test_v002.####`, with two view layers `Env_All` and `Utility_All`, the addon will produce:

```
renders/Test_v002/Env_All/Test_v002_Env_All.####.exr
renders/Test_v002/Env_All/Test_v002_Env_All_data.####.exr

renders/Test_v002/Utility_All/Test_v002_Utility_All.####.exr
renders/Test_v002/Utility_All/Test_v002_Utility_All_data.####.exr
```

A live **Output Preview** is shown in the panel so you can verify the resolved paths before running Create Render Nodes.

#### Manual Template *(Use Native Filepath off)*

When the toggle is turned off, the field auto-populates with the native-derived pattern as an editable template:

```
//renders/Test_v002/{LayerName}/Test_v002_{LayerName}
```

`{LayerName}` is a token that gets replaced with each view layer's name at node creation time. Edit the template freely to customise folder depth, naming conventions, or prefixes. A **Resolved paths** preview updates live below the field to show exactly what each layer will produce.

---

### Render Layer Settings

Opens a popup spreadsheet showing all render passes side by side across every view layer. Useful for quickly enabling or disabling passes on multiple layers without switching between them one by one.

Sections covered:
- **Render** toggles (enable/disable per layer)
- **Custom Passes** (cryptomatte, shadow catcher, etc.)
- **Light Passes** (diffuse, glossy, transmission, etc.)
- **Material & World overrides**
- **Sample counts per layer**

---

### Create Render Nodes

Clicking **Create Render Nodes** clears the existing compositor node tree and rebuilds it from scratch based on your current settings. For each active view layer it creates:

| Node | Contents |
|---|---|
| **Color Output** | Beauty, RGBA, Alpha, and light pass outputs |
| **Data Output** | Normal, depth, and auxiliary data passes |
| **Noisy Output** *(optional)* | Pre-denoised beauty passes saved separately |
| **Backup Output** *(optional)* | Full unmodified 32-bit pass copy |

All nodes are wired automatically. Output paths follow whichever mode is selected (native or manual template).

> **Note:** The file must be saved before running Create Render Nodes.

---

### Per-Pass Denoising

Denoising can be applied selectively per pass rather than only to the final composite. Available passes depend on the active render engine.

**Cycles passes:**
- Image, Diffuse, Glossy, Transmission, Alpha, Volume Direct/Indirect, Shadow Catcher, Emit, Environment, AO, Light Groups

**EEVEE passes:**
- Image, Diffuse, Glossy, Transmission, Alpha, Emit, Environment, Shadow, AO

Additional options:
- **Save Noisy in File** — embed the noisy version alongside the denoised output in the same EXR.
- **Save Noisy Separately** — write noisy passes to their own `_noisy` output node.

---

### Combine Passes

Merges diffuse and glossy sub-passes into a single combined output to reduce the number of output slots.

- **Cycles** → `Combine Diffuse + Glossy` merges direct, indirect, and color sub-passes into unified Diffuse, Glossy, and Transmission outputs.
- **EEVEE** → produces `Diffuse Combined` and `Glossy Combined` slots.

---

### EXR Compression & Color Depth

**Color Depth**
- `16` — half float, smaller files, sufficient for most beauty passes.
- `32` — full float, used automatically for data passes regardless of this setting.

**EXR Compression** — set independently for Beauty and Data outputs:

| Codec | Description |
|---|---|
| `ZIP` | Lossless, good general purpose |
| `ZIPS` | Lossless, per-scanline |
| `PIZ` | Lossless, best for noisy images |
| `RLE` | Lossless, best for flat regions |
| `DWAA` | Lossy, very small files |
| `DWAB` | Lossy, block-based variant of DWAA |

When DWAA or DWAB is selected, a **Compression Level** slider appears (range 0–500; Blender default is 45).

**Compatibility — Y-Up Fix**
Enables a coordinate-system correction node for pipelines that expect Y-up orientation (e.g. game engines or certain compositing applications).

---

## Collection Manager

Accessed via the **Collection Manager** button in the Render Manager panel. Opens a popup spreadsheet where rows are your scene's collections and columns are your view layers.

For each collection / view layer combination you can toggle:

| Control | Effect |
|---|---|
| **Exclude** | Removes the collection from the view layer entirely |
| **Holdout** | Renders the collection as a holdout matte |
| **Indirect Only** | Collection contributes to lighting but is not directly visible |

Collections are displayed in a tree matching your outliner hierarchy. Click the arrow next to any collection to expand or collapse its children. The popup width scales automatically with the number of view layers.

---

## Special Thanks

A huge thank you to **Tinkerboi** and **MJ** for their awesome support throughout the development of this addon. This project wouldn't be what it is without them.

---

## License

Render Manager is released under the **GNU General Public License v3.0**.

You are free to use, modify, and distribute this addon under the terms of the GPL v3. See the [`LICENSE`](LICENSE) file for the full license text, or visit [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).
