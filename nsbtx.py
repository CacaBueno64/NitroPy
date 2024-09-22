from struct import unpack, unpack_from, calcsize
from io import BytesIO
from nitro import *

class Nsbtx:
    Btx0Signature = 0x30585442
    def __init__(self, data):
        if isinstance(data, type(BytesIO())):
            self.Read(data)
    def Read(self, data):
        Btx0Signature = self.Btx0Signature
        Header = G3dFileHeader(data=data, expectedSignature=Btx0Signature)
        if Header.NrBlocks > 0:
            data.seek(Header.BlockOffsets[0])
            self.TextureSet = G3dTextureSet(data)

class G3dTextureSet:
    Tex0Signature = 0x30584554
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        Signature = unpack("<I", data.read(4))[0]
        SectionSize = unpack("<I", data.read(4))[0]
        TextureInfo = G3dTextureInfo(data)
        Texture4x4Info = G3dTexture4x4Info(data)


class G3dTextureInfo:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        BeginChunk = data.tell()
        
        VramKey = unpack("<I", data.read(4))[0]
        TextureDataSize = unpack("<H", data.read(2))[0]
        self.DictionaryOffset = unpack("<H", data.read(2))[0]
        self.Flag = unpack("<H", data.read(2))[0]
        TextureDataOffset = unpack("<I", data.read(4))[0]
        
        data.seek(BeginChunk + TextureDataOffset)
        curPos = data.tell()
        self.TextureData = []
        for i in range(TextureDataSize << 3):
            self.TextureData.append(unpack("<B", data.read(1))[0])
        
        data.seek(curPos)

class G3dTexture4x4Info:
    def __init__(self, data=None):
        if data:
            self.Read(data)
    def Read(self, data):
        pass
