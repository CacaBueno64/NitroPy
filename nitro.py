from struct import unpack, unpack_from, calcsize, Struct
from io import BytesIO
from enum import Enum
import numpy as np
from collections import OrderedDict


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


class GxPolygonAttr:
    def __init__(self, value):
        self._value = value
class GxTexImageParam:
    def __init__(self, value):
        self._value = value

class GxEnum(Enum):
    pass


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


class GLDisplayListBuffer:
    def __init__(self, dl):
        _vertexArray = GLVertexArray()
