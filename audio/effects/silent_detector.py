import os
import inspect
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from audio_streams import AudioData

class SilentDetector:
  def detect(self, data: AudioData):
    return data.get_ps_mean([0, 20000]) < 200 # 200 bcs it's a silent detector