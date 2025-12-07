import bpy
import os
import pathlib
import inspect

# --------------------------------------------------------------------------
# GLOBAL CLIPBOARD + Helpers for Copy/Paste
# --------------------------------------------------------------------------
def get_latest_input(node):
    if bpy.app.version >= (5, 0, 0):
        return node.inputs[-2]
    else:
        return node.inputs[-1]

def get_output_slots(node):
    if bpy.app.version >= (5, 0, 0):
        return node.file_output_items
    else:
        return node.layer_slots

def get_output_slot_by_name(node, slot_name):

    for slot in node.file_output_items:
        if slot.name == slot_name:
            target_slot = slot
            return target_slot

def create_mix_node(node_tree, use_clamp):

    if bpy.app.version >= (5, 0, 0):
        mix_node = node_tree.nodes.new('ShaderNodeMix')
        mix_node.clamp_result = use_clamp
        return mix_node

    else:
        mix_node = node_tree.nodes.new('CompositorNodeMixRGB')
        mix_node.use_clamp = use_clamp
        return mix_node


def get_pass_name(pass_name):
    if pass_name == "volume_direct": 
        if bpy.app.version >= (5, 0, 0):
            return "Volume Direct"
        else:
            return "VolumeDir"
    if pass_name == "volume_indirect": 
        if bpy.app.version >= (5, 0, 0):
            return "Volume Indirect"
        else:
            return "VolumeInd"

    if pass_name == "alpha": 
        if bpy.app.version >= (5, 0, 0):
            return "Alpha"
        else:
            return "Alpha"

    if pass_name == "normal": 
        if bpy.app.version >= (5, 0, 0):
            return "Normal"
        else:
            return "Normal"

    if pass_name == "diffuse_direct": 
        if bpy.app.version >= (5, 0, 0):
            return "Diffuse Direct"
        else:
            return "DiffDir"

    if pass_name == "diffuse_indirect": 
        if bpy.app.version >= (5, 0, 0):
            return "Diffuse Indirect"
        else:
            return "DiffInd"

    if pass_name == "diffuse_color": 
        if bpy.app.version >= (5, 0, 0):
            return "Diffuse Color"
        else:
            return "DiffCol"

    if pass_name == "glossy_direct": 
        if bpy.app.version >= (5, 0, 0):
            return "Glossy Direct"
        else:
            return "GlossDir"

    if pass_name == "glossy_indirect": 
        if bpy.app.version >= (5, 0, 0):
            return "Glossy Indirect"
        else:
            return "GlossInd"

    if pass_name == "glossy_color": 
        if bpy.app.version >= (5, 0, 0):
            return "Glossy Color"
        else:
            return "GlossCol"

    if pass_name == "transmission_direct": 
        if bpy.app.version >= (5, 0, 0):
            return "Transmission Direct"
        else:
            return "TransDir"

    if pass_name == "transmission_indirect": 
        if bpy.app.version >= (5, 0, 0):
            return "Transmission Indirect"
        else:
            return "TransInd"

    if pass_name == "transmission_color": 
        if bpy.app.version >= (5, 0, 0):
            return "Transmission Color"
        else:
            return "TransCol"

    if pass_name == "transparent": 
        if bpy.app.version >= (5, 0, 0):
            return "Transparent"
        else:
            return "Transp"




RENDER_MANAGER_CLIPBOARD = {}

