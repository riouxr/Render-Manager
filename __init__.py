bl_info = {
    "name": "Render Manager",
    "author": "BlenderBob, TinkerBoi, MJ",
    "version": (1, 1, 1),
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


def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()


if __name__ == "__main__":
    register()
