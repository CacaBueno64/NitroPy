from struct import unpack, unpack_from, Struct, calcsize, pack
from mathutils import Matrix, Vector
import math
from enum import Enum

def ReadSignature(reader, expected):
    signature = unpack("<I", reader.read(4))[0]
    if signature != expected:
        raise Exception(f"Expected signature : {expected}, got : {signature}")
    return signature

class G3dFileHeader:
    def __init__(self, reader, expectedSignature):
        self.Signature, self.ByteOrder, self.Version, self.FileSize, self.HeaderSize, self.NrBlocks = \
            unpack("<IHHIHH", reader.read(16))
        if self.Signature != expectedSignature:
            raise Exception(f"Expected signature : {expectedSignature}, got : {self.Signature}")
        self.BlockOffsets = [unpack("<I", reader.read(4))[0] for i in range(self.NrBlocks)]

class G3dDictionary:
    def __init__(self, reader, TData):
        self.Data = []
        G3dDictionarySerializer.ReadG3dDictionary(reader, self, TData)
    
    def Add(self, name, data):
        self.Data.append(G3dDictionaryEntry(name, data))
    
    def __len__(self):
        return len(self.Data)

class G3dDictionaryEntry:
    def __init__(self, name, data):
        self.Name = name
        self.Data = data

class G3dDictionarySerializer:
    @staticmethod
    def ReadG3dDictionary(reader, dictionary, TData):
        startPosition = reader.tell()
        revision = unpack("<B", reader.read(1))[0]
        entryCount = unpack("<B", reader.read(1))[0]
        dictionarySize = unpack("<H", reader.read(2))[0]
        reader.read(2)
        entriesOffset = unpack("<H", reader.read(2))[0]
        if revision != 0:
            raise Exception(f"Unsupported dictionary revision. Got {revision}, expected 0.")
        reader.seek(startPosition + entriesOffset)
        entrySize = unpack("<H", reader.read(2))[0]
        namesOffset = unpack("<H", reader.read(2))[0]
        if entrySize != TData.DataSize:
            raise Exception(f"Dictionary entry size mismatch. Got {entrySize}, expected {TData.DataSize}.")
        data = [TData(reader) for i in range(entryCount)]
        reader.seek(startPosition + entriesOffset + namesOffset)
        for i in range(entryCount):
            name = reader.read(16).decode("shift-jis")
            dictionary.Add(name, data[i])
        reader.seek(startPosition + dictionarySize)

class OffsetDictionaryData:
    DataSize = 4
    def __init__(self, reader):
        self.Offset = unpack("<I", reader.read(4))[0]
class TextureToMaterialDictionaryData:
    DataSize = 4
    def __init__(self, reader):
        self.Materials = []
        self.flags = unpack("<I", reader.read(4))[0]
        self.Offset = self.flags & 0xFFFF
        self.MaterialCount = self.flags >> 16 & 0x7F
        self.Bound = self.flags >> 24 & 0xFF
class PaletteToMaterialDictionaryData:
    DataSize = 4
    def __init__(self, reader):
        self.Materials = []
        self.flags = unpack("<I", reader.read(4))[0]
        self.Offset = self.flags & 0xFFFF
        self.MaterialCount = self.flags >> 16 & 0x7F
        self.Bound = self.flags >> 24 & 0xFF
class TextureDictionaryData:
    DataSize = 8
    def __init__(self, reader):
        ParamExOrigWMask = 0x000007ff
        ParamExOrigHMask = 0x003ff800
        ParamExWHSameMask = 0x80000000
        ParamExOrigWShift = 0
        ParamExOrigHShift = 11
        ParamExWHSameShift = 31
        
        self.TexImageParam = GxTexImageParam(unpack("<I", reader.read(4))[0])
        self.ExtraParam = unpack("<I", reader.read(4))[0]
class PaletteDictionaryData:
    DataSize = 4
    def __init__(self, reader):
        self.Offset = unpack("<H", reader.read(2))[0]
        self.Flags = unpack("<H", reader.read(2))[0]

class G3dConfig:
    MaxJointCount = 64
    MaxMaterialCount = 64
    MaxShpCount = 64

