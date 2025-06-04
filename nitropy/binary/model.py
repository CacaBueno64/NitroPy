from .nitro import *
from . import sbc, displaylist
from struct import unpack
from io import BytesIO
from enum import Enum
from mathutils import Matrix, Vector

from ..operators import nitro_import

class BufferCacheEntry:
    def __init__(self, shapeProxies):
        self.UseCount = 0
        self.ShapeProxies = shapeProxies
class G3dModelManager:
    def __init__(self):
        self._bufferCache = {}
    
    def InitializeRenderObject(self, renderObject, textures=None):
        if renderObject.ModelResource is None:
            return
        
        if self._bufferCache.get(renderObject.ModelResource) is None:
            shapeProxies = [None] * len(renderObject.ModelResource.Shapes.Shapes)
            for i in range(len(renderObject.ModelResource.Shapes.Shapes)):
                shapeProxies[i] = self.CreateDisplayListBuffer(renderObject.ModelResource.Shapes.Shapes[i].DisplayList)
            bufferCacheEntry = BufferCacheEntry(shapeProxies)
            self._bufferCache[renderObject.ModelResource] = bufferCacheEntry
        
        bufferCacheEntry.UseCount += 1
        renderObject.ShapeProxies = bufferCacheEntry.ShapeProxies
        
        #textures ...
    
    def CreateDisplayListBuffer(self, dl):
        return displaylist.DisplayListBuffer(dl)

class G3dRenderObject:
    def __init__(self, model):
        self.ModelResource = model
        self.Flag = 0
        self.UserSbc = None
        self.CallbackFunction = None
        self.CallbackCmd = 0
        self.CallbackTiming = 0
        self.CallbackInitFunction = None
        self.RecordedJointAnimations = None
        self.JointAnimations = None
        self.MaterialAnimations = None
        self.VisibilityAnimations = None
        self.MaterialAnimationMayExist = [False] * G3dConfig.MaxMaterialCount
        self.JointAnimationMayExist = [False] * G3dConfig.MaxJointCount
        self.VisibilityAnimationMayExist = [False] * G3dConfig.MaxJointCount
    
    def TestFlag(self, flag) -> bool:
        return self.Flag & flag == flag

class G3dGlobalState:
    def __init__(self):
        self.CameraMatrix = Matrix.Identity(4)
        self.MaterialColor0 = 0x4210C210
        self.MaterialColor1 = 0x4210C210
        self.PolygonAttr = GxPolygonAttr(0)
        self.PolygonAttr.LightMask = 0xF
        self.PolygonAttr.PolygonMode = GxPolygonMode.Modulate
        self.PolygonAttr.GxCull = GxCull.Back
        self.PolygonAttr.PolygonId = 0
        self.PolygonAttr.Alpha = 31
        self.BaseTrans = Vector([0.0, 0.0, 0.0])
        self.BaseRot = Matrix.Identity(3)
        self.BaseScale = Vector([1.0, 1.0, 1.0])
        self.TexImageParam = None
    
    def FlushP(self, geState):
        geState.LoadMatrix(self.CameraMatrix)
        geState.MaterialColor0 = self.MaterialColor0
        geState.MaterialColor1 = self.MaterialColor1
        geState.MultMatrix(Matrix([
            self.BaseRot[0],
            self.BaseRot[1],
            self.BaseRot[2],
            self.BaseTrans]))
        geState.Scale(self.BaseScale)
        geState.TexImageParam = self.TexImageParam

class G3dGlobalRenderState:
    def __init__(self):
        self.MaterialCache = [MaterialAnimationResult()] * G3dConfig.MaxMaterialCount
        self.ScaleCache = [self.ScaleCacheEntry()] * G3dConfig.MaxJointCount
        self.EnvelopeCache = [self.EnvelopeCacheEntry()] * G3dConfig.MaxJointCount
    class ScaleCacheEntry:
        def __init__(self):
            self.Scale = Vector([0.0, 0.0, 0.0])
            self.InverseScale = Vector([0.0, 0.0, 0.0])
    class EnvelopeCacheEntry:
        def __init__(self):
            self.PositionMtx = Matrix.Identity(4)
            self.DirectionMtx = Matrix.Identity(3)

