import bpy
import os
import pathlib
import inspect


# --------------------------------------------------------------------------
#  GLOBAL CLIPBOARD + Helpers for Copy/Paste
# --------------------------------------------------------------------------

# This global dictionary will store pass settings after we click "Copy" on a layer.
RENDER_MANAGER_CLIPBOARD = {}


def gather_layer_settings(layer):
    """
    Gather pass properties from a given layer (and sub-objects if needed),
    storing them in a dict. Adjust or add pass properties as desired.
    """
    data = {}
    # Here we list all properties you might want to copy (both Cycles and Eevee).
    # For example, all these come from your “Data/Light Passes” and cryptomatte.
    # If a property doesn't exist on this layer, we skip it.
    # Modify or expand this list if needed.

    props_to_copy = [
        # Common:
        ("", "use_pass_combined"),
        ("", "use_pass_z"),
        ("", "use_pass_mist"),
        ("", "use_pass_normal"),
        ("", "use_pass_position"),
        ("", "use_pass_uv"),
        ("", "use_pass_object_index"),
        ("", "use_pass_material_index"),
        # Light passes:
        ("", "use_pass_shadow"),
        ("", "use_pass_ambient_occlusion"),
        ("", "use_pass_emit"),
        ("", "use_pass_environment"),
        ("", "use_pass_diffuse_direct"),
        ("", "use_pass_diffuse_indirect"),
        ("", "use_pass_diffuse_color"),
        ("", "use_pass_glossy_direct"),
        ("", "use_pass_glossy_indirect"),
        ("", "use_pass_glossy_color"),
        ("", "use_pass_transmission_direct"),
        ("", "use_pass_transmission_indirect"),
        ("", "use_pass_transmission_color"),
        ("", "use_pass_subsurface_direct"),
        ("", "use_pass_subsurface_indirect"),
        ("", "use_pass_subsurface_color"),
        # Cryptomatte:
        ("", "use_pass_cryptomatte_object"),
        ("", "use_pass_cryptomatte_material"),
        ("", "use_pass_cryptomatte_asset"),
        ("", "pass_cryptomatte_depth"),
        ("", "pass_cryptomatte_accurate"),
        # Eevee-specific:
        ("eevee", "use_pass_transparent"),
        # Cycles-specific:
        ("cycles", "denoising_store_passes"),
        ("cycles", "use_pass_shadow_catcher"),
    ]

    for prop_path, prop_name in props_to_copy:
        container = getattr(layer, prop_path, None) if prop_path else layer
        if container and hasattr(container, prop_name):
            data[(prop_path, prop_name)] = getattr(container, prop_name)

    return data

def update_exr_compression(self, context):
    for scene in bpy.data.scenes:
        if not scene.use_nodes:
            continue
        for node in scene.node_tree.nodes:
            if isinstance(node, bpy.types.CompositorNodeOutputFile):
                if "Color Output" in node.label:
                    node.format.exr_codec = scene.render_manager.beauty_compression
                elif "Data Output" in node.label:
                    node.format.exr_codec = scene.render_manager.data_compression


def apply_layer_settings(layer, settings):
    """
    Apply the previously copied settings to layer.
    We skip any property that does not exist on this layer.
    """
    for (prop_path, prop_name), value in settings.items():
        container = getattr(layer, prop_path, None) if prop_path else layer
        if container and hasattr(container, prop_name):
            setattr(container, prop_name, value)


# --------------------------------------------------------------------------
#  Helpers to get/set the "render use" property for a View Layer
#    (unchanged from your script)
# --------------------------------------------------------------------------


def get_use_prop(view_layer):
    """Get the render toggle property (varies by Blender version)."""
    if hasattr(view_layer, "use"):
        return view_layer.use
    elif hasattr(view_layer, "use_for_render"):
        return view_layer.use_for_render
    return True


def set_use_prop(view_layer, value):
    """Set the render toggle property (varies by Blender version)."""
    if hasattr(view_layer, "use"):
        view_layer.use = value
    elif hasattr(view_layer, "use_for_render"):
        view_layer.use_for_render = value


# --------------------------------------------------------------------------
#  PASS DEFINITIONS + get_pass_groups_for_engine
#    (unchanged from your script so the spreadsheet still works)
# --------------------------------------------------------------------------

CYCLES_PASS_GROUPS = [
    (
        "Main Pass",
        [
            ("", "use_pass_combined", "Combined"),
        ],
    ),
    (
        "Data Passes",
        [
            ("", "use_pass_z", "Z"),
            ("", "use_pass_mist", "Mist"),
            ("", "use_pass_normal", "Normal"),
            ("", "use_pass_position", "Position"),
            ("", "use_pass_uv", "UV"),
            ("", "use_pass_vector", "Vector"),
            ("", "use_pass_object_index", "Object Index"),
            ("", "use_pass_material_index", "Material Index"),
            ("cycles", "denoising_store_passes", "Denoising Data"),
        ],
    ),
    (
        "Light Passes",
        [
            ("", "use_pass_shadow", "Shadow"),
            ("", "use_pass_ambient_occlusion", "Ambient Occlusion"),
            ("", "use_pass_emit", "Emission"),
            ("", "use_pass_environment", "Environment"),
            ("", "use_pass_diffuse_direct", "Diffuse Direct"),
            ("", "use_pass_diffuse_indirect", "Diffuse Indirect"),
            ("", "use_pass_diffuse_color", "Diffuse Color"),
            ("", "use_pass_glossy_direct", "Glossy Direct"),
            ("", "use_pass_glossy_indirect", "Glossy Indirect"),
            ("", "use_pass_glossy_color", "Glossy Color"),
            ("", "use_pass_transmission_direct", "Transmission Direct"),
            ("", "use_pass_transmission_indirect", "Transmission Indirect"),
            ("", "use_pass_transmission_color", "Transmission Color"),
            ("", "use_pass_volume_direct", "Volume Direct"),
            ("", "use_pass_volume_indirect", "Volume Indirect"),
            ("cycles", "use_pass_shadow_catcher", "Shadow Catcher"),
        ],
    ),
    (
        "Cryptomatte",
        [
            ("", "use_pass_cryptomatte_object", "Crypto Object"),
            ("", "use_pass_cryptomatte_material", "Crypto Material"),
            ("", "use_pass_cryptomatte_asset", "Crypto Asset"),
            ("", "pass_cryptomatte_depth", "Levels (Depth)"),
            ("", "pass_cryptomatte_accurate", "Accurate"),
        ],
    ),
]

