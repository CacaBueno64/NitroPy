from .nitro import *
from struct import unpack, unpack_from
from io import BytesIO
from enum import Enum
from mathutils import Matrix, Vector

class G3dRenderState:
    def __init__(self):
        self.c = 0
        self.SbcData = None
        self.RenderObject = None
        self.Flag = 0
        self._callbackFunctions = [object] * Sbc.CommandNum
        self._callbackTimings = [object] * Sbc.CommandNum
        self.CurrentNode = 0
        self.CurrentMaterial = 0
        self.CurrentNodeDescription = 0
        self.MaterialAnimation = None
        self.JointAnimation = None
        self.VisibilityAnimation = None
        self.IsMaterialCached = [False] * G3dConfig.MaxMaterialCount
        self.IsScaleCacheOne = [False] * G3dConfig.MaxJointCount
        self.IsEnvelopeCached = [False] * G3dConfig.MaxJointCount
        self.NodeResource = None
        self.MaterialResource = None
        self.ShapeResource = None
        self.PosScale = 0
        self.InversePosScale = 0
        self.GetJointScale = None
        self.SendJointSrt = None
        self.SendTexSrt = None

        self.TmpMatAnmResult = MaterialAnimationResult()
        self.TmpJntAnmResult = JointAnimationResult()
        self.TmpVisAnmResult = VisibilityAnimationResult()
    
    def Clear(self):
        self.SbcData = None
        self.RenderObject = None
        self.Flag = 0
        self._callbackFunctions = [None] * Sbc.CommandNum
        self._callbackTimings = [None] * Sbc.CommandNum
        self.CurrentNode = 0
        self.CurrentMaterial = 0
        self.CurrentNodeDescription = 0
        self.MaterialAnimation = None
        self.JointAnimation = None
        self.VisibilityAnimation = None
        self.IsMaterialCached = [False] * G3dConfig.MaxMaterialCount
        self.IsScaleCacheOne = [False] * G3dConfig.MaxJointCount
        self.IsEnvelopeCached = [False] * G3dConfig.MaxJointCount
        self.NodeResource = None
        self.MaterialResource = None
        self.ShapeResource = None
        self.PosScale = 0
        self.InversePosScale = 0
        self.GetJointScale = None
        self.SendJointSrt = None
        self.SendTexSrt = None

        self.TmpMatAnmResult.Clear()
        self.TmpJntAnmResult.Clear()
        self.TmpVisAnmResult.Clear()
    
    def SetCallback(self, function, command, timing):
        self._callbackFunctions[command] = function
        self._callbackTimings[command] = timing
    
    def GetCallbackTiming(self, cmd):
        return self._callbackTimings[cmd] if self._callbackFunctions[cmd] is not None else SbcCallbackTiming.Null
    
    def PerformCallbackA(self, context, cmd) -> bool:
        if self.GetCallbackTiming(cmd) == SbcCallbackTiming.TimingA:
            self.Flag &= ~G3dRenderStateFlag.Skip.value
            self._callbackFunctions[cmd](context)
            return self.Flag & G3dRenderStateFlag.Skip.value != 0
        return False
    def PerformCallbackB(self, context, cmd) -> bool:
        if self.GetCallbackTiming(cmd) == SbcCallbackTiming.TimingB:
            self.Flag &= ~G3dRenderStateFlag.Skip.value
            self._callbackFunctions[cmd](context)
            return self.Flag & G3dRenderStateFlag.Skip.value != 0
        return False
    def PerformCallbackC(self, context, cmd) -> bool:
        if self.GetCallbackTiming(cmd) == SbcCallbackTiming.TimingC:
            self.Flag &= ~G3dRenderStateFlag.Skip.value
            self._callbackFunctions[cmd](context)
            return self.Flag & G3dRenderStateFlag.Skip.value != 0
        return False

class SbcCallbackTiming(Enum):
    Null = 0
    TimingA = 1
    TimingB = 2
    TimingC = 3

class SbcCommand(Enum):
    Nop = 0x00
    Return = 0x01
    Node = 0x02
    Matrix = 0x03
    Material = 0x04
    Shape = 0x05
    NodeDescription = 0x06
    Billboard = 0x07
    BillboardY = 0x08
    NodeMix = 0x09
    CallDisplayList = 0x0A
    PosScale = 0x0B
    EnvironmentMap = 0x0C
    ProjectionMap = 0x0D

class SbcNodeDescFlag:
    MayaSscApply  = 0x01
    MayaSscParent = 0x02

