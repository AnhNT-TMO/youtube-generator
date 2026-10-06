import math
import os
import re
import struct
import wave


SR = 48000
SF2 = os.path.expanduser("~/ace-step/sf2/MuseScore_General.sf2")
PIANO_SF2 = os.path.expanduser("~/ace-step/sf2/SalamanderGrandPiano.sf2")
LEAD, LH, HARP, CELESTA, MUSICBOX, STRINGS, PAD, GLOCK, VOICE = range(9)
VIBRAPHONE = 10
VIOLA, CELLO = 11, 12
PROGRAMS = {LEAD: 0, LH: 0, HARP: 46, CELESTA: 8, MUSICBOX: 10, STRINGS: 49, PAD: 89, GLOCK: 9, VOICE: 52,
            VIBRAPHONE: 11, VIOLA: 41, CELLO: 42}
ROOTS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
QUALITY = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10),
           "dim": (0, 3, 6), "sus4": (0, 5, 7), "sus2": (0, 2, 7), "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9)}
CHORD_RE = re.compile(r"^([A-G])([#b]?)(|m|7|maj7|m7|dim|sus4|sus2|6|m6)(/([A-G])([#b]?))?$")


def pc_of(root, acc):
    return (ROOTS[root] + (1 if acc == "#" else -1 if acc == "b" else 0)) % 12


def parse_chord(sym):
    match = CHORD_RE.fullmatch(sym)
    if match is None:
        raise ValueError(f"Unsupported chord symbol: {sym}")
    root = pc_of(match.group(1), match.group(2))
    tones = [(root + interval) % 12 for interval in QUALITY[match.group(3)]]
    bass = pc_of(match.group(5), match.group(6)) if match.group(5) else root
    return root, tones, bass


def shift_chord(chord, semis):
    root, tones, bass = chord
    return (root + semis) % 12, [(tone + semis) % 12 for tone in tones], (bass + semis) % 12


def write_midi(path, events, bpm):
    if not math.isfinite(bpm) or bpm <= 0:
        raise ValueError("MIDI BPM must be finite and positive")
    tpq = 480

    def vlq(value):
        out = [value & 0x7F]
        value >>= 7
        while value:
            out.append((value & 0x7F) | 0x80)
            value >>= 7
        return bytes(reversed(out))

    tracks = []
    tempo = int(60_000_000 / bpm)
    tracks.append(b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big") + b"\x00\xff\x2f\x00")
    for channel in sorted({event[4] for event in events}):
        data, last = bytearray(), 0
        data += b"\x00" + bytes([0xC0 | channel, PROGRAMS[channel]])
        for when, on, key, velocity, chan in events:
            if chan != channel:
                continue
            tick = int(round(when * bpm / 60 * tpq))
            data += vlq(max(0, tick - last)) + bytes([(0x90 if on else 0x80) | channel, key, velocity if on else 0])
            last = max(last, tick)
        data += b"\x00\xff\x2f\x00"
        tracks.append(bytes(data))
    with open(path, "wb") as handle:
        handle.write(b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), tpq))
        for track in tracks:
            handle.write(b"MTrk" + struct.pack(">I", len(track)) + track)


def render(events, total_s):
    if any(event[4] in (LEAD, LH) for event in events) and not os.path.exists(PIANO_SF2):
        raise FileNotFoundError(f"Requested piano SoundFont unavailable: {PIANO_SF2}")
    import numpy as np
    import tinysoundfont

    synth = tinysoundfont.Synth(samplerate=SR, gain=-3.0)
    sfid = synth.sfload(SF2)
    piano = synth.sfload(PIANO_SF2) if os.path.exists(PIANO_SF2) else None
    for channel, preset in PROGRAMS.items():
        if channel in (LEAD, LH) and piano is not None:
            synth.program_select(channel, piano, 0, 0)
        else:
            synth.program_select(channel, sfid, 0, preset)
    out, now = [], 0
    for when, on, key, velocity, channel in events + [(total_s, 0, 0, 0, 0)]:
        target = int(when * SR)
        if target > now:
            out.append(np.frombuffer(synth.generate(target - now), dtype=np.float32).reshape(-1, 2).copy())
            now = target
        if key:
            synth.noteon(channel, key, velocity) if on else synth.noteoff(channel, key)
    return np.concatenate(out)


def write_wav(path, samples):
    import numpy as np

    samples = samples / (np.abs(samples).max() + 1e-9) * 10 ** (-1 / 20)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes((samples * 32767).astype("<i2").tobytes())
