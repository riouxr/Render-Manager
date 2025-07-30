bl_info = {
    "name": "Render Manager",
    "author": "BlenderBob, TinkerBoi, MJ",
    "version": (2, 0, 0),
    "blender": (4, 1, 0),
    "description": "Manage render visibility, passes, collections and node-based file outputs",
    "warning": "",
    "location": "Properties > View Layer",
    "wiki_url": "",
    "category": "Render",
}

import bpy
from . import LayerManager
from . import CollectionManager

modules = [
    LayerManager,
    CollectionManager,
]

class RENDER_MANAGER_PT_view_layer(bpy.types.Panel):
    bl_label = "Render Manager"
    bl_idname = "RENDER_MANAGER_PT_view_layer"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "view_layer"

    def draw(self, context):
        layout = self.layout
        layout.operator("render_manager.collection_spreadsheet", text="Collection Manager")

def register():
    for module in modules:
        try:
            module.register()
        except Exception as e:
            print(f"Error registering module {module.__name__}: {e}")
    bpy.utils.register_class(RENDER_MANAGER_PT_view_layer)

def unregister():
    bpy.utils.unregister_class(RENDER_MANAGER_PT_view_layer)
    for module in reversed(modules):
        try:
            module.unregister()
        except Exception as e:
            print(f"Error unregistering module {module.__name__}: {e}")

if __name__ == "__main__":
    register()