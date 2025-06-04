from .nitro import *
from struct import unpack, unpack_from, calcsize
from io import BytesIO
from enum import Enum
from mathutils import Matrix, Vector

class Nsbmd:
    def __init__(self, reader):
        self.Header = G3dFileHeader(reader, 0x30444D42)
        if self.Header.NrBlocks > 0:
            reader.seek(self.Header.BlockOffsets[0])
            self.ModelSet = G3dModelSet(reader)

class G3dModelSet:
    def __init__(self, reader):
        BeginChunk = reader.tell()
        
        signature = reader.read(4)
        if signature != b"MDL0":
            raise Exception(f"Wrong signature, got : {signature}, exepted : MDL0")
        sectionSize = unpack("<I", reader.read(4))[0]
        self.Dictionary = G3dDictionary(reader, OffsetDictionaryData)
        self.Models = []
        for i in range(len(self.Dictionary)):
            reader.seek(BeginChunk + self.Dictionary.Data[i].Data.Offset)
            self.Models.append(G3dModel(reader))

class G3dModel:
    def __init__(self, reader):
        BeginChunk = reader.tell()
        
        Size = unpack("<I", reader.read(4))[0]
        self.SbcOffset = unpack("<I", reader.read(4))[0]
        MaterialsOffset = unpack("<I", reader.read(4))[0]
        ShapesOffset = unpack("<I", reader.read(4))[0]
        EnvelopeMatricesOffset = unpack("<I", reader.read(4))[0]
        self.Info = G3dModelInfo(reader)
        self.Nodes = G3dNodeSet(reader)
        reader.seek(BeginChunk + self.SbcOffset)
        self.Sbc = reader.read(MaterialsOffset - self.SbcOffset)
        reader.seek(BeginChunk + MaterialsOffset)
        self.Materials = G3dMaterialSet(reader)
        reader.seek(BeginChunk + ShapesOffset)
        self.Shapes = G3dShapeSet(reader)
        self.EnvelopeMatrices = None
        if EnvelopeMatricesOffset != Size and EnvelopeMatricesOffset != 0:
            reader.seek(EnvelopeMatricesOffset + BeginChunk)
            self.EnvelopeMatrices = G3dEnvelopeMatrices(reader, len(self.Nodes.NodeDictionary))

class G3dModelInfo:
    def __init__(self, reader):
        BeginChunk = reader.tell()
        
        self.SbcType = unpack("<B", reader.read(1))[0]
        self.ScalingRule = unpack("<B", reader.read(1))[0]
        #print(self.ScalingRule)
        self.TextureMatrixMode = unpack("<B", reader.read(1))[0]
        self.NodeCount = unpack("<B", reader.read(1))[0]
        self.MaterialCount = unpack("<B", reader.read(1))[0]
        self.ShapeCount = unpack("<B", reader.read(1))[0]
        self.FirstUnusedMatrixStackId = unpack("<B", reader.read(1))[0]
        reader.read(1) #dummy
        self.PosScale, self.InversePosScale = ReadFx32s(reader, 2)
        self.VertexCount = unpack("<H", reader.read(2))[0]
        self.PolygonCount = unpack("<H", reader.read(2))[0]
        self.TriangleCount = unpack("<H", reader.read(2))[0]
        self.QuadCount = unpack("<H", reader.read(2))[0]
        self.BoxX, self.BoxY, self.BoxZ = ReadFx16s(reader, 3)
        self.BoxW, self.BoxH, self.BoxD = ReadFx16s(reader, 3)
        self.BoxPosScale, self.BoxInversePosScale = ReadFx32s(reader, 2)

class G3dNodeSet:
    def __init__(self, reader):
        BeginChunk = reader.tell()
        self.NodeDictionary = G3dDictionary(reader, OffsetDictionaryData)
        self.Data = []
        curpos = reader.tell()
        for i in range(len(self.NodeDictionary)):
            reader.seek(BeginChunk + self.NodeDictionary.Data[i].Data.Offset)
            self.Data.append(G3dNodeData(reader))
        reader.seek(curpos)