EEVEE_PASS_GROUPS = [
    (
        "Main Pass",
        [
            ("", "use_pass_combined", "Combined"),
        ],
    ),
    (
        "Data Passes",
        [
            ("", "use_pass_combined", "Combined"),
            ("", "use_pass_z", "Z"),
            ("", "use_pass_mist", "Mist"),
            ("", "use_pass_normal", "Normal"),
            ("", "use_pass_position", "Position"),
            ("", "use_pass_vector", "Vector"),
        ],
    ),
    (
        "Light Passes",
        [
            ("", "use_pass_diffuse_direct", "Diffuse Light"),
            ("", "use_pass_diffuse_color", "Diffuse Color"),
            ("", "use_pass_glossy_direct", "Specular Light"),
            ("", "use_pass_glossy_color", "Specular Color"),
            ("", "use_pass_emit", "Emission"),
            ("", "use_pass_environment", "Environment"),
            ("", "use_pass_shadow", "Shadow"),
            ("", "use_pass_ambient_occlusion", "Ambient Occlusion"),
            ("eevee", "use_pass_transparent", "Transparent"),
        ],
    ),
    (
        "Cryptomatte",
        [
            ("", "use_pass_cryptomatte_object", "Crypto Object"),
            ("", "use_pass_cryptomatte_material", "Crypto Material"),
            ("", "use_pass_cryptomatte_asset", "Crypto Asset"),
            ("", "pass_cryptomatte_depth", "Levels (Depth)"),
            ("", "pass_cryptomatte_accurate", "Accurate"),
        ],
    ),
]

# at some point we'll expose the node operators to the spreadsheet, but not yet
NODE_OPERATIONS = [
    (
        "Node Operations",
        [
            ("", "override_layer", "Enable Overrides For Layer"),
            ("", "fixed_for_y_up", "Make Y Up"),
            ("", "combine_diff_glossy", "Combine Diff/Glossy/Trans"),
            ("", "denoise", "Enable Per Pass Denoising"),
            ("", "denoise_image", "Image Pass"),
            ("", "denoise_diffuse", "Diffuse Pass"),
            ("", "denoise_glossy", "Glossy Pass"),
            ("", "denoise_trans", "Transmission Pass"),
            ("", "denoise_alpha", "Alpha Pass"),
            ("", "denoise_volumetrics", "Volumetrics"),
            ("", "denoise_shadow_catcher", "Shadow Catcher"),
            ("", "save_noisy_in_file", "Embed Noisy Passes"),
            ("", "save_noisy_separately", "Save Noisy Passes Separately"),
            ("", "backup_passes", "Backup Original Passes"),
        ],
    ),
]


def get_pass_groups_for_engine(engine):
    """
    Return pass groups based on the engine name.
    Handles 'BLENDER_EEVEE_NEXT' or 'BLENDER_CYCLES' by substring check.
    """
    eng_up = engine.upper()
    if "CYCLES" in eng_up:
        return CYCLES_PASS_GROUPS
    elif "EEVEE" in eng_up:
        return EEVEE_PASS_GROUPS
    else:
        # Workbench or unknown engine
        return []

# --------------------------------------------------------------------------
#  Switch View Layer Operators
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_switch_layer(bpy.types.Operator):
    """Switch View Layer"""

    bl_idname = "wm.switch_view_layer"
    bl_label = "Switch View Layer"

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        vl = scene.view_layers[self.layer_index]
        context.window.view_layer = vl

        for screen in bpy.data.screens:
            for area in screen.areas:
                area.tag_redraw()
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Reorder View Layer Operators
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_reorder_view_layer(bpy.types.Operator):
    """Reorder View Layer"""

    bl_idname = "wm.reorder_view_layer"
    bl_label = "Reorder View Layer"

    direction: bpy.props.EnumProperty(
        items=[
            ("UP", "Up", "Up"),
            ("DOWN", "Down", "Down"),
        ]
    )

    def execute(self, context):
        scene = context.scene
        active_index = None

        for i, vl in enumerate(context.scene.view_layers):
            if vl == context.view_layer:
                active_index = i
                break

        if self.direction == "DOWN":
            if len(context.scene.view_layers) > active_index + 1:
                vl = scene.view_layers.move(active_index, active_index + 1)
        if self.direction == "UP":
            if active_index - 1 >= 0:
                vl = scene.view_layers.move(active_index, active_index - 1)

        for screen in bpy.data.screens:
            for area in screen.areas:
                area.tag_redraw()
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  COPY & PASTE Operators
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_copy_layer_settings(bpy.types.Operator):
    """Copy all pass settings from this View Layer into an internal clipboard"""

    bl_idname = "wm.copy_layer_settings"
    bl_label = "Copy Layer Settings"

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        vl = scene.view_layers[self.layer_index]

        global RENDER_MANAGER_CLIPBOARD
        RENDER_MANAGER_CLIPBOARD = gather_layer_settings(vl)
        print(RENDER_MANAGER_CLIPBOARD)

        self.report({"INFO"}, f"Copied settings from layer '{vl.name}'.")
        return {"FINISHED"}


