from abc import ABC, abstractmethod
from enum import Enum

class PacketType(Enum):
    BEAT = 0
    SNARE = 1
    BREAK = 2
    NEW_MUSIC = 3 # Should be on when silent and off when the music starts
    DROP = 4

class PacketStatus(Enum):
    ON = 0
    OFF = 1

class PacketData:
    def __init__(self, packet_type:PacketType, packet_status:PacketStatus):
        self.packet_type = packet_type
        self.packet_status = packet_status
        
class Device(ABC):
    
    def __init__(self, fatal_non_discovery=True):
        success = self.scan_for_device()
        if not success and fatal_non_discovery:
            raise Exception("No device was found")
        elif not success:
            super().__init__()
            return
        success = self.init_device()
        if not success and fatal_non_discovery:
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