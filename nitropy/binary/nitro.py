from struct import unpack, unpack_from, calcsize, Struct
from io import BytesIO
from enum import Enum
import numpy as np


def ReadSignature(reader, expectedSignature: int):
    Signature = unpack("<I", reader.read(4))[0]
    if Signature != expectedSignature:
        raise Exception(f"Signature not correct.\nGot : {Signature}\nExpected : {expectedSignature}")

class G3dFileHeader:
    def __init__(self, reader=None, writer=None, version: int=None, signature: int=None, expectedSignature: int=None):
        self.Header = Struct("<I HH I HH")
        self.Signature = signature
        self.ByteOrder = 0xFEFF
        self.Version = version
        self.HeaderSize = 16
        if reader:
            self.Read(reader, expectedSignature)
    
    def Read(self, reader, expectedSignature):
        unpackedHeader = self.Header.unpack_from(reader.read(self.Header.size))
        self.Signature = unpackedHeader[0]
        self.Version = unpackedHeader[2]
        self.NrBlocks = unpackedHeader[5]
        if self.Signature != expectedSignature:
            raise Exception(f"Signature not correct.\nGot : {unpackedHeader[0]}\nExpected : {self.Signature}")
        self.BlockOffsets = unpack(f"{self.NrBlocks}I", reader.read(self.NrBlocks*4))

class G3dAnimationHeader:
    def __init__(self, reader=None, writer=None, expectedCategory0=b"", expectedCategory1=b""):
        Category0 = unpack("<1s", reader.read(1))[0]
        if Category0 != expectedCategory0:
            raise Exception(f"Category not correct.\nGot : {Category0}\nExpected : {expectedCategory0}")
        Revision = unpack("<B", reader.read(1))[0]
        Category1 = unpack("<2s", reader.read(2))[0]
        if Category1 != expectedCategory1:
            raise Exception(f"Category not correct.\nGot : {Category1}\nExpected : {expectedCategory1}")

class G3dDictionary:
    def __init__(self, reader=None, writer=None, TData=None):
        self.NAME_LENGTH = 16
        self.Data = []
        if reader:
            self.Read(reader, TData)
    
    def Read(self, reader, TData):
        G3dDictionarySerializer.ReadG3dDictionary(reader, TData, self)
    
    def Add(self, name, data):
        self.Data.append(G3dDictionaryEntry(name, data))
    
    def Count(self):
        return len(self.Data)

class G3dDictionaryEntry:
    def __init__(self, name, data):
        self.Name = name
        self.Data = data

class G3dDictionarySerializer:
    DICTIONARY_REVISION = 0
    NAME_LENGTH = 16
    
    @staticmethod
    def ReadG3dDictionary(reader, TData, dictionary):
        startPosition = reader.tell()
        # Header
        revision = unpack("<B", reader.read(1))[0]
        entryCount = unpack("<B", reader.read(1))[0]
        dictionarySize = unpack("<H", reader.read(2))[0]
        reader.read(2)
        entriesOffset = unpack("<H", reader.read(2))[0]
        G3dDictionarySerializer.ThrowIfInvalidRevision(revision)
        # Entries
        reader.seek(startPosition + entriesOffset)
        entrySize = unpack("<H", reader.read(2))[0]
        namesOffset = unpack("<H", reader.read(2))[0]
        G3dDictionarySerializer.ThrowIfIncorrectEntrySize(entrySize, TData)
        data = [TData(reader) for i in range(entryCount)]
        reader.seek(startPosition + entriesOffset + namesOffset)
        for i in range(entryCount):
            name = reader.read(G3dDictionarySerializer.NAME_LENGTH).decode("shift-jis")
            dictionary.Add(name, data[i])
        reader.seek(startPosition + dictionarySize)
    
    @staticmethod
    def ThrowIfInvalidRevision(revision):
        if revision != G3dDictionarySerializer.DICTIONARY_REVISION:
            raise Exception(f"Unsupported dictionary revision.\nGot {revision}\nExpected {G3dDictionarySerializer.DICTIONARY_REVISION}")
    
    @staticmethod
    def ThrowIfIncorrectEntrySize(entrySize, TData):
        if entrySize != TData.DataSize:
            raise Exception(f"Dictionary entry size mismatch.\nGot {entrySize}, expected {TData.DataSize}.")

