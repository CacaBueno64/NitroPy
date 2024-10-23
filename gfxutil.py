from struct import unpack, unpack_from, calcsize
from io import BytesIO
from enum import Enum
import numpy as np
from PIL import Image
from nitro import *

import math

class ColorFormat:
    def __init__(self, a_shift, a_size, r_shift, r_size, g_shift, g_size, b_shift, b_size):
        self.AShift = a_shift
        self.ASize = a_size
        self.RShift = r_shift
        self.RSize = r_size
        self.GShift = g_shift
        self.GSize = g_size
        self.BShift = b_shift
        self.BSize = b_size
    
    @property
    def NrBytes(self):
        # Calculate the number of bytes by adding the sizes and dividing by 8, then rounding up
        return math.ceil((self.ASize + self.RSize + self.GSize + self.BSize) / 8.0)

ColorFormat.ARGB8888 = ColorFormat(24, 8, 16, 8, 8, 8, 0, 8)
ColorFormat.ARGB3444 = ColorFormat(12, 3, 8, 4, 4, 4, 0, 4)
ColorFormat.RGBA8888 = ColorFormat(0, 8, 24, 8, 16, 8, 8, 8)
ColorFormat.RGBA4444 = ColorFormat(0, 4, 12, 4, 8, 4, 4, 4)
ColorFormat.RGB888 = ColorFormat(0, 0, 16, 8, 8, 8, 0, 8)
ColorFormat.RGB565 = ColorFormat(0, 0, 11, 5, 5, 6, 0, 5)
ColorFormat.ARGB1555 = ColorFormat(15, 1, 10, 5, 5, 5, 0, 5)
ColorFormat.XRGB1555 = ColorFormat(0, 0, 10, 5, 5, 5, 0, 5)
ColorFormat.ABGR1555 = ColorFormat(15, 1, 0, 5, 5, 5, 10, 5)
ColorFormat.XBGR1555 = ColorFormat(0, 0, 0, 5, 5, 5, 10, 5)
ColorFormat.RGBA5551 = ColorFormat(0, 1, 11, 5, 6, 5, 1, 5)

