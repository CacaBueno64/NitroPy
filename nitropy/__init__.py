import bpy
import pip
from .operators import *

if "nitro_import" in locals():
    importlib.reload(nitro_import)
    importlib.reload(nsbmd)

bl_info = {
        "name": "NitroPy",
        "category": "Import-Export",
        "description": "Imports nitro binary files from nds games.",
        "author": "Isma | @cacabueno (discord), @cacabueno64 (github)",
        "version": (0, 1),
        "blender": (2, 80, 0),
        "location": "Properties > Import-Export > NitroPy",
        "warning": "",
        "doc_url": "",
        "support": "COMMUNITY",
        }

class Nitro_Menu_Import(bpy.types.Menu):
    bl_label = "NitroPy (.nsbmd)"
    bl_idname = "TOPBAR_MT_file_nitro_import"
    
    def draw(self, context):
        layout = self.layout
        layout.operator(ImportNitro.bl_idname, text="Model (.nsbmd)", icon="MESH_DATA")

def draw_menu_import(self, context):
    self.layout.menu(Nitro_Menu_Import.bl_idname)

def register():
    bpy.utils.register_class(Nitro_Menu_Import)
    bpy.utils.register_class(ImportNitro)
    bpy.types.TOPBAR_MT_file_import.append(draw_menu_import)

def unregister():
    bpy.utils.unregister_class(Nitro_Menu_Import)
    bpy.utils.unregister_class(ImportNitro)
    bpy.types.TOPBAR_MT_file_import.remove(draw_menu_import)

if __name__ == "__main__":
    register()