def gather_layer_settings(layer):
    """
    Gather pass properties from a given layer (and sub-objects if needed),
    storing them in a dict. Adjust or add pass properties as desired.
    """
    data = {}
    props_to_copy = [
        ("", "use_pass_combined"),
        ("", "use_pass_z"),
        ("", "use_pass_mist"),
        ("", "use_pass_normal"),
        ("", "use_pass_position"),
        ("", "use_pass_uv"),
        ("", "use_pass_object_index"),
        ("", "use_pass_material_index"),
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
        ("", "use_pass_cryptomatte_object"),
        ("", "use_pass_cryptomatte_material"),
        ("", "use_pass_cryptomatte_asset"),
        ("", "pass_cryptomatte_depth"),
        ("", "pass_cryptomatte_accurate"),
        ("eevee", "use_pass_transparent"),
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
                codec = None
                if "Color Output" in node.label:
                    codec = scene.render_manager.beauty_compression
                    node.format.exr_codec = codec
                elif "Data Output" in node.label:
                    codec = scene.render_manager.data_compression
                    node.format.exr_codec = codec
                elif "Noisy Output" in node.label or "Backup Output" in node.label:
                    codec = scene.render_manager.beauty_compression
                    node.format.exr_codec = codec
                if codec in {"DWAA", "DWAB"}:
                    node.format.exr_codec_level = scene.render_manager.dwaa_compression_level

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
# Helpers to get/set the "render use" property for a View Layer
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
# PASS DEFINITIONS + get_pass_groups_for_engine
# --------------------------------------------------------------------------

CYCLES_PASS_GROUPS = [
    ("Main Pass", [("", "use_pass_combined", "Combined")]),
    ("Data Passes", [
        ("", "use_pass_z", "Z"),
        ("", "use_pass_mist", "Mist"),
        ("", "use_pass_normal", "Normal"),
        ("", "use_pass_position", "Position"),
        ("", "use_pass_uv", "UV"),
        ("", "use_pass_vector", "Vector"),
        ("", "use_pass_object_index", "Object Index"),
        ("", "use_pass_material_index", "Material Index"),
        ("cycles", "denoising_store_passes", "Denoising Data"),
    ]),
    ("Light Passes", [
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
    ]),
    ("Cryptomatte", [
        ("", "use_pass_cryptomatte_object", "Crypto Object"),
        ("", "use_pass_cryptomatte_material", "Crypto Material"),
        ("", "use_pass_cryptomatte_asset", "Crypto Asset"),
        ("", "pass_cryptomatte_depth", "Levels (Depth)"),
        ("", "pass_cryptomatte_accurate", "Accurate"),
    ]),
]

EEVEE_PASS_GROUPS = [
    ("Main Pass", [("", "use_pass_combined", "Combined")]),
    ("Data Passes", [
        ("", "use_pass_z", "Z"),
        ("", "use_pass_mist", "Mist"),
        ("", "use_pass_normal", "Normal"),
        ("", "use_pass_position", "Position"),
        ("", "use_pass_vector", "Vector"),
    ]),
    ("Light Passes", [
        ("", "use_pass_diffuse_direct", "Diffuse Light"),
        ("", "use_pass_diffuse_color", "Diffuse Color"),
        ("", "use_pass_glossy_direct", "Specular Light"),
        ("", "use_pass_glossy_color", "Specular Color"),
        ("", "use_pass_emit", "Emission"),
        ("", "use_pass_environment", "Environment"),
        ("", "use_pass_shadow", "Shadow"),
        ("", "use_pass_ambient_occlusion", "Ambient Occlusion"),
        ("eevee", "use_pass_transparent", "Transparent"),
    ]),
    ("Cryptomatte", [
        ("", "use_pass_cryptomatte_object", "Crypto Object"),
        ("", "use_pass_cryptomatte_material", "Crypto Material"),
        ("", "use_pass_cryptomatte_asset", "Crypto Asset"),
        ("", "pass_cryptomatte_depth", "Levels (Depth)"),
        ("", "pass_cryptomatte_accurate", "Accurate"),
    ]),
]

NODE_OPERATIONS = [
    ("Node Operations", [
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
    ]),
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
        return []

# --------------------------------------------------------------------------
# Eevee-specific Denoise Helper
# --------------------------------------------------------------------------

def eevee_denoise_if_available(
    pass_name,
    per_layer_node,
    layer_color_node,
    node_tree,
    x_pos,
    y_pos,
    column_spacing,
    noisy_passes,
    y_offset=0
):
    print(f"DEBUG: Checking Eevee denoise for pass: {pass_name}")
    if (
        pass_name in per_layer_node.outputs and
        not per_layer_node.outputs[pass_name].is_unavailable and
        "Normal" in per_layer_node.outputs and
        not per_layer_node.outputs["Normal"].is_unavailable and
        get_pass_name("diffuse_color") in per_layer_node.outputs and
        not per_layer_node.outputs[get_pass_name("diffuse_color")].is_unavailable
    ):
        print(f"🟡 Creating denoise node for Eevee pass: {pass_name}")
        denoise_pass(
            node_tree,
            pass_name,
            per_layer_node.outputs[pass_name],
            per_layer_node.outputs[get_pass_name("normal")],
            per_layer_node.outputs[get_pass_name("diffuse_color")],
            layer_color_node,
            x_pos + column_spacing + 300,
            y_pos + y_offset,
            noisy_passes,
        )
    else:
        print(f"⚠ Skipped Eevee denoise for '{pass_name}' — Missing sockets or data.")

# --------------------------------------------------------------------------
# Switch View Layer Operators
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
# Reorder View Layer Operators
# --------------------------------------------------------------------------

class RENDER_MANAGER_OT_reorder_view_layer(bpy.types.Operator):
    """Reorder View Layer"""
    bl_idname = "wm.reorder_view_layer"
    bl_label = "Reorder View Layer"
    direction: bpy.props.EnumProperty(items=[("UP", "Up", "Up"), ("DOWN", "Down", "Down")])

    def execute(self, context):
        scene = context.scene
        active_index = None
        for i, vl in enumerate(context.scene.view_layers):
            if vl == context.view_layer:
                active_index = i
                break
        if self.direction == "DOWN" and len(context.scene.view_layers) > active_index + 1:
            scene.view_layers.move(active_index, active_index + 1)
        if self.direction == "UP" and active_index - 1 >= 0:
            scene.view_layers.move(active_index, active_index - 1)
        for screen in bpy.data.screens:
            for area in screen.areas:
                area.tag_redraw()
        return {"FINISHED"}

# --------------------------------------------------------------------------
# COPY & PASTE Operators
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
# Operator: Render Layer Settings (Spreadsheet)
# --------------------------------------------------------------------------

class RENDER_MANAGER_OT_view_layer_settings(bpy.types.Operator):
    """Show a pop-up table to toggle passes per View Layer."""
    bl_idname = "wm.view_layer_settings"
    bl_label = "Render Layer Settings"

    def invoke(self, context, event):
        screen_width = context.window.width
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
        row = box_render_toggle.row(align=True)
        row_split = row.split(factor=0.2, align=True)
        row_split.label(text="Rendering")
        sub_rend = row_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split = sub_rend.split(factor=1.0 / (len(view_layers) - i), align=True)
                if hasattr(vl, "use"):
                    col_split.prop(vl, "use", text="")
                elif hasattr(vl, "use_for_render"):
                    col_split.prop(vl, "use_for_render", text="")
                else:
                    col_split.label(text="N/A")
                sub_rend = col_split
            else:
                if hasattr(vl, "use"):
                    sub_rend.prop(vl, "use", text="")
                elif hasattr(vl, "use_for_render"):
                    sub_rend.prop(vl, "use_for_render", text="")
                else:
                    sub_rend.label(text="N/A")

        row_cp = box_render_toggle.row(align=True)
        row_cp_split = row_cp.split(factor=0.2, align=True)
        row_cp_split.label(text="Copy/Paste")
        sub_cp = row_cp_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_cp = sub_cp.split(factor=1.0 / (len(view_layers) - i), align=True)
                row_icons = col_split_cp.row(align=True)
                op_copy = row_icons.operator("wm.copy_layer_settings", text="", icon="COPYDOWN")
                op_copy.layer_index = i
                op_paste = row_icons.operator("wm.paste_layer_settings", text="", icon="PASTEDOWN")
                op_paste.layer_index = i
                sub_cp = col_split_cp
            else:
                row_icons = sub_cp.row(align=True)
                op_copy = row_icons.operator("wm.copy_layer_settings", text="", icon="COPYDOWN")
                op_copy.layer_index = i
                op_paste = row_icons.operator("wm.paste_layer_settings", text="", icon="PASTEDOWN")
                op_paste.layer_index = i

        for group_title, pass_list in pass_groups:
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
                        subcol = sub2.split(factor=1.0 / (len(view_layers) - j), align=True)
                    else:
                        subcol = sub2
                    if data_ref and hasattr(data_ref, prop_name):
                        subcol.prop(data_ref, prop_name, text="")
                    else:
                        subcol.label(text="")
                    sub2 = subcol

        box_overrides = layout.box()
        box_overrides.label(text="View Layer Overrides")
        row_material = box_overrides.row(align=True)
        row_material_split = row_material.split(factor=0.2, align=True)
        row_material_split.label(text="Material Override")
        sub_material = row_material_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_material = sub_material.split(factor=1.0 / (len(view_layers) - i), align=True)
            else:
                col_split_material = sub_material
            if hasattr(vl, "material_override"):
                col_split_material.prop(vl, "material_override", text="")
            else:
                col_split_material.label(text="N/A")
            sub_material = col_split_material

        row_world = box_overrides.row(align=True)
        row_world_split = row_world.split(factor=0.2, align=True)
        row_world_split.label(text="World Override")
        sub_world = row_world_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_world = sub_world.split(factor=1.0 / (len(view_layers) - i), align=True)
            else:
                col_split_world = sub_world
            if hasattr(vl, "world_override"):
                col_split_world.prop(vl, "world_override", text="")
            else:
                col_split_world.label(text="N/A")
            sub_world = col_split_world

        row_samples = box_overrides.row(align=True)
        row_samples_split = row_samples.split(factor=0.2, align=True)
        row_samples_split.label(text="Samples")
        sub_samples = row_samples_split.split(factor=1.0, align=True)
        for i, vl in enumerate(view_layers):
            if i < len(view_layers) - 1:
                col_split_samples = sub_samples.split(factor=1.0 / (len(view_layers) - i), align=True)
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
# Panel: Render Manager
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
        side_col.operator("wm.add_render_layer", text="", icon="ADD")
        side_col.operator("wm.remove_render_layer", text="", icon="REMOVE")
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
        col = layout.column(heading="")
        col.prop(scene.render_manager, "file_output_basepath")
        layout.operator("wm.view_layer_settings", text="Render Layer Settings", icon="MODIFIER")
        layout.operator("render_manager.collection_spreadsheet", text="Collection Manager", icon="OUTLINER_COLLECTION")
        layout.operator("wm.create_render_nodes", text="Create Render Nodes", icon="NODETREE")
        side_col.separator()
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(heading="Compatibility")
        col.prop(scene.render_manager, "fixed_for_y_up")

        engine = scene.render.engine.upper()
        col = layout.column(heading="Combine Passes")
        if "CYCLES" in engine:
            col.prop(scene.render_manager, "combine_diff_glossy")
        elif "EEVEE" in engine:
            col.prop(scene.render_manager, "combine_diff_glossy_eevee")

        col = layout.column(heading="Per Pass Denoising")
        sub = col.row()
        sub.prop(scene.render_manager, "denoise")
        sub = col.row()
        sub.prop(scene.render_manager, "denoise_image")
        sub.active = scene.render_manager.denoise
        if "CYCLES" in engine:
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
            sub.prop(scene.render_manager, "denoise_lightgroup")
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
            # Added checkboxes for Emit, Environment, AO in Cycles
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_emit")
            sub.active = scene.render_manager.denoise
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_environment")
            sub.active = scene.render_manager.denoise
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_ao")
            sub.active = scene.render_manager.denoise
        elif "EEVEE" in engine:
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
            sub.prop(scene.render_manager, "denoise_emit")
            sub.active = scene.render_manager.denoise
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_environment")
            sub.active = scene.render_manager.denoise
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_shadow")
            sub.active = scene.render_manager.denoise
            sub = col.row()
            sub.prop(scene.render_manager, "denoise_ao")
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
        if scene.render_manager.beauty_compression in {"DWAA", "DWAB"} or scene.render_manager.data_compression in {"DWAA", "DWAB"}:
            col = layout.column(heading="Compression Level")
            col.prop(scene.render_manager, "dwaa_compression_level", slider=True)
# --------------------------------------------------------------------------
# Operator: Create new layer
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
            self.report({"ERROR"}, "Unable to create a new render layer. Check Blender version.")
            return {"CANCELLED"}
        return {"FINISHED"}

# --------------------------------------------------------------------------
# Operator: Remove layer
# --------------------------------------------------------------------------

class RENDER_MANAGER_OT_remove_render_layer(bpy.types.Operator):
    """Remove render layer"""
    bl_idname = "wm.remove_render_layer"
    bl_label = "Remove Render Layer"
    bl_icon = "RENDERLAYERS"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        return len(context.scene.view_layers) > 1

    def execute(self, context):
        scene = context.scene
        scene.view_layers.remove(context.view_layer)
        return {"FINISHED"}

# --------------------------------------------------------------------------
# Operator: Debug Denoise Flags
# --------------------------------------------------------------------------

class RENDER_MANAGER_OT_debug_denoise_flags(bpy.types.Operator):
    """Debug: Print current denoise flag values to the console"""
    bl_idname = "wm.debug_denoise_flags"
    bl_label = "Debug Denoise Flags"

    def execute(self, context):
        scene = context.scene
        rm = scene.render_manager
        print("--- DEBUG DENOISE FLAGS ---")
        print(f"scene.render_manager type: {type(rm)}")
        print(f"scene.render_manager.denoise: {rm.denoise}")
        print(f"scene.render_manager.denoise_image: {rm.denoise_image}")
        print(f"scene.render_manager.denoise_diffuse: {rm.denoise_diffuse}")
        print(f"scene.render_manager.denoise_glossy: {rm.denoise_glossy}")
        print(f"scene.render_manager.denoise_transmission: {rm.denoise_transmission}")
        print(f"scene.render_manager.denoise_alpha: {rm.denoise_alpha}")
        print(f"scene.render_manager.denoise_emit: {rm.denoise_emit}")
        print(f"scene.render_manager.denoise_environment: {rm.denoise_environment}")
        print(f"scene.render_manager.denoise_shadow: {rm.denoise_shadow}")
        print(f"scene.render_manager.denoise_ao: {rm.denoise_ao}")
        print(f"scene.render_manager.denoise_lightgroup: {rm.denoise_lightgroup}")
        print(f"scene.render_manager.denoise_volumedir: {rm.denoise_volumedir}")
        print(f"scene.render_manager.denoise_volumeind: {rm.denoise_volumeind}")
        print(f"scene.render_manager.denoise_shadow_catcher: {rm.denoise_shadow_catcher}")
        print("---------------------------")
        self.report({'INFO'}, "Denoise flags printed to console.")
        return {'FINISHED'}

# --------------------------------------------------------------------------
# Operator: Create Render Nodes
# --------------------------------------------------------------------------

def get_node_group_path():
    addon_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
    return os.path.join(addon_dir, "node_groups.blend")

def ensure_node_group(name):
    group = bpy.data.node_groups.get(name)
    if group is None:
        with bpy.data.libraries.load(get_node_group_path()) as (data_from, data_to):
            data_to.node_groups = [name]
    group = bpy.data.node_groups.get(name)
    group.use_fake_user = True
    return group 


def output_node_clear_slot(node):
    if bpy.app.version >= (5, 0, 0):
        node.file_output_items.clear()
    else:
        node.layer_slots.clear()

def output_node_new_slot(node, name):
    if bpy.app.version >= (5, 0, 0):
        slot = node.file_output_items.new("RGBA", name)
        return slot
    else:
        slot = node.layer_slots.new(name)
        return slot



def ensure_compositor_node_tree(scene):

    if bpy.app.version >= (5, 0, 0):
        if not scene.compositing_node_group:
            new_node_tree = bpy.data.node_groups.new("Render Node", "CompositorNodeTree")
            scene.compositing_node_group = new_node_tree
            new_node_tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        node_tree = scene.compositing_node_group
        return node_tree
    else:
        scene.use_nodes = True
        node_tree = scene.node_tree
        return node_tree

def create_output_node(node_tree):
    if bpy.app.version >= (5, 0, 0):
        composite_node = node_tree.nodes.new(type="NodeGroupOutput")
        return composite_node
    else:
        composite_node = node_tree.nodes.new(type="CompositorNodeComposite")
        return composite_node

def set_output_node_base_path(output_node, base_path, file_name):

    if bpy.app.version >= (5, 0, 0):
        output_node.directory = base_path
        output_node.file_name = file_name
    else:
        output_node.base_path = os.path.join(base_path, file_name)


class RENDER_MANAGER_OT_create_render_nodes(bpy.types.Operator):
    """Create and connect file output nodes based on the selected File Handling mode."""
    bl_idname = "wm.create_render_nodes"
    bl_label = "Create Render Nodes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Please save the file first.")
            return {'CANCELLED'}
        scene = context.scene
        node_tree = ensure_compositor_node_tree(scene)


        y_up = ensure_node_group("Y-Up")
        vector_node = ensure_node_group("Vector")
        node_tree.nodes.clear()
        column_spacing = 300
        row_spacing = -600
        previous_alpha_node = None

        composite_node = create_output_node(node_tree)
        composite_node.location = (7 * column_spacing, 0)
        engine = scene.render.engine.upper()
        used_slots = set()  # Track used slots for cleanup
        combine_diff_glossy_active = scene.render_manager.combine_diff_glossy and "CYCLES" in engine
        combine_diff_glossy_eevee_active = scene.render_manager.combine_diff_glossy_eevee and "EEVEE" in engine

        for i, vl in enumerate(scene.view_layers):
            clean_layer_name = vl.name.split("_", 1)[-1] if vl.name.startswith("layers_") else vl.name
            if not vl.use:
                continue

            # Enable passes for Eevee before creating RLayers node to ensure sockets
            needs_normal_data = False
            if scene.render_manager.denoise and "EEVEE" in engine:
                scene.render.film_transparent = True
                if scene.render_manager.denoise_diffuse:
                    vl.use_pass_diffuse_direct = True
                    vl.use_pass_diffuse_color = True
                    needs_normal_data = True
                if scene.render_manager.denoise_glossy:
                    vl.use_pass_glossy_direct = True
                    vl.use_pass_glossy_color = True
                    needs_normal_data = True
                if scene.render_manager.denoise_transmission:
                    vl.eevee.use_pass_transparent = True
                    needs_normal_data = True
                if scene.render_manager.denoise_alpha:
                    vl.use_pass_diffuse_color = True
                    needs_normal_data = True
                if scene.render_manager.denoise_emit:
                    vl.use_pass_emit = True
                    needs_normal_data = True
                if scene.render_manager.denoise_environment:
                    vl.use_pass_environment = True
                    needs_normal_data = True
                if scene.render_manager.denoise_shadow:
                    vl.use_pass_shadow = True
                    needs_normal_data = True
                if scene.render_manager.denoise_ao:
                    vl.use_pass_ambient_occlusion = True
                    needs_normal_data = True
                if needs_normal_data:
                    vl.use_pass_normal = True

            # Create RLayers node after enabling passes
            x_pos = 0
            y_pos = i * row_spacing
            per_layer_node = node_tree.nodes.new(type="CompositorNodeRLayers")
            per_layer_node.layer = vl.name
            per_layer_node.location = (x_pos, y_pos)

            # Initialize File Output nodes
            layer_color_node = node_tree.nodes.new("CompositorNodeOutputFile")
            layer_data_node = node_tree.nodes.new("CompositorNodeOutputFile")
            layer_color_node.label = f"{clean_layer_name} Color Output"
            layer_data_node.label = f"{clean_layer_name} Data Output"
            user_path = bpy.path.abspath(scene.render_manager.file_output_basepath)

            layer_base_path = os.path.join(user_path, clean_layer_name)

            os.makedirs(layer_base_path, exist_ok=True)
            abs_layer_base_path = bpy.path.abspath(layer_base_path)
            os.makedirs(abs_layer_base_path, exist_ok=True)



            set_output_node_base_path(layer_color_node, layer_base_path, f"{clean_layer_name}.####.exr")
            set_output_node_base_path(layer_data_node, layer_base_path, f"{clean_layer_name}_data.####.exr")



            layer_color_node.format.file_format = "OPEN_EXR_MULTILAYER"
            layer_data_node.format.file_format = "OPEN_EXR_MULTILAYER"
            layer_color_node.format.exr_codec = scene.render_manager.beauty_compression
            layer_data_node.format.exr_codec = scene.render_manager.data_compression
            if int(scene.render_manager.color_depth_override) == 0:
                layer_color_node.format.color_depth = scene.render.image_settings.color_depth
            else:
                layer_color_node.format.color_depth = scene.render_manager.color_depth_override
            layer_data_node.format.color_depth = "32"
            output_node_clear_slot(layer_color_node)
            output_node_clear_slot(layer_data_node)
            layer_color_node.location = (x_pos + 4 * column_spacing, y_pos)
            layer_data_node.location = (x_pos + 5 * column_spacing, y_pos)

            # Pre-create expected slots, adjusted for engine and combine settings
            initial_slots = ["Image", "rgba", "Alpha"]
            if "CYCLES" in engine:
                if combine_diff_glossy_active:
                    initial_slots.extend(["Diffuse", "Glossy", "Transmission"])
                else:
                    initial_slots.extend([get_pass_name("diffuse_direct"), get_pass_name("diffuse_indirect"), get_pass_name("diffuse_color"), get_pass_name("glossy_direct"), get_pass_name("glossy_indirect"), get_pass_name("glossy_color"), get_pass_name("transmission_direct"), get_pass_name("transmission_indirect"), get_pass_name("transmission_color")])
            elif "EEVEE" in engine:
                if combine_diff_glossy_eevee_active:
                    initial_slots.extend(["Diffuse Combined", "Glossy Combined"])
                else:
                    initial_slots.extend([get_pass_name("diffuse_direct"), get_pass_name("diffuse_color"), get_pass_name("glossy_direct"), get_pass_name("glossy_color"), get_pass_name("transparent")])
            for slot_name in initial_slots:
                output_node_new_slot(layer_color_node, slot_name)

            # Handle Noisy and Backup Nodes
            if scene.render_manager.save_noisy_separately and scene.render_manager.denoise and a_denoising_operation_is_checked(scene):
                layer_noisy_node = node_tree.nodes.new("CompositorNodeOutputFile")
                layer_noisy_node.label = f"{clean_layer_name} Noisy Output"
                layer_noisy_node.format.file_format = "OPEN_EXR_MULTILAYER"
                
                set_output_node_base_path(layer_noisy_node, layer_base_path, f"{clean_layer_name}_noisy.####.exr")

                layer_noisy_node.format.color_depth = layer_color_node.format.color_depth
                output_node_clear_slot(layer_noisy_node)
                layer_noisy_node.location = (x_pos + 6 * column_spacing, y_pos)
            if scene.render_manager.backup_passes:
                layer_backup_node = node_tree.nodes.new("CompositorNodeOutputFile")
                layer_backup_node.label = f"{clean_layer_name} Backup Output"
                layer_backup_node.format.file_format = "OPEN_EXR_MULTILAYER"

                set_output_node_base_path(layer_backup_node, layer_base_path, f"{clean_layer_name}_backup.####.exr")

                layer_backup_node.format.color_depth = "32"
                output_node_clear_slot(layer_backup_node)
                layer_backup_node.location = (x_pos - 1 * column_spacing, y_pos)

            # Handle Y-Up Fix
            y_ups = {}
            if scene.render_manager.fixed_for_y_up:
                for pass_name, label, offset in [
                    ("Position", "Y-Up Position", 40),
                    ("Normal", "Y-Up Normal", 10),
                    ("Vector", "Y-Up Vector", -20)
                ]:
                    if pass_name in per_layer_node.outputs:
                        y_up_node = node_tree.nodes.new("CompositorNodeGroup")
                        y_up_node.node_tree = y_up if pass_name != "Vector" else vector_node
                        y_up_node.location = (x_pos + column_spacing, y_pos + offset)
                        y_up_node.label = label
                        y_up_node.hide = True
                        y_ups[pass_name] = y_up_node
                        node_tree.links.new(per_layer_node.outputs[pass_name], y_up_node.inputs[0])

            # Create Alpha Over nodes
            alpha_over = per_layer_node if i == 0 else node_tree.nodes.new("CompositorNodeAlphaOver")
            if i != 0:
                alpha_over.location = (x_pos + 6 * column_spacing, y_pos)
                node_tree.links.new(per_layer_node.outputs["Image"], alpha_over.inputs[1])
            if previous_alpha_node:
                node_tree.links.new(previous_alpha_node.outputs["Image"], alpha_over.inputs[2])
            previous_alpha_node = alpha_over

            # Link Image and Alpha
            color_node_image_input_name = "rgba" if scene.render_manager.fixed_for_y_up else "Image"
            try:
                node_tree.links.new(per_layer_node.outputs["Image"], layer_color_node.inputs[color_node_image_input_name])
                node_tree.links.new(per_layer_node.outputs["Alpha"], layer_color_node.inputs["Alpha"])
                used_slots.add(color_node_image_input_name)
                used_slots.add("Alpha")
            except KeyError as e:
                self.report({'ERROR'}, f"Failed to link Image/Alpha to {color_node_image_input_name}: {str(e)}")
                return {'CANCELLED'}

            # Pass Definitions
            color_passes = [get_pass_name("diffuse_color"), get_pass_name("glossy_color"), get_pass_name("transmission_color")]
            data_passes = [
                "Depth", "Mist", "Position", "Normal", "UV", "Vector",
                "IndexOB", "IndexMA",
                "CryptoObject00", "CryptoObject01", "CryptoObject02",
                "CryptoMaterial00", "CryptoMaterial01", "CryptoMaterial02",
                "CryptoAsset00", "CryptoAsset01", "CryptoAsset02",
                "Denoising Normal", "Denoising Albedo", "Denoising Depth"
            ]
            noisy_passes = []
            backup_only_passes = ["Noisy Image", "Noisy Shadow Catcher"]

            # Enable remaining passes for Cycles or other cases
            needs_denoising_data = False
            if scene.render_manager.denoise and "CYCLES" in engine:
                if scene.render_manager.denoise_image:
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_normal = True
                if scene.render_manager.denoise_diffuse:
                    vl.use_pass_diffuse_direct = True
                    vl.use_pass_diffuse_indirect = True
                    vl.use_pass_diffuse_color = True
                    needs_normal_data = combine_diff_glossy_active
                    needs_denoising_data = not combine_diff_glossy_active
                if scene.render_manager.denoise_glossy:
                    vl.use_pass_glossy_direct = True
                    vl.use_pass_glossy_indirect = True
                    vl.use_pass_glossy_color = True
                    needs_normal_data = combine_diff_glossy_active
                    needs_denoising_data = not combine_diff_glossy_active
                if scene.render_manager.denoise_transmission:
                    vl.use_pass_transmission_direct = True
                    vl.use_pass_transmission_indirect = True
                    vl.use_pass_transmission_color = True
                    needs_normal_data = combine_diff_glossy_active
                    needs_denoising_data = not combine_diff_glossy_active
                if scene.render_manager.denoise_lightgroup:
                    needs_denoising_data = True
                if scene.render_manager.denoise_volumedir:
                    vl.cycles.use_pass_volume_direct = True
                    needs_denoising_data = True
                if scene.render_manager.denoise_volumeind:
                    vl.cycles.use_pass_volume_indirect = True
                    needs_denoising_data = True
                if scene.render_manager.denoise_shadow_catcher:
                    vl.cycles.use_pass_shadow_catcher = True
                    vl.use_pass_normal = True
                    needs_denoising_data = True
                if scene.render_manager.denoise_alpha:
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_normal = True
                    needs_denoising_data = True
                if needs_denoising_data:
                    vl.cycles.denoising_store_passes = True
                if needs_normal_data:
                    vl.use_pass_normal = True

            if combine_diff_glossy_active or combine_diff_glossy_eevee_active:
                if "CYCLES" in engine:
                    vl.use_pass_diffuse_direct = True
                    vl.use_pass_diffuse_indirect = True
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_glossy_direct = True
                    vl.use_pass_glossy_indirect = True
                    vl.use_pass_glossy_color = True
                    vl.use_pass_transmission_direct = True
                    vl.use_pass_transmission_indirect = True
                    vl.use_pass_transmission_color = True
                elif "EEVEE" in engine:
                    vl.use_pass_diffuse_direct = True
                    vl.use_pass_diffuse_color = True
                    vl.use_pass_glossy_direct = True
                    vl.use_pass_glossy_color = True
                    vl.eevee.use_pass_transparent = True

            # Handle Color Passes
            for pass_name in color_passes:
                if pass_name == get_pass_name("diffuse_color"):
                    diffuse_direct_name = get_pass_name("diffuse_direct")
                    diffuse_color_name = get_pass_name("diffuse_color")
                    diffuse_indirect_name = get_pass_name("diffuse_indirect")
                    has_direct = diffuse_direct_name in per_layer_node.outputs and not per_layer_node.outputs[diffuse_direct_name].is_unavailable
                    has_color = diffuse_color_name in per_layer_node.outputs and not per_layer_node.outputs[diffuse_color_name].is_unavailable
                    if "EEVEE" in engine and combine_diff_glossy_eevee_active:
                        if has_direct and has_color:
                            multiply_diffuse_node = create_mix_node(node_tree, False)
                            multiply_diffuse_node.blend_type = 'MULTIPLY'
                            multiply_diffuse_node.label = "Multiply Diffuse Eevee"
                            multiply_diffuse_node.location = (x_pos + column_spacing + 100, y_pos - 120)
                            multiply_diffuse_node.hide = True
                            node_tree.links.new(per_layer_node.outputs[diffuse_direct_name], multiply_diffuse_node.inputs[1])
                            node_tree.links.new(per_layer_node.outputs[diffuse_color_name], multiply_diffuse_node.inputs[2])
                            input_slot = layer_color_node.inputs["Diffuse Combined"]
                            if scene.render_manager.denoise and scene.render_manager.denoise_diffuse:
                                normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                                albedo_socket = per_layer_node.outputs.get(get_pass_name("diffuse_color"))
                                if normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, "Diffuse Combined", multiply_diffuse_node.outputs[0], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 150, noisy_passes)
                                    used_slots.add("Diffuse Combined")
                                else:
                                    node_tree.links.new(multiply_diffuse_node.outputs[0], input_slot)
                                    used_slots.add("Diffuse Combined")
                            else:
                                node_tree.links.new(multiply_diffuse_node.outputs[0], input_slot)
                                used_slots.add("Diffuse Combined")
                        else:
                            if has_direct or has_color:
                                input_slot = layer_color_node.inputs.get("Diffuse Color (Fallback)")
                                if input_slot:
                                    if has_direct:
                                        node_tree.links.new(per_layer_node.outputs[diffuse_direct_name], input_slot)
                                    elif has_color:
                                        node_tree.links.new(per_layer_node.outputs[diffuse_color_name], input_slot)
                                    used_slots.add("Diffuse Color (Fallback)")
                    elif "CYCLES" in engine and combine_diff_glossy_active:
                        if has_direct and has_color:
                            indirect_output = per_layer_node.outputs.get(diffuse_indirect_name, per_layer_node.outputs[diffuse_direct_name])
                            diffuse_combined_output = combine_inputs(node_tree, "Diffuse", per_layer_node.outputs[diffuse_direct_name], indirect_output, per_layer_node.outputs[diffuse_color_name], x_pos + column_spacing + 100, y_pos - 120)
                            input_slot = layer_color_node.inputs["Diffuse"]
                            if scene.render_manager.denoise_diffuse and scene.render_manager.denoise:
                                normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                                albedo_socket = per_layer_node.outputs.get(get_pass_name("diffuse_color"))
                                if normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, "Diffuse", diffuse_combined_output.outputs[0], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 150, noisy_passes)
                                    used_slots.add("Diffuse")
                                else:
                                    node_tree.links.new(diffuse_combined_output.outputs[0], input_slot)
                                    used_slots.add("Diffuse")
                            else:
                                node_tree.links.new(diffuse_combined_output.outputs[0], input_slot)
                                used_slots.add("Diffuse")
                        else:
                            if has_color:
                                input_slot = layer_color_node.inputs.get("Diffuse Color (Fallback)")
                                if input_slot:
                                    node_tree.links.new(per_layer_node.outputs[diffuse_color_name], input_slot)
                                    used_slots.add("Diffuse Color (Fallback)")
                    else:
                        # Only process individual passes if not combining
                        if scene.render_manager.denoise and scene.render_manager.denoise_diffuse and not (combine_diff_glossy_active or combine_diff_glossy_eevee_active):
                            normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                            albedo_socket = per_layer_node.outputs.get(get_pass_name("diffuse_color"))
                            if has_direct and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, get_pass_name("diffuse_direct"), per_layer_node.outputs[get_pass_name("diffuse_direct")], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 150, noisy_passes)
                                used_slots.add(get_pass_name("diffuse_direct"))
                            if has_color and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, get_pass_name("diffuse_color"), per_layer_node.outputs[get_pass_name("diffuse_color")], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 200, noisy_passes)
                                used_slots.add(get_pass_name("diffuse_color"))
                            if "CYCLES" in engine:
                                indirect_socket = per_layer_node.outputs.get(get_pass_name("diffuse_indirect"))
                                if indirect_socket and not indirect_socket.is_unavailable and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, get_pass_name("diffuse_direct"), indirect_socket, normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 250, noisy_passes)
                                    used_slots.add(get_pass_name("diffuse_indirect"))

                elif pass_name == get_pass_name("glossy_color"):
                    glossy_direct_name = get_pass_name("glossy_direct")
                    glossy_color_name = get_pass_name("glossy_color")
                    glossy_indirect_name = get_pass_name("glossy_indirect")
                    has_direct = glossy_direct_name in per_layer_node.outputs and not per_layer_node.outputs[glossy_direct_name].is_unavailable
                    has_color = glossy_color_name in per_layer_node.outputs and not per_layer_node.outputs[glossy_color_name].is_unavailable
                    if "EEVEE" in engine and combine_diff_glossy_eevee_active:
                        if has_direct and has_color:
                            multiply_glossy_node = create_mix_node(node_tree, False)
                            multiply_glossy_node.blend_type = 'MULTIPLY'
                            multiply_glossy_node.label = "Multiply Glossy Eevee"
                            multiply_glossy_node.location = (x_pos + column_spacing + 100, y_pos - 190)
                            multiply_glossy_node.hide = True
                            node_tree.links.new(per_layer_node.outputs[glossy_direct_name], multiply_glossy_node.inputs[1])
                            node_tree.links.new(per_layer_node.outputs[glossy_color_name], multiply_glossy_node.inputs[2])
                            input_slot = layer_color_node.inputs["Glossy Combined"]
                            if scene.render_manager.denoise and scene.render_manager.denoise_glossy:
                                normal_socket = per_layer_node.outputs.get("Normal")
                                albedo_socket = per_layer_node.outputs.get(get_pass_name("diffuse_color"))
                                if normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, "Glossy Combined", multiply_glossy_node.outputs[0], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 300, noisy_passes)
                                    used_slots.add("Glossy Combined")
                                else:
                                    node_tree.links.new(multiply_glossy_node.outputs[0], input_slot)
                                    used_slots.add("Glossy Combined")
                            else:
                                node_tree.links.new(multiply_glossy_node.outputs[0], input_slot)
                                used_slots.add("Glossy Combined")
                        else:
                            if has_direct or has_color:
                                input_slot = layer_color_node.inputs.get("Glossy Color (Fallback)")
                                if input_slot:
                                    if has_direct:
                                        node_tree.links.new(per_layer_node.outputs[glossy_direct_name], input_slot)
                                    elif has_color:
                                        node_tree.links.new(per_layer_node.outputs[glossy_color_name], input_slot)
                                    used_slots.add("Glossy Color (Fallback)")
                    elif "CYCLES" in engine and combine_diff_glossy_active:
                        if has_direct and has_color:
                            indirect_output = per_layer_node.outputs.get(glossy_indirect_name, per_layer_node.outputs[glossy_direct_name])
                            glossy_combined_output = combine_inputs(node_tree, "Glossy", per_layer_node.outputs[glossy_direct_name], indirect_output, per_layer_node.outputs[glossy_color_name], x_pos + column_spacing + 100, y_pos - 190)
                            input_slot = layer_color_node.inputs["Glossy"]
                            if scene.render_manager.denoise_glossy and scene.render_manager.denoise:
                                normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                                albedo_socket = per_layer_node.outputs.get(get_pass_name("glossy_color"))
                                if normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, "Glossy", glossy_combined_output.outputs[0], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 300, noisy_passes)
                                    used_slots.add("Glossy")
                                else:
                                    node_tree.links.new(glossy_combined_output.outputs[0], input_slot)
                                    used_slots.add("Glossy")
                            else:
                                node_tree.links.new(glossy_combined_output.outputs[0], input_slot)
                                used_slots.add("Glossy")
                        else:
                            if has_color:
                                input_slot = layer_color_node.inputs.get("Glossy Color (Fallback)")
                                if input_slot:
                                    node_tree.links.new(per_layer_node.outputs[glossy_color_name], input_slot)
                                    used_slots.add("Glossy Color (Fallback)")
                    else:
                        if scene.render_manager.denoise and scene.render_manager.denoise_glossy and not (combine_diff_glossy_active or combine_diff_glossy_eevee_active):
                            normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                            albedo_socket = per_layer_node.outputs.get(get_pass_name("glossy_color"))
                            if has_direct and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, get_pass_name("glossy_direct"), per_layer_node.outputs[glossy_direct_name], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 300, noisy_passes)
                                used_slots.add(get_pass_name("glossy_direct"))
                            if has_color and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, get_pass_name("glossy_color"), per_layer_node.outputs[get_pass_name("glossy_color")], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 350, noisy_passes)
                                used_slots.add(get_pass_name("glossy_color"))
                            if "CYCLES" in engine:
                                indirect_socket = per_layer_node.outputs.get(get_pass_name("glossy_indirect"))
                                if indirect_socket and not indirect_socket.is_unavailable and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, get_pass_name("glossy_indirect"), indirect_socket, normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 400, noisy_passes)
                                    used_slots.add(get_pass_name("glossy_indirect"))

                elif pass_name == get_pass_name("transmission_color"):
                    transmission_direct_name = get_pass_name("transmission_direct") if "CYCLES" in engine else get_pass_name("transparent")
                    transmission_indirect_name = get_pass_name("transmission_indirect") if "CYCLES" in engine else get_pass_name("transparent")
                    transmission_color_name = get_pass_name("transmission_color") if "CYCLES" in engine else get_pass_name("transparent")

                    print(transmission_direct_name, transmission_indirect_name, transmission_color_name,  "----------")

                    has_direct = transmission_direct_name in per_layer_node.outputs and not per_layer_node.outputs[transmission_direct_name].is_unavailable
                    has_color = transmission_color_name in per_layer_node.outputs and not per_layer_node.outputs[transmission_color_name].is_unavailable
                    if (combine_diff_glossy_active and "CYCLES" in engine) or (combine_diff_glossy_eevee_active and "EEVEE" in engine):
                        if has_direct and has_color:
                            transmission_combined_output = combine_inputs(node_tree, "Transmission", per_layer_node.outputs[transmission_direct_name], per_layer_node.outputs.get(transmission_indirect_name, per_layer_node.outputs[transmission_direct_name]), per_layer_node.outputs[transmission_color_name], x_pos + column_spacing + 100, y_pos - 260)
                            # input_slot = layer_color_node.inputs["Transmission"]
                            input_slot = transmission_combined_output.inputs[0]
                            if scene.render_manager.denoise_transmission and scene.render_manager.denoise:
                                normal_socket = per_layer_node.outputs.get(get_pass_name("normal"))
                                albedo_socket = per_layer_node.outputs.get(get_pass_name("transmission_color") if "CYCLES" in engine else get_pass_name("diffuse_color"))
                                if normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, "Transmission", transmission_combined_output.outputs[0], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 450, noisy_passes)
                                    used_slots.add("Transmission")
                                else:
                                    node_tree.links.new(transmission_combined_output.outputs[0], input_slot)
                                    used_slots.add("Transmission")
                            else:
                                node_tree.links.new(transmission_combined_output.outputs[0], input_slot)
                                used_slots.add("Transmission")
                        else:
                            if has_color:
                                input_slot = layer_color_node.inputs.get("Transmission Color (Fallback)")
                                if input_slot:
                                    node_tree.links.new(per_layer_node.outputs[transmission_color_name], input_slot)
                                    used_slots.add("Transmission Color (Fallback)")
                    else:
                        if scene.render_manager.denoise_transmission and scene.render_manager.denoise and not (combine_diff_glossy_active or combine_diff_glossy_eevee_active):
                            normal_socket = per_layer_node.outputs.get("Normal")
                            albedo_socket = per_layer_node.outputs.get(get_pass_name("transmission_color") if "CYCLES" in engine else get_pass_name("diffuse_color"))
                            if has_direct and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, transmission_direct_name, per_layer_node.outputs[transmission_direct_name], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 450, noisy_passes)
                                used_slots.add(transmission_direct_name)
                            if has_color and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                denoise_pass(node_tree, transmission_color_name, per_layer_node.outputs[transmission_color_name], normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 500, noisy_passes)
                                used_slots.add(transmission_color_name)
                            if "CYCLES" in engine:
                                indirect_socket = per_layer_node.outputs.get(transmission_indirect_name)
                                if indirect_socket and not indirect_socket.is_unavailable and normal_socket and albedo_socket and not normal_socket.is_unavailable and not albedo_socket.is_unavailable:
                                    denoise_pass(node_tree, transmission_indirect_name, indirect_socket, normal_socket, albedo_socket, layer_color_node, x_pos + column_spacing + 300, y_pos - 550, noisy_passes)
                                    used_slots.add(transmission_indirect_name)

            # Handle Eevee-specific Denoising
            if scene.render_manager.denoise and "EEVEE" in engine:
                print(f"DEBUG: Eevee denoising settings - denoise: {scene.render_manager.denoise}")
                print(f"DEBUG: denoise_emit: {scene.render_manager.denoise_emit}")
                print(f"DEBUG: denoise_environment: {scene.render_manager.denoise_environment}")
                print(f"DEBUG: denoise_shadow: {scene.render_manager.denoise_shadow}")
                print(f"DEBUG: denoise_ao: {scene.render_manager.denoise_ao}")
                for pass_name, y_offset in [
                    ("Emit", -600),
                    ("Env", -650),
                    ("Shadow", -700),
                    ("AO", -750)
                ]:
                    denoise_property = f"denoise_{pass_name.lower()}" if pass_name != "Env" else "denoise_environment"
                    if getattr(scene.render_manager, denoise_property, False):
                        print(f"DEBUG: Attempting to denoise Eevee pass: {pass_name}")
                        pass_available = pass_name in per_layer_node.outputs
                        normal_available = "Normal" in per_layer_node.outputs
                        diffcol_available = get_pass_name("diffuse_color") in per_layer_node.outputs
                        pass_unavailable = pass_available and hasattr(per_layer_node.outputs[pass_name], 'is_unavailable') and per_layer_node.outputs[pass_name].is_unavailable
                        normal_unavailable = normal_available and hasattr(per_layer_node.outputs["Normal"], 'is_unavailable') and per_layer_node.outputs["Normal"].is_unavailable
                        diffcol_unavailable = diffcol_available and hasattr(per_layer_node.outputs[get_pass_name("diffuse_color")], 'is_unavailable') and per_layer_node.outputs[get_pass_name("diffuse_color")].is_unavailable
                        print(f"DEBUG: Pass '{pass_name}' available: {pass_available}, is_unavailable: {pass_unavailable}")
                        print(f"DEBUG: Normal available: {normal_available}, is_unavailable: {normal_unavailable}")
                        print(f"DEBUG: DiffCol available: {diffcol_available}, is_unavailable: {diffcol_unavailable}")
                        if (
                            pass_available and
                            not pass_unavailable and
                            normal_available and
                            not normal_unavailable and
                            diffcol_available and
                            not diffcol_unavailable
                        ):
                            print(f"🟡 Creating denoise node for Eevee pass: {pass_name}")
                            denoise_pass(
                                node_tree,
                                pass_name,
                                per_layer_node.outputs[pass_name],
                                per_layer_node.outputs["Normal"],
                                per_layer_node.outputs[get_pass_name("diffuse_color")],
                                layer_color_node,
                                x_pos + column_spacing + 300,
                                y_pos + y_offset,
                                noisy_passes,
                            )
                            used_slots.add(pass_name)
                        else:
                            print(f"⚠ Skipped Eevee denoise for '{pass_name}' — Missing or unavailable sockets:")
                            print(f"  - Pass '{pass_name}': {'Available' if pass_available else 'Missing'}, {'unavailable' if pass_unavailable else 'available'}")
                            print(f"  - Normal: {'Available' if normal_available else 'Missing'}, {'unavailable' if normal_unavailable else 'available'}")
                            print(f"  - DiffCol: {'Available' if diffcol_available else 'Missing'}, {'unavailable' if diffcol_unavailable else 'available'}")
                            if pass_name == "Env":
                                print(f"WARNING: Environment pass denoising failed. Ensure 'Environment' pass is enabled in View Layer settings.")

            # Handle Cycles-specific Denoising for Emit, Env, AO
            if scene.render_manager.denoise and "CYCLES" in engine:
                print(f"DEBUG: Cycles denoising settings - denoise: {scene.render_manager.denoise}")
                print(f"DEBUG: denoise_emit: {scene.render_manager.denoise_emit}")
                print(f"DEBUG: denoise_environment: {scene.render_manager.denoise_environment}")
                print(f"DEBUG: denoise_ao: {scene.render_manager.denoise_ao}")
                for pass_name, y_offset in [
                    ("Emit", -600),
                    ("Env", -650),
                    ("AO", -700)
                ]:
                    denoise_property = f"denoise_{pass_name.lower()}" if pass_name != "Env" else "denoise_environment"
                    if getattr(scene.render_manager, denoise_property, False):
                        print(f"DEBUG: Attempting to denoise Cycles pass: {pass_name}")
                        pass_available = pass_name in per_layer_node.outputs
                        normal_available = "Normal" in per_layer_node.outputs
                        diffcol_available = get_pass_name("diffuse_color") in per_layer_node.outputs
                        pass_unavailable = pass_available and hasattr(per_layer_node.outputs[pass_name], 'is_unavailable') and per_layer_node.outputs[pass_name].is_unavailable
                        normal_unavailable = normal_available and hasattr(per_layer_node.outputs["Normal"], 'is_unavailable') and per_layer_node.outputs["Normal"].is_unavailable
                        diffcol_unavailable = diffcol_available and hasattr(per_layer_node.outputs[get_pass_name("diffuse_color")], 'is_unavailable') and per_layer_node.outputs[get_pass_name("diffuse_color")].is_unavailable
                        print(f"DEBUG: Pass '{pass_name}' available: {pass_available}, is_unavailable: {pass_unavailable}")
                        print(f"DEBUG: Normal available: {normal_available}, is_unavailable: {normal_unavailable}")
                        print(f"DEBUG: DiffCol available: {diffcol_available}, is_unavailable: {diffcol_unavailable}")
                        if (
                            pass_available and
                            not pass_unavailable and
                            normal_available and
                            not normal_unavailable and
                            diffcol_available and
                            not diffcol_unavailable
                        ):
                            print(f"🟡 Creating denoise node for Cycles pass: {pass_name}")
                            denoise_pass(
                                node_tree,
                                pass_name,
                                per_layer_node.outputs[pass_name],
                                per_layer_node.outputs["Normal"],
                                per_layer_node.outputs[get_pass_name("diffuse_color")],
                                layer_color_node,
                                x_pos + column_spacing + 300,
                                y_pos + y_offset,
                                noisy_passes,
                            )
                            used_slots.add(pass_name)
                        else:
                            print(f"⚠ Skipped Cycles denoise for '{pass_name}' — Missing or unavailable sockets:")
                            print(f"  - Pass '{pass_name}': {'Available' if pass_available else 'Missing'}, {'unavailable' if pass_unavailable else 'available'}")
                            print(f"  - Normal: {'Available' if normal_available else 'Missing'}, {'unavailable' if normal_unavailable else 'available'}")
                            print(f"  - DiffCol: {'Available' if diffcol_available else 'Missing'}, {'unavailable' if diffcol_unavailable else 'available'}")
                            if pass_name == "Env":
                                print(f"WARNING: Environment pass denoising failed. Ensure 'Environment' pass is enabled in View Layer settings.")
                            elif pass_name == "AO":
                                print(f"WARNING: Ambient Occlusion pass denoising failed. Ensure 'Ambient Occlusion' pass is enabled in View Layer settings.")

            # Handle Light Group Denoising
            if scene.render_manager.denoise_lightgroup and scene.render_manager.denoise and "CYCLES" in engine:
                lg_y_offset_base = -750
                for output_socket in per_layer_node.outputs:
                    if output_socket.name == "Combined_LightG" and not output_socket.is_unavailable:
                        lg_pass_name = output_socket.name
                        lg_y_pos = y_pos + lg_y_offset_base
                        if "Denoising Normal" in per_layer_node.outputs and "Denoising Albedo" in per_layer_node.outputs:
                            denoise_pass(node_tree, lg_pass_name, output_socket, per_layer_node.outputs["Denoising Normal"], per_layer_node.outputs["Denoising Albedo"], layer_color_node, x_pos + column_spacing + 300, lg_y_pos, noisy_passes)
                            used_slots.add(lg_pass_name)
                        else:
                            lg_slot = output_node_new_slot(layer_color_node, lg_pass_name)
                            node_tree.links.new(output_socket, lg_slot)
                            used_slots.add(lg_pass_name)
                        break

            # Handle Other Individual Pass Denoising
            if scene.render_manager.denoise:
                def try_denoise_pass(pass_name, normal_name, albedo_name, y_offset):
                    if (
                        pass_name in per_layer_node.outputs and
                        not per_layer_node.outputs[pass_name].is_unavailable and
                        normal_name in per_layer_node.outputs and
                        not per_layer_node.outputs[normal_name].is_unavailable and
                        albedo_name in per_layer_node.outputs and
                        not per_layer_node.outputs[albedo_name].is_unavailable
                    ):
                        denoise_pass(node_tree, pass_name, per_layer_node.outputs[pass_name], per_layer_node.outputs[normal_name], per_layer_node.outputs[albedo_name], layer_color_node, x_pos + column_spacing + 300, y_pos + y_offset, noisy_passes)
                        used_slots.add(pass_name)

                if "CYCLES" in engine and not combine_diff_glossy_active:
                    if scene.render_manager.denoise_diffuse:
                        try_denoise_pass(get_pass_name("diffuse_direct"), get_pass_name("normal"), get_pass_name("diffuse_color"), -150)
                        try_denoise_pass(get_pass_name("diffuse_indirect"), get_pass_name("normal"), get_pass_name("diffuse_color"), -200)
                        try_denoise_pass(get_pass_name("diffuse_color"), get_pass_name("normal"), get_pass_name("diffuse_color"), -250)
                    if scene.render_manager.denoise_glossy:
                        try_denoise_pass(get_pass_name("glossy_direct"), get_pass_name("normal"), get_pass_name("glossy_color"), -300)
                        try_denoise_pass(get_pass_name("glossy_indirect"), get_pass_name("normal"), get_pass_name("glossy_color"), -350)
                        try_denoise_pass(get_pass_name("glossy_color"), get_pass_name("normal"), get_pass_name("glossy_color"), -400)
                    if scene.render_manager.denoise_transmission:
                        try_denoise_pass(get_pass_name("transmission_direct"), get_pass_name("normal"),     get_pass_name("transmission_color"), -450)
                        try_denoise_pass(get_pass_name("transmission_indirect"), get_pass_name("normal"),   get_pass_name("transmission_color"), -500)
                        try_denoise_pass(get_pass_name("transmission_color"), get_pass_name("normal"),      get_pass_name("transmission_color"), -550)
                if scene.render_manager.denoise_alpha:
                    try_denoise_pass("Alpha", "Normal", get_pass_name("diffuse_color"), 0)
                if "CYCLES" in engine:
                    if scene.render_manager.denoise_volumedir:
                        try_denoise_pass(get_pass_name("volume_direct"), "Denoising Normal", "Denoising Albedo", -600)
                    if scene.render_manager.denoise_volumeind:
                        try_denoise_pass(get_pass_name("volume_indirect"), "Denoising Normal", "Denoising Albedo", -650)
                    if scene.render_manager.denoise_shadow_catcher:
                        try_denoise_pass("Shadow Catcher", "Denoising Normal", "Denoising Albedo", -700)
                    
                if scene.render_manager.denoise_image:
                    if "CYCLES" in engine and scene.cycles.use_denoising:
                        node_tree.links.new(per_layer_node.outputs["Image"], layer_color_node.inputs[color_node_image_input_name])
                        denoise_node = node_tree.nodes.new("CompositorNodeDenoise")
                        denoise_node.label = "Denoise Noisy Image"
                        denoise_node.location = (x_pos + column_spacing + 300, y_pos - 50)
                        denoise_node.hide = True
                        node_tree.links.new(per_layer_node.outputs["Noisy Image"], denoise_node.inputs["Image"])
                        node_tree.links.new(per_layer_node.outputs["Normal"], denoise_node.inputs["Normal"])
                        node_tree.links.new(per_layer_node.outputs[get_pass_name("diffuse_color")], denoise_node.inputs["Albedo"])

                        output_node_new_slot(layer_color_node, color_node_image_input_name + " (Compositor Denoised)")
                        node_tree.links.new(denoise_node.outputs["Image"], layer_color_node.inputs[color_node_image_input_name + " (Compositor Denoised)"])

                        used_slots.add(color_node_image_input_name + " (Compositor Denoised)")
                        noisy_passes.append([per_layer_node.outputs["Noisy Image"], "Image"])
                    else:
                        denoise_pass(node_tree, color_node_image_input_name, per_layer_node.outputs["Image"], per_layer_node.outputs["Normal"], per_layer_node.outputs[get_pass_name("diffuse_color")], layer_color_node, x_pos + column_spacing + 300, y_pos - 50, noisy_passes)
                        used_slots.add(color_node_image_input_name)
                else:
                    node_tree.links.new(per_layer_node.outputs["Image"], layer_color_node.inputs[color_node_image_input_name])
                    used_slots.add(color_node_image_input_name)

            # Save Noisy Passes
            if scene.render_manager.save_noisy_in_file:
                for noisy_pass_array in noisy_passes:
                    noisy_pass = noisy_pass_array[0]
                    noisy_name = "Noisy " + noisy_pass_array[1]

                    output_node_new_slot(layer_color_node, noisy_name)
                    node_tree.links.new(noisy_pass, layer_color_node.inputs[noisy_name])

                    used_slots.add(noisy_name)
            if scene.render_manager.save_noisy_separately and scene.render_manager.denoise:
                for noisy_pass_array in noisy_passes:
                    noisy_pass = noisy_pass_array[0]
                    noisy_name = "Noisy " + noisy_pass_array[1]

                    output_node_new_slot(layer_noisy_node, noisy_name)
                    node_tree.links.new(noisy_pass, layer_noisy_node.inputs[noisy_name])

            # Connect Data Passes
            for pass_name in data_passes:
                if pass_name in per_layer_node.outputs:
                    data_slot = output_node_new_slot(layer_data_node, pass_name)
                    # data_input = layer_data_node.inputs[-1]
                    data_input = get_latest_input(layer_data_node)

                    if scene.render_manager.fixed_for_y_up and pass_name in y_ups:
                        node_tree.links.new(y_ups[pass_name].outputs[0], data_input)
                    else:
                        node_tree.links.new(per_layer_node.outputs[pass_name], data_input)

            # Connect Unlinked Passes
            for output_socket in per_layer_node.outputs:
                if not output_socket.is_unavailable and not output_socket.is_linked and output_socket.name not in backup_only_passes:
                    if output_socket.name not in layer_color_node.inputs:
                        try:
                            output_node_new_slot(layer_color_node, output_socket.name)
                            
                            node_tree.links.new(output_socket, get_latest_input(layer_color_node))
                            used_slots.add(output_socket.name)
                        except Exception as e:
                            print(f"Warning: Could not create/connect slot '{output_socket.name}': {e}")
                    else:
                        node_tree.links.new(output_socket, layer_color_node.inputs[output_socket.name])
                        used_slots.add(output_socket.name)

            # Handle Backup Passes
            if scene.render_manager.backup_passes:
                for output_socket in per_layer_node.outputs:
                    if not output_socket.is_unavailable:
                        if output_socket.name not in [slot.name for slot in get_output_slots(layer_backup_node)]:
                            output_node_new_slot(layer_backup_node, output_socket.name)
                        node_tree.links.new(output_socket, layer_backup_node.inputs[output_socket.name])

            # Clean up unused slots
            slots_to_check = []
            if "CYCLES" in engine:
                slots_to_check = [
                    "Diffuse Color (Fallback)", "Glossy Color (Fallback)", "Transmission Color (Fallback)"
                ]
                if combine_diff_glossy_active:
                    slots_to_check.extend([get_pass_name("diffuse_direct"), get_pass_name("diffuse_indirect"), get_pass_name("diffuse_color"), get_pass_name("glossy_direct"), get_pass_name("glossy_indirect"), get_pass_name("glossy_color"), get_pass_name("transmission_direct"), get_pass_name("transmission_indirect"), get_pass_name("transmission_color")])
                else:
                    slots_to_check.extend(["Diffuse", "Glossy", "Transmission"])
            elif "EEVEE" in engine:
                slots_to_check = [
                    "Diffuse Color (Fallback)", "Glossy Color (Fallback)"
                ]
                if combine_diff_glossy_eevee_active:
                    slots_to_check.extend([get_pass_name("diffuse_direct"), get_pass_name("diffuse_color"), get_pass_name("glossy_direct"), get_pass_name("glossy_color"), get_pass_name("transparent")])
                else:
                    slots_to_check.extend(["Diffuse Combined", "Glossy Combined"])
            
            # Store used slots with their connections
            slot_connections = []
            for slot in get_output_slots(layer_color_node):
                if slot.name in used_slots:
                    input_socket = next((inp for inp in layer_color_node.inputs if inp.name == slot.name), None)
                    if input_socket and input_socket.is_linked:
                        source_socket = input_socket.links[0].from_socket if input_socket.links else None
                        slot_connections.append((slot.name, source_socket))
                    else:
                        slot_connections.append((slot.name, None))
            
            # Clear all slots
            output_node_clear_slot(layer_color_node)
            
            # Re-add used slots and reconnect
            for slot_name, source_socket in slot_connections:
                output_node_new_slot(layer_color_node, slot_name)
                if source_socket:
                    node_tree.links.new(source_socket, layer_color_node.inputs[slot_name])
                print(f"Kept used slot: {slot_name}")
            
            # Log removed slots
            for slot_name in slots_to_check:
                if slot_name not in used_slots:
                    print(f"Removed unused slot: {slot_name}")

        if previous_alpha_node:
            node_tree.links.new(previous_alpha_node.outputs["Image"], composite_node.inputs[0])

        self.report({"INFO"}, "Created node setup for all render layers in spreadsheet layout.")
        return {"FINISHED"}
# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def combine_inputs(node_tree, group_name, input_slot1, input_slot2, input_slot3, x_pos, y_pos):
    combine_node = ensure_node_group("Combine_Passes")
    combine_nodegroup = node_tree.nodes.new("CompositorNodeGroup")
    combine_nodegroup.node_tree = combine_node
    combine_nodegroup.location = (x_pos, y_pos)
    combine_nodegroup.label = "Combine " + group_name
    combine_nodegroup.hide = True
    node_tree.links.new(input_slot1, combine_nodegroup.inputs[0])
    node_tree.links.new(input_slot2, combine_nodegroup.inputs[1])
    node_tree.links.new(input_slot3, combine_nodegroup.inputs[2])
    return combine_nodegroup

def denoise_pass(node_tree, slot_name, source_image_slot, source_normal_slot, source_albedo_slot, dest_node, x_pos, y_pos, noisy_passes):
    print(f"🟡 Creating denoise node for: {slot_name}")
    denoise_node = node_tree.nodes.new("CompositorNodeDenoise")
    denoise_node.label = "Denoise " + str(slot_name)
    denoise_node.location = (x_pos, y_pos)
    denoise_node.hide = True
    node_tree.links.new(source_image_slot, denoise_node.inputs["Image"])
    node_tree.links.new(source_normal_slot, denoise_node.inputs["Normal"])
    node_tree.links.new(source_albedo_slot, denoise_node.inputs["Albedo"])
    
    # Check if slot already exists

    target_slot = get_output_slot_by_name(dest_node, slot_name)

    
    # Create new slot only if it doesn't exist
    if target_slot is None:
        try:
            output_node_new_slot(dest_node, slot_name)
            target_slot = get_latest_input(dest_node)
        except RuntimeError as e:
            print(f"Error creating slot '{slot_name}': {e}")
            return
    
    # Find the corresponding input socket for the slot
    target_input_socket = None
    for input_socket in dest_node.inputs:
        if input_socket.name == slot_name:
            target_input_socket = input_socket
            break
    
    # Remove existing links to the target input socket
    if target_input_socket and target_input_socket.is_linked:
        for link in target_input_socket.links:
            node_tree.links.remove(link)
    
    # Connect denoised output to the target input socket
    if target_input_socket:
        node_tree.links.new(denoise_node.outputs["Image"], target_input_socket)
        print(f"✅ Connected denoise output to: {slot_name} → {target_input_socket.name}")
    else:
        print(f"⚠ Could not find input socket for slot '{slot_name}'")
        return
    
    noisy_passes.append([source_image_slot, slot_name])

