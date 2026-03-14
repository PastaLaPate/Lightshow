## Linux Audio Detection Fix - Summary

### Problem
Audio detection quality on Linux was significantly worse than Windows, with weak and unclear spikes due to:
1. Quiet audio input from default Linux input devices
2. Inconsistent audio normalization for float32 samples
3. Sub-optimal default processor sensitivity

### Changes Made

#### 1. **Audio Amplification** ([audio_streams.py](lightshow/audio/audio_streams.py#L97-L104))
Added intelligent amplification in the audio callback:
- Detects quiet audio (0.001 < max < 0.1 range)
- Applies 5x amplification to quiet signals
- Clamps values exceeding [-1, 1] range

This compensates for Linux's quieter default input devices compared to Windows WASAPI loopback.

#### 2. **Improved Float Normalization** ([processors.py](lightshow/audio/processors.py#L37-L44))
Fixed processor normalization for float32 audio:
- More robust detection of underutilized audio range
- Only normalizes when truly needed (values < 0.001 or > 1.01)
- Prevents over-normalization of already correct signals

#### 3. **Higher Default Sensitivity** ([processors.py](lightshow/audio/processors.py#L14))
Increased default sensitivity from 1.0 to 2.0:
- Makes mel-energies more responsive to audio features
- Better spike detection on quiet Linux systems

#### 4. **Configurable Audio Sensitivity** ([config.py](lightshow/utils/config.py))
Added `audio_sensitivity` configuration:
- Defaults to 2.0 on all platforms
- Can be tuned in `~/.LightShow/config.json`
- Example: `{"audio_sensitivity": 3.0}` for even more sensitivity

### Testing

To verify the improvements work on your system:

```bash
# Check your audio configuration
python -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"

# Monitor audio levels in real-time
python debug_audio.py
```

### Tuning on Linux

If detection is still too quiet or too sensitive, adjust in `~/.LightShow/config.json`:

```json
{
  "audio_sensitivity": 3.0
}
```

Common values:
- `1.0` - Similar to Windows WASAPI behavior
- `2.0` - Good for most Linux setups (default)
- `3.0-4.0` - Very quiet systems or weak speakers
- `0.5-1.0` - If too much noise is detected

### Why Windows vs Linux?
- **Windows WASAPI**: Captures speaker output directly at full volume
- **Linux PulseAudio/PipeWire**: Uses system input device which may be set to microphone at low volume

These changes normalize that difference without losing detection quality.
