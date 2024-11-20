import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty

from ..binary import nsbmd, gxcommands

def axis_convert(vertex):
    x, y, z = vertex
    return [x, -z, y]

def vertex_colors(vertex):
    x, y, z = vertex
    return [x, y, z, 1.0]

def make_model(model):
    for i in range(model.ModelSet.Dictionary.Count()):
        
        model_name = model.ModelSet.Dictionary.Data[i].Name
        
        for j in range(model.ModelSet.Models[i].Shapes.ShapeDictionary.Count()):
            
            mesh_name = model.ModelSet.Models[i].Shapes.ShapeDictionary.Data[j].Name
            
            mesh = bpy.data.meshes.new(name=mesh_name)
            mesh_obj = bpy.data.objects.new(name=mesh_name, object_data=mesh)
            bpy.context.collection.objects.link(mesh_obj)
            bpy.context.view_layer.objects.active = mesh_obj
            mesh_obj.select_set(True)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            dl = gxcommands.DisplayListBuffer(model.ModelSet.Models[i].Shapes.Shapes[j].DisplayList)
            vertices = dl._vtxData
            indices = dl._idxData
            
            positions = []
            normals = []
            colors = []
            texcoords = []
            for vertex in vertices:
                if vertex.Position:
                    positions.append(axis_convert(vertex.Position))
                if vertex.NormalOrColor:
                    if dl.mtxId != 0:
                        normals.append(vertex.NormalOrColor)
                        colors.append([0.0, 0.0, 0.0, 1.0])
                    else:
                        colors.append(vertex_colors(vertex.NormalOrColor))
                        normals.append([0.0, 0.0, 0.0])
                if vertex.TexCoord:
                    texcoords.append(vertex.TexCoord)
            
            triangles = [indices[k:k + 3] for k in range(0, len(indices), 3)]
            mesh.from_pydata(positions, [], triangles)
            mesh.validate()
            mesh.update()
            
            if normals:
                mesh.normals_split_custom_set_from_vertices(normals)
            
            if colors:
                color_layer = mesh.vertex_colors.new(name="Col")
                for loop_idx, color in enumerate(colors):
                    color_layer.data[loop_idx].color = color
            
            if texcoords:
                uv_layer = mesh.uv_layers.new(name="UVMap")
                for loop in mesh.loops:
                    vertex_index = loop.vertex_index
                    if vertex_index < len(texcoords):
                        uv_layer.data[loop.index].uv = texcoords[vertex_index]

def open_nitro(context, filepath):
    filedata = open(filepath, "rb")
    
    if filepath.endswith(".nsbmd"):
        modeldata = nsbmd.Nsbmd(reader=filedata)
        make_model(modeldata)

class ImportNitro(bpy.types.Operator, ImportHelper):
    bl_idname = "import.nsbmd"
    bl_label = "Import a .nsbmd"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".nsbmd"
    filter_glob: StringProperty(default="*.nsbmd", options={'HIDDEN'})
    
    def execute(self, context):
        open_nitro(context, self.filepath)
        return {'FINISHED'}
