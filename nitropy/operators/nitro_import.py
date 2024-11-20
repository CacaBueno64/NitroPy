import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty

from ..binary import nsbmd, gxcommands

def triangulate(strips):
    triangles = []

    for strip in strips:
        if len(strip) < 3: continue
        i = strip.__iter__()
        j = False
        t1, t2 = next(i), next(i)
        for k in range(2, len(strip)):
            j = not j
            t0, t1, t2 = t1, t2, next(i)
            if t0 == t1 or t1 == t2 or t2 == t0: continue
            triangles.append((t0, t1, t2) if j else (t0, t2, t1))

    return triangles

def axis_convert(vertex):
    x, y, z = vertex
    return [x, -z, y]

def vertex_colors(vertex):
    x, y, z = vertex
    return [x, y, z, 1.0]

def make_mesh(model):
    for i in range(model.ModelSet.Dictionary.Count()):
        mesh_name = model.ModelSet.Dictionary.Data[i].Name
        
        mesh = bpy.data.meshes.new(name=mesh_name)
        mesh_obj = bpy.data.objects.new(name=mesh_name, object_data=mesh)
        bpy.context.collection.objects.link(mesh_obj)
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        dl = gxcommands.DisplayListBuffer(model.ModelSet.Models[i].Shapes.Shapes[0].DisplayList)
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
                if dl.useNormal:
                    normals.append(vertex.NormalOrColor)
                else:
                    colors.append(vertex.NormalOrColor)
            if vertex.TexCoord:
                texcoords.append(vertex.TexCoord)
        
        mesh.from_pydata(positions, [], triangulate([indices]))
        
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
        make_mesh(modeldata)

class ImportNitro(bpy.types.Operator, ImportHelper):
    bl_idname = "import.nsbmd"
    bl_label = "Import a .nsbmd"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".nsbmd"
    filter_glob: StringProperty(default="*.nsbmd", options={'HIDDEN'})
    
    def execute(self, context):
        open_nitro(context, self.filepath)
        return {'FINISHED'}
