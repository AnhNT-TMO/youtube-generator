import json
from pathlib import Path
import subprocess
import sys

import mix_accents
import plan_io
from alignment import PITCH_NAMES, align, estimate_key

CHIME = plan_io.CHIME
LOUD = plan_io.LOUDNESS
STALE = ['actual-cover-alignment.json', 'base-headroom.wav', 'mix-plan.json', 'finished-with-accents.wav', 'finished-with-accents.wav.json', 'finishing.json']


def measure(path):
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(path), '-af', f'loudnorm=I={LOUD["target_lufs"]}:TP={LOUD["true_peak_max_dbtp"]}:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    data = json.loads(result.stderr[result.stderr.rfind('{'):result.stderr.rfind('}') + 1])
    return {'integrated_lufs': float(data['input_i']), 'true_peak_dbtp': float(data['input_tp']), 'lra_lu': float(data['input_lra']), 'method': 'ffmpeg loudnorm input analysis only; no normalized output used'}


def tonic_triad(key):
    tonic = PITCH_NAMES.index(key.split()[0])
    return [tonic, (tonic + 4) % 12, (tonic + 7) % 12]


def boundary_record(seconds, section, key, map_time, cover_times, cover):
    mapped = map_time(seconds)
    local = cover[:, (cover_times >= mapped) & (cover_times < mapped + 2.0)].mean(axis=1)
    before = cover[:, (cover_times >= mapped - 2.0) & (cover_times < mapped)].mean(axis=1)
    share = float(local[tonic_triad(key)].sum() / local.sum())
    return {'section_id': section, 'source_s': seconds, 'actual_cover_time_s': mapped, 'delta_s': mapped - seconds, 'planned_key': key, 'local_pitch_class_strength_after_2s': dict(zip(PITCH_NAMES, local.tolist())), 'local_pitch_class_strength_before_2s': dict(zip(PITCH_NAMES, before.tolist())), 'tonic_triad_share_after': share, 'tonic_triad_share_uniform_expectation': 0.25, 'local_2s_key_estimate': estimate_key(local)[0][1], 'harmony_context_verified': False, 'harmony_context_note': f'Bar-chime sweep is dense inharmonic (non-tonal); local actual-cover chroma diagnostics in {key} only, perceptual fit unverified', 'method': 'Actual selected cover/source chroma DTW, 100 ms frames, max 2 s warp; not note transcription'}