def a_denoising_operation_is_checked(scene):
    return any([
        scene.render_manager.denoise_image,
        scene.render_manager.denoise_diffuse,
        scene.render_manager.denoise_glossy,
        scene.render_manager.denoise_transmission,
        scene.render_manager.denoise_alpha,
        scene.render_manager.denoise_volumedir,
        scene.render_manager.denoise_volumeind,
        scene.render_manager.denoise_shadow_catcher,
        scene.render_manager.denoise_lightgroup,
        scene.render_manager.denoise_emit,
        scene.render_manager.denoise_environment,
        scene.render_manager.denoise_shadow,
        scene.render_manager.denoise_ao
    ])

# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------

class RenderManagerSettings(bpy.types.PropertyGroup):
    beauty_compression: bpy.props.EnumProperty(
        name="Beauty Compression",
        description="Compression method for beauty EXR outputs",
        items=[
            ("NONE", "None", ""), ("RLE", "RLE", ""), ("ZIPS", "ZIPS", ""), ("ZIP", "ZIP", ""),
            ("PIZ", "PIZ", ""), ("PXR24", "PXR24", ""), ("B44", "B44", ""), ("B44A", "B44A", ""),
            ("DWAA", "DWAA", ""), ("DWAB", "DWAB", "")
        ],
        default="DWAA",
        update=update_exr_compression
    )
    data_compression: bpy.props.EnumProperty(
        name="Data Compression",
        description="Compression method for data EXR outputs",
        items=[
            ("NONE", "None", ""), ("RLE", "RLE", ""), ("ZIPS", "ZIPS", ""), ("ZIP", "ZIP", ""),
            ("PIZ", "PIZ", ""), ("PXR24", "PXR24", ""), ("B44", "B44", ""), ("B44A", "B44A", ""),
            ("DWAA", "DWAA", ""), ("DWAB", "DWAB", "")
        ],
        default="ZIP",
        update=update_exr_compression
    )
    dwaa_compression_level: bpy.props.IntProperty(
        name="DWAA Compression Level",
        description="Lossy compression level for DWAA/DWAB (0 = highest compression, 100 = lossless)",
        default=45,
        min=0,
        max=100,
        update=update_exr_compression
    )
    fixed_for_y_up: bpy.props.BoolProperty(
        name="Make Y Up",
        description="Enable to make the coordinate system compatible with software that assumes Y is up",
        default=False
    )
    combine_diff_glossy: bpy.props.BoolProperty(
        name="Combine Diff/Glossy/Trans",
        description="Combine diff and glossy channels together (Cycles)",
        default=True
    )
    combine_diff_glossy_eevee: bpy.props.BoolProperty(
        name="Combine Diff/Glossy (Eevee)",
        description="In Eevee, combine Diffuse Direct * Diffuse Color and Specular Direct * Specular Color",
        default=True
    )
    denoise: bpy.props.BoolProperty(
        name="Enable",
        description="Enable per-pass denoising operations",
        default=True
    )
    denoise_image: bpy.props.BoolProperty(name="Image", description="Denoises the image pass", default=True)
    denoise_alpha: bpy.props.BoolProperty(name="Alpha", description="Denoises the alpha channel pass", default=False)
    denoise_diffuse: bpy.props.BoolProperty(name="Diffuse", description="Denoises diffuse pass", default=True)
    denoise_glossy: bpy.props.BoolProperty(name="Glossy", description="Denoises glossy pass", default=True)
    denoise_transmission: bpy.props.BoolProperty(name="Transmission", description="Denoises transparent pass", default=True)
    denoise_emit: bpy.props.BoolProperty(name="Emission", description="Denoise emission pass", default=False)
    denoise_environment: bpy.props.BoolProperty(name="Environment", description="Denoise environment pass", default=False)
    denoise_shadow: bpy.props.BoolProperty(name="Shadow", description="Denoise shadow pass", default=False)
    denoise_ao: bpy.props.BoolProperty(name="AO", description="Denoise ambient occlusion pass", default=False)
    denoise_lightgroup: bpy.props.BoolProperty(
        name="Light Group",
        description="Denoises passes related to light groups (requires manual setup in compositor)",
        default=False
    )
    denoise_volumedir: bpy.props.BoolProperty(name="Volume Direct", description="Denoises Direct Volumetrics", default=False)
    denoise_volumeind: bpy.props.BoolProperty(name="Volume Indirect", description="Denoises Indirect Volumetrics", default=False)
    denoise_shadow_catcher: bpy.props.BoolProperty(name="Shadow Catcher", description="Denoises shadow catcher pass", default=False)
    save_noisy_in_file: bpy.props.BoolProperty(
        name="Embed Noisy Passes",
        description="Keeps the noisy passes as a backup in the same file",
        default=False
    )
    save_noisy_separately: bpy.props.BoolProperty(
        name="Save Noisy Passes Separately",
        description="Keeps the noisy passes as a backup in a separate file",
        default=False
    )
    backup_passes: bpy.props.BoolProperty(
        name="Original Passes (32bit Only)",
        description="Save a full copy of the unmodified passes into a separate file",
        default=False
    )
    color_depth_override: bpy.props.EnumProperty(
        items=(("16", "16", ""), ("32", "32", "")),
        description="Use the color depth configured in the OpenEXR output settings",
        name="Color Depth"
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
    RENDER_MANAGER_OT_reorder_view_layer,
    RENDER_MANAGER_OT_debug_denoise_flags,
    RENDER_MANAGER_PT_panel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_manager = bpy.props.PointerProperty(type=RenderManagerSettings)

def unregister():
    del bpy.types.Scene.render_manager
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
