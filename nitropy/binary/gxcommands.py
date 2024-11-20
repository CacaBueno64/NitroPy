from struct import unpack, Struct
from io import BytesIO
from enum import Enum
import numpy as np
from .nitro import *

class NitroVertexData:
    MtxIdMask     = 0x1F
    CurMtxId      = 0x1F
    HasNormalFlag = 1 << 5
    
    PosIdx      = 0
    NrmClrIdx   = 1
    TexCoordIdx = 2
    MtxIdIdx    = 3
    
    def __init__(self, Position=None, NormalOrColor=None, TexCoord=None, MtxId=None):
        self.Position = Position
        self.NormalOrColor = NormalOrColor
        self.TexCoord = TexCoord
        self.MtxId = MtxId

class DisplayListBuffer:
    def __init__(self, dl=None, vtxData=None, idxData=None, Flags=None):
        self._vtxData = vtxData or []
        self._idxData = idxData or []
        self.Flags = Flags
        self.Read(dl)
    
    def Read(self, dl):
        self.vertices  = []
        self.indices   = []
        self.normal    = []
        self.texCoord  = []
        self.mode      = GxBegin(-1)
        self.color     = []
        self.vtxX      = 0
        self.vtxY      = 0
        self.vtxZ      = 0
        self.useNormal = False
        self.mtxId     = NitroVertexData.CurMtxId
        self.vtxCount  = 0
        self.flags     = 0
        GxCmdUtil.ParseDl(dl, self.ParseDlCallBack)
        self._vtxData = self.vertices
        self._idxData = self.indices
        self.Flags = self.flags
    
    def ParseDlCallBack(self, op, param):
        if op == GxCmd.RestoreMatrix:
            if (param[0] & 0x1F) == 0x1F:
                raise Exception()
            self.mtxId = param[0] & 0x1F
        
        elif op == GxCmd.Color:
            rgb5 = param[0] & 0x7FFF
            self.color = [
                (rgb5 & 0x1F) / 31,
                ((rgb5 >> 5) & 0x1F) / 31,
                ((rgb5 >> 10) & 0x1F) / 31,
            ]
            self.useNormal = False
            self.flags |= DlFlags.HasColor.value
        
        elif op == GxCmd.Normal:
            self.normal = [
                (Short((param[0] & 0x3FF) << 6) >> 6) / 512,
                (Short(((param[0] >> 10) & 0x3FF) << 6) >> 6) / 512,
                (Short(((param[0] >> 20) & 0x3FF) << 6) >> 6) / 512,
            ]
            self.useNormal = True
            self.flags |= DlFlags.HasNormals.value
        
        elif op == GxCmd.TexCoord:
            self.texCoord = [
                Short(param[0] & 0xFFFF) / 512,
                Short(param[0] >> 16) / 512,
            ]
            self.flags |= DlFlags.HasTexCoords.value
        
        elif op == GxCmd.Vertex:
            self.vtxX = Short(param[0] & 0xFFFF)
            self.vtxY = Short(param[0] >> 16)
            self.vtxZ = Short(param[1] & 0xFFFF)
        
        elif op == GxCmd.VertexShort:
            self.vtxX = Short((param[0] & 0x3FF) << 6)
            self.vtxY = Short(((param[0] >> 10) & 0x3FF) << 6)
            self.vtxZ = Short(((param[0] >> 20) & 0x3FF) << 6)
        
        elif op == GxCmd.VertexXY:
            self.vtxX = Short(param[0] & 0xFFFF)
            self.vtxY = Short(param[0] >> 16)
        
        elif op == GxCmd.VertexXZ:
            self.vtxX = Short(param[0] & 0xFFFF)
            self.vtxZ = Short(param[0] >> 16)
        
        elif op == GxCmd.VertexYZ:
            self.vtxY = Short(param[0] & 0xFFFF)
            self.vtxZ = Short(param[0] >> 16)
        
        elif op == GxCmd.VertexDiff:
            self.vtxX += Short(((param[0] & 0x3FF) << 6) >> 6)
            self.vtxY += Short((((param[0] >> 10) & 0x3FF) << 6) >> 6)
            self.vtxZ += Short((((param[0] >> 20) & 0x3FF) << 6) >> 6)
        
        elif op == GxCmd.Begin:
            self.mode     = GxBegin(param[0] & 3)
            self.vtxCount = 0
        
        elif op == GxCmd.End:
            self.mode = GxBegin(-1)
        
        if self.mode != GxBegin.Null and GxCmdUtil.IsVertex(op):
            self.vertices.append(NitroVertexData(
                    [
                        self.vtxX / 4096,
                        self.vtxY / 4096,
                        self.vtxZ / 4096,
                    ],
                    self.normal if self.normal else self.color,
                    self.texCoord,
                    self.mtxId | (NitroVertexData.HasNormalFlag if self.useNormal else 0)
                )
            )
            
            def emitQuad(idxA, idxB, idxC, idxD):
                vtxA = np.array(self.vertices[idxA].Position)
                vtxB = np.array(self.vertices[idxB].Position)
                vtxC = np.array(self.vertices[idxC].Position)
                vtxD = np.array(self.vertices[idxD].Position)
                
                if np.dot(vtxC - vtxA, vtxC - vtxA) < np.dot(vtxD - vtxB, vtxD - vtxB):
                    self.indices.append(idxA)
                    self.indices.append(idxB)
                    self.indices.append(idxC)

                    self.indices.append(idxA)
                    self.indices.append(idxB)
                    self.indices.append(idxC)
                else:
                    self.indices.append(idxA)
                    self.indices.append(idxB)
                    self.indices.append(idxD)

                    self.indices.append(idxB)
                    self.indices.append(idxC)
                    self.indices.append(idxD)
            
            if self.mode == GxBegin.Triangles:
                self.indices.append(len(self.vertices) - 1)
            
            elif self.mode == GxBegin.Quads:
                if (self.vtxCount % 4) == 3:
                    emitQuad(len(self.vertices) - 4, len(self.vertices) - 3, len(self.vertices) - 2, len(self.vertices) - 1)
            
            elif self.mode == GxBegin.TriangleStrip:
                if self.vtxCount < 3:
                    self.indices.append(len(self.vertices) - 1)
                elif (self.vtxCount % 1) != 0:
                    self.indices.append(len(self.vertices) - 2)
                    self.indices.append(len(self.vertices) - 3)
                    self.indices.append(len(self.vertices) - 1)
                else:
                    self.indices.append(len(self.vertices) - 3)
                    self.indices.append(len(self.vertices) - 2)
                    self.indices.append(len(self.vertices) - 1)
            
            elif self.mode == GxBegin.QuadStrip:
                if self.vtxCount >= 3 and (self.vtxCount & 1) == 1:
                    emitQuad(len(self.vertices) - 4, len(self.vertices) - 3, len(self.vertices) - 1, len(self.vertices) - 2)
            
            self.vtxCount += 1

