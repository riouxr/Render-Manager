bl_info = {
    "name": "Render Manager",
    "author": "BlenderBob, TinkerBoi, MJ",
    "version": (3, 0, 11),
    "blender": (4, 2, 0),
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

def register():
    for module in modules:
        try:
            module.register()
        except Exception as e:
            print(f"Error registering module {module.__name__}: {e}")

def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except Exception as e:
            print(f"Error unregistering module {module.__name__}: {e}")

if __name__ == "__main__":
    register()