def finish_style(root, revision, style, config_path, config, delivery):
    work = root / style / revision
    plan_spec = plan_io.load(work / 'track-plan.json')
    picks = plan_io.load(work / 'picks.json')
    if not picks['picks_instr']:
        return None
    selected, gate_status = picks['picks_instr'][0], 'all_gates_pass'
    backup_pass = bool(picks['backups'])
    for name in STALE:
        (work / name).unlink(missing_ok=True)
    beat_s = plan_io.beat_seconds(plan_spec)
    raw = work / selected
    backup_name = picks['backups'][0] if picks['backups'] else next(name for name in plan_io.PIPELINE['selection_order'] if name != selected)
    backup = work / backup_name
    map_time, cosine, (cover_times, cover) = align(work / 'src_A.wav', raw)
    chime = plan_spec['form']['chime']
    chime_section = next(item for item in plan_spec['form']['sections'] if item['section'] == chime['section'])
    boundary = boundary_record(chime['seconds'], chime['section'], chime_section['key'], map_time, cover_times, cover)
    end_beat = plan_io.melody_end_beat(plan_spec)
    musical_end = map_time(end_beat * beat_s)
    sections = [{'section_id': item['section'], 'kind': item['kind'], 'key': item.get('key'), 'source_start_s': item['start_seconds'], 'actual_cover_start_s_DTW': map_time(item['start_seconds'])} for item in plan_spec['form']['sections']]
    alignment = {'base_sha256': plan_io.digest(raw), 'source_sha256': plan_io.digest(work / 'src_A.wav'), 'mean_aligned_cosine': cosine, 'chime_boundary': boundary, 'sections': sections, 'musical_end_s': musical_end, 'musical_end_evidence': f'Last melody note-off at source beat {end_beat} ({end_beat * beat_s:.3f} s) mapped to the actual cover by DTW; release/reverb tail excluded', 'perceptual_boundary_verified': False}
    plan_io.save(work / 'actual-cover-alignment.json', alignment)
    base = work / 'base-headroom.wav'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(raw), '-af', f'volume={LOUD["base_headroom_db"]}dB', '-c:a', 'pcm_s24le', str(base)], check=True)
    sample = root.parent / CHIME['server_path']
    license_page = root.parent / CHIME['license_evidence_server']
    assert plan_io.digest(sample) == CHIME['sha256'] and plan_io.digest(license_page) == CHIME['license_evidence_sha256']
    assert 'Creative Commons 0' in license_page.read_text(errors='replace')
    onset = round(boundary['actual_cover_time_s'], 3)
    plan = {'style': style, 'revision': revision, 'audition_only': True,
            'base': {'path': str(base), 'sha256': plan_io.digest(base), 'raw_path': str(raw), 'raw_sha256': plan_io.digest(raw), 'fixed_attenuation_db': LOUD['base_headroom_db']},
            'musical_end_s': musical_end, 'musical_end_evidence': alignment['musical_end_evidence'],
            'base_gesture_review': {'status': 'unverified', 'evidence': 'Actual cover feature diagnostics and source/caption identity do not establish complete AI instrument or gesture retention; audition only.'},
            'accents': [{'accent_id': f'{revision}-{style}-accent-1', 'asset_id': CHIME['asset_id'], 'gesture': 'bar_chime_sweep', 'onset_s': onset, 'relative_db': CHIME['relative_db'],
                         'phrase_boundary': {'timeline': 'actual_cover', 'base_sha256': plan_io.digest(base), 'time_s': boundary['actual_cover_time_s'], 'method': boundary['method'], 'evidence': json.dumps(boundary) + f'; selected raw sha256 {plan_io.digest(raw)}; fixed attenuation preserves timeline'},
                         'sample': {'path': str(sample), 'sha256': CHIME['sha256'], 'gesture': 'bar_chime_sweep', 'real_recording': True, 'source': CHIME['source'], 'recordist': CHIME['recordist'], 'license': CHIME['license'], 'license_evidence': str(license_page), 'recording_evidence': CHIME['recording_evidence'], 'production_use_authorized': True, 'trim_start_s': 0, 'lowpass_hz': CHIME['lowpass_hz']},
                         'tonal_compatibility': {'non_tonal': True, 'verified': False, 'cover_key': boundary['planned_key'], 'evidence': f'Bar chime sweep, inharmonic; {boundary["planned_key"]} boundary diagnostics: tonic triad share {boundary["tonic_triad_share_after"]:.3f}, local estimate {boundary["local_2s_key_estimate"]}; perceptual fit unverified'}}],
            'chime_authority': CHIME['authority']}
    plan_io.save(work / 'mix-plan.json', plan)
    mixed = work / 'finished-with-accents.wav'
    validated = mix_accents.validate(plan, config, work, mixed)
    manifest = mix_accents.render(plan, config, config_path, work / 'mix-plan.json', mixed, validated)
    assert len(manifest['accents']) == 1
    event = manifest['accents'][0]
    assert -16 <= event['actual_relative_db'] <= -10 and event['hf_power_ratio_above_5khz'] <= .30
    level_deviation = event['actual_relative_db'] - CHIME['relative_db']
    pre = measure(mixed)
    gain = min(LOUD['target_lufs'] - pre['integrated_lufs'], LOUD['encode_true_peak_aim_dbtp'] - pre['true_peak_dbtp'])
    name = f'{plan_io.file_title(plan_spec)}_{plan_io.FILE_LABEL[style]}_{revision}.mp3'
    mp3 = delivery / name
    attempts = []
    for attempt in range(3):
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(mixed), '-af', f'volume={gain:.9f}dB', '-ar', '48000', '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '320k', str(mp3)], check=True)
        encoded = measure(mp3)
        attempts.append({'gain_db': gain, 'encoded': encoded})
        if encoded['true_peak_dbtp'] <= LOUD['true_peak_max_dbtp']:
            break
        gain -= encoded['true_peak_dbtp'] - LOUD['retry_true_peak_step_db']
    assert encoded['true_peak_dbtp'] <= LOUD['true_peak_max_dbtp'] and encoded['integrated_lufs'] <= LOUD['lufs_max']
    keys = plan_io.load(work / 'key_gate.json')
    report = {'song': plan_spec['meta']['slug'], 'style': style, 'revision': revision, 'primary_mp3': name, 'sha256': plan_io.digest(mp3), 'duration_s': manifest['duration_s'],
              'selected_raw': selected, 'selected_raw_sha256': plan_io.digest(raw), 'backup_raw': backup_name, 'backup_raw_sha256': plan_io.digest(backup), 'backup_passes_same_gates': backup_pass, 'gate_status': gate_status,
              'key_gate': {file: [{k: row[k] for k in ('section_id', 'expected', 'estimated', 'margin_vs_next_candidate', 'min_margin', 'span_s', 'pass')} for row in item['sections']] for file, item in keys['files'].items()},
              'source_verified': True, 'technical_pass': True, 'ready_for_listening': gate_status == 'all_gates_pass', 'listener_accepted': False, 'release_approved': False, 'audition_only': True,
              'instrument_retention': 'unverified', 'absence_of_extra_AI_gestures': 'unverified',
              'before_global_fixed_gain': pre, 'base_headroom_attenuation_db': LOUD['base_headroom_db'], 'global_fixed_gain_db': gain, 'encoded': encoded, 'attempts': attempts,
              'inserted_events': manifest['accents'], 'chime_requested_relative_db': CHIME['relative_db'], 'chime_level_deviation_db': level_deviation, 'chime_level_deviation_over_1db': abs(level_deviation) > 1,
              'mix_manifest_sha256': plan_io.digest(Path(str(mixed) + '.json')), 'finished_wav_sha256': manifest['output_sha256'], 'alignment': alignment,
              'processing': 'Whole AI cover of the rendered source; post-cover additive recorded CC0 chime, fixed -3 dB headroom and global fixed gain only. No base EQ, compression, ducking, limiting, splice or time stretch.'}
    plan_io.save(work / 'finishing.json', report)
    print(style, json.dumps({'selected': selected, 'encoded': encoded, 'onset_s': event['onset_s'], 'actual_relative_db': event['actual_relative_db'], 'limited_by': event['gain_limited_by']}), flush=True)
    return report


plan_io.require_server()
root = Path(sys.argv[1]).resolve()
revision = sys.argv[2]
delivery = Path(sys.argv[3]).resolve()
config_path = plan_io.CONFIG_PATH
config = plan_io.CONFIG
delivery.mkdir(parents=True, exist_ok=False)
reports = {}
for style in plan_io.styles_for(root, revision):
    report = finish_style(root, revision, style, config_path, config, delivery)
    reports[style] = report if report else {'style': style, 'status': plan_io.load(root / style / revision / 'picks.json')['status']}
plan_io.save(root / f'{revision}-run' / 'finish-report.json', reports)
print('FINISH_DONE', json.dumps({style: report.get('primary_mp3', report.get('status')) for style, report in reports.items()}), flush=True)