class RENDER_MANAGER_OT_paste_layer_settings(bpy.types.Operator):
    """Paste the previously copied pass settings into this View Layer"""

    bl_idname = "wm.paste_layer_settings"
    bl_label = "Paste Layer Settings"

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        global RENDER_MANAGER_CLIPBOARD

        scene = context.scene
        vl = scene.view_layers[self.layer_index]

        if not RENDER_MANAGER_CLIPBOARD:
            self.report({"WARNING"}, "No copied settings found. Please copy first.")
            return {"CANCELLED"}

        apply_layer_settings(vl, RENDER_MANAGER_CLIPBOARD)
        self.report({"INFO"}, f"Pasted settings onto layer '{vl.name}'.")
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Operator: Render Layer Settings (the spreadsheet) - UNCHANGED
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_view_layer_settings(bpy.types.Operator):
    """Show a pop-up table to toggle passes per View Layer."""

    bl_idname = "wm.view_layer_settings"
    bl_label = "Render Layer Settings"

    def invoke(self, context, event):
        # Get the width of the entire Blender window
        screen_width = context.window.width  # Width of the entire Blender window
        max_width = screen_width - 20
        scene = context.scene
        view_layers = scene.view_layers
        num_view_layers = len(view_layers)
        base_width = 500
        column_width = 100
        total_width = base_width + (num_view_layers * column_width)
        width = min(total_width, max_width)
        return context.window_manager.invoke_props_dialog(self, width=width)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        view_layers = scene.view_layers

        if not view_layers:
            layout.label(text="No View Layers found.")
            return

        engine = scene.render.engine
        pass_groups = get_pass_groups_for_engine(engine)

        if not pass_groups:
            layout.label(text=f"No passes defined for engine: {engine}")
            return

        # Table header row
        header = layout.row(align=True)
        split = header.split(factor=0.2, align=True)
        split.label(text="Passes")
        sub = split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split = sub.split(factor=1.0 / (len(view_layers) - i), align=True)
                col_split.label(text=vl.name)
                sub = col_split
            else:
                sub.label(text=vl.name)

        # Render On/Off and Copy/Paste Rows
        box_render_toggle = layout.box()
        # box_render_toggle.label(text="Render / Copy-Paste Tools")

        # -- Row for "Rendering" checkboxes --
        row = box_render_toggle.row(align=True)
        row_split = row.split(factor=0.2, align=True)
        row_split.label(text="Rendering")  # left column label
        sub_rend = row_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split = sub_rend.split(
                    factor=1.0 / (len(view_layers) - i), align=True
                )
                # Try using vl.use first; if not present, use vl.use_for_render
                if hasattr(vl, "use"):
                    col_split.prop(vl, "use", text="")
                elif hasattr(vl, "use_for_render"):
                    col_split.prop(vl, "use_for_render", text="")
                else:
                    col_split.label(text="N/A")
                sub_rend = col_split
            else:
                # Last column
                if hasattr(vl, "use"):
                    sub_rend.prop(vl, "use", text="")
                elif hasattr(vl, "use_for_render"):
                    sub_rend.prop(vl, "use_for_render", text="")
                else:
                    sub_rend.label(text="N/A")

        # -- Row for "Copy/Paste" buttons --
        row_cp = box_render_toggle.row(align=True)
        row_cp_split = row_cp.split(factor=0.2, align=True)
        row_cp_split.label(text="Copy/Paste")  # left column label
        sub_cp = row_cp_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_cp = sub_cp.split(
                    factor=1.0 / (len(view_layers) - i), align=True
                )
                # We create a mini-row for the two icons
                row_icons = col_split_cp.row(align=True)
                op_copy = row_icons.operator(
                    "wm.copy_layer_settings", text="", icon="COPYDOWN"
                )
                op_copy.layer_index = i
                op_paste = row_icons.operator(
                    "wm.paste_layer_settings", text="", icon="PASTEDOWN"
                )
                op_paste.layer_index = i
                sub_cp = col_split_cp
            else:
                row_icons = sub_cp.row(align=True)
                op_copy = row_icons.operator(
                    "wm.copy_layer_settings", text="", icon="COPYDOWN"
                )
                op_copy.layer_index = i
                op_paste = row_icons.operator(
                    "wm.paste_layer_settings", text="", icon="PASTEDOWN"
                )
                op_paste.layer_index = i

        # Show each pass group
        for group_title, pass_list in pass_groups:
            # Filter out passes that no View Layer has
            valid_rows = []
            for prop_path, prop_name, prop_label in pass_list:
                any_layer_has_it = False
                for vl in view_layers:
                    data_ref = getattr(vl, prop_path, None) if prop_path else vl
                    if data_ref and hasattr(data_ref, prop_name):
                        any_layer_has_it = True
                        break
                if any_layer_has_it:
                    valid_rows.append((prop_path, prop_name, prop_label))
            if not valid_rows:
                # Skip this entire group if no row is valid
                continue
            box = layout.box()
            box.label(text=group_title)
            for prop_path, prop_name, prop_label in valid_rows:
                row = box.row(align=True)
                row_split = row.split(factor=0.2, align=True)
                row_split.label(text=prop_label)
                sub2 = row_split.split(factor=1.0, align=True)
                for j, vl in enumerate(view_layers):
                    data_ref = getattr(vl, prop_path, None) if prop_path else vl
                    if j < len(view_layers) - 1:
                        subcol = sub2.split(
                            factor=1.0 / (len(view_layers) - j), align=True
                        )
                    else:
                        subcol = sub2
                    if data_ref and hasattr(data_ref, prop_name):
                        subcol.prop(data_ref, prop_name, text="")
                    else:
                        subcol.label(text="")  # skip
                    sub2 = subcol

        # Add Material Override, World Override, and Samples
        box_overrides = layout.box()
        box_overrides.label(text="View Layer Overrides")

        # Material Override
        row_material = box_overrides.row(align=True)
        row_material_split = row_material.split(factor=0.2, align=True)
        row_material_split.label(text="Material Override")
        sub_material = row_material_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_material = sub_material.split(
                    factor=1.0 / (len(view_layers) - i), align=True
                )
            else:
                col_split_material = sub_material
            if hasattr(vl, "material_override"):
                col_split_material.prop(vl, "material_override", text="")
            else:
                col_split_material.label(text="N/A")
            sub_material = col_split_material

        # World Override
        row_world = box_overrides.row(align=True)
        row_world_split = row_world.split(factor=0.2, align=True)
        row_world_split.label(text="World Override")
        sub_world = row_world_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_world = sub_world.split(
                    factor=1.0 / (len(view_layers) - i), align=True
                )
            else:
                col_split_world = sub_world
            if hasattr(vl, "world_override"):
                col_split_world.prop(vl, "world_override", text="")
            else:
                col_split_world.label(text="N/A")
            sub_world = col_split_world

        # Samples
        row_samples = box_overrides.row(align=True)
        row_samples_split = row_samples.split(factor=0.2, align=True)
        row_samples_split.label(text="Samples")
        sub_samples = row_samples_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_samples = sub_samples.split(
                    factor=1.0 / (len(view_layers) - i), align=True
                )
            else:
                col_split_samples = sub_samples
            if hasattr(vl, "samples"):
                col_split_samples.prop(vl, "samples", text="")
            else:
                col_split_samples.label(text="N/A")
            sub_samples = col_split_samples

    def execute(self, context):
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Panel: Render Manager - Add Copy/Paste Buttons (new)
# --------------------------------------------------------------------------


class RENDER_MANAGER_PT_panel(bpy.types.Panel):
    """Panel to list and toggle View Layers, plus open pass settings"""

    bl_label = "Render Manager"
    bl_idname = "RENDER_MANAGER_PT_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "view_layer"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="View Layer Visibility:")
        main_row = layout.row()
        box = main_row.box()
        col = box.column()
        side_col = main_row.column(align=True)

        side_col.operator(
            "wm.add_render_layer",
            text="",
            icon="ADD",
        )
        side_col.operator(
            "wm.remove_render_layer",
            text="",
            icon="REMOVE",
        )
        side_col.separator()
        op = side_col.operator("wm.reorder_view_layer", icon="TRIA_UP", text="")
        op.direction = "UP"
        op = side_col.operator("wm.reorder_view_layer", icon="TRIA_DOWN", text="")
        op.direction = "DOWN"

        for i, vl in enumerate(context.scene.view_layers):
            row = col.row(align=True)
            if vl == context.view_layer:
                row.label(text="", icon="RADIOBUT_ON")
            else:
                op = row.operator("wm.switch_view_layer", text="", icon="RADIOBUT_OFF")
                op.layer_index = i
            row.prop(vl, "name", text="")
            row.prop(vl, "use", text="", icon="RESTRICT_RENDER_OFF")

            op = row.operator("wm.copy_layer_settings", text="", icon="COPYDOWN")
            op.layer_index = i
            op = row.operator("wm.paste_layer_settings", text="", icon="PASTEDOWN")
            op.layer_index = i

        box.separator()

        layout.separator()
       
       # file path 
        col = layout.column(heading="")
        col.prop(scene.render_manager, "file_output_basepath")
        col = layout.column(heading="EXR Compression")

        # Add "Create Render Layer Settings" Button
        layout.operator(
            "wm.collection_spreadsheet",
            text="Collection Manager",
            icon="OUTLINER_COLLECTION",
        )
        layout.operator(
            "wm.view_layer_settings",
            text="Render Layer Settings",
            icon="MODIFIER",
        )

        # Add "Create Render Nodes" Button
        layout.operator(
            "wm.create_render_nodes",
            text="Create Render Nodes",
            icon="NODETREE",
        )

        side_col.separator()

        # Add all checkboxes in a column
        layout.use_property_split = True
        layout.use_property_decorate = False

        # Always show the following property (or any others you need)
        col = layout.column(heading="Compatibility")
        col.prop(scene.render_manager, "fixed_for_y_up")

        # Only show the following options if Cycles is used
        if scene.render.engine == "CYCLES":
            col.prop(scene.render_manager, "combine_diff_glossy")

        col = layout.column(heading="Per Pass Denoising")
        sub = col.row()
        sub.prop(scene.render_manager, "denoise")
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_image")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_diffuse")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_glossy")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_transmission")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_alpha")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_volumedir")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_volumeind")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_shadow_catcher")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "save_noisy_in_file")
        sub.active = scene.render_manager.denoise
        sub = col.row()
        sub.prop(scene.render_manager, "save_noisy_separately")
        sub.active = scene.render_manager.denoise

        col = layout.column(heading="Backup")
        sub = col.row()
        sub.prop(scene.render_manager, "backup_passes")

        col = layout.column(heading="Color Depth")
        sub = col.row()
        sub.prop(scene.render_manager, "color_depth_override", expand=True)
        
        col = layout.column(heading="EXR Compression")
        col.prop(scene.render_manager, "beauty_compression")
        col.prop(scene.render_manager, "data_compression")