class OffsetDictionaryData:
    DataSize = 4
    
    def __init__(self, reader=None, writer=None):
        self.Offset = None
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.Offset = unpack("<I", reader.read(4))[0]

class TextureToMaterialDictionaryData:
    DataSize = 4
    
    def __init__(self, reader=None, writer=None):
        self.Offset = None
        self.Materials = []
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        flags = unpack("<I", reader.read(4))[0]
        self.Offset = flags & 0xFFFF
        self.MaterialCount = flags >> 16 & 0x7F
        self.Bound = flags >> 24 & 0xFF

class PaletteToMaterialDictionaryData:
    DataSize = 4
    
    def __init__(self, reader=None, writer=None):
        self.Offset = None
        self.Materials = []
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        flags = unpack("<I", reader.read(4))[0]
        self.Offset = flags & 0xFFFF
        self.MaterialCount = flags >> 16 & 0x7F
        self.Bound = flags >> 24 & 0xFF

class TextureDictionaryData:
    DataSize = 8
    
    def __init__(self, reader=None, writer=None):
        self.ParamExOrigWMask = 0x000007ff
        self.ParamExOrigHMask = 0x003ff800
        self.ParamExWHSameMask = 0x80000000
        self.ParamExOrigWShift = 0
        self.ParamExOrigHShift = 11
        self.ParamExWHSameShift = 31
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.TexImageParam = GxTexImageParam(unpack("<I", reader.read(4))[0])
        self.ExtraParam = unpack("<I", reader.read(4))[0]

class PaletteDictionaryData:
    DataSize = 4
    
    def __init__(self, reader=None, writer=None):
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.Offset = unpack("<H", reader.read(2))[0]
        self.Flags = unpack("<H", reader.read(2))[0]


class GxPolygonAttr:
    def __init__(self, value):
        self._value = value
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

class GxEnum(Enum):
    pass
class GxTexGen(Enum):
    Null = 0
    TexCoord = 1
    Normal = 2
    Vertex = 3


def Short(value):
    value = value & 0xFFFF
    if value >= 0x8000:
        value -= 0x10000
    return value

def ReadFx16(reader):
    return unpack("<H", reader.read(2))[0] / 4096
def ReadFx16s(reader, count):
    return [unpack("<H", reader.read(2))[0] / 4096 for i in range(count)]
def ReadFx32(reader):
    return unpack("<I", reader.read(4))[0] / 4096
def ReadFx32s(reader, count):
    return [unpack("<I", reader.read(4))[0] / 4096 for i in range(count)]
def ReadVecFx16(reader):
    return tuple([ReadFx16(reader) for i in range(3)])
def ReadVecFx32(reader):
    return tuple([ReadFx32(reader) for i in range(3)])

def ReadU16Le(data: bytes, count: int):
    return list(unpack('<' + 'H' * count, data[:count * 2]))

def ReadPadding(reader, alignment):
    pos = reader.tell()
    if pos % alignment == 0:
        return
    reader.seek(pos + alignment - (pos % alignment))


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


class GLDisplayListBuffer:
    def __init__(self, dl):
        _vertexArray = GLVertexArray()

class G3dUtil:
    PivotUtil = np.array([
        [ 4, 5, 7, 8 ],
        [ 3, 5, 6, 8 ],
        [ 3, 4, 6, 7 ],
        [ 1, 2, 7, 8 ],
        [ 0, 2, 6, 8 ],
        [ 0, 1, 6, 7 ],
        [ 1, 2, 4, 5 ],
        [ 0, 2, 3, 5 ],
        [ 0, 1, 3, 4 ]
    ], dtype=np.uint8)

    @staticmethod
    def DecodePivotRotation(pivot_idx, pivot_neg, sign_rev_c, sign_rev_d, a, b):
        mtx = np.zeros((3, 3))
        def set_value(idx, value):
            mtx[idx // 3, idx % 3] = value
        set_value(int(pivot_idx), -1 if pivot_neg else 1)
        set_value(G3dUtil.PivotUtil[pivot_idx, 0], a)
        set_value(G3dUtil.PivotUtil[pivot_idx, 1], b)
        set_value(G3dUtil.PivotUtil[pivot_idx, 2], -b if sign_rev_c else b)
        set_value(G3dUtil.PivotUtil[pivot_idx, 3], -a if sign_rev_d else a)
        return mtx