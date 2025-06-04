import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty

from ..binary import nsbmd, model

def axis_convert(v):
    x, y, z = (v[0], v[1], v[2])
    return [x, -z, y]

def vertex_colors(vertex):
    x, y, z = vertex
    return [x, y, z, 1.0]

def render_shp(shp, buffer):
    mesh_name = "test"
    mesh = bpy.data.meshes.new(name=mesh_name)
    mesh_obj = bpy.data.objects.new(name=mesh_name, object_data=mesh)
    bpy.context.collection.objects.link(mesh_obj)
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    verts = []
    for i in range(len(buffer._vtxData)):
        verts.append(axis_convert(buffer._vtxData[i].Position))
    
    mesh.from_pydata(verts, [], buffer._idxData)

def open_nitro(context, filepath):
    filedata = open(filepath, "rb")
    
    if filepath.endswith(".nsbmd"):
        modeldata = nsbmd.Nsbmd(reader=filedata)
        rendergroup = model.ModelRenderGroup(modeldata)
        rendergroup.InitModel()
        rendergroup.Render()

class ImportNitro(bpy.types.Operator, ImportHelper):
    bl_idname = "import.nsbmd"
    bl_label = "Import a .nsbmd"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".nsbmd"
    filter_glob: StringProperty(default="*.nsbmd", options={'HIDDEN'})
    
    def execute(self, context):
        open_nitro(context, self.filepath)
        return {'FINISHED'}