class DlFlags(Enum):
    HasColor = (1 << 0)
    HasNormals = (1 << 1)
    HasTexCoords = (1 << 2)

class GxBegin(Enum):
    Triangles     = 0
    Quads         = 1
    TriangleStrip = 2
    QuadStrip     = 3
    Null          = -1

class GxCmd(Enum):
    Nop = 0x00,
    
    MatrixMode    = 0x10
    PushMatrix    = 0x11
    PopMatrix     = 0x12
    StoreMatrix   = 0x13
    RestoreMatrix = 0x14
    Identity      = 0x15
    LoadMatrix44  = 0x16
    LoadMatrix43  = 0x17
    MultMatrix44  = 0x18
    MultMatrix43  = 0x19
    MultMatrix33  = 0x1A
    Scale         = 0x1B
    Translate     = 0x1C
    
    Color         = 0x20
    Normal        = 0x21
    TexCoord      = 0x22
    Vertex        = 0x23
    VertexShort   = 0x24
    VertexXY      = 0x25
    VertexXZ      = 0x26
    VertexYZ      = 0x27
    VertexDiff    = 0x28
    PolygonAttr   = 0x29
    TexImageParam = 0x2A
    TexPlttBase   = 0x2B
    
    MaterialColor0 = 0x30
    MaterialColor1 = 0x31
    LightVector    = 0x32
    LightColor     = 0x33
    Shininess      = 0x34
    
    Begin = 0x40
    End   = 0x41
    
    SwapBuffers = 0x50
    
    Viewport = 0x60
    
    BoxTest      = 0x70
    PositionTest = 0x71
    VectorTest   = 0x72