class GfxUtil:
    DataSize = [0, 8, 2, 4, 8, 2, 8, 16]
    
    @staticmethod
    def ToColorFormat(a, r, g, b, outputFormat: ColorFormat):
        result = 0
        mask = 0
        if outputFormat.ASize != 0:
            mask   =  ~(0xFFFFFFFF << outputFormat.ASize)
            result |= int((a * mask + 127) / 255) << outputFormat.AShift
        
        mask   =  ~(0xFFFFFFFF << outputFormat.RSize)
        result |= int((r * mask + 127) / 255) << outputFormat.RShift
        mask   =  ~(0xFFFFFFFF << outputFormat.GSize)
        result |= int((g * mask + 127) / 255) << outputFormat.GShift
        mask   =  ~(0xFFFFFFFF << outputFormat.BSize);
        result |= int((b * mask + 127) / 255) << outputFormat.BShift
        return result
    
    @staticmethod
    def ConvertColorFormat(inColor, inputFormat: ColorFormat, outputFormat: ColorFormat):
        if inputFormat == outputFormat:
            return inColor
        # From color format to components
        a = 0
        mask = 0
        if inputFormat.ASize == 0:
            a = 255
        else:
            mask = ~(0xFFFFFFFF << inputFormat.ASize)
            a    = ((((inColor >> inputFormat.AShift) & mask) * 255) + mask / 2) / mask
        mask = ~(0xFFFFFFFF << inputFormat.RSize)
        r    = ((((inColor >> inputFormat.RShift) & mask) * 255) + mask / 2) / mask
        mask = ~(0xFFFFFFFF << inputFormat.GSize)
        g    = ((((inColor >> inputFormat.GShift) & mask) * 255) + mask / 2) / mask
        mask = ~(0xFFFFFFFF << inputFormat.BSize)
        b    = ((((inColor >> inputFormat.BShift) & mask) * 255) + mask / 2) / mask
        return GfxUtil.ToColorFormat(a, r, g, b, outputFormat)
    
    @staticmethod
    def ConvertColorFormatFromU16(inColor, inputFormat: ColorFormat, outputFormat: ColorFormat):
        output = []
        for i in range(len(inColor)):
            output.append(GfxUtil.ConvertColorFormat(inColor[i], inputFormat, outputFormat))
        return output
    
    @staticmethod
    def Detile(data, tileSize, width, height):
        result = [None] * (width * height)
        offset = 0
        for y in range(0, height, tileSize):
            for x in range(0, width, tileSize):
                for y2 in range(tileSize):
                    for x2 in range(tileSize):
                        result[(y + y2) * width + x + x2] = data[offset]
                        offset += 1
    
    @staticmethod
    def DecodeRawComp4x4(pixelData, tex4x4data, palette):
        result = [None] * (len(pixelData) * 4)
        offset = 0
        offset4x4 = 0
        for i in range(0, len(pixelData) * 4, 4 * 4):
            tex4x4 = ReadU16Le(tex4x4data[offset4x4:])
            # not finished
    
    @staticmethod
    def DecodeRaw(pixelData, palette, imageFormat, firstTransparent=False, tex4x4data=None):
        print(imageFormat)
        if imageFormat == ImageFormat.Null:
            raise Exception("Invalid pixel format")
        elif imageFormat == ImageFormat.A3I5:
            result = []
            for i in range(len(pixelData)):
                a = pixelData[i] >> 5
                a = (a << 2) + (a << 1)
                result.append(int((palette[pixelData[i] & 0x1F] & ~0xFF000000) | int((a * 255 / 31) << 24)))
            return result
        elif imageFormat == ImageFormat.Pltt4:
            result = [None] * (len(pixelData) * 4)
            for i in range(len(pixelData)):
                for j in range(4):
                    idx = (pixelData[i] >> (j * 2)) & 0x3
                    result[i * 4 + j] = int(idx != 0 or palette[idx] if not firstTransparent else 0)
            return result
        elif imageFormat == ImageFormat.Pltt16:
            result = [None] * (len(pixelData) * 2)
            for i in range(len(pixelData)):
                idx = pixelData[i] & 0xF
                result[i * 2]     = int(idx != 0 or palette[idx] if not firstTransparent else 0)
                idx               = pixelData[i] >> 4
                result[i * 2 + 1] = int(idx != 0 or palette[idx] if not firstTransparent else 0)
            return result
        elif imageFormat == ImageFormat.Pltt256:
            result = []
            for i in range(len(pixelData)):
                idx = pixelData[i]
                result.append(int(idx != 0 or palette[idx] if not firstTransparent else 0))
            return result
        elif imageFormat == ImageFormat.Comp4x4:
            raise Exception("Image Format Comp4x4 not implemented")
            return GfxUtil.DecodeRawComp4x4(pixelData, tex4x4data, palette)
        elif imageFormat == ImageFormat.Direct:
            return GfxUtil.ConvertColorFormatFromU16(
                ReadU16Le(pixelData, len(pixelData) / 2),
                ColorFormat.ABGR1555, ColorFormat.ARGB8888
            )
        else:
            raise Exception(f"{imageFormat} not supported")
    
    @staticmethod
    def DecodeBmp(data, imageFormat, width, height, palette=None, firstTransparent=False, tex4x4data=None):
        pltt = None
        if palette is not None:
            if len(palette) % 1 == 0:
                pltt = GfxUtil.ConvertColorFormatFromU16(
                    ReadU16Le(palette, len(palette) // 2),
                    ColorFormat.XBGR1555, ColorFormat.ARGB8888
                )
                print('ReadOnlySpan<byte>')
            elif len(palette) % 2 == 0:
                pltt = GfxUtil.ConvertColorFormatFromU16(
                    palette, ColorFormat.XBGR1555, ColorFormat.ARGB8888
                )
                print('ReadOnlySpan<ushort>')
            else:
                raise Exception('Unknown byte format')
        if imageFormat == ImageFormat.Null:
            raise Exception("Image Format: None")
        if imageFormat != ImageFormat.Direct and pltt is None:
            raise Exception("None Palette + Image Format is not Direct")
        if (width & 7) != 0:
            raise Exception("Width error")
        if (height & 7) != 0:
            raise Exception("Height error")
        length = int(width * height * GfxUtil.DataSize[imageFormat.value] / 8)
        if imageFormat == ImageFormat.Comp4x4:
            tex4x4data = tex4x4data[:(length >> 1)]
        bmpdata = GfxUtil.DecodeRaw(data[:length], pltt, imageFormat, firstTransparent, tex4x4data)
        if imageFormat == ImageFormat.Comp4x4:
                bmpdata = GfxUtil.Detile(bmpdata, 4, width, height)
        
        return Rgba8Bitmap(width, height, bmpdata)

class Rgba8Bitmap:
    def __init__(self, width, height, data=None):
        self.Width = width
        self.Height = height
        if data is None:
            self.Pixels = [int] * (width * height)
        else:
            if len(data) != width * height:
                raise ValueError("Data length does not match bitmap size.")
            self.Pixels = data.copy()

    def __getitem__(self, index):
        x = index
        y = index
        return self.Pixels[y * self.Width + x]

    def __setitem__(self, index, value):
        x = index
        y = index
        self.Pixels[y * self.Width + x] = value
    
    def SaveImage(self, FileName):
        imgData = bytearray()
        for pixel in self.Pixels:
            a = (pixel >> 24) & 0xFF  # Alpha channel
            r = (pixel >> 16) & 0xFF  # Red channel
            g = (pixel >> 8) & 0xFF   # Green channel
            b = pixel & 0xFF          # Blue channel
            imgData.extend([r, g, b, a])  # Add RGBA values to the byte array
        
        # Create an Image object using Pillow and save it as PNG
        img = Image.frombytes('RGBA', (self.Width, self.Height), bytes(imgData))
        img.save(FileName)