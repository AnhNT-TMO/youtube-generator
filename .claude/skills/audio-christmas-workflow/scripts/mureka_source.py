#!/usr/bin/env python3
import argparse
import glob
import hashlib
import json
import math
import os
import struct
import wave
from pathlib import Path

SR = 48000
CHANNEL = 0
PROGRAM = 0


def vlq(value):
    out = [value & 0x7f]
    value >>= 7
    while value:
        out.append((value & 0x7f) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def write_midi(path, notes, bpm):
    tpq = 480
    tempo = int(round(60000000 / bpm))
    tempo_track = b'\x00\xff\x51\x03' + tempo.to_bytes(3, 'big') + b'\x00\xff\x2f\x00'
    events = []
    for start, end, pitch in notes:
        on = int(round(start * bpm / 60 * tpq))
        off = int(round(end * bpm / 60 * tpq))
        events.extend([(on, 1, pitch), (off, 0, pitch)])
    events.sort(key=lambda item: (item[0], item[1]))
    data = bytearray(b'\x00' + bytes([0xc0 | CHANNEL, PROGRAM]))
    last = 0
    for tick, on, pitch in events:
        data += vlq(max(0, tick - last))
        data += bytes([(0x90 if on else 0x80) | CHANNEL, pitch, 86 if on else 0])
        last = max(last, tick)
    data += b'\x00\xff\x2f\x00'
    track = bytes(data)
    with open(path, 'wb') as handle:
        handle.write(b'MThd' + struct.pack('>IHHH', 6, 1, 2, tpq))
        handle.write(b'MTrk' + struct.pack('>I', len(tempo_track)) + tempo_track)
        handle.write(b'MTrk' + struct.pack('>I', len(track)) + track)


def render_wav(path, notes, duration_s, sf2):
    import numpy as np
    import soundfile as sf
    import tinysoundfont

    synth = tinysoundfont.Synth(samplerate=SR, gain=-3.0)
    sfid = synth.sfload(str(sf2))
    synth.program_select(CHANNEL, sfid, 0, PROGRAM)
    events = []
    for start, end, pitch in notes:
        events.extend([(start, 1, pitch), (end, 0, pitch)])
    events.sort(key=lambda item: (item[0], item[1]))
    chunks = []
    now = 0
    for when, on, pitch in events + [(duration_s, 0, 0)]:
        target = int(round(when * SR))
        if target > now:
            chunks.append(np.frombuffer(synth.generate(target - now), dtype=np.float32).reshape(-1, 2).copy())
            now = target
        if pitch:
            if on:
                synth.noteon(CHANNEL, pitch, 86)
            else:
                synth.noteoff(CHANNEL, pitch)
    audio = np.concatenate(chunks) if chunks else np.zeros((1, 2), dtype=np.float32)
    peak = float(np.max(np.abs(audio)))
    if peak:
        audio = audio * (10 ** (-3 / 20)) / peak
    sf.write(str(path), audio, SR, subtype='PCM_24')


def source_files(root):
    return {Path(path).stem: Path(path) for path in glob.glob(str(root / 'melodies' / 'b*' / '*.json'))}


def audit_is_independent(root, slug):
    allowlist_path = root / 'MUREKA-ALLOWLIST.json'
    allowlist = json.loads(allowlist_path.read_text()) if allowlist_path.exists() else {'songs': {}}
    allow = allowlist.get('songs', {}).get(slug)
    if not allow:
        return False, 'not in PM-approved Mureka allowlist'
    audit_path = root / 'pd-audit' / f'{slug}.json'
    if not audit_path.exists():
        return False, 'missing audit JSON'
    basis = allow.get('basis', '')
    if basis.lower().startswith('ceo exception'):
        return True, basis
    data = json.loads(audit_path.read_text())
    text = json.dumps(data, ensure_ascii=False).upper()
    if 'NO_SCAN' in text:
        return False, 'audit contains NO_SCAN'
    melody = data.get('melody', {})
    pm_override = allow.get('basis', '').lower().startswith('pm re-audit')
    if pm_override:
        return True, allow.get('basis', '')
    scans = []
    for source in melody.get('pd_sources', []):
        evidence = source.get('evidence', [])
        compared = source.get('compared', '').lower()
        has_print = any('print-' in item and item.endswith('.abc') for item in evidence)
        has_compare = any('compare-' in item and item.endswith('.txt') for item in evidence)
        files_exist = all((root / 'pd-audit' / item).exists() for item in evidence)
        provisional = any('independent-initial' in item or 'provisional-not-independent' in item.lower() for item in evidence)
        if (source.get('kind') == 'scan' and int(source.get('year', 9999)) <= 1930 and
                'independent transcription' in compared and has_print and has_compare and files_exist and not provisional):
            scans.append(source)
    if data.get('verdict') != 'clean' or melody.get('status') != 'pd_confirmed':
        return False, f"verdict={data.get('verdict')} melody={melody.get('status')}"
    if not scans:
        return False, 'no qualifying scan evidence with final print/compare files'
    return True, allow.get('basis', '')


def bpm_for(root, slug, melody):
    decisions = json.loads((root / 'tempo_relaxed_decisions.json').read_text())
    item = decisions.get(slug)
    if item and item.get('quarter_note_bpm'):
        return float(item['quarter_note_bpm']), 'tempo_relaxed_decisions.json:quarter_note_bpm'
    return float(melody['native_bpm']), 'melody JSON:native_bpm fallback; tempo decision missing'


def support_instruments(bpm, meter):
    if bpm <= 60:
        return ['celesta', 'vibraphone', 'glockenspiel']
    if bpm >= 84:
        return ['glockenspiel', 'celesta', 'vibraphone']
    if meter in {'6/8', '9/8', '12/8'}:
        return ['celesta', 'vibraphone', 'glockenspiel']
    return ['celesta', 'vibraphone', 'glockenspiel']


def variant_names(instruments):
    return [f'pad_{instruments[0]}', f'cello_{instruments[1]}', f'strings_{instruments[2]}']


PROMPT_VERSION = 'v6c-chamber-trio-steady'


def prompt_text(key, bpm, instruments):
    beds = [
        ('soft pad', 'Soft warm sustained pad stays quietly behind the piano.', 'No strings. ', 'The pad never plays the melody. The pad never rises to high notes. The pad stays quieter than the piano.'),
        ('sustained strings', 'Soft sustained string ensemble stays in the middle register, quietly behind the piano.', 'No synths. ', 'Strings never play the melody. Strings never rise to high notes. Strings stay quieter than the piano.'),
        ('soft string pad', 'Soft low string pad stays in the middle register, quietly behind the piano.', '', 'Strings never play the melody. Strings never rise to high notes. Strings stay quieter than the piano.'),
    ]
    variants = []
    for n, ((bed, bed_line, also_forbidden, bed_steady), accent) in enumerate(zip(beds, instruments), 1):
        variants.append('\n\n'.join([
            f'STYLE {n} - piano + {bed} + {accent}\nMinimal intimate chamber trio.',
            f'Grand piano is the clear lead and plays the uploaded melody faithfully. {bed_line} '
            f'Sparse {accent} plays only occasional single notes.',
            'No rhythm section. No beat. No drums. No kick. No snare. No hi-hat. No cymbals. No toms. No shaker. '
            'No tambourine. No sleigh bells. No rhythmic percussion. '
            f'No bass. No guitar. {also_forbidden}No brass. No woodwinds. No choir. No vocals.',
            f'The {accent} is the only pitched percussion instrument and must never play a rhythmic pattern.',
            'Same soft volume and energy from beginning to end. No crescendo. No swells. No build-up. No climax. '
            + bed_steady,
            f'{key}, {bpm:g} BPM. Gentle, warm, bright and intimate. Sparse arrangement with lots of empty space. '
            'Dry, close grand piano with short natural decay.',
            f'Only piano, {bed} and sparse {accent}.',
        ]))
    return '\n\n\n'.join(variants) + '\n'


def render_one(root, out_root, slug, melody_path, piano_sf2, audit_basis):
    melody = json.loads(melody_path.read_text())
    bpm, bpm_source = bpm_for(root, slug, melody)
    one_pass_notes = []
    beat = 0.0
    for pitch, beats in melody['melody']:
        beats = float(beats)
        if pitch is not None:
            start = beat * 60 / bpm
            end = (beat + beats) * 60 / bpm
            one_pass_notes.append((start, end, int(pitch)))
        beat += beats
    one_pass_beats = beat
    one_pass_duration_s = beat * 60 / bpm
    notes = []
    for pass_index in range(3):
        offset = pass_index * one_pass_duration_s
        notes.extend((start + offset, end + offset, pitch) for start, end, pitch in one_pass_notes)
    total_beats = one_pass_beats * 3
    duration_s = total_beats * 60 / bpm + 2.0
    mode = melody.get('mode') or 'major'
    key = f"{melody['tonic']} {'minor' if mode in ('minor', 'aeolian') else mode}"
    inst = support_instruments(bpm, melody['meter'])
    allow = json.loads((root / 'MUREKA-ALLOWLIST.json').read_text())['songs'][slug]
    out = out_root / slug
    out.mkdir(parents=True, exist_ok=True)
    write_midi(out / f'{slug}.mid', notes, bpm)
    render_wav(out / f'{slug}.wav', notes, duration_s, piano_sf2)
    audit = json.loads((root / 'pd-audit' / f'{slug}.json').read_text())
    tiers = json.loads((root / 'popularity' / 'tiers.json').read_text())
    tier = next((row.get('tier') for row in tiers.get('songs', []) if row.get('slug') == slug), None)
    meta = {
        'slug': slug,
        'title': melody['title'],
        'source_melody': str(melody_path.relative_to(root)),
        'audit': str((root / 'pd-audit' / f'{slug}.json').relative_to(root)),
        'audit_verdict': audit['verdict'],
        'audit_basis': audit_basis,
        'audit_scan_sources': [s for s in audit['melody']['pd_sources'] if s.get('kind') == 'scan'],
        'popularity_tier': tier,
        'meter': melody['meter'],
        'key': key,
        'bpm_quarter_note': bpm,
        'bpm_source': bpm_source,
        'one_pass_beats': one_pass_beats,
        'total_beats': total_beats,
        'one_pass_duration_s': round(one_pass_duration_s, 6),
        'melody_duration_s': round(total_beats * 60 / bpm, 6),
        'render_duration_s': round(duration_s, 6),
        'pass_count': 3,
        'note_count': len(notes),
        'melody_sha256': hashlib.sha256(melody_path.read_bytes()).hexdigest(),
        'source_contract': 'Three consecutive exact melody passes; no added notes, rests, harmony, intro or outro; fixed meter, key and BPM; piano only.',
        'support_instruments_for_styles': inst,
        'prompt_version': PROMPT_VERSION,
        'album_limit': allow.get('album_limit'),
        'files': {'wav': f'{slug}.wav', 'midi': f'{slug}.mid', 'styles': 'styles.md'},
    }
    (out / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    (out / 'styles.md').write_text(prompt_text(key, bpm, inst))
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--piano-sf2', type=Path, required=True)
    parser.add_argument('--slug', action='append', dest='slugs')
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    melodies = source_files(root)
    out.mkdir(parents=True, exist_ok=True)
    tiers = json.loads((root / 'popularity' / 'tiers.json').read_text())
    tier_by_slug = {row.get('slug'): row.get('tier') for row in tiers.get('songs', [])}
    manifest = {'contract': 'mureka-piano-source-v1', 'selection': 'tier I/II + clean + pd_confirmed + final independent scan evidence + no NO_SCAN', 'songs': [], 'skipped': []}
    for slug in sorted(melodies):
        if args.slugs and slug not in args.slugs:
            continue
        tier = tier_by_slug.get(slug)
        if tier not in {'I', 'II'}:
            manifest['skipped'].append({'slug': slug, 'reason': f'popularity tier {tier or "missing"}; only I/II requested'})
            continue
        ok, reason = audit_is_independent(root, slug)
        if not ok:
            manifest['skipped'].append({'slug': slug, 'reason': reason})
            continue
        try:
            manifest['songs'].append(render_one(root, out, slug, melodies[slug], args.piano_sf2, reason))
        except Exception as exc:
            manifest['skipped'].append({'slug': slug, 'reason': f'render failed: {exc}'})
    previous_path = out / 'manifest.json'
    if args.slugs and previous_path.exists():
        previous = json.loads(previous_path.read_text())
        redone = set(args.slugs)
        manifest['songs'] = [s for s in previous.get('songs', []) if s.get('slug') not in redone] + manifest['songs']
        manifest['skipped'] = [s for s in previous.get('skipped', []) if s.get('slug') not in redone] + [
            s for s in manifest['skipped'] if s['slug'] in redone]
        manifest['songs'].sort(key=lambda s: s.get('slug', ''))
    previous_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (out / 'README.md').write_text(
        '# Mureka Christmas PD sources\n\n'
        'Each song directory contains three consecutive exact melody passes as dry piano WAV, matching MIDI, metadata, and three English Mureka style prompts.\n\n'
        'Selection requires popularity tier I or II, a clean audit, pd_confirmed melody, final independent scan evidence with existing print/compare files, and no NO_SCAN marker.\n\n'
        f"Generated songs: {len(manifest['songs'])}. Skipped: {len(manifest['skipped'])}.\n"
    )
    print(json.dumps({'generated': len(manifest['songs']), 'skipped': len(manifest['skipped']), 'out': str(out)}, indent=2))


if __name__ == '__main__':
    main()
