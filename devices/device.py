from abc import ABC, abstractmethod
from enum import Enum

class PacketType(Enum):
    BEAT = 0
    SNARE = 1
    BREAK = 2
    NEW_MUSIC = 3

class PacketStatus(Enum):
    ON = 0
    OFF = 1

class PacketData:
    def __init__(self, packet_type:PacketType, packet_status:PacketStatus):
        self.packet_type = packet_type
        self.packet_status = packet_status
        
class Device(ABC):
    
    def __init__(self):
        success = self.scan_for_device()
        if not success:
            raise Exception("No device was found")
        success = self.init_device()
        if not success:
            raise Exception("The device could not be found")
        super().__init__()
    
    @abstractmethod
    def scan_for_device() -> bool: # Returns if a device was found
        pass
    
    @abstractmethod
    def init_device() -> bool: # Returns if the device was successfully initialized
        pass
    
    
    @property
    @abstractmethod
    def name(self):
        pass
    
    @abstractmethod
    def on(self, packet:PacketData):
        pass
    
    def __str__(self):
        return self.name