# --------------------------------------------------------------------------
#  Operator: Create new layer
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_add_render_layer(bpy.types.Operator):
    """Add a new render layer"""

    bl_idname = "wm.add_render_layer"
    bl_label = "New Render Layer"
    bl_icon = "RENDERLAYERS"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        try:
            new_layer = scene.view_layers.new(name="New Layer")
            context.window.view_layer = new_layer
            self.report({"INFO"}, f"Created new render layer: {new_layer.name}")
        except AttributeError:
            self.report(
                {"ERROR"}, "Unable to create a new render layer. Check Blender version."
            )
            return {"CANCELLED"}
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Operator: Remove layer
# --------------------------------------------------------------------------


class RENDER_MANAGER_OT_remove_render_layer(bpy.types.Operator):
    """Remove render layer"""

    bl_idname = "wm.remove_render_layer"
    bl_label = "Remove Render Layer"
    bl_icon = "RENDERLAYERS"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        if len(context.scene.view_layers) > 1:
            return True

    def execute(self, context):
        scene = context.scene
        scene.view_layers.remove(context.view_layer)

        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Operator: Create Render Nodes
# --------------------------------------------------------------------------


def get_node_group_path():
    # Get the absolute path of the current script (even inside Blender)
    addon_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
    return os.path.join(addon_dir, "node_groups.blend")


def ensure_node_group(name):
    group = bpy.data.node_groups.get(name)

    if group is None:
        with bpy.data.libraries.load(get_node_group_path()) as (data_from, data_to):
            data_to.node_groups.append(name)

    group = bpy.data.node_groups.get(name)
    group.use_fake_user = True
    return group


