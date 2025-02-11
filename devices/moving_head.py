from typing import List
from pywifi.iface import Interface
from device import *
import scapy
import time

MovingHeadCount = 0

class MovingHead(Device):
    def __init__(self):
        self.id = MovingHeadCount
        self.ip = ""
        MovingHeadCount += 1
        super().__init__()
    
    def scan_for_device(self):
        self.wifi_interface.scan()
        time.sleep(0.5)
        results = self.wifi_interface.scan_results()
        
        return False
            
    
    @property
    def name(self):
        return f"MovingHead #{self.id} Connected to {self.ip}"