class GxCmdUtil:
    @staticmethod
    def GetParamCount(cmd):
        cmdcount = {
            GxCmd.Nop            : 0,
            GxCmd.MatrixMode     : 1,
            GxCmd.PushMatrix     : 0,
            GxCmd.PopMatrix      : 1,
            GxCmd.StoreMatrix    : 1,
            GxCmd.RestoreMatrix  : 1,
            GxCmd.Identity       : 0,
            GxCmd.LoadMatrix44   : 16,
            GxCmd.LoadMatrix43   : 12,
            GxCmd.MultMatrix44   : 16,
            GxCmd.MultMatrix43   : 12,
            GxCmd.MultMatrix33   : 9,
            GxCmd.Scale          : 3,
            GxCmd.Translate      : 3,
            GxCmd.Color          : 1,
            GxCmd.Normal         : 1,
            GxCmd.TexCoord       : 1,
            GxCmd.Vertex         : 2,
            GxCmd.VertexShort    : 1,
            GxCmd.VertexXY       : 1,
            GxCmd.VertexXZ       : 1,
            GxCmd.VertexYZ       : 1,
            GxCmd.VertexDiff     : 1,
            GxCmd.PolygonAttr    : 1,
            GxCmd.TexImageParam  : 1,
            GxCmd.TexPlttBase    : 1,
            GxCmd.MaterialColor0 : 1,
            GxCmd.MaterialColor1 : 1,
            GxCmd.LightVector    : 1,
            GxCmd.LightColor     : 1,
            GxCmd.Shininess      : 32,
            GxCmd.Begin          : 1,
            GxCmd.End            : 0,
            GxCmd.SwapBuffers    : 1,
            GxCmd.Viewport       : 1,
            GxCmd.BoxTest        : 3,
            GxCmd.PositionTest   : 2,
            GxCmd.VectorTest     : 1,
        }
        count = cmdcount.get(cmd)
        if not count:
            count = 0
        return count
    
    @staticmethod
    def IsValid(cmd) -> bool:
        return  cmd.value == GxCmd.Nop.value or \
                cmd.value >= GxCmd.MatrixMode.value and cmd.value <= GxCmd.Translate.value or \
                cmd.value >= GxCmd.Color.value and cmd.value <= GxCmd.TexPlttBase.value or \
                cmd.value >= GxCmd.MaterialColor0.value and cmd.value <= GxCmd.Shininess.value or \
                cmd.value == GxCmd.Begin.value or cmd.value == GxCmd.End.value or \
                cmd.value == GxCmd.SwapBuffers.value or \
                cmd.value == GxCmd.Viewport.value or \
                cmd.value >= GxCmd.BoxTest.value and cmd.value <= GxCmd.VectorTest.value
    
    @staticmethod
    def IsUnsafeParameterless(cmd) -> bool:
        return cmd.value >= GxCmd.MatrixMode.value and GxCmdUtil.GetParamCount(cmd) == 0
    @staticmethod
    def IsVertex(cmd) -> bool:
        return cmd.value >= GxCmd.Vertex.value and cmd.value <= GxCmd.VertexDiff.value
    
    @staticmethod
    def ParseDl(dl, callback):
        offs = 0
        while offs + 4 <= len(dl):
            ops = unpack("<I", dl[offs:offs+4])[0]
            offs += 4
            while ops != 0:
                op = GxCmd(ops & 0xFF)
                if op != GxCmd.Nop and GxCmdUtil.IsValid(op):
                    paramCount = GxCmdUtil.GetParamCount(op)
                    param = []
                    for i in range(paramCount):
                        param.append(unpack("<i", dl[offs:offs+4])[0])
                        offs += 4
                    callback(op, param)
                ops >>= 8