class RENDER_MANAGER_OT_create_render_nodes(bpy.types.Operator):
    """Create and connect file output nodes based on the selected File Handling mode."""

    bl_idname = "wm.create_render_nodes"
    bl_label = "Create Render Nodes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Check if the file has been saved
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Please save the file first.")
            return {'CANCELLED'}
        scene = context.scene

        # ✅ Ensure the compositor is enabled
        scene.use_nodes = True

        node_tree = scene.node_tree

        y_up = ensure_node_group("Y-Up")
        vector_node = ensure_node_group("Vector")
        # y_up = ensure_node_group("Y-Up")
        # combine_node = ensure_combine_pass_node_groups()
        # vector_node = ensure_vector_node_groups()

        # ✅ Clear existing nodes
        node_tree.nodes.clear()

        # ✅ Define column and row spacing for structured node layout
        column_spacing = 300
        row_spacing = -600  # Adjusted for even node spacing
        previous_alpha_node = None

        composite_node = node_tree.nodes.new(type="CompositorNodeComposite")
        composite_node.location = (7 * column_spacing, 0)

        # ✅ Create render nodes
        for i, vl in enumerate(scene.view_layers):
            clean_layer_name = (
                vl.name.split("_", 1)[-1] if vl.name.startswith("layers_") else vl.name
            )
            # Skip this view layer if its "use" flag is not enabled.
            # (Note: the original code indexes scene.view_layers by name.
            # Here we assume 'vl' already represents the current view layer.)
            if not vl.use:
                continue
            x_pos = 0  # Keep first column aligned
            y_pos = i * row_spacing  # Arrange nodes in rows per layer

            # ✅ Create a unique Render Layers node for this layer
            per_layer_node = node_tree.nodes.new(type="CompositorNodeRLayers")
            per_layer_node.layer = vl.name
            per_layer_node.location = (x_pos, y_pos)

            # ✅ Handle Y-Up Fix for Normal and Position Passes
            normal_combine_xyz = None
            position_combine_xyz = None
            y_ups = {}

            if scene.render_manager.fixed_for_y_up:
                # Check if Position pass exists
                if "Position" in per_layer_node.outputs:
                    y_up_node = node_tree.nodes.new("CompositorNodeGroup")
                    y_up_node.node_tree = y_up
                    y_up_node.location = (x_pos + column_spacing, y_pos + 40)
                    y_up_node.label = "Y-Up Position"
                    y_up_node.hide = True
                    y_ups["Position"] = y_up_node

                    node_tree.links.new(
                        per_layer_node.outputs["Position"], y_up_node.inputs[0]
                    )

                # Check if Normal pass exists
                if "Normal" in per_layer_node.outputs:
                    y_up_node = node_tree.nodes.new("CompositorNodeGroup")
                    y_up_node.node_tree = y_up
                    y_up_node.location = (x_pos + column_spacing, y_pos + 10)
                    y_up_node.label = "Y-Up Normal"
                    y_up_node.hide = True
                    y_ups["Normal"] = y_up_node

                    node_tree.links.new(
                        per_layer_node.outputs["Normal"], y_up_node.inputs[0]
                    )

                if "Vector" in per_layer_node.outputs:
                    y_up_node = node_tree.nodes.new("CompositorNodeGroup")
                    y_up_node.node_tree = vector_node
                    # Adjust the offset as needed for a proper layout.
                    y_up_node.location = (x_pos + column_spacing, y_pos - 20)
                    y_up_node.label = "Y-Up Vector"
                    y_up_node.hide = True
                    y_ups["Vector"] = y_up_node
                    node_tree.links.new(
                        per_layer_node.outputs["Vector"], y_up_node.inputs[0]
                    )

            # ✅ Create File Output nodes for Color and Data
            layer_color_node = node_tree.nodes.new("CompositorNodeOutputFile")
            layer_data_node = node_tree.nodes.new("CompositorNodeOutputFile")
            layer_color_node.label = f"{clean_layer_name} Color Output"
            layer_data_node.label = f"{clean_layer_name} Data Output"

            # --- Modified base path block begins here ---
            user_path = bpy.path.abspath(scene.render_manager.file_output_basepath)
            layer_base_path = os.path.join(user_path, clean_layer_name)
            os.makedirs(layer_base_path, exist_ok=True)

            # Convert the (possibly relative) base path to an absolute path and create the directory.
            abs_layer_base_path = bpy.path.abspath(layer_base_path)
            os.makedirs(abs_layer_base_path, exist_ok=True)

            # Set the file output nodes' base_path property.
            layer_color_node.base_path = os.path.join(
                layer_base_path, f"{clean_layer_name}.####.exr"
            )
            layer_data_node.base_path = os.path.join(
                layer_base_path, f"{clean_layer_name}_data.####.exr"
            )
            # --- Modified base path block ends here ---

            layer_color_node.format.file_format = "OPEN_EXR_MULTILAYER"
            layer_data_node.format.file_format = "OPEN_EXR_MULTILAYER"
            layer_color_node.format.exr_codec = scene.render_manager.beauty_compression
            layer_data_node.format.exr_codec = scene.render_manager.data_compression
            if int(scene.render_manager.color_depth_override) == 0:
                layer_color_node.format.color_depth = (
                    scene.render.image_settings.color_depth
                )
            else:
                layer_color_node.format.color_depth = (
                    scene.render_manager.color_depth_override
                )
            layer_data_node.layer_slots.clear()  # we don't need the Image input
            layer_color_node.layer_slots.clear()  # we don't need the Image input
            layer_data_node.format.color_depth = "32"  # data node is always 32 bit

            layer_color_node.location = (x_pos + 4 * column_spacing, y_pos)
            layer_data_node.location = (x_pos + 5 * column_spacing, y_pos)

            if (
                scene.render_manager.save_noisy_separately
                and scene.denoise
                and a_denoising_operation_is_checked(scene)
            ):
                layer_noisy_node = node_tree.nodes.new("CompositorNodeOutputFile")
                layer_noisy_node.label = f"{clean_layer_name} Noisy Output"
                layer_noisy_node.format.file_format = "OPEN_EXR_MULTILAYER"
                layer_noisy_node.base_path = os.path.join(
                    layer_base_path, f"{clean_layer_name}_noisy.####.exr"
                )
                layer_noisy_node.format.color_depth = (
                    layer_color_node.format.color_depth
                )
                layer_noisy_node.layer_slots.clear()  # we don't need the Image input
                layer_noisy_node.location = (x_pos + 6 * column_spacing, y_pos)

            if scene.render_manager.backup_passes:
                layer_backup_node = node_tree.nodes.new("CompositorNodeOutputFile")
                layer_backup_node.label = f"{clean_layer_name} Backup Output"
                layer_backup_node.format.file_format = "OPEN_EXR_MULTILAYER"
                layer_backup_node.base_path = os.path.join(
                    layer_base_path, f"{clean_layer_name}_backup.####.exr"
                )
                layer_backup_node.format.color_depth = (
                    "32"  # force 32-bit for data layer compatibility
                )
                layer_backup_node.layer_slots.clear()  # Image input will be created by node linking process
                layer_backup_node.location = (x_pos - 1 * column_spacing, y_pos)

            # ✅ Create Alpha Over nodes for compositing
            alpha_over = None

            if i == 0:
                alpha_over = per_layer_node
            else:
                alpha_over = node_tree.nodes.new("CompositorNodeAlphaOver")
                alpha_over.location = (x_pos + 6 * column_spacing, y_pos)
                node_tree.links.new(
                    per_layer_node.outputs["Image"], alpha_over.inputs[1]
                )

            if alpha_over:
                if previous_alpha_node:
                    node_tree.links.new(
                        previous_alpha_node.outputs["Image"], alpha_over.inputs[2]
                    )
                previous_alpha_node = alpha_over

            # Link the Render Layers node’s "Image" output.
            if scene.render_manager.fixed_for_y_up:
                input_slot = layer_color_node.layer_slots.new("rgba")
            else:
                input_slot = layer_color_node.layer_slots.new("Image")

            node_tree.links.new(per_layer_node.outputs["Image"], input_slot)

            # Create an alpha input socket.
            alpha_slot = layer_color_node.layer_slots.new("Alpha")

            # Connect passes for Color and Data.
            color_passes = [
                "DiffDir",
                "DiffInd",
                "DiffCol",
                "GlossDir",
                "GlossInd",
                "GlossCol",
                "TransDir",
                "TransInd",
                "TransCol",
                "Emit",
                "AO",
                "Env",
                "Shadow Catcher",
            ]
            data_passes = [
                "Depth",
                "Mist",
                "Position",
                "Normal",
                "UV",
                "Vector",
                "IndexOB",
                "IndexMA",
                "CryptoObject00",
                "CryptoObject01",
                "CryptoObject02",
                "CryptoMaterial00",
                "CryptoMaterial01",
                "CryptoMaterial02",
                "CryptoAsset00",
                "CryptoAsset01",
                "CryptoAsset02",
                "Denoising Normal",
                "Denoising Albedo",
                "Denoising Depth",
            ]
            noisy_passes = []
            backup_only_passes = ["Noisy Image", "Noisy Shadow Catcher"]

            if scene.render_manager.combine_diff_glossy:
                vl.use_pass_diffuse_color = True
                vl.use_pass_diffuse_direct = True
                vl.use_pass_diffuse_indirect = True
                vl.use_pass_glossy_color = True
                vl.use_pass_glossy_direct = True
                vl.use_pass_glossy_indirect = True
                vl.use_pass_transmission_color = True
                vl.use_pass_transmission_direct = True
                vl.use_pass_transmission_indirect = True

            if scene.render_manager.denoise:
                needs_cycles_denoising_data = False
                needs_normal_data = False

                if scene.render_manager.denoise_image:
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_normal = True

                if scene.render_manager.denoise_diffuse:
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_diffuse_direct = True
                    vl.use_pass_diffuse_indirect = True
                    if scene.render_manager.combine_diff_glossy:
                        needs_normal_data = True
                    else:
                        needs_cycles_denoising_data = True

                if scene.render_manager.denoise_glossy:
                    vl.use_pass_glossy_color = True
                    vl.use_pass_glossy_direct = True
                    vl.use_pass_glossy_indirect = True
                    if scene.render_manager.combine_diff_glossy:
                        needs_normal_data = True
                    else:
                        needs_cycles_denoising_data = True

                if scene.render_manager.denoise_transmission:
                    vl.use_pass_transmission_color = True
                    vl.use_pass_transmission_direct = True
                    vl.use_pass_transmission_indirect = True
                    if scene.render_manager.combine_diff_glossy:
                        needs_normal_data = True
                    else:
                        needs_cycles_denoising_data = True

                if scene.render_manager.denoise_volumedir:
                    vl.cycles.use_pass_volume_direct = True
                    needs_cycles_denoising_data = True

                if scene.render_manager.denoise_volumeind:
                    vl.cycles.use_pass_volume_indirect = True
                    needs_cycles_denoising_data = True

                if scene.render_manager.denoise_shadow_catcher:
                    vl.cycles.use_pass_shadow_catcher = True
                    vl.use_pass_normal = True
                    needs_cycles_denoising_data = True

                if scene.render_manager.denoise_alpha:
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_normal = True
                    needs_cycles_denoising_data = True

                if needs_normal_data:
                    vl.use_pass_normal = True
                if needs_cycles_denoising_data:
                    vl.cycles.denoising_store_passes = True

            for pass_name in color_passes:
                if pass_name in per_layer_node.outputs:
                    if pass_name == "DiffCol":
                        if scene.render_manager.combine_diff_glossy:
                            diffuse_combined_output = combine_inputs(
                                node_tree,
                                "Diffuse",
                                per_layer_node.outputs["DiffDir"],
                                per_layer_node.outputs["DiffInd"],
                                per_layer_node.outputs["DiffCol"],
                                x_pos + column_spacing + 100,
                                y_pos - 120,
                            )
                            if (
                                scene.render_manager.denoise_diffuse
                                and scene.render_manager.denoise
                            ):
                                denoise_pass(
                                    node_tree,
                                    "Diffuse",
                                    diffuse_combined_output.outputs[0],
                                    per_layer_node.outputs["Normal"],
                                    per_layer_node.outputs["DiffCol"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 120,
                                    noisy_passes,
                                )
                            else:
                                input_slot = layer_color_node.layer_slots.new("Diffuse")
                                node_tree.links.new(
                                    diffuse_combined_output.outputs[0], input_slot
                                )
                        else:
                            if (
                                scene.render_manager.denoise_diffuse
                                and scene.render_manager.denoise
                            ):
                                denoise_pass(
                                    node_tree,
                                    "DiffDir",
                                    per_layer_node.outputs["DiffDir"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 120,
                                    noisy_passes,
                                )
                                denoise_pass(
                                    node_tree,
                                    "DiffInd",
                                    per_layer_node.outputs["DiffInd"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 150,
                                    noisy_passes,
                                )
                                denoise_pass(
                                    node_tree,
                                    "DiffCol",
                                    per_layer_node.outputs["DiffCol"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 180,
                                    noisy_passes,
                                )
                    if pass_name == "GlossCol":
                        if scene.render_manager.combine_diff_glossy:
                            glossy_combined_output = combine_inputs(
                                node_tree,
                                "Glossy",
                                per_layer_node.outputs["GlossDir"],
                                per_layer_node.outputs["GlossInd"],
                                per_layer_node.outputs["GlossCol"],
                                x_pos + column_spacing + 100,
                                y_pos - 190,
                            )
                            if (
                                scene.render_manager.denoise_glossy
                                and scene.render_manager.denoise
                            ):
                                denoise_pass(
                                    node_tree,
                                    "Glossy",
                                    glossy_combined_output.outputs[0],
                                    per_layer_node.outputs["Normal"],
                                    per_layer_node.outputs["GlossCol"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 190,
                                    noisy_passes,
                                )
                            else:
                                input_slot = layer_color_node.layer_slots.new("Glossy")
                                node_tree.links.new(
                                    glossy_combined_output.outputs[0], input_slot
                                )
                        else:
                            if (
                                scene.render_manager.denoise_glossy
                                and scene.render_manager.denoise
                            ):
                                denoise_pass(
                                    node_tree,
                                    "GlossDir",
                                    per_layer_node.outputs["GlossDir"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 210,
                                    noisy_passes,
                                )
                                denoise_pass(
                                    node_tree,
                                    "GlossInd",
                                    per_layer_node.outputs["GlossInd"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 240,
                                    noisy_passes,
                                )
                                denoise_pass(
                                    node_tree,
                                    "GlossCol",
                                    per_layer_node.outputs["GlossCol"],
                                    per_layer_node.outputs["Denoising Normal"],
                                    per_layer_node.outputs["Denoising Albedo"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 270,
                                    noisy_passes,
                                )
                    if pass_name == "TransCol":
                        if scene.render_manager.combine_diff_glossy:
                            transmission_combined_output = combine_inputs(
                                node_tree,
                                "Transmission",
                                per_layer_node.outputs["TransDir"],
                                per_layer_node.outputs["TransInd"],
                                per_layer_node.outputs["TransCol"],
                                x_pos + column_spacing + 100,
                                y_pos - 260,
                            )
                            if (
                                scene.render_manager.denoise_transmission
                                and scene.render_manager.denoise
                            ):
                                denoise_pass(
                                    node_tree,
                                    "Transmission",
                                    transmission_combined_output.outputs[0],
                                    per_layer_node.outputs["Normal"],
                                    per_layer_node.outputs["TransCol"],
                                    layer_color_node,
                                    x_pos + column_spacing + 300,
                                    y_pos - 260,
                                    noisy_passes,
                                )
                            else:
                                input_slot = layer_color_node.layer_slots.new(
                                    "Transmission"
                                )
                                node_tree.links.new(
                                    transmission_combined_output.outputs[0], input_slot
                                )
                        else:
                            if (
                                scene.render_manager.denoise_transmission
                                and scene.render_manager.denoise
                            ):
                                if "TransDir" in per_layer_node.outputs:
                                    denoise_pass(
                                        node_tree,
                                        "TransDir",
                                        per_layer_node.outputs["TransDir"],
                                        per_layer_node.outputs["Denoising Normal"],
                                        per_layer_node.outputs["Denoising Albedo"],
                                        layer_color_node,
                                        x_pos + column_spacing + 300,
                                        y_pos - 300,
                                        noisy_passes,
                                    )
                                if "TransInd" in per_layer_node.outputs:
                                    denoise_pass(
                                        node_tree,
                                        "TransInd",
                                        per_layer_node.outputs["TransInd"],
                                        per_layer_node.outputs["Denoising Normal"],
                                        per_layer_node.outputs["Denoising Albedo"],
                                        layer_color_node,
                                        x_pos + column_spacing + 300,
                                        y_pos - 330,
                                        noisy_passes,
                                    )
                                if "TransCol" in per_layer_node.outputs:
                                    denoise_pass(
                                        node_tree,
                                        "TransCol",
                                        per_layer_node.outputs["TransCol"],
                                        per_layer_node.outputs["Denoising Normal"],
                                        per_layer_node.outputs["Denoising Albedo"],
                                        layer_color_node,
                                        x_pos + column_spacing + 300,
                                        y_pos - 360,
                                        noisy_passes,
                                    )

            if scene.render_manager.denoise:
                if scene.render_manager.denoise_volumedir:
                    denoise_pass(
                        node_tree,
                        "VolumeDir",
                        per_layer_node.outputs["VolumeDir"],
                        per_layer_node.outputs["Denoising Normal"],
                        per_layer_node.outputs["Denoising Albedo"],
                        layer_color_node,
                        x_pos + column_spacing + 300,
                        y_pos - 400,
                        noisy_passes,
                    )
                if scene.render_manager.denoise_volumeind:
                    denoise_pass(
                        node_tree,
                        "VolumeInd",
                        per_layer_node.outputs["VolumeInd"],
                        per_layer_node.outputs["Denoising Normal"],
                        per_layer_node.outputs["Denoising Albedo"],
                        layer_color_node,
                        x_pos + column_spacing + 300,
                        y_pos - 440,
                        noisy_passes,
                    )
                denoise_node = None
                if scene.render_manager.denoise_alpha:
                    denoise_pass(
                        node_tree,
                        "Alpha",
                        per_layer_node.outputs["Alpha"],
                        per_layer_node.outputs["Denoising Normal"],
                        per_layer_node.outputs["Denoising Albedo"],
                        layer_color_node,
                        x_pos + column_spacing + 300,
                        y_pos - 80,
                        noisy_passes,
                    )
                denoise_node = None
                if scene.render_manager.fixed_for_y_up:
                    color_node_image_input_name = "rgba"
                else:
                    color_node_image_input_name = "Image"
                if (not scene.render_manager.denoise) or (
                    not scene.render_manager.denoise_image
                ):
                    node_tree.links.new(
                        per_layer_node.outputs["Image"],
                        layer_color_node.inputs[color_node_image_input_name],
                    )
                else:
                    if scene.cycles.use_denoising:
                        node_tree.links.new(
                            per_layer_node.outputs["Image"],
                            layer_color_node.inputs[color_node_image_input_name],
                        )
                        denoise_node = node_tree.nodes.new("CompositorNodeDenoise")
                        denoise_node.label = "Denoise Noisy Image"
                        denoise_node.location = (
                            x_pos + column_spacing + 300,
                            y_pos - 40,
                        )
                        denoise_node.hide = True
                        node_tree.links.new(
                            per_layer_node.outputs["Noisy Image"],
                            denoise_node.inputs["Image"],
                        )
                        node_tree.links.new(
                            per_layer_node.outputs["Normal"],
                            denoise_node.inputs["Normal"],
                        )
                        node_tree.links.new(
                            per_layer_node.outputs["DiffCol"],
                            denoise_node.inputs["Albedo"],
                        )
                        node_tree.links.new(
                            denoise_node.outputs["Image"],
                            layer_color_node.layer_slots.new(
                                color_node_image_input_name + " (Compositor Denoised)"
                            ),
                        )
                        noisy_passes.append([
                            per_layer_node.outputs["Noisy Image"],
                            "Image",
                        ])
                    else:
                        denoise_pass(
                            node_tree,
                            color_node_image_input_name,
                            per_layer_node.outputs["Image"],
                            per_layer_node.outputs["Normal"],
                            per_layer_node.outputs["DiffCol"],
                            layer_color_node,
                            x_pos + column_spacing + 300,
                            y_pos - 40,
                            noisy_passes,
                        )
                denoise_node = None
                if scene.render_manager.denoise_shadow_catcher:
                    denoise_pass(
                        node_tree,
                        "Shadow Catcher",
                        per_layer_node.outputs["Shadow Catcher"],
                        per_layer_node.outputs["Denoising Normal"],
                        per_layer_node.outputs["Denoising Albedo"],
                        layer_color_node,
                        x_pos + column_spacing + 300,
                        y_pos - 480,
                        noisy_passes,
                    )
                if scene.render_manager.save_noisy_in_file:
                    for noisy_pass_array in noisy_passes:
                        noisy_pass = noisy_pass_array[0]
                        noisy_name = "Noisy " + noisy_pass_array[1]
                        node_tree.links.new(
                            noisy_pass,
                            layer_color_node.layer_slots.new(noisy_name),
                        )
                if (
                    scene.render_manager.save_noisy_separately
                    and scene.render_manager.denoise
                ):
                    for noisy_pass_array in noisy_passes:
                        noisy_pass = noisy_pass_array[0]
                        noisy_name = "Noisy " + noisy_pass_array[1]
                        print("trying to connect noisy name " + noisy_name)
                        node_tree.links.new(
                            noisy_pass,
                            layer_noisy_node.layer_slots.new(noisy_name),
                        )

            for pass_name in data_passes:
                if pass_name in per_layer_node.outputs:
                    data_slot = layer_data_node.layer_slots.new(pass_name)
                    data_input = layer_data_node.inputs[-1]
                    if scene.render_manager.fixed_for_y_up:
                        fallback = True
                        if pass_name == "Normal" and y_ups.get("Normal"):
                            node_tree.links.new(
                                y_ups.get("Normal").outputs[0], data_input
                            )
                            fallback = False
                        if pass_name == "Position" and y_ups.get("Position"):
                            node_tree.links.new(
                                y_ups.get("Position").outputs[0], data_input
                            )
                            fallback = False
                        if pass_name == "Vector" and y_ups.get("Vector"):
                            node_tree.links.new(
                                y_ups.get("Vector").outputs[0], data_input
                            )
                            fallback = False
                        if pass_name == "Position" and y_ups.get("Position"):
                            node_tree.links.new(
                                y_ups.get("Position").outputs[0], data_input
                            )
                            fallback = False
                        if fallback:
                            node_tree.links.new(
                                per_layer_node.outputs[pass_name], data_input
                            )
                    else:
                        node_tree.links.new(
                            per_layer_node.outputs[pass_name], data_input
                        )

            for pass_name in per_layer_node.outputs:
                if pass_name.name not in backup_only_passes:
                    if (not pass_name.is_unavailable) and (not pass_name.is_linked):
                        if not pass_name.name in layer_color_node.inputs:
                            node_tree.links.new(
                                pass_name,
                                layer_color_node.layer_slots.new(pass_name.name),
                            )
                        else:
                            node_tree.links.new(
                                pass_name, layer_color_node.inputs[pass_name.name]
                            )

            if scene.render_manager.backup_passes:
                for pass_name in per_layer_node.outputs:
                    if not pass_name.is_unavailable:
                        layer_backup_node.layer_slots.new(pass_name.name)
                        node_tree.links.new(
                            per_layer_node.outputs[pass_name.name],
                            layer_backup_node.inputs[pass_name.name],
                        )

        if previous_alpha_node:
            node_tree.links.new(
                previous_alpha_node.outputs["Image"], composite_node.inputs[0]
            )

        self.report(
            {"INFO"}, "Created node setup for all render layers in spreadsheet layout."
        )
        return {"FINISHED"}


# --------------------------------------------------------------------------
#  Registration
# --------------------------------------------------------------------------

color_depth_options = (("16", "16", ""), ("32", "32", ""))


class RenderManagerSettings(bpy.types.PropertyGroup):
    
    beauty_compression: bpy.props.EnumProperty(
        name="Beauty Compression",
        description="Compression method for beauty EXR outputs",
        items=[
            ("NONE", "None", ""),
            ("RLE", "RLE", ""),
            ("ZIPS", "ZIPS", ""),
            ("ZIP", "ZIP", ""),
            ("PIZ", "PIZ", ""),
            ("PXR24", "PXR24", ""),
            ("B44", "B44", ""),
            ("B44A", "B44A", ""),
            ("DWAA", "DWAA", ""),
            ("DWAB", "DWAB", ""),
        ],
        default="DWAA",
        update=update_exr_compression
    )

    data_compression: bpy.props.EnumProperty(
        name="Data Compression",
        description="Compression method for data EXR outputs",
        items=[
            ("NONE", "None", ""),
            ("RLE", "RLE", ""),
            ("ZIPS", "ZIPS", ""),
            ("ZIP", "ZIP", ""),
            ("PIZ", "PIZ", ""),
            ("PXR24", "PXR24", ""),
            ("B44", "B44", ""),
            ("B44A", "B44A", ""),
            ("DWAA", "DWAA", ""),
            ("DWAB", "DWAB", ""),
        ],
        default="ZIP",
        update=update_exr_compression
    )
       
    
    fixed_for_y_up: bpy.props.BoolProperty(
        name="Make Y Up",
        description="Enable to make the coordinate system for compatible with software that assumes Y is up (Currently does nothing)",
        default=False,
    )

    combine_diff_glossy: bpy.props.BoolProperty(
        name="Combine Diff/Glossy/Trans",
        description="Combine diff and glossy channels together",
        default=True,
    )

    denoise: bpy.props.BoolProperty(
        name="Enable",
        description="Enable per-pass denoising operations",
        default=True,
    )

    denoise_image: bpy.props.BoolProperty(
        name="Image",
        description="Denoises the image pass",
        default=True,
    )

    denoise_alpha: bpy.props.BoolProperty(
        name="Alpha",
        description="Denoises the alpha channel pass",
        default=False,
    )

    denoise_diffuse: bpy.props.BoolProperty(
        name="Diffuse",
        description="Denoises diffuse pass",
        default=True,
    )

    denoise_glossy: bpy.props.BoolProperty(
        name="Glossy",
        description="Denoises glossy pass",
        default=True,
    )

    denoise_transmission: bpy.props.BoolProperty(
        name="Transmission",
        description="Denoises transparent pass",
        default=True,
    )

    denoise_volumedir: bpy.props.BoolProperty(
        name="Volume Direct",
        description="Denoises Direct Volumetrics",
        default=False,
    )

    denoise_volumeind: bpy.props.BoolProperty(
        name="Volume Indirect",
        description="Denoises Indirect Volumetrics",
        default=False,
    )

    denoise_shadow_catcher: bpy.props.BoolProperty(
        name="Shadow Catcher",
        description="Denoises shadow catcher pass",
        default=False,
    )

    save_noisy_in_file: bpy.props.BoolProperty(
        name="Embed Noisy Passes",
        description="Keeps the noisy passes as a backup in the same file",
        default=False,
    )

    save_noisy_separately: bpy.props.BoolProperty(
        name="Save Noisy Passes Separately",
        description="Keeps the noisy passes as a backup in a separate file",
        default=False,
    )

    backup_passes: bpy.props.BoolProperty(
        description="Save a full copy of the unmodified passes into a separate file",
        name="Original Passes (32bit Only)",
        default=False,
    )

    color_depth_override: bpy.props.EnumProperty(
        items=(("16", "16", ""), ("32", "32", "")),
        description="Use the color depth configured in the OpenEXR output settings",
        name="Color Depth",
    )

    file_output_basepath: bpy.props.StringProperty(
        name="File Output Path",
        description="Base directory to store output EXR files",
        subtype="DIR_PATH",
        default="//RenderOutputs"
    )



classes = (
    RenderManagerSettings,
    RENDER_MANAGER_OT_create_render_nodes,
    RENDER_MANAGER_OT_copy_layer_settings,
    RENDER_MANAGER_OT_paste_layer_settings,
    RENDER_MANAGER_OT_view_layer_settings,
    RENDER_MANAGER_OT_add_render_layer,
    RENDER_MANAGER_OT_remove_render_layer,
    RENDER_MANAGER_OT_switch_layer,
    RENDER_MANAGER_PT_panel,
    RENDER_MANAGER_OT_reorder_view_layer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.render_manager = bpy.props.PointerProperty(
        type=RenderManagerSettings
    )


def combine_inputs(
    node_tree,
    group_name,
    input_slot1,
    input_slot2,
    input_slot3,
    x_pos,
    y_pos,
):
    combine_node = ensure_node_group("Combine_Passes")
    # combine_node = ensure_combine_pass_node_groups()
    combine_nodegroup = node_tree.nodes.new("CompositorNodeGroup")
    combine_nodegroup.node_tree = combine_node
    combine_nodegroup.location = (x_pos, y_pos)
    combine_nodegroup.label = "Combine " + group_name
    combine_nodegroup.hide = True

    node_tree.links.new(input_slot1, combine_nodegroup.inputs[0])
    node_tree.links.new(input_slot2, combine_nodegroup.inputs[1])
    node_tree.links.new(
        input_slot3,
        combine_nodegroup.inputs[2],
    )
    return combine_nodegroup


def denoise_pass(
    node_tree,
    slot_name,  # denoise_node_name (in)
    source_image_slot,  # in node slot object
    source_normal_slot,  # in node slot object
    source_albedo_slot,  # in node slot object
    dest_node,  # in
    x_pos,
    y_pos,  # in numbers
    noisy_passes,  # out!
):
    # create compositor node
    denoise_node = node_tree.nodes.new("CompositorNodeDenoise")
    denoise_node.label = "Denoise " + str(slot_name)
    denoise_node.location = (
        x_pos,
        y_pos,
    )
    denoise_node.hide = True
    node_tree.links.new(
        source_image_slot,
        denoise_node.inputs["Image"],
    )
    node_tree.links.new(
        source_normal_slot,
        denoise_node.inputs["Normal"],
    )
    node_tree.links.new(
        source_albedo_slot,
        denoise_node.inputs["Albedo"],
    )
    if slot_name in dest_node.inputs:
        input_slot = dest_node.inputs[str(slot_name)]
    else:
        #        input_slot = dest_node.file_slots.new(
        input_slot = dest_node.layer_slots.new(  # I think this is supposed to be a layer, not a file slot
            str(slot_name)
        )
    node_tree.links.new(
        denoise_node.outputs[0],
        input_slot,
    )
    noisy_passes.append([source_image_slot, slot_name])


def a_denoising_operation_is_checked(scene):
    if (
        scene.render_manager.denoise_image
        or scene.render_manager.denoise_diffuse
        or scene.render_manager.denoise_glossy
        or scene.render_manager.denoise_transmission
        or scene.render_manager.denoise_alpha
        or scene.render_manager.denoise_volumedir
        or scene.render_manager.denoise_volumeind
        or scene.render_manager.denoise_shadow_catcher
    ):
        return True
    else:
        return False


def unregister():
    del bpy.types.Scene.render_manager

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

