#!/usr/bin/env python3
import importlib.util

if importlib.util.resolve_name("soundcard", ""):
    import soundcard as sc
else:
    try:
        import soundcard as sc
    except Exception:
        raise Exception("Install soundcard!")

if __name__ == "__main__":
    def_mic_id = sc.default_microphone().id
    def_speaker_id = sc.default_speaker().id
    for speaker in sc.all_speakers():
        print(">" if speaker.id == def_speaker_id else "", end="")
        print(f"Speaker: {speaker.id}")
        print(f"  Name: {speaker.name}")
        print(f"  Channels: {speaker.channels}")
    for mic in sc.all_microphones(include_loopback=True):
        print(">" if mic.id == def_mic_id else "", end="")
        print(f"Microphone: {mic.id}")
        print(f"  Name: {mic.name}")
        print(f"  Channels: {mic.channels}")
        print(f"  Is loopback: {mic.isloopback}")
