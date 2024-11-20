from struct import unpack, unpack_from, calcsize
from io import BytesIO
from enum import Enum
import numpy as np
from .nitro import *
#from nsbtx import *
from .gxcommands import *

class Nsbmd:
    def __init__(self, reader=None, writer=None):
        self.Bmd0Signature = 0x30444D42
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        Header = G3dFileHeader(reader=reader, expectedSignature=self.Bmd0Signature)
        if Header.NrBlocks > 0:
            reader.seek(Header.BlockOffsets[0])
            self.ModelSet = G3dModelSet(reader=reader)
        #if Header.NrBlocks > 1:
        #    reader.seek(Header.BlockOffsets[1])
        #    self.TextureSet = G3dTextureSet(reader=reader)

class G3dModelSet:
    def __init__(self, reader=None, writer=None):
        self.Mdl0Signature = 0x304C444D
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        ReadSignature(reader, self.Mdl0Signature)
        sectionSize = unpack("<I", reader.read(4))[0]
        self.Dictionary = G3dDictionary(reader=reader, TData=OffsetDictionaryData)
        self.Models = [None] * self.Dictionary.Count()
        for i in range(self.Dictionary.Count()):
            reader.seek(self.Dictionary.Data[i].Data.Offset + beginChunk)
            self.Models[i] = G3dModel(reader=reader)

class G3dModel:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        Size = unpack("<I", reader.read(4))[0]
        SbcOffset = unpack("<I", reader.read(4))[0]
        MaterialsOffset = unpack("<I", reader.read(4))[0]
        ShapesOffset = unpack("<I", reader.read(4))[0]
        EnvelopeMatricesOffset = unpack("<I", reader.read(4))[0]
        self.Info = G3dModelInfo(reader=reader)
        self.Nodes = G3dNodeSet(reader=reader)
        reader.seek(SbcOffset + beginChunk)
        self.Sbc = reader.read(MaterialsOffset - SbcOffset)
        reader.seek(MaterialsOffset + beginChunk)
        self.Materials = G3dMaterialSet(reader=reader)
        reader.seek(ShapesOffset + beginChunk)
        self.Shapes = G3dShapeSet(reader=reader)
        if EnvelopeMatricesOffset != Size and EnvelopeMatricesOffset != 0:
            reader.seek(EnvelopeMatricesOffset + beginChunk)
            self.EnvelopeMatrices = G3dEnvelopeMatrices(reader=reader, nodeCount=self.Nodes.NodeDictionary.Count())
            print("envelopped")

class G3dModelInfo:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.SbcType = unpack("<B", reader.read(1))[0]
        self.ScalingRule = unpack("<B", reader.read(1))[0]
        self.TextureMatrixMode = unpack("<B", reader.read(1))[0]
        self.NodeCount = unpack("<B", reader.read(1))[0]
        self.MaterialCount = unpack("<B", reader.read(1))[0]
        self.ShapeCount = unpack("<B", reader.read(1))[0]
        #reader.read(1) # maybe here
        self.FirstUnusedMatrixStackId = unpack("<B", reader.read(1))[0]
        reader.read(1) # or here
        self.PosScale = ReadFx32(reader)
        self.InversePosScale = ReadFx32(reader)
        self.VertexCount = unpack("<H", reader.read(2))[0]
        self.PolygonCount = unpack("<H", reader.read(2))[0]
        self.TriangleCount = unpack("<H", reader.read(2))[0]
        self.QuadCount = unpack("<H", reader.read(2))[0]
        self.BoxX = ReadFx16(reader)
        self.BoxY = ReadFx16(reader)
        self.BoxZ = ReadFx16(reader)
        self.BoxW = ReadFx16(reader)
        self.BoxH = ReadFx16(reader)
        self.BoxD = ReadFx16(reader)
        self.BoxPosScale = ReadFx32(reader)
        self.BoxInversePosScale = ReadFx32(reader)