class GxPolygonAttr:
    def __init__(self, value):
        self._value = value
        self.LightMask = self._value & 0xF
        self.PolygonMode = GxPolygonMode((self._value >> 4) & 3)
        self.CullMode = GxCull((self._value >> 6) & 3)
        self.TranslucentDepthUpdate: bool = (self._value & (1 << 11)) != 0
        self.FarClip: bool = (self._value & (1 << 12)) != 0
        self.Render1Dot: bool = (self._value & (1 << 13)) != 0
        self.DepthEquals: bool = (self._value & (1 << 14)) != 0
        self.FogEnable: bool = (self._value & (1 << 15)) != 0
        self.Alpha = (self._value >> 16) & 0x1F
        self.PolygonId = (self._value >> 24) & 0x3F

class GxTexImageParam:
    def __init__(self, value):
        self._value = value
        self.Address = self._value & 0xFFFF
        self.RepeatS: bool = (self._value & (1 << 16)) != 0
        self.RepeatT: bool = (self._value & (1 << 17)) != 0
        self.FlipS: bool = (self._value & (1 << 18)) != 0
        self.FlipT: bool = (self._value & (1 << 19)) != 0
        self.Width = (self._value >> 20) & 7
        self.Height = (self._value >> 23) & 7
        self.Format = ImageFormat((self._value >> 26) & 7)
        self.Color0Transparent: bool = (self._value & (1 << 29)) != 0
        self.TexGen = GxTexGen((self._value >> 30) & 3)

class GxPolygonMode(Enum):
    Modulate      = 0
    Decal         = 1
    ToonHighlight = 2
    Shadow        = 3
class GxCull(Enum):
    All   = 0
    Front = 1
    Back  = 2
    Null  = 3
class GxTexGen(Enum):
    Null = 0
    TexCoord = 1
    Normal = 2
    Vertex = 3
class GxMtxMode(Enum):
    Projection     = 0
    Position       = 1
    PositionVector = 2
    Texture        = 3

class ImageFormat(Enum):
    Null = 0
    A3I5 = 1
    Pltt4 = 2
    Pltt16 = 3
    Pltt256 = 4
    Comp4x4 = 5
    A5I3 = 6
    Direct = 7
class CharFormat(Enum):
    Char = 0
    Bmp = 1
class MapFormat(Enum):
    Text = 0
    Affine = 1
class ColorFormat:
    def __init__(self, aShift, aSize, rShift, rSize, gShift, gSize, bShift, bSize):
        self.AShift = aShift
        self.ASize = aSize
        self.RShift = rShift
        self.RSize = rSize
        self.GShift = gShift
        self.GSize = gSize
        self.BShift = bShift
        self.BSize = bSize
    @property
    def NrBytes(self):
        return math.ceil((self.ASize + self.RSize + self.GSize + self.BSize) / 8)
    def __eq__(self, other):
        if not isinstance(other, ColorFormat):
            return False
        return (
            self.AShift == other.AShift and \
            self.ASize == other.ASize and \
            self.RShift == other.RShift and \
            self.RSize == other.RSize and \
            self.GShift == other.GShift and \
            self.GSize == other.GSize and \
            self.BShift == other.BShift and \
            self.BSize == other.BSize
        )

class G3dRenderObjectFlag(Enum):
    Record         = 0x00000001
    NoGeCmd        = 0x00000002
    SkipSbcDraw    = 0x00000004
    SkipSbcMtxCalc = 0x00000008
    HintObsolete   = 0x00000010

class G3dRenderStateFlag(Enum):
    NodeVisible = 0x00000001
    MaterialTransparent = 0x00000002
    CurrentNodeValid = 0x00000004
    CurrentMaterialValid = 0x00000008
    CurrentNodeDescriptionValid = 0x00000010
    Return = 0x00000020
    Skip = 0x00000040

    OptRecord = 0x00000080
    OptNoGeCmd = 0x00000100
    OptSkipSbcDraw = 0x00000200
    OptSkipSbcMtxCalc = 0x00000400

class Rgba8Bitmap:
    def __init__(self, width, height, data=[]):
        self.Width = width
        self.Height = height
        self.Pixels = data
    
    #def ToPngFile(self, filepath):
    #    data = [tuple(self.Pixels[i:i+3]) for i in range(0, len(self.Pixels), 4)]
    #    image = Image.new("RGBA", (self.Width, self.Height))
    #    image.putdata(self.Pixels)
    #    image.save(filepath)


def ReadFx16(reader):
    return unpack("<h", reader.read(2))[0] / 4096.0