class Sbc:
    NoCmd = 0x1f
    CommandNum = 0x20
    SbcFlg000 = 0x00
    SbcFlg001 = 0x20
    SbcFlg010 = 0x40
    SbcFlg011 = 0x60
    SbcFlg100 = 0x80
    SbcFlg101 = 0xa0
    SbcFlg110 = 0xc0
    SbcFlg111 = 0xe0
    SbcCmdMask = 0x1f
    SbcFlgMask = 0xe0
    MtxStackSys  = 30
    MtxStackUser = 29
    
    def __init__(self, context):
        self._context = context
        self.SbcFunctionTable = [
            self.SbcNop,
            self.SbcRet,
            self.SbcNode,
            self.SbcMtx,
            self.SbcMat,
            self.SbcShp,
            self.SbcNodeDesc,
            self.SbcBB,
            self.SbcBBY,
            self.SbcNodeMix,
            self.SbcCallDl,
            self.SbcPosScale,
            self.SbcEnvMap,
            self.SbcPrjMap,
        ]
        self.FuncSbcShpTable = [
            self.SbcShpDefault
        ]
        self.FuncSbcMatTable = [
            self.SbcMatDefault
        ]
        
        self._materialColorMask = [
            0x00000000,
            0x00007fff,
            0x7fff0000,
            0x7fff7fff,
            0x00008000,
            0x0000ffff,
            0x7fff8000,
            0x7fffffff
        ]
    
    def DrawInternal(self, renderState, renderObj):
        renderState.Clear()
        renderState.IsScaleCacheOne[0] = True
        
        renderState.Flag = G3dRenderStateFlag.NodeVisible.value
        
        renderState.SbcData = renderObj.UserSbc or renderObj.ModelResource.Sbc
        
        renderState.RenderObject = renderObj
        
        renderState.NodeResource  = renderObj.ModelResource.Nodes
        renderState.MaterialResource       = renderObj.ModelResource.Materials
        renderState.ShapeResource       = renderObj.ModelResource.Shapes
        renderState.GetJointScale = self._context.GetJointScaleFuncArray[renderObj.ModelResource.Info.ScalingRule]
        renderState.SendJointSrt   = self._context.SendJointSrtFuncArray[renderObj.ModelResource.Info.ScalingRule]
        renderState.SendTexSrt   = self._context.SendTexSrtFuncArray[renderObj.ModelResource.Info.TextureMatrixMode]
        renderState.PosScale     = renderObj.ModelResource.Info.PosScale
        renderState.InversePosScale  = renderObj.ModelResource.Info.InversePosScale
        
        if renderObj.CallbackFunction is not None and renderObj.CallbackCmd < Sbc.CommandNum:
            renderState.SetCallback(renderObj.CallbackFunction, renderObj.CallbackCmd, renderObj.CallbackTiming)
        
        if renderObj.Flag & G3dRenderObjectFlag.Record.value != 0:
            renderState.Flag |= G3dRenderStateFlag.OptRecord.value

        if renderObj.Flag & G3dRenderObjectFlag.NoGeCmd.value != 0:
            renderState.Flag |= G3dRenderStateFlag.OptNoGeCmd.value

        if renderObj.Flag & G3dRenderObjectFlag.SkipSbcDraw.value != 0:
            renderState.Flag |= G3dRenderStateFlag.OptSkipSbcDraw.value

        if renderObj.Flag & G3dRenderObjectFlag.SkipSbcMtxCalc.value != 0:
            renderState.Flag |= G3dRenderStateFlag.OptSkipSbcMtxCalc.value
        
        if renderObj.CallbackInitFunction:
            renderObj.CallbackInitFunction(self._context)
        
        while True:
            renderState.Flag &= ~G3dRenderStateFlag.Skip.value
            cmd = self.GetSbc(renderState.SbcData, renderState.c) & Sbc.SbcCmdMask
            opt = self.GetSbc(renderState.SbcData, renderState.c) & Sbc.SbcFlgMask
            self.SbcFunctionTable[cmd](renderState, opt)
            if renderState.Flag & G3dRenderStateFlag.Return.value != 0:
                break
        
        renderObj.Flag &= ~G3dRenderObjectFlag.Record.value
    
    def GetSbc(self, data, ptr):
        return unpack("<B", data[ptr:ptr+1])[0]
    
    def Draw(self, renderObj):
        if renderObj.TestFlag(G3dRenderObjectFlag.HintObsolete.value):
            # incomplete
            pass
        
        if self._context.RenderState is not None:
            self.DrawInternal(self._context.RenderState, renderObj)
        else:
            self._context.RenderState = G3dRenderState()
            self.DrawInternal(self._context.RenderState, renderObj)
            self._context.RenderState = None
    
    def SbcNop(self, renderState, opt):
        renderState.c += 1
    
    def SbcRet(self, renderState, opt):
        renderState.Flag |= G3dRenderStateFlag.Return.value
    
    def SbcNode(self, renderState, opt):
        if renderState.Flag & G3dRenderStateFlag.OptSkipSbcDraw.value == 0:
            renderState.CurrentNode = self.GetSbc(renderState.SbcData, renderState.c + 1)
            curNode = renderState.CurrentNode
            renderState.Flag |= G3dRenderStateFlag.CurrentNodeValid.value
            renderState.VisibilityAnimation = renderState.TmpVisAnmResult

            if not renderState.PerformCallbackA(self._context, SbcCommand.Node.value):
                #incomplete
                if renderState.RenderObject.VisibilityAnimations is None or \
                    not renderState.RenderObject.VisibilityAnimationMayExist[curNode]:
                        renderState.VisibilityAnimation.IsVisible = self.GetSbc(renderState.SbcData, renderState.c + 2) & 1 == 1

            if not renderState.PerformCallbackB(self._context, SbcCommand.Node.value):
                if renderState.VisibilityAnimation.IsVisible:
                    renderState.Flag |= G3dRenderStateFlag.NodeVisible.value
                else:
                    renderState.Flag &= ~G3dRenderStateFlag.NodeVisible.value
            
            renderState.PerformCallbackC(self._context, SbcCommand.Node.value)
        
        renderState.c += 3
    
    def SbcMtx(self, renderState, opt):
        if renderState.Flag & G3dRenderStateFlag.OptSkipSbcDraw.value == 0 and \
            renderState.Flag & G3dRenderStateFlag.NodeVisible.value != 0:
                if not renderState.PerformCallbackA(self._context, SbcCommand.Matrix.value):
                    if renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
                        self._context.GeState.RestoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + 1))
            
                renderState.PerformCallbackC(self._context, SbcCommand.Matrix.value)
        
        renderState.c += 2
    
    def SbcMatDefault(self, renderState, opt, mat, idxMat):
        #i have not enough patience to do this sorry
        pass
    
    def SbcMat(self, renderState, opt):
        if renderState.Flag & G3dRenderStateFlag.OptSkipSbcDraw.value == 0:
            idxMat = self.GetSbc(renderState.SbcData, renderState.c + 1)
            if renderState.Flag & G3dRenderStateFlag.NodeVisible.value != 0 or \
                not renderState.Flag & G3dRenderStateFlag.CurrentMaterialValid.value != 0 and \
                idxMat == renderState.CurrentMaterial:
                    mat = renderState.MaterialResource.Materials[idxMat]
                    self.FuncSbcMatTable[mat.ItemTag](renderState, opt, mat, idxMat)
        
        renderState.c += 2
    
    def SbcShpDefault(self, renderState, opt, shp, shpIdx):
        if not renderState.PerformCallbackA(self._context, SbcCommand.Shape.value) and \
            renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
                self._context.RenderShp(shp, renderState.RenderObject.ShapeProxies[shpIdx])
        
        renderState.PerformCallbackB(self._context, SbcCommand.Shape.value)
        renderState.PerformCallbackC(self._context, SbcCommand.Shape.value)
    
    def SbcShp(self, renderState, opt):
        if renderState.Flag & G3dRenderStateFlag.OptSkipSbcDraw.value == 0 and \
            renderState.Flag & G3dRenderStateFlag.MaterialTransparent.value == 0 and \
            renderState.Flag & G3dRenderStateFlag.NodeVisible.value != 0:
                idxShp = self.GetSbc(renderState.SbcData, renderState.c + 1)
                shp    = renderState.ShapeResource.Shapes[idxShp]
                self.FuncSbcShpTable[shp.ItemTag](renderState, opt, shp, idxShp)
        
        renderState.c += 2
    
    def SbcNodeDesc(self, renderState, opt):
        cmdLen = 4
        
        idxNode = self.GetSbc(renderState.SbcData, renderState.c + 1)
        renderState.CurrentNodeDesc = idxNode
        renderState.Flag |= G3dRenderStateFlag.CurrentNodeDescriptionValid.value
        
        if renderState.Flag & G3dRenderStateFlag.OptSkipSbcMtxCalc.value != 0:
            if opt == Sbc.SbcFlg010 or opt == Sbc.SbcFlg011:
                cmdLen += 1
            
            if opt == Sbc.SbcFlg001 or opt == Sbc.SbcFlg011:
                cmdLen += 1
                if renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
                    self._context.GeState.RestoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + 4))
            
            renderState.c += cmdLen
            return
        
        if opt == Sbc.SbcFlg010 or opt == Sbc.SbcFlg011:
            cmdLen += 1
            if renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
                self._context.GeState.RestoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + (4 if opt == Sbc.SbcFlg010 else 5)))
        
        renderState.JointAnimation = renderState.TmpJntAnmResult
        
        if not renderState.PerformCallbackA(self._context, SbcCommand.NodeDescription.value):
            anmResult = 0
            isUseRecordData = False
            
            if renderState.RenderObject.RecordedJointAnimations is not None:
                anmResult       = renderState.RenderObject.RecordedJointAnimations[idxNode]
                isUseRecordData = (renderState.Flag & G3dRenderStateFlag.OptRecord) == 0
            else:
                isUseRecordData = False
                anmResult       = renderState.TmpJntAnmResult
            
            if not isUseRecordData:
                anmResult.Flag = 0

                if renderState.RenderObject.JointAnimations is None:
                    nodeData = renderState.NodeResource.Data[idxNode]
                    nodeData.GetTranslation(anmResult)
                    nodeData.GetRotation(anmResult)
                    #incomplete
                    renderState.GetJointScale(anmResult, nodeData, renderState.SbcData, renderState.c, self._context)
            
            renderState.JointAnimation = anmResult
        
        if not renderState.PerformCallbackB(self._context, SbcCommand.NodeDescription.value) \
                    and renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
            #incomplete
            renderState.SendJointSrt(renderState.JointAnimation, self._context)
        
        renderState.JointAnimation = None
        
        callbackFlag = renderState.PerformCallbackC(self._context, SbcCommand.NodeDescription.value)
        if opt == Sbc.SbcFlg001 or opt == Sbc.SbcFlg011:
            cmdLen += 1
            
            if not callbackFlag and renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0:
                self._context.GeState.StoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + 4))
        
        renderState.c += cmdLen
    
    def SbcBB(self, renderState, opt):
        print("sbcbb")
        pass
    def SbcBBY(self, renderState, opt):
        print("sbcbby")
        pass
    def SbcNodeMix(self, renderState, opt):
        w = 0
        evpMtx = renderState.RenderObject.ModelResource.EnvelopeMatrices
        numMtx = self.GetSbc(renderState.SbcData, renderState.c + 2)
        p = 3
        y = None
        
        sumM = Matrix.Identity(4)
        sumN = Matrix.Identity(4)
        
        for i in range(numMtx):
            idxJnt = self.GetSbc(renderState.SbcData, renderState.c + p + 1)
            evpCached = renderState.IsEnvelopeCached[idxJnt]
            
            x = self._context.GlobalRenderState.EnvelopeCache[idxJnt]
            if not evpCached:
                renderState.IsEnvelopeCached[idxJnt] = True
                self._context.GeState.RestoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + p))
                self._context.GeState.MatrixMode = GxMtxMode.Position
                self._context.GeState.MultMatrix(evpMtx.Envelopes[idxJnt].InversePositionMatrix)
            
            if i != 0:
                sumN[0] = y.DirectionMtx[0]
                sumN[1] = y.DirectionMtx[1]
                sumN[2] = y.DirectionMtx[2]
            
            if not evpCached:
                x.PositionMtx = self._context.GeState.PositionMatrix
                self._context.GeState.MatrixMode = GxMtxMode.PositionVector
                self._context.GeState.MultMatrix(evpMtx.Envelopes[idxJnt].InverseDirectionMatrix)
            
            w = self.GetSbc(renderState.SbcData, renderState.c + p + 1) / 256.0
            
            sumM[0] += w * x.PositionMtx[0]
            sumM[1] += w * x.PositionMtx[1]
            sumM[2] += w * x.PositionMtx[2]
            sumM[3] += w * x.PositionMtx[3]
            
            p += 3
            y = self._context.GlobalRenderState.EnvelopeCache[idxJnt]
            
            if not evpCached:
                y.DirectionMtx = self._context.GeState.DirectionMatrix
        
        sumN[0] += w * y.DirectionMtx[0]
        sumN[1] += w * y.DirectionMtx[1]
        sumN[2] += w * y.DirectionMtx[2]
        
        self._context.GeState.LoadMatrix(sumN)
        self._context.GeState.MatrixMode = GxMtxMode.Position
        self._context.GeState.LoadMatrix(sumM)
        self._context.GeState.MatrixMode = GxMtxMode.PositionVector

        self._context.GeState.StoreMatrix(self.GetSbc(renderState.SbcData, renderState.c + 1))
        renderState.c += 3 + self.GetSbc(renderState.SbcData, renderState.c + 2) * 3
    
    def SbcCallDl(self, renderState, opt):
        print("sbccalldl")
        pass
    
    def SbcPosScale(self, renderState, opt):
        if renderState.Flag & G3dRenderStateFlag.OptNoGeCmd.value == 0 and \
            renderState.Flag & G3dRenderStateFlag.OptSkipSbcDraw.value == 0:
                s = renderState.PosScale if opt == Sbc.SbcFlg000 else renderState.InversePosScale
                self._context.GeState.Scale(Vector([s, s, s]))
        
        renderState.c += 1
    
    def SbcEnvMap(self, renderState, opt):
        print("sbcenvmap")
        pass
    def SbcPrjMap(self, renderState, opt):
        print("sbcprjmap")
        pass