from io import BytesIO
from struct import pack, unpack

class G3dFileHeader:
    def __init__(self, data=None, expectedSignature=None, signature=None, version=None):
        if data and expectedSignature:
            self.Read(data, expectedSignature)
        elif signature and version:
            self.Signature  = signature
            self.ByteOrder  = 0xFEFF
            self.Version    = version
            self.HeaderSize = 16

    def Read(self, data, expectedSignature):
        self.Signature = unpack("<I", data.read(4))[0]
        self.ByteOrder = unpack("<H", data.read(2))[0]
        self.Version = unpack("<H", data.read(2))[0]
        self.FileSize = unpack("<I", data.read(4))[0]
        self.HeaderSize = unpack("<H", data.read(2))[0]
        self.NrBlocks = unpack("<H", data.read(2))[0]
        self.BlockOffsets = []
        
        if self.Signature != expectedSignature:
            raise ValueError(f"Wrong file signature\nGot : {self.Signature}\nExpected {expectedSignature}")
        
        for i in range(self.NrBlocks):
            self.BlockOffsets.append(unpack("<I", data.read(4))[0])

# not really a dictionary
class G3dDictionary:
    NAME_TOO_LONG_EXCEPTION_MESSAGE = "Names can be at most 16 characters long."
    NAME_LENGTH = 16
    
    UNSUPPORTED_REVISION_EXCEPTION_MESSAGE = "Unsupported dictionary revision. Got {0}, expected {1}."
    ENTRY_SIZE_MISMATCH_EXCEPTION_MESSAGE = "Dictionary entry size mismatch. Got {0}, expected {1}."
    INVALID_NUMBER_OF_BYTES_READ_EXCEPTION_MESSAGE = "Invalid number of bytes read for dictionary entry. {0} bytes were read, expected {1} bytes."
    
    DICTIONARY_REVISION = 0
    NAME_LENGTH = 16
    
    DataSize = 4
    
    def __init__(self, data=None):
        self.dictionary = []
        if data:
            self.ReadG3dDictionary(data)
    
    def ReadG3dDictionary(self, data):
        startPosition = data.tell()
        
        # Header
        revision = unpack("<B", data.read(1))[0]
        entryCount = unpack("<B", data.read(1))[0]
        dictionarySize = unpack("<H", data.read(2))[0]
        data.read(2)
        entriesOffset = unpack("<H", data.read(2))[0]
        self.ThrowIfInvalidRevision(revision)
        
        # Entries
        data.seek(startPosition + entriesOffset)
        entrySize = unpack("<H", data.read(2))[0]
        namesOffset = unpack("<H", data.read(2))[0]
        Data = self.ReadData(data, entryCount)
        
        data.seek(startPosition + entriesOffset + namesOffset)
        
        for i in range(entryCount):
            name = data.read(self.NAME_LENGTH).decode().strip("\x00")
            self.dictionary.append([name, Data[i]])
        
        data.seek(startPosition + dictionarySize)
    
    def ThrowIfInvalidRevision(self, revision):
        if revision != self.DICTIONARY_REVISION:
            raise ValueError(f"{self.UNSUPPORTED_REVISION_EXCEPTION_MESSAGE}")
    
    def ReadData(self, data, entryCount):
        Data = [None] * entryCount
        for i in range(entryCount):
            entryStart = data.tell()
            Data[i] = unpack("<I", data.read(4))[0]
            
            dataRead = data.tell() - entryStart
            if dataRead != self.DataSize:
                raise ValueError(f"{self.INVALID_NUMBER_OF_BYTES_READ_EXCEPTION_MESSAGE}")
        return Data

def ReadSignature(data, expectedSignature):
    signature = unpack("<I", data.read(4))[0]
    if expectedSignature != signature:
        raise ValueError(f"Wrong signature\nGot : {signature}\nExpected {expectedSignature}")
    return signature

def Fx32(data):
    return unpack("<i", data.read(4))[0] / 4096.0
def Fx16(data):
    return unpack("<h", data.read(2))[0] / 4096.0
def ReadVecFx32(data):
    return tuple(Fx32(data), Fx32(data), Fx32(data))
def ReadVecFx16(data):
    return tuple(Fx16(data), Fx16(data), Fx16(data))