def ReadFx16s(reader, count):
    return [ReadFx16(reader) for i in range(count)]
def ReadVecFx16(reader):
    return [ReadFx16(reader) for i in range(3)]
FX32_SHIFT = 12
def ReadFx32(reader):
    return unpack("<i", reader.read(4))[0] / 4096.0
def ReadFx32s(reader, count):
    return [ReadFx32(reader) for i in range(count)]
def ReadVecFx32(reader):
    return [ReadFx32(reader) for i in range(3)]

PivotUtil = [
    [4, 5, 7, 8],
    [3, 5, 6, 8],
    [3, 4, 6, 7],

    [1, 2, 7, 8],
    [0, 2, 6, 8],
    [0, 1, 6, 7],

    [1, 2, 4, 5],
    [0, 2, 3, 5],
    [0, 1, 3, 4],
]
def DecodePivotRotation(pivotIdx, pivotNeg, signRevC, signRevD, a, b):
    mtx = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    
    def Set(idx, value):
        mtx[idx // 3][idx % 3] = value
    
    Set(pivotIdx, -1.0 if pivotNeg else 1.0)
    
    Set(PivotUtil[pivotIdx][0], a)
    Set(PivotUtil[pivotIdx][1], b)
    
    Set(PivotUtil[pivotIdx][2], -b if signRevC else b)
    Set(PivotUtil[pivotIdx][3], -a if signRevD else a)
    
    return mtx


class JointAnimationResultFlag:
    ScaleOne = 0x01
    RotationZero = 0x02
    TranslationZero = 0x04
    ScaleEx0One = 0x08
    ScaleEx1One = 0x10
    MayaSsc = 0x20

class Maya:
    @staticmethod
    def SendJointSrt(animationResult, context):
        pass
    @staticmethod
    def GetJointScale(animationResult, nodeData, sbc, ptr, context):
        pass
    @staticmethod
    def SendTextureSrt(animationResult, context):
        pass
    @staticmethod
    def CalculateTextureMatrix(matrix, animationResult):
        pass
class Basic:
    @staticmethod
    def SendJointSrt(animationResult, context):
        pass
    @staticmethod
    def GetJointScale(animationResult, nodeData, sbc, ptr, context):
        pass
class Si3d:
    @staticmethod
    def SendJointSrt(animationResult, context):
        trFlag = False
        flagScaleEx = animationResult.Flag & (JointAnimationResultFlag.ScaleEx0One | JointAnimationResultFlag.ScaleEx1One)
        if not flagScaleEx:
            context.GeState.Scale(animationResult.ScaleEx1)
        if not animationResult.Flag & JointAnimationResultFlag.TranslationZero:
            if not flagScaleEx:
                tmp = Vector([
                animationResult.Translation.x * animationResult.ScaleEx0.x,
                animationResult.Translation.y * animationResult.ScaleEx0.y,
                animationResult.Translation.z * animationResult.ScaleEx0.z])
                context.GeState.Translate(tmp)
            else:
                trFlag = True
        if not animationResult.Flag & JointAnimationResultFlag.RotationZero:
            if trFlag:
                context.GeState.MultMatrix(Matrix([
                    animationResult.Rotation[0], animationResult.Rotation[1], animationResult.Rotation[2],
                    animationResult.Translation]))
            else:
                context.GeState.MultMatrix(animationResult.Rotation)
        else:
            if trFlag:
                context.GeState.Translation(animationResult.Translation)
        if not flagScaleEx:
            context.GeState.Scale(animationResult.ScaleEx0)
        if not animationResult.Flag & JointAnimationResultFlag.ScaleOne:
            context.GeState.Scale(animationResult.Scale)
    
    @staticmethod
    def GetJointScale(animationResult, nodeData, sbc, ptr, context):
        nodeId = unpack("<B", sbc[ptr+1:ptr+2])[0]
        parentId = unpack("<B", sbc[ptr+2:ptr+3])[0]
        if nodeData.Flags & nodeData.FLAGS_SCALE_ONE != 0:
            nodeData.Flags |= JointAnimationResultFlag.ScaleOne
            if context.RenderState.IsScaleCacheOne[parentId]:
                context.RenderState.IsScaleCacheOne[nodeId] = True
                nodeData.Flags |= (JointAnimationResultFlag.ScaleEx0One | JointAnimationResultFlag.ScaleEx1One)
            else:
                context.GlobalRenderState.ScaleCache[nodeId] = context.GlobalRenderState.ScaleCache[parentId]
                animationResult.ScaleEx0 = context.GlobalRenderState.ScaleCache[parentId].Scale
        else:
            animationResult.Scale = nodeData.Scale
            if context.RenderState.IsScaleCacheOne[parentId]:
                context.GlobalRenderState.ScaleCache[nodeId].Scale = nodeData.Scale
                context.GlobalRenderState.ScaleCache[nodeId].InverseScale = nodeData.InverseScale
                context.RenderState.IsScaleCacheOne[nodeId] = False
                nodeData.Flags |= (JointAnimationResultFlag.ScaleEx0One | JointAnimationResultFlag.ScaleEx1One)
            else:
                context.RenderState.IsScaleCacheOne[nodeId] = False
                
                context.GlobalRenderState.ScaleCache[nodeId].Scale.x = \
                    nodeData.Scale.x * context.GlobalRenderState.ScaleCache[parentId].Scale.x
                context.GlobalRenderState.ScaleCache[nodeId].Scale.y = \
                    nodeData.Scale.y * context.GlobalRenderState.ScaleCache[parentId].Scale.y
                context.GlobalRenderState.ScaleCache[nodeId].Scale.z = \
                    nodeData.Scale.z * context.GlobalRenderState.ScaleCache[parentId].Scale.z
                context.GlobalRenderState.ScaleCache[nodeId].InverseScale.x = \
                    nodeData.InverseScale.x * context.GlobalRenderState.ScaleCache[parentId].InverseScale.x
                context.GlobalRenderState.ScaleCache[nodeId].InverseScale.y = \
                    nodeData.InverseScale.y * context.GlobalRenderState.ScaleCache[parentId].InverseScale.y
                context.GlobalRenderState.ScaleCache[nodeId].InverseScale.z = \
                    nodeData.InverseScale.z * context.GlobalRenderState.ScaleCache[parentId].InverseScale.z
                
                context.GlobalRenderState.ScaleCache[parentId].Scale = animationResult.ScaleEx0
                context.GlobalRenderState.ScaleCache[parentId].InverseScale = animationResult.ScaleEx1
    
    @staticmethod
    def SendTextureSrt(animationResult, context):
        pass


class MaterialAnimationResult:
    def __init__(self):
        self.Flag = 0
        self.PrmMatColor0 = 0
        self.PrmMatColor1 = 0
        self.PrmPolygonAttr = 0
        self.PrmTexImage = 0
        self.PrmTexPltt = 0
        self.ScaleS = 0
        self.ScaleT = 0
        self.RotationSin = 0
        self.RotationCos = 0
        self.TranslationS = 0
        self.TranslationT = 0
        self.OriginalWidth = 0
        self.OriginalHeight = 0
        self.MagW = 0
        self.MagH = 0
        self.TextureInfo = None
    def Clear(self):
        self.Flag = 0
        self.PrmMatColor0 = 0
        self.PrmMatColor1 = 0
        self.PrmPolygonAttr = 0
        self.PrmTexImage = 0
        self.PrmTexPltt = 0
        self.ScaleS = 0
        self.ScaleT = 0
        self.RotationSin = 0
        self.RotationCos = 0
        self.TranslationS = 0
        self.TranslationT = 0
        self.OriginalWidth = 0
        self.OriginalHeight = 0
        self.MagW = 0
        self.MagH = 0
        self.TextureInfo = None
class JointAnimationResult:
    def __init__(self):
        self.Flag = 0
        self.Scale = Vector([0.0, 0.0, 0.0])
        self.ScaleEx0 = Vector([0.0, 0.0, 0.0])
        self.ScaleEx1 = Vector([0.0, 0.0, 0.0])
        self.Rotation = Matrix([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        self.Translation = Vector([0.0, 0.0, 0.0])
    def Clear(self):
        self.Flag = 0
        self.Scale = Vector([0.0, 0.0, 0.0])
        self.ScaleEx0 = Vector([0.0, 0.0, 0.0])
        self.ScaleEx1 = Vector([0.0, 0.0, 0.0])
        self.Rotation = Matrix([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        self.Translation = Vector([0.0, 0.0, 0.0])
class VisibilityAnimationResult:
    def __init__(self):
        self.IsVisible = False
    def Clear(self):
        self.IsVisible = False



# the one and only
def Short(value):
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value
