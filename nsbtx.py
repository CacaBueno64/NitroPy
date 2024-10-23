from struct import unpack, unpack_from, calcsize
from io import BytesIO
from enum import Enum
import numpy as np
from nitro import *
from gfxutil import *

class Nsbtx:
    def __init__(self, reader=None, writer=None):
        self.Btx0Signature = 0x30585442
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        self.Header = G3dFileHeader(reader=reader, expectedSignature=self.Btx0Signature)
        if self.Header.NrBlocks > 0:
            reader.seek(self.Header.BlockOffsets[0])
            self.TextureSet = G3dTextureSet(reader=reader)

class G3dTextureSet:
    def __init__(self, reader=None, writer=None):
        self.Tex0Signature = 0x30584554
        if reader:
            self.Read(reader)
    
    def Read(self, reader):
        beginChunk = reader.tell()
        ReadSignature(reader, self.Tex0Signature)
        SectionSize = unpack("<I", reader.read(4))[0]
        self.TextureInfo = G3dTextureInfo(reader=reader, offset=beginChunk)
        self.Texture4x4Info = G3dTexture4x4Info(reader=reader, offset=beginChunk)
        self.PaletteInfo = G3dPaletteInfo(reader=reader, offset=beginChunk)
        self.TextureDictionary = G3dDictionary(reader=reader, TData=TextureDictionaryData)
        self.PaletteDictionary = G3dDictionary(reader=reader, TData=PaletteDictionaryData)

class G3dTextureInfo:
    def __init__(self, reader=None, writer=None, offset=None):
        if reader:
            self.Read(reader, offset)
    
    def Read(self, reader, offset):
        VramKey = unpack("<I", reader.read(4))[0]
        TextureDataSize = unpack("<H", reader.read(2))[0]
        DictionaryOffset = unpack("<H", reader.read(2))[0]
        Flag = unpack("<H", reader.read(2))[0]
        reader.read(2)
        TextureDataOffset = unpack("<I", reader.read(4))[0]
        curPos = reader.tell()
        reader.seek(TextureDataOffset + offset)
        self.TextureData = reader.read(TextureDataSize << 3)
        reader.seek(curPos)

class G3dTexture4x4Info:
    def __init__(self, reader=None, writer=None, offset=None):
        if reader:
            self.Read(reader, offset)
    
    def Read(self, reader, offset):
        VramKey = unpack("<I", reader.read(4))[0]
        TextureDataSize = unpack("<H", reader.read(2))[0]
        DictionaryOffset = unpack("<H", reader.read(2))[0]
        Flag = unpack("<H", reader.read(2))[0]
        reader.read(2)
        TextureDataOffset = unpack("<I", reader.read(4))[0]
        TexturePaletteIndexDataOffset = unpack("<I", reader.read(4))[0]
        curPos = reader.tell()
        reader.seek(TextureDataOffset + offset)
        self.TextureData = reader.read(TextureDataSize << 3)
        reader.seek(TexturePaletteIndexDataOffset + offset)
        self.TexturePaletteIndexData = reader.read(TextureDataSize << 2)
        reader.seek(curPos)

class G3dPaletteInfo:
    def __init__(self, reader=None, writer=None, offset=None):
        if reader:
            self.Read(reader, offset)
    
    def Read(self, reader, offset):
        VramKey = unpack("<I", reader.read(4))[0]
        PaletteDataSize = unpack("<H", reader.read(2))[0]
        DictionaryOffset = unpack("<H", reader.read(2))[0]
        Flag = unpack("<H", reader.read(2))[0]
        reader.read(2)
        PaletteDataOffset = unpack("<I", reader.read(4))[0]
        curPos = reader.tell()
        reader.seek(PaletteDataOffset + offset)
        self.PaletteData = reader.read(PaletteDataSize << 3)
        reader.seek(curPos)

def ToBitMap(tex: TextureDictionaryData, pltt: PaletteDictionaryData,
        TextureInfo: G3dTextureInfo, PaletteInfo: G3dPaletteInfo, Texture4x4Info: G3dTexture4x4Info):
    
    width = 8 << tex.TexImageParam.Width
    height = 8 << tex.TexImageParam.Height
    if tex.TexImageParam.Format == ImageFormat.Comp4x4:
        return GfxUtil.DecodeBmp(
            Texture4x4Info.TextureData[tex.TexImageParam.Address << 3:],
            ImageFormat.Comp4x4, width, height,
            PaletteInfo.PaletteData[pltt.Offset << 3:],
            tex.TexImageParam.Color0Transparent,
            Texture4x4Info.TexturePaletteIndexData[tex.TexImageParam.Address << 2:]
        )
    elif tex.TexImageParam.Format == ImageFormat.Direct:
        return GfxUtil.DecodeBmp(
            TextureInfo.TextureData[tex.TexImageParam.Address << 3:],
            ImageFormat.Direct, width, height
        )
    else:
        return GfxUtil.DecodeBmp(
            TextureInfo.TextureData[tex.TexImageParam.Address << 3:],
            tex.TexImageParam.Format, width, height,
            PaletteInfo.PaletteData[pltt.Offset << 3:],
            tex.TexImageParam.Color0Transparent
        )