class G3dNodeData:
    def __init__(self, reader):
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
        
        self.Flags = unpack("<H", reader.read(2))[0]
        
        self._00 = ReadFx16(reader)
        
        if (self.Flags & self.FLAGS_TRANSLATION_ZERO) == 0:
            self.Translation = Vector(ReadVecFx32(reader))
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
            self.Scale = Vector(ReadVecFx32(reader))
            self.InverseScale = Vector(ReadVecFx32(reader))
    
    def GetTranslation(self, jntAnmResult):
        if (self.Flags & self.FLAGS_TRANSLATION_ZERO) != 0:
            jntAnmResult.Flag |= JointAnimationResultFlag.TranslationZero
        else:
            jntAnmResult.trans = self.Translation
    def GetRotation(self, jntAnmResult):
        if (self.Flags & self.FLAGS_ROTATION_ZERO) != 0:
            jntAnmResult.Flag |= JointAnimationResultFlag.RotationZero
        else:
            if (self.Flags & self.FLAGS_ROTATION_PIVOT) != 0:
                jntAnmResult.rot = DecodePivotRotation(
                    (self.Flags & self.FLAGS_ROTATION_PIVOT_INDEX_MASK) >> self.FLAGS_ROTATION_PIVOT_INDEX_SHIFT,
                    (self.Flags & self.FLAGS_ROTATION_PIVOT_NEGATIVE) != 0,
                    (self.Flags & self.FLAGS_ROTATION_PIVOT_SIGN_REVERSE_C) != 0,
                    (self.Flags & self.FLAGS_ROTATION_PIVOT_SIGN_REVERSE_D) != 0,
                    self.A, self.B)
            else:
                rot = [[self._00, self._01, self._02],
                       [self._10, self._11, self._12],
                       [self._20, self._21, self._22]]
                jntAnmResult.rot = rot

class G3dMaterialSet:
    def __init__(self, reader):
        beginChunk = reader.tell()
        
        textureToMaterialListDictionaryOffset = unpack("<H", reader.read(2))[0]
        paletteToMaterialListDictionaryOffset = unpack("<H", reader.read(2))[0]
        self.MaterialDictionary = G3dDictionary(reader, OffsetDictionaryData)
        reader.seek(textureToMaterialListDictionaryOffset + beginChunk)
        self.TextureToMaterialListDictionary = G3dDictionary(reader, TextureToMaterialDictionaryData)
        reader.seek(paletteToMaterialListDictionaryOffset + beginChunk)
        self.PaletteToMaterialListDictionary = G3dDictionary(reader, PaletteToMaterialDictionaryData)
        self.Materials = []
        for i in range(len(self.MaterialDictionary)):
            reader.seek(self.MaterialDictionary.Data[i].Data.Offset + beginChunk)
            self.Materials.append(G3dMaterial(reader))
        for item in self.TextureToMaterialListDictionary.Data:
            reader.seek(item.Data.Offset + beginChunk)
            item.Data.Materials.append(reader.read(item.Data.MaterialCount))
        for item in self.PaletteToMaterialListDictionary.Data:
            reader.seek(item.Data.Offset + beginChunk)
            item.Data.Materials.append(reader.read(item.Data.MaterialCount))

class G3dMaterial:
    def __init__(self, reader):
        beginChunk = reader.tell()
        
        self.ItemTag = unpack("<H", reader.read(2))[0]
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
            m = ReadFx32s(reader, 16)
            self.EffectMtx = Matrix([[m[0],  m[1],  m[2],  m[3]],
                                     [m[4],  m[5],  m[6],  m[7]],
                                     [m[8],  m[9],  m[10], m[11]],
                                     [m[12], m[13], m[14], m[15]]])

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
    def __init__(self, reader):
        BeginChunk = reader.tell()
        
        self.ShapeDictionary = G3dDictionary(reader, OffsetDictionaryData)
        self.Shapes = []
        for i in range(len(self.ShapeDictionary)):
            reader.seek(BeginChunk + self.ShapeDictionary.Data[i].Data.Offset)
            self.Shapes.append(G3dShape(reader))

class G3dShape:
    def __init__(self, reader):
        BeginChunk = reader.tell()
        
        self.ItemTag = unpack("<H", reader.read(2))[0]
        Size = unpack("<H", reader.read(2))[0]
        self.Flags = unpack("<I", reader.read(4))[0]
        DisplaylistOffset = unpack("<I", reader.read(4))[0]
        DisplaylistSize = unpack("<I", reader.read(4))[0]
        reader.seek(BeginChunk + DisplaylistOffset)
        self.DisplayList = reader.read(DisplaylistSize)

class G3dEnvelopeMatrices:
    def __init__(self, reader, nodeCount):
        self.Envelopes = []
        for i in range(nodeCount):
            self.Envelopes.append(G3dEnvelope(reader))

class G3dEnvelope:
    def __init__(self, reader):
        m = ReadFx32s(reader, 16)
        self.InversePositionMatrix = Matrix([[m[0], m[1],  m[2],  0.0],
                                             [m[3], m[4],  m[5],  0.0],
                                             [m[6], m[7],  m[8],  0.0],
                                             [m[9], m[10], m[11], 1.0]])
        m = ReadFx32s(reader, 9)
        self.InverseDirectionMatrix = Matrix([[m[0], m[1], m[2], 0.0],
                                              [m[3], m[4], m[5], 0.0],
                                              [m[6], m[7], m[8], 0.0],
                                              [0.0,  0.0,  0.0,  1.0]])