class RenderContext:
    def __init__(self, geState):
        self.GeState = geState
        self.GlobalRenderState = G3dGlobalRenderState()
        self.GlobalState = G3dGlobalState()
        self.Sbc = sbc.Sbc(self)
        self.RenderState = None
        self.GetJointScaleFuncArray = [
            Basic.GetJointScale,
            Maya.GetJointScale,
            Si3d.GetJointScale,
        ]
        self.SendJointSrtFuncArray = [
            Basic.SendJointSrt,
            Maya.SendJointSrt,
            Si3d.SendJointSrt,
        ]
        self.SendTexSrtFuncArray = [
            Maya.SendTextureSrt,
            Si3d.SendTextureSrt,
            None, #3dsMax
            None, #Xsi
        ]
    
    def RenderShp(self, shp, buffer):
        nitro_import.render_shp(shp, buffer)

class GeometryEngineState:
    MATERIAL_COLOR_1_SHININESS_FLAG = 0x8000

    def __init__(self):
        self.TranslucentPass = False
        self.PolygonAttr = 0x1F008F
        self.TexImageParam = None
        self.MaterialColor0 = 0x2108A108
        self.MaterialColor1 = 0x2108A108
        
        self.MatrixMode = GxMtxMode.PositionVector

        self._positionMatrixStack = [Matrix.Identity(4)] * 31
        self._directionMatrixStack = [Matrix.Identity(3)] * 31
        self._textureMatrixStack = Matrix.Identity(4)

        self.PositionMatrix = Matrix.Identity(4)
        self.DirectionMatrix = Matrix.Identity(3)
        self._textureMatrix = Matrix.Identity(4)

        self.TexCoord = Vector([0.0, 0.0])
    
    def Translate(self, translation):
        m = Matrix.Translation(translation)
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self.PositionMatrix @= m
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrix @= m
    def Scale(self, scale):
        m = Matrix.Scale(scale.x, 4, Vector((1, 0, 0))) @ \
            Matrix.Scale(scale.y, 4, Vector((0, 1, 0))) @ \
            Matrix.Scale(scale.z, 4, Vector((0, 0, 1)))
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self.PositionMatrix @= m
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrix @= m
    def LoadMatrix(self, mtx):
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self.PositionMatrix = mtx
        if self.MatrixMode == GxMtxMode.PositionVector:
            self.DirectionMatrix = mtx
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrix = mtx
    def MultMatrix(self, mtx):
        if len(mtx.row) == 3 and len(mtx.col) == 3:
            mtx = mtx.to_4x4()
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self.PositionMatrix @= mtx
        if self.MatrixMode == GxMtxMode.PositionVector:
            self.DirectionMatrix @= mtx
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrix @= mtx
    def RestoreMatrix(self, index):
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self.PositionMatrix = self._positionMatrixStack[index]
            self.DirectionMatrix = self._directionMatrixStack[index]
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrix = self._textureMatrixStack
    def StoreMatrix(self, index):
        if self.MatrixMode == GxMtxMode.Position or self.MatrixMode == GxMtxMode.PositionVector:
            self._positionMatrixStack[index] = self.PositionMatrix
            self._directionMatrixStack[index] = self.DirectionMatrix
        if self.MatrixMode == GxMtxMode.Texture:
            self._textureMatrixStack = self._textureMatrix

class G3dModelRenderer:
    def __init__(self):
        self._geState = GeometryEngineState()
        self._renderContext = RenderContext(self._geState)
        self.RenderObj = None
        self.BaseScale = Vector([16.0, 16.0, 16.0])
        self.MultMatrix = Matrix.Identity(4)
        self.Scale = Vector([0.0, 0.0, 0.0])
    
    def Render(self):
        self._renderContext.GlobalState.BaseTrans = Vector([0.0, 0.0, 0.0])
        self._renderContext.GlobalState.BaseRot = Matrix.Identity(3)
        self._renderContext.GlobalState.BaseScale = self.BaseScale
        
        self._renderContext.GlobalState.FlushP(self._geState)
        
        self._renderContext.GeState.MultMatrix(self.MultMatrix)
        self._renderContext.GeState.Scale(self.Scale)
        
        self._renderContext.Sbc.Draw(self.RenderObj)

class ModelRenderGroup:
    def __init__(self, nsbmd):
        self._renderer = None
        self._renderObj = None
        self._modelManager = G3dModelManager()
        self.nsbmd = nsbmd
        self.model = None
    
    def InitModel(self):
        self._renderer = G3dModelRenderer()
        self.model = self.nsbmd.ModelSet.Models[0]
        self._renderObj = G3dRenderObject(self.model)
        self._modelManager.InitializeRenderObject(self._renderObj)
    
    def Render(self):
        self._renderer.RenderObj = self._renderObj
        self._renderer.Render()

#with open("./models/eff10355010.nsbmd", "rb") as file:
#    nsbmd = Nsbmd(BytesIO(file.read()))
#    test = ModelRenderGroup(nsbmd)
#    test.InitModel()
#    test.Render()