class G3dNodeSet:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        self.NodeDictionary = G3dDictionary(reader=reader, TData=OffsetDictionaryData)
        self.Data = [None] * self.NodeDictionary.Count()
        curpos = reader.tell()
        for i in range(self.NodeDictionary.Count()):
            reader.seek(self.NodeDictionary.Data[i].Data.Offset + beginChunk)
            self.Data[i] = G3dNodeData(reader=reader)
        reader.seek(curpos)

class G3dNodeData:
    def __init__(self, reader=None, writer=None):
        self.FLAGS_TRANSLATION_ZERO = 0x0001
        self.FLAGS_ROTATION_ZERO = 0x0002
        self.FLAGS_SCALE_ONE = 0x0004
        self.FLAGS_ROTATION_PIVOT = 0x0008
        self.FLAGS_ROTATION_PIVOT_INDEX_MASK = 0x00F0
        self.FLAGS_ROTATION_PIVOT_INDEX_SHIFT = 4
        self.FLAGS_ROTATION_PIVOT_NEGATIVE = 0x0100
        self.FLAGS_ROTATION_PIVOT_SIGN_REVERSE_C = 0x0200
        self.FLAGS_ROTATION_PIVOT_SIGN_REVERSE_D = 0x0400
        self.FLAGS_MATRIX_STACK_INDEX_MASK = 0xF800
        self.FLAGS_MATRIX_STACK_INDEX_SHIFT = 11
        self.FLAGS_IDENTITY = self.FLAGS_TRANSLATION_ZERO | self.FLAGS_ROTATION_ZERO | self.FLAGS_SCALE_ONE
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.Flags = unpack("<H", reader.read(2))[0]
        self._00 = ReadFx16(reader)
        
        if (self.Flags & self.FLAGS_TRANSLATION_ZERO) == 0:
            self.Translation = ReadVecFx32(reader)
        if (self.Flags & self.FLAGS_ROTATION_ZERO) == 0 and (self.Flags & self.FLAGS_ROTATION_PIVOT) == 0:
            self._01 = ReadFx16(reader)
            self._02 = ReadFx16(reader)
            self._10 = ReadFx16(reader)
            self._11 = ReadFx16(reader)
            self._12 = ReadFx16(reader)
            self._20 = ReadFx16(reader)
            self._21 = ReadFx16(reader)
            self._22 = ReadFx16(reader)
        if (self.Flags & self.FLAGS_ROTATION_ZERO) == 0 and (self.Flags & self.FLAGS_ROTATION_PIVOT) != 0:
            self.A = ReadFx16(reader)
            self.B = ReadFx16(reader)
        if (self.Flags & self.FLAGS_SCALE_ONE) == 0:
            self.Scale = ReadVecFx32(reader)
            self.InverseScale = ReadVecFx32(reader)

class G3dMaterialSet:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        textureToMaterialListDictionaryOffset = unpack("<H", reader.read(2))[0]
        paletteToMaterialListDictionaryOffset = unpack("<H", reader.read(2))[0]
        self.MaterialDictionary = G3dDictionary(reader=reader, TData=OffsetDictionaryData)
        reader.seek(textureToMaterialListDictionaryOffset + beginChunk)
        self.TextureToMaterialListDictionary = G3dDictionary(reader=reader, TData=TextureToMaterialDictionaryData)
        reader.seek(paletteToMaterialListDictionaryOffset + beginChunk)
        self.PaletteToMaterialListDictionary = G3dDictionary(reader=reader, TData=PaletteToMaterialDictionaryData)
        self.Materials = [None] * self.MaterialDictionary.Count()
        for i in range(self.MaterialDictionary.Count()):
            reader.seek(self.MaterialDictionary.Data[i].Data.Offset + beginChunk)
            self.Materials[i] = G3dMaterial(reader=reader)
        for item in self.TextureToMaterialListDictionary.Data:
            reader.seek(item.Data.Offset + beginChunk)
            item.Data.Materials.append(reader.read(item.Data.MaterialCount))
        for item in self.PaletteToMaterialListDictionary.Data:
            reader.seek(item.Data.Offset + beginChunk)
            item.Data.Materials.append(reader.read(item.Data.MaterialCount))

