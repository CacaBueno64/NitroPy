from struct import unpack, unpack_from, calcsize
from io import BytesIO
from enum import Enum
import numpy as np
from nitro import *
from nsbtx import *

class Nsbmd:
    Bmd0Signature = 0x30444D42
    def __init__(self, data):
        if isinstance(data, type(BytesIO())):
            self.Read(data)
    def Read(self, data):
        Bmd0Signature = self.Bmd0Signature
        Header = G3dFileHeader(data=data, expectedSignature=Bmd0Signature)
        if Header.NrBlocks > 0:
            data.seek(Header.BlockOffsets[0])
            self.ModelSet = G3dModelSet(data)
        if Header.NrBlocks > 1:
            pass # Texture

class G3dModelSet:
    Mdl0Signature = 0x304C444D
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        signature = ReadSignature(data, self.Mdl0Signature)
        sectionSize = unpack("<I", data.read(4))[0]
        Dictionary = G3dDictionary(data).dictionary
        self.Models = [None] * len(Dictionary)
        for i in range(len(Dictionary)):
            data.seek(BeginChunk + Dictionary[i][1])
            self.Models[i] = G3dModel(data)

class G3dModel:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        Size = unpack("<I", data.read(4))[0]
        SbcOffset = unpack("<I", data.read(4))[0]
        MaterialsOffset = unpack("<I", data.read(4))[0]
        ShapesOffset = unpack("<I", data.read(4))[0]
        EnvelopeMatricesOffset = unpack("<I", data.read(4))[0]
        self.Info = G3dModelInfo(data)
        self.Nodes = G3dNodeSet(data)
        data.seek(BeginChunk + SbcOffset)
        self.Sbc = []
        for i in range(MaterialsOffset - SbcOffset):
            self.Sbc.append(unpack("<B", data.read(1))[0])
        data.seek(BeginChunk + MaterialsOffset)
        self.Materials = G3dMaterialSet(data)
        data.seek(BeginChunk + ShapesOffset)
        self.Shapes = G3dShapeSet(data)
        if EnvelopeMatricesOffset != Size and EnvelopeMatricesOffset != 0:
            data.seek(BeginChunk + EnvelopeMatricesOffset)
            self.EnvelopeMatrices = G3dEnvelopeMatrices(data, len(self.Nodes.Data))

class G3dModelInfo:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        data.read(3)
        self.NodeCount = unpack("<B", data.read(1))[0]
        self.MaterialCount = unpack("<B", data.read(1))[0]
        self.ShapeCount = unpack("<B", data.read(1))[0]
        data.read(2)
        self.PosScale = Fx32(data)
        self.InversePosScale = Fx32(data)
        self.VertexCount = unpack("<H", data.read(2))[0]
        self.PolygonCount = unpack("<H", data.read(2))[0]
        self.TriangleCount = unpack("<H", data.read(2))[0]
        self.QuadCount = unpack("<H", data.read(2))[0]
        
        self.BoxX = Fx16(data)
        self.BoxY = Fx16(data)
        self.BoxZ = Fx16(data)
        self.BoxW = Fx16(data)
        self.BoxH = Fx16(data)
        self.BoxD = Fx16(data)
        self.BoxPosScale = Fx32(data)
        self.BoxInversePosScale = Fx32(data)

class G3dNodeSet:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        NodeDictionary = G3dDictionary(data).dictionary
        self.Data = [None] * len(NodeDictionary)
        curpos = data.tell()
        for i in range(len(NodeDictionary)):
            data.seek(BeginChunk + NodeDictionary[i][1])
            self.Data[i] = G3dNodeData(data)
        data.seek(curpos)

class G3dNodeData:
    FLAGS_TRANSLATION_ZERO = 0x0001
    FLAGS_ROTATION_ZERO = 0x0002
    FLAGS_SCALE_ONE = 0x0004
    FLAGS_ROTATION_PIVOT = 0x0008
    FLAGS_ROTATION_PIVOT_INDEX_MASK = 0x00F0
    FLAGS_ROTATION_PIVOT_INDEX_SHIFT = 4
    FLAGS_ROTATION_PIVOT_NEGATIVE = 0x0100
    FLAGS_ROTATION_PIVOT_SIGN_REVERSE_C = 0x0200
    FLAGS_ROTATION_PIVOT_SIGN_REVERSE_D = 0x0400
    FLAGS_MATRIX_STACK_INDEX_MASK = 0xF800
    FLAGS_MATRIX_STACK_INDEX_SHIFT = 11
    FLAGS_IDENTITY = FLAGS_TRANSLATION_ZERO | FLAGS_ROTATION_ZERO | FLAGS_SCALE_ONE

    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        self.Flags = unpack("<H", data.read(2))[0]
        self._00 = Fx16(data)
        
        if self.Flags & self.FLAGS_TRANSLATION_ZERO == 0:
            self.Translation = ReadVecFx32(data)
        
        if self.Flags & self.FLAGS_ROTATION_ZERO == 0 and self.Flags & self.FLAGS_ROTATION_PIVOT == 0:
            self._01 = Fx16(data)
            self._02 = Fx16(data)
            self._10 = Fx16(data)
            self._11 = Fx16(data)
            self._12 = Fx16(data)
            self._20 = Fx16(data)
            self._21 = Fx16(data)
            self._22 = Fx16(data)
        
        if self.Flags & self.FLAGS_ROTATION_ZERO == 0 and self.Flags & self.FLAGS_ROTATION_PIVOT != 0:
            self.A = Fx16(data)
            self.B = Fx16(data)

        if self.Flags & self.FLAGS_SCALE_ONE == 0:
            self.Scale = ReadVecFx32(data)
            self.InverseScale = ReadVecFx32(data)

