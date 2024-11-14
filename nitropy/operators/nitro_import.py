import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty

from ..binary import nsbmd

def open_nitro(context, filepath):
    filedata = open(filepath, "rb")
    
    if filepath.endswith(".nsbmd"):
        nsbmd.NSBMD(reader=filedata)

class ImportNitro(bpy.types.Operator, ImportHelper):
    bl_idname = "import.nsbmd"
    bl_label = "Import a .nsbmd"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".nsbmd"
    filter_glob: StringProperty(default="*.nsbmd", options={'HIDDEN'})
    
    def execute(self, context):
        open_nitro(context, self.filepath)
        return {'FINISHED'}