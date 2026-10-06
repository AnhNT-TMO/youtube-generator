import json
from pathlib import Path
import sys

import numpy as np
import plan_io
import soundfile as sf
from source_effects import dark_reverb
from source_metrics import biquad, mask_for, measure, spectrum

TOLERANCE = 1 / 8388608 + 1e-11
SR = plan_io.RENDER['sample_rate']
CEILING = plan_io.RENDER['source_peak_ceiling']


def scale(plan):
    return plan['source_revision']['fixed_common_scale']


def piano_parts(raw, plan):
    gain = plan['source_revision']['piano_linear_gain']
    assert gain == plan['baseline_mix']['piano_linear_gain']
    rh = np.load(raw / 'melody.npy').astype('float64') * scale(plan) * gain
    lh = np.load(raw / 'left_hand.npy').astype('float64') * scale(plan) * gain
    return rh, lh


def pad_stem(samples, plan):
    mix = plan['baseline_mix']
    beat_s = plan_io.beat_seconds(plan)
    samples = samples.copy()
    samples *= 10 ** (mix['gains_db']['pad'] / 20)
    envelope = np.ones(len(samples), dtype=np.float32)
    spans = {item['id']: item for item in plan_io.sections(plan)}
    for section, gain in mix['pad_section_gain_db'].items():
        form = spans[section]
        start = int(form['start_beat'] * beat_s * SR)
        end = int(form['end_beat'] * beat_s * SR)
        ramp = min(int(plan_io.RENDER['pad_ramp_seconds'] * SR), (end - start) // 2)
        level = 10 ** (gain / 20)
        final = form['end_beat'] == plan_io.length_beats(plan)
        envelope[start:start + ramp] = np.linspace(1, level, ramp)
        envelope[start + ramp:end - ramp] = level
        envelope[end - ramp:end] = level if final else np.linspace(level, 1, ramp)
        if final:
            envelope[end:] = level
    samples *= envelope[:, None]
    return samples * scale(plan)


def support_stem(raw, plan, style, notes):
    revision = plan['source_revision']
    support = np.load(raw / f'{style}.npy').astype('float64') * scale(plan)
    support[:, 0] *= np.sqrt(1 - plan['baseline_mix']['pans'][style] / 100)
    mask = mask_for(notes, len(support), SR, plan_io.beat_seconds(plan))
    before = measure(support, mask)
    corrected = support.copy()
    operations = []
    if revision['source_support_high_shelf_db']:
        corrected, operation = biquad(corrected, 'high_shelf', plan_io.RENDER['support_high_shelf_hz'], revision['source_support_high_shelf_db'], SR)
        operations.append(operation)
    match_db = before['rms_dbfs'] - measure(corrected, mask)['rms_dbfs'] if operations else 0
    corrected *= 10 ** (match_db / 20)
    matched = measure(corrected, mask)
    assert abs(matched['rms_dbfs'] - before['rms_dbfs']) <= .5
    gain = revision['source_support_balance_gain_db']
    corrected *= 10 ** (gain / 20)
    assert np.max(np.abs(corrected)) < CEILING
    return corrected, {'FX_before_shared_reverb': operations, 'FX_level_match_gain_db': match_db, 'balance_gain_db': gain, 'pan': plan['baseline_mix']['pans'][style], 'original_active': before, 'level_matched_active': matched}


def write_stems(work, raw, plan):
    style = plan_io.support_part(plan)
    rh, lh = piano_parts(raw, plan)
    sf.write(work / 'stem-piano.wav', rh + lh, SR, subtype='PCM_24')
    sf.write(work / 'stem-piano-RH.wav', rh, SR, subtype='PCM_24')
    sf.write(work / 'stem-left-hand.wav', lh, SR, subtype='PCM_24')
    sf.write(work / 'stem-pad.wav', pad_stem(np.load(raw / 'pad.npy'), plan), SR, subtype='PCM_24')
    support_info = None
    if style:
        notes = [n for n in plan['note_plan']['events'] if n['part'] == style]
        corrected, support_info = support_stem(raw, plan, style, notes)
        sf.write(work / f'stem-{style}.wav', corrected, SR, subtype='PCM_24')
    stems = {name: sf.read(work / f'stem-{name}.wav', dtype='float64', always_2d=True)[0] for name in ['piano', 'pad'] + ([style] if style else [])}
    dry = sum(stems.values())
    reverb = plan['baseline_mix']['shared_reverb']
    wet = dark_reverb(dry, seconds=reverb['seconds'], wet=reverb['wet'], damping_hz=reverb['damping_hz'])
    assert np.max(np.abs(wet)) < CEILING, 'No authorized whole-source normalization/headroom change'
    sf.write(work / 'src_A.wav', wet, SR, subtype='PCM_16')
    return stems, dry, wet, support_info


def compare(path, reference):
    ours, _ = sf.read(path, dtype='float64', always_2d=True)
    stored, _ = sf.read(reference, dtype='float64', always_2d=True)
    delta = float(np.abs(ours - stored).max()) if ours.shape == stored.shape else None
    return {'reference': str(reference), 'reference_sha256': plan_io.digest(reference), 'ours_sha256': plan_io.digest(path), 'byte_identical': plan_io.digest(path) == plan_io.digest(reference), 'shape_equal': ours.shape == stored.shape, 'max_PCM_delta': delta, 'pass': delta is not None and delta <= TOLERANCE}


def calibrate(work_root, out):
    raw = out / 'raw-source'
    gate = {'tolerance': TOLERANCE, 'method': 'Generic tools re-render Deck r009 track-plans (tempo, sections, mix read from the plan) and compare to stored r009 stems and src_A.wav', 'styles': {}}
    for style, path in plan_io.RENDER['calibration']['plans'].items():
        plan = plan_io.load(work_root / path / 'track-plan.json')
        work = out / style
        work.mkdir(parents=True)
        write_stems(work, raw, plan)
        gate['styles'][style] = {name: compare(work / name, work_root / path / name) for name in ['stem-piano.wav', 'stem-pad.wav', f'stem-{style}.wav', 'src_A.wav']}
    gate['pass'] = all(row['pass'] for style in gate['styles'].values() for row in style.values())
    plan_io.save(out / 'renderer-calibration.json', gate)
    print(json.dumps({style: {name: [row['byte_identical'], row['max_PCM_delta']] for name, row in rows.items()} for style, rows in gate['styles'].items()}), flush=True)
    assert gate['pass'], 'Renderer calibration against stored Deck r009 stems failed'
    print('CALIBRATION_PASS', flush=True)


def note_checks(pm, plan):
    style = plan_io.support_part(plan)
    events = plan['note_plan']['events']
    shared = [n for n in events if n['part'] != style]
    assert shared == pm['non_support_events'], 'Non-support events differ from PM plan'
    support = [n for n in events if style and n['part'] == style]
    if style:
        keys = ['beat', 'pitch', 'duration', 'velocity', 'channel', 'section', 'note_id']
        assert [{k: n[k] for k in keys} for n in support] == [{k: n[k] for k in keys} for n in pm['support_events_by_style'][style]], 'Support events differ from PM plan'
    melody = [n for n in shared if n['part'] == 'melody']
    register, clashes, chime = [], [], []
    chime_beat = plan['form']['chime']['beat']
    for n in support:
        sounding = [m for m in melody if m['beat'] < n['beat'] + n['duration'] and m['beat'] + m['duration'] > n['beat']]
        if sounding and n['pitch'] < max(m['pitch'] for m in sounding) + 3:
            register.append(n['note_id'])
        clashes += [(n['note_id'], m['note_id']) for m in sounding if (n['pitch'] - m['pitch']) % 12 in (1, 11)]
        if n['beat'] == chime_beat:
            chime.append(n['note_id'])
    assert not register and not clashes and not chime, (register, clashes, chime)
    return {'all_pass': True, 'equals_PM_plan_exactly': True, 'counts': {part: sum(n['part'] == part for n in events) for part in ['melody', 'left_hand', 'pad'] + ([style] if style else [])}, 'support_per_section': {item['id']: sum(n['section'] == item['id'] for n in support) for item in plan_io.sections(plan)} if style else None, 'support_register_min_3_semitones_above_sounding_melody': True, 'support_semitone_clashes_with_melody': 0, 'support_onsets_on_chime_beat': 0}


def song(root, revision):
    run = root / f'{revision}-run'
    raw = run / 'raw-source'
    calibration = plan_io.load(Path(sys.argv[4]) / 'renderer-calibration.json')
    assert calibration['pass']
    pm = plan_io.load(root / f'{revision}-pm/arrangement-plan.json')
    summary = {}
    for style in plan_io.styles_for(root, revision):
        work = root / style / revision
        assert not (work / 'src_A.wav').exists()
        plan = plan_io.load(work / 'track-plan.json')
        checks = note_checks(pm, plan)
        stems, dry, wet, support_info = write_stems(work, raw, plan)
        part = plan_io.support_part(plan)
        beat_s = plan_io.beat_seconds(plan)
        if part:
            notes = [n for n in plan['note_plan']['events'] if n['part'] == part]
            mask = mask_for(notes, len(stems[part]), SR, beat_s)
            support_info.update({'note_count': len(notes), 'final_active': measure(stems[part], mask), 'final_full_track': measure(stems[part]), 'spectrum_after': spectrum(stems[part], notes, SR, beat_s), 'pattern_set': plan['support_pattern']['per_verse']})
        delta = {'revision': revision, 'standard': plan_io.RENDER['standard'], 'common_baseline_scale': scale(plan), 'piano_linear_gain': plan['source_revision']['piano_linear_gain'], 'calibration_pass': True, 'source_note_checks': checks, 'stems_actual': {name: measure(value) for name, value in stems.items()}, 'support': support_info, 'shared_reverb': {**plan['baseline_mix']['shared_reverb'], 'dry_peak_dbfs': measure(dry)['sample_peak_dbfs'], 'wet_source_peak_dbfs': measure(wet)['sample_peak_dbfs']}, 'new_source_actual': measure(wet), 'normalization_EQ_compression_of_whole_source': False, 'physical_source_parts': plan['base_parts'], 'AI_instrument_retention': 'unverified', 'AI_support_pattern_retention': 'unverified' if part else None}
        plan_io.save(work / 'source-delta.json', delta)
        metadata = {'slug': plan['meta']['slug'], 'variant': 'A', 'style': plan['style'], 'base_parts': plan['base_parts'], 'accents_in_source': 0, 'key': plan['meta']['key'], 'meter': plan['meta']['meter'], 'bpm': plan['meta']['tempo'], 'vocal': False, 'arrangement_caption': plan['render']['ace_step']['caption'], 'duration_s': len(wet) / SR, 'instrument_note_counts': checks['counts'], 'source_revision': revision, 'key_plan': plan['key_plan']['sections'], 'form_sections': plan['form']['sections']}
        plan_io.save(work / 'src_A.json', metadata)
        verification = {'source_verified': True, 'source_note_checks': checks, 'paired_MIDI_events': len(plan['note_plan']['events']), 'renderer_calibration_pass': True, 'caption_frozen_before_covers': True, 'accents_in_source': 0, 'base_parts': plan['base_parts'], 'source_wav_sha256': plan_io.digest(work / 'src_A.wav'), 'source_midi_sha256': plan_io.digest(work / 'src_A.mid'), 'track_plan_sha256': plan_io.digest(work / 'track-plan.json'), 'actual_event_plan_sha256': plan_io.digest(work / 'actual-event-plan.json'), 'dry_stem_sha256': {path.name: plan_io.digest(path) for path in sorted(work.glob('stem-*.wav'))}}
        plan_io.save(work / 'source-verification.json', verification)
        summary[style] = {'source_peak_dbfs': measure(wet)['sample_peak_dbfs'], 'source_rms_dbfs': measure(wet)['rms_dbfs'], 'duration_s': len(wet) / SR}
        print('SOURCE_READY', style, json.dumps(summary[style]), flush=True)
    plan_io.save(run / 'source-checks.json', {'all_pass': True, 'styles': summary, 'calibration_reference': str(Path(sys.argv[4]) / 'renderer-calibration.json'), 'source_ready_for_ACE': True})


plan_io.require_server()
if sys.argv[1] == 'calibrate':
    calibrate(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
elif sys.argv[1] == 'song':
    song(Path(sys.argv[2]).resolve(), sys.argv[3])
else:
    raise SystemExit('usage: render_sources.py calibrate <work_root> <out_dir> | song <song_root> <revision> <calibration_dir>')