class G3dMaterialSet:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        textureToMaterialListDictionaryOffset = unpack("<H", data.read(2))[0]
        paletteToMaterialListDictionaryOffset = unpack("<H", data.read(2))[0]
        MaterialDictionary = G3dDictionary(data).dictionary
        
        data.seek(BeginChunk + textureToMaterialListDictionaryOffset)
        TextureToMaterialListDictionary = G3dDictionary(data).dictionary
        
        data.seek(BeginChunk + paletteToMaterialListDictionaryOffset)
        PaletteToMaterialListDictionary = G3dDictionary(data).dictionary
        
        self.Materials = [None] * len(MaterialDictionary)
        for i in range(len(MaterialDictionary)):
            data.seek(BeginChunk + MaterialDictionary[i][1])
            self.Materials[i] = G3dMaterial(data)
        
        for item in TextureToMaterialListDictionary:
            flags = item[1]
            offset = flags & 0xFFFF
            materialcount = flags >> 16 & 0x7F
            bound = flags >> 24 & 0xFF
            data.seek(BeginChunk + offset)
            for i in range(materialcount):
                item.append(unpack("<B", data.read(1))[0])
        
        for item in PaletteToMaterialListDictionary:
            flags = item[1]
            offset = flags & 0xFFFF
            materialcount = flags >> 16 & 0x7F
            bound = flags >> 24 & 0xFF
            data.seek(BeginChunk + offset)
            for i in range(materialcount):
                item.append(unpack("<B", data.read(1))[0])

class G3dMaterial:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        ItemTag = unpack("<H", data.read(2))[0]
        Size = unpack("<H", data.read(2))[0]
        DiffuseAmbient = unpack("<I", data.read(4))[0]
        SpecularEmission = unpack("<I", data.read(4))[0]
        PolygonAttribute = unpack("<I", data.read(4))[0]
        PolygonAttributeMask = unpack("<I", data.read(4))[0]
        TexImageParam = unpack("<I", data.read(4))[0]
        TexImageParamMask = unpack("<I", data.read(4))[0]
        TexPlttBase = unpack("<H", data.read(2))[0]
        Flags = unpack("<H", data.read(2))[0]
        OriginalWidth = unpack("<H", data.read(2))[0]
        OriginalHeight = unpack("<H", data.read(2))[0]
        MagW = Fx32(data)
        MagH = Fx32(data)
        
        if Flags & G3dMaterialFlags.TexMtxScaleOne.value == 0:
            ScaleS = Fx32(data)
            ScaleT = Fx32(data)
        
        if Flags & G3dMaterialFlags.TexMtxRotZero.value == 0:
            RotationSin = Fx32(data)
            RotationCos = Fx32(data)
        
        if Flags & G3dMaterialFlags.TexMtxTransZero.value == 0:
            TranslationS = Fx32(data)
            TranslationT = Fx32(data)
        
        if Flags & G3dMaterialFlags.EffectMtx.value == G3dMaterialFlags.EffectMtx.value:
            # 4x4 matrix
            EffectMtx = np.zeros((4, 4), dtype=float)
            for i in range(4):
                for j in range(4):
                    EffectMtx[i, j] = Fx32(data)
            print(EffectMtx)

class G3dMaterialFlags(Enum):
    TexMtxUse = 0x0001
    TexMtxScaleOne = 0x0002
    TexMtxRotZero = 0x0004
    TexMtxTransZero = 0x0008
    OrigWHSame = 0x0010
    Wireframe = 0x0020
    Diffuse = 0x0040
    Ambient = 0x0080
    VtxColor = 0x0100
    Specular = 0x0200
    Emission = 0x0400
    Shininess = 0x0800
    TexPlttBase = 0x1000
    EffectMtx = 0x2000

class G3dShapeSet:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        ShapeDictionary = G3dDictionary(data).dictionary
        self.Shapes = [None] * len(ShapeDictionary)
        for i in range(len(ShapeDictionary)):
            data.seek(BeginChunk + ShapeDictionary[i][1])
            self.Shapes[i] = G3dShape(data)

class G3dShape:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        ItemTag = unpack("<H", data.read(2))[0]
        Size = unpack("<H", data.read(2))[0]
        Flags = unpack("<I", data.read(4))[0]
        DisplayListOffset = unpack("<I", data.read(4))[0]
        DisplayListSize = unpack("<I", data.read(4))[0]
        
        data.seek(BeginChunk + DisplayListOffset)
        self.DisplayList = []
        for i in range(DisplayListSize):
            self.DisplayList.append(unpack("<B", data.read(1))[0])

class G3dEnvelopeMatrices:
    def __init__(self, data=None, nodeCount=None):
        if data and nodeCount:
            self.Read(data, nodeCount)
    def Read(self, data, nodeCount):
        Envelopes = [None] * nodeCount
        for i in range(nodeCount):
            Envelopes[i] = G3dEnvelope(data)

class G3dEnvelope:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        self.InversePositionMatrix = np.zeros((4, 3), dtype=float)
        for y in range(4):
            for x in range(3):
                self.InversePositionMatrix[y, x] = read_fx32(data_stream)
        
        self.InverseDirectionMatrix = np.zeros((3, 3), dtype=float)
        for y in range(3):
            for x in range(3):
                self.InverseDirectionMatrix[y, x] = read_fx32(data_stream)

with open("./models/psf00000100.nsbmd", 'rb') as file:
    data = BytesIO(file.read())
    Nsbmd(data)