import bpy

# ------------------------------------------------------------------------------
# 1. Define a custom PropertyGroup for storing expanded/collapsed state.
#    (Includes an explicit "name" property.)
# ------------------------------------------------------------------------------


class CollectionExpandedState(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Collection Name")
    value: bpy.props.BoolProperty(name="Expanded", default=False)


# ------------------------------------------------------------------------------
# 2. Initialize our custom property on the Scene.
#    (Remove any previous registration for hot‑reload safety.)
# ------------------------------------------------------------------------------


def init_custom_properties():
    if hasattr(bpy.types.Scene, "collection_spreadsheet_expanded"):
        del bpy.types.Scene.collection_spreadsheet_expanded
    bpy.types.Scene.collection_spreadsheet_expanded = bpy.props.CollectionProperty(
        type=CollectionExpandedState
    )


# ------------------------------------------------------------------------------
# 3. Helper functions to get and set the expanded state.
# ------------------------------------------------------------------------------


def get_expanded_state():
    scene = bpy.context.scene
    expanded_state = {}
    for item in scene.collection_spreadsheet_expanded:
        expanded_state[item.name] = item.value
    return expanded_state


def set_expanded_state(collection_name, value):
    scene = bpy.context.scene
    item = None
    for existing_item in scene.collection_spreadsheet_expanded:
        if existing_item.name == collection_name:
            item = existing_item
            break
    if not item:
        item = scene.collection_spreadsheet_expanded.add()
        item.name = collection_name
    item.value = value


# ------------------------------------------------------------------------------
# 4. UI Drawing Helper Functions
# ------------------------------------------------------------------------------


def find_layer_collection_by_collection(root_layer_collection, collection):
    """Recursively find the LayerCollection whose .collection is the given collection."""
    if root_layer_collection.collection == collection:
        return root_layer_collection
    for child in root_layer_collection.children:
        found = find_layer_collection_by_collection(child, collection)
        if found:
            return found
    return None


def draw_collection(layout, view_layer, child_coll):
    """Draw the settings for a single collection in a view layer."""
    matching_lc = find_layer_collection_by_collection(
        view_layer.layer_collection, child_coll
    )
    if matching_lc:
        cell_row = layout.row(align=True)
        cell_row.prop(matching_lc, "exclude", text="", emboss=False)
        cell_row.prop(matching_lc, "holdout", text="", emboss=False)
        cell_row.prop(matching_lc, "indirect_only", text="", emboss=False)
    else:
        layout.label(text="N/A")


def get_split_factors(n):
    """
    Compute a list of factors that, when used successively,
    split a layout evenly into n columns.

    For example, if n=3:
      - The first column gets 1/3 of the available width (factor = 1/3).
      - Then the remaining area is 2/3, so the second column gets (1/3) / (2/3) = 0.5.
      - The third column uses the remainder.
    """
    factors = []
    remaining = 1.0
    for i in range(n - 1):
        f = (1.0 / n) / remaining
        factors.append(f)
        remaining -= 1.0 / n
    return factors


def draw_right_columns(layout, view_layers, draw_func):
    """
    Draw the right-side columns (one per view layer) using the same split factors.

    This ensures that both header and table rows have equally sized columns.
    """
    n = len(view_layers)
    factors = get_split_factors(n)
    row = layout.row(align=True)
    for i, vl in enumerate(view_layers):
        if i < len(factors):
            split = row.split(factor=factors[i], align=True)
            col = split.column(align=True)
            draw_func(col, vl)
            row = split
        else:
            col = row.column(align=True)
            draw_func(col, vl)


def draw_recursive_collections(layout, view_layers, collection, level=0):
    """Recursively draw collections with an expand/collapse toggle."""
    expanded_state = get_expanded_state()
    is_expanded = expanded_state.get(collection.name, False)

    # Create a row split into two parts:
    #  - Left (30% width) for the collection name (with indentation and toggle)
    #  - Right (70% width) for the view layer settings.
    main_row = layout.row(align=True)
    split = main_row.split(factor=0.3, align=True)
    left = split.column()
    right = split.column()

    # Left column: add indentation, toggle button, and collection name.
    left_row = left.row(align=True)
    for _ in range(level):
        left_row.label(text="", icon="BLANK1")
    icon = "TRIA_DOWN" if is_expanded else "TRIA_RIGHT"
    op = left_row.operator("wm.toggle_expand", text="", icon=icon, emboss=False)
    op.collection_name = collection.name
    left_row.label(text=collection.name, icon="OUTLINER_COLLECTION")

    # Right column: split equally among view layers.
    def draw_cell(col, vl):
        draw_collection(col, vl, collection)

    draw_right_columns(right, view_layers, draw_cell)

    # If expanded, recursively draw child collections.
    if is_expanded:
        for child in collection.children:
            draw_recursive_collections(layout, view_layers, child, level + 1)


# ------------------------------------------------------------------------------
# 5. Operators
# ------------------------------------------------------------------------------


class RENDER_MANAGER_OT_toggle_expand(bpy.types.Operator):
    """Toggle the expanded/collapsed state of a collection."""

    bl_idname = "wm.toggle_expand"
    bl_label = "Toggle Expand"
    bl_options = {"INTERNAL"}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        current_state = get_expanded_state().get(self.collection_name, False)
        set_expanded_state(self.collection_name, not current_state)
        return {"FINISHED"}


class RENDER_MANAGER_OT_collection_spreadsheet(bpy.types.Operator):
    """Popup with rows = child collections, columns = view layers."""

    bl_idname = "wm.collection_spreadsheet"
    bl_label = "Collection Manager"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        scene = context.scene
        # Clear any previous expanded state so all collections start collapsed.
        if hasattr(scene, "collection_spreadsheet_expanded"):
            scene.collection_spreadsheet_expanded.clear()
        view_layers = scene.view_layers
        num_view_layers = len(view_layers)
        base_width = 400
        column_width = 120
        total_width = base_width + num_view_layers * column_width
        max_width = context.window.width - 20
        width = min(total_width, max_width)
        return context.window_manager.invoke_props_dialog(self, width=width)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        view_layers = scene.view_layers
        if not view_layers:
            layout.label(text="No View Layers found.")
            return

        # --- HEADER ---
        header = layout.row(align=True)
        split = header.split(factor=0.3, align=True)
        left = split.column()
        right = split.column()
        left.label(text="Collections")

        def draw_header_cell(col, vl):
            col.label(text=vl.name, icon="RENDERLAYERS")

        draw_right_columns(right, view_layers, draw_header_cell)

        # --- TABLE ROWS ---
        scene_children = scene.collection.children
        if not scene_children:
            layout.label(
                text="No sub-collections under the Scene Collection.", icon="INFO"
            )
            return

        for child_coll in scene_children:
            draw_recursive_collections(layout, view_layers, child_coll)

    def execute(self, context):
        return {"FINISHED"}


# ------------------------------------------------------------------------------
# 6. Registration
# ------------------------------------------------------------------------------

classes = (
    CollectionExpandedState,
    RENDER_MANAGER_OT_toggle_expand,
    RENDER_MANAGER_OT_collection_spreadsheet,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    init_custom_properties()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "collection_spreadsheet_expanded"):
        del bpy.types.Scene.collection_spreadsheet_expanded


if __name__ == "__main__":
    register()