class G3dMaterial:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        ItemTag = unpack("<H", reader.read(2))[0]
        Size = unpack("<H", reader.read(2))[0]
        self.DiffuseAmbient = unpack("<I", reader.read(4))[0]
        self.SpecularEmission = unpack("<I", reader.read(4))[0]
        self.PolygonAttribute = GxPolygonAttr(unpack("<I", reader.read(4))[0])
        self.PolygonAttributeMask = unpack("<I", reader.read(4))[0]
        self.TexImageParam = GxTexImageParam(unpack("<I", reader.read(4))[0])
        self.TexImageParamMask = unpack("<I", reader.read(4))[0]
        self.TexPlttBase = unpack("<H", reader.read(2))[0]
        self.Flags = unpack("<H", reader.read(2))[0]
        self.OriginalWidth = unpack("<H", reader.read(2))[0]
        self.OriginalHeight = unpack("<H", reader.read(2))[0]
        self.MagW = ReadFx32(reader)
        self.MagH = ReadFx32(reader)
        if self.Flags & G3dMaterialFlags.TexMtxScaleOne.value == 0:
            self.ScaleS = ReadFx32(reader)
            self.ScaleT = ReadFx32(reader)
        if self.Flags & G3dMaterialFlags.TexMtxRotZero.value == 0:
            self.RotationSin = ReadFx16(reader)
            self.RotationCos = ReadFx16(reader)
        if self.Flags & G3dMaterialFlags.TexMtxTransZero.value == 0:
            self.TranslationS = ReadFx32(reader)
            self.TranslationT = ReadFx32(reader)
        if self.Flags & G3dMaterialFlags.EffectMtx.value == G3dMaterialFlags.EffectMtx.value:
            self.EffectMtx = np.zeros((4, 4), dtype=np.float32)
            for i in range(4):
                for j in range(4):
                    self.EffectMtx[i, j] = ReadFx32(reader)

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
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        self.ShapeDictionary = G3dDictionary(reader=reader, TData=OffsetDictionaryData)
        self.Shapes = [None] * self.ShapeDictionary.Count()
        for i in range(self.ShapeDictionary.Count()):
            reader.seek(self.ShapeDictionary.Data[i].Data.Offset + beginChunk)
            self.Shapes[i] = G3dShape(reader=reader)

class G3dShape:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        ItemTag = unpack("<H", reader.read(2))[0]
        Size = unpack("<H", reader.read(2))[0]
        self.Flags = unpack("<I", reader.read(4))[0]
        DisplayListOffset = unpack("<I", reader.read(4))[0]
        DisplayListSize = unpack("<I", reader.read(4))[0]
        reader.seek(DisplayListOffset + beginChunk)
        self.DisplayList = reader.read(DisplayListSize)

class G3dEnvelopeMatrices:
    def __init__(self, reader=None, writer=None, nodeCount=None):
        if reader and nodeCount:
            self.Read(reader, nodeCount)
    
    def Read(self, reader, nodeCount):
        self.Envelopes = [None] * nodeCount
        for i in range(nodeCount):
            self.Envelopes[i] = G3dEnvelope(reader=reader)

class G3dEnvelope:
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.InversePositionMatrix = np.zeros((4, 3), dtype=np.float32)
        for i in range(4):
            for j in range(3):
                self.InversePositionMatrix[i, j] = ReadFx32(reader)
        self.InverseDirectionMatrix = np.zeros((3, 3), dtype=np.float32)
        for i in range(3):
            for j in range(3):
                self.InverseDirectionMatrix[i, j] = ReadFx32(reader)