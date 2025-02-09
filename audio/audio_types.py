from typing import Union, Callable, Type
from abc import ABC, abstractmethod
import numpy as np

class AudioData:
    def __init__(self, power_spectrum, mel_energies):
        self.power_spectrum = power_spectrum
        self.mel_energies = mel_energies
    
    def get_ps_mean(self, range):
        if len(range) > 2:
            raise ValueError("Range must be a list of two elements.")
        return np.mean(self.power_spectrum[range[0]:range[1]])
    
    def get_mel_mean(self, range):
        if len(range) > 2:
            raise ValueError("Range must be a list of two elements.")
        return np.mean(self.mel_energies[range[0]:range[1]])
    
class AudioListener(ABC):
    
    def __init__(self, channels, chunk_size, sample_rate):
        self.channels = channels
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        super().__init__()
    
    @abstractmethod
    def __call__(self, data:AudioData) -> bool: # Return False if the listener wants to stop listening
        pass

AudioListenerType = Union[AudioListener, Callable[[AudioData], bool], Type[AudioListener]]


class Processor(ABC):
    
    def __init__(self, chunk_size, sample_rate):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        super().__init__()
        
    @abstractmethod
    def process(self, data) -> AudioData:
        pass