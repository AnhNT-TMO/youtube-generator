import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

import mix_accents
import plan_io

plan_io.require_server()
if len(sys.argv) < 6:
    raise SystemExit('usage: remix.py <song_root> <parent_revision> <new_revision> <delivery_dir> <reason>')
root = Path(sys.argv[1]).resolve()
PARENT, REVISION = sys.argv[2], sys.argv[3]
delivery = Path(sys.argv[4]).resolve()
CHANGE = ' '.join(sys.argv[5:])
STYLES = [style for style in plan_io.STYLE_ORDER if (root / style / PARENT / 'mix-plan.json').is_file()]
assert STYLES, f'no {PARENT}/mix-plan.json under {root}'
LABEL = plan_io.STYLE_LABEL
CHIME = plan_io.CHIME
LOUD = plan_io.LOUDNESS
config_path = plan_io.CONFIG_PATH
config = plan_io.CONFIG
sample = root.parent / CHIME['server_path']
license_page = root.parent / CHIME['license_evidence_server']
assert plan_io.digest(sample) == CHIME['sha256'] and plan_io.digest(license_page) == CHIME['license_evidence_sha256']
delivery.mkdir(parents=True, exist_ok=False)


def measure(path):
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(path), '-af', f'loudnorm=I={LOUD["target_lufs"]}:TP={LOUD["true_peak_max_dbtp"]}:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    data = json.loads(result.stderr[result.stderr.rfind('{'):result.stderr.rfind('}') + 1])
    return {'integrated_lufs': float(data['input_i']), 'true_peak_dbtp': float(data['input_tp']), 'lra_lu': float(data['input_lra']), 'method': 'ffmpeg loudnorm input analysis only; no normalized output used'}


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def mmss(seconds):
    return f'{int(seconds // 60)}:{seconds % 60:04.1f}'


def remix_style(style):
    parent_dir = root / style / PARENT
    work = root / style / REVISION
    work.mkdir(parents=True, exist_ok=False)
    parent_plan = plan_io.load(parent_dir / 'mix-plan.json')
    parent_manifest = plan_io.load(parent_dir / 'finished-with-accents.wav.json')
    raw = Path(parent_plan['base']['raw_path'])
    base = Path(parent_plan['base']['path'])
    base_dir = raw.parent
    base_revision = base_dir.name
    base_finish = plan_io.load(base_dir / 'finishing.json')
    assert base.parent == base_dir
    raw_sha, base_sha = plan_io.digest(raw), plan_io.digest(base)
    assert raw_sha == parent_plan['base']['raw_sha256'] == base_finish['selected_raw_sha256'], f'{style}: raw base changed since {base_revision}'
    assert base_sha == parent_plan['base']['sha256'], f'{style}: headroom base changed since {base_revision}'
    assert len(parent_plan['accents']) == 1 and len(parent_manifest['accents']) == 1
    onset = parent_manifest['accents'][0]['onset_s']
    old_accent = parent_plan['accents'][0]
    accent = copy.deepcopy(old_accent)
    accent.pop('reused_from', None)
    accent.update({'accent_id': f'{REVISION}-{style}-accent-1', 'asset_id': CHIME['asset_id'], 'onset_s': onset, 'relative_db': CHIME['relative_db'],
                   'replaces': {'revision': PARENT, 'asset_id': old_accent['asset_id'], 'license': old_accent['sample']['license'], 'onset_s': old_accent['onset_s'], 'relative_db': old_accent['relative_db']}})
    accent['sample'] = {'path': str(sample), 'sha256': CHIME['sha256'], 'gesture': 'bar_chime_sweep', 'real_recording': True, 'source': CHIME['source'], 'recordist': CHIME['recordist'], 'license': CHIME['license'], 'license_evidence': str(license_page),
                        'recording_evidence': CHIME['recording_evidence'], 'production_use_authorized': True, 'trim_start_s': 0, 'lowpass_hz': CHIME['lowpass_hz']}
    accent['tonal_compatibility'] = {'non_tonal': True, 'verified': False, 'cover_key': old_accent['tonal_compatibility']['cover_key'], 'evidence': f'Bar chime sweep, inharmonic; boundary diagnostics as {base_revision}/{PARENT} on the identical base; perceptual fit unverified'}
    plan = copy.deepcopy(parent_plan)
    for key in ('removed_accents', 'accent_level_basis', 'change_vs_r009', 'change_vs_parent', 'parent_revision'):
        plan.pop(key, None)
    plan.update({'revision': REVISION, 'parent_revision': PARENT, 'change_vs_parent': CHANGE, 'accents': [accent], 'chime_authority': CHIME['authority']})
    plan_io.save(work / 'mix-plan.json', plan)
    mixed = work / 'finished-with-accents.wav'
    validated = mix_accents.validate(plan, config, work, mixed)
    manifest = mix_accents.render(plan, config, config_path, work / 'mix-plan.json', mixed, validated)
    assert len(manifest['accents']) == 1 and manifest['inserted_event_count'] == 1
    event = manifest['accents'][0]
    assert event['onset_s'] == onset and event['sample_sha256'] == CHIME['sha256'] and event['lowpass_hz'] == CHIME['lowpass_hz']
    assert -16 <= event['actual_relative_db'] <= -10 and event['hf_power_ratio_above_5khz'] <= .30
    pre = measure(mixed)
    gain = min(LOUD['target_lufs'] - pre['integrated_lufs'], LOUD['encode_true_peak_aim_dbtp'] - pre['true_peak_dbtp'])
    track = plan_io.load(base_dir / 'track-plan.json')
    name = f'{plan_io.file_title(track)}_{plan_io.FILE_LABEL[style]}_{REVISION}.mp3'
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
    backup = base_dir / base_finish['backup_raw']
    assert plan_io.digest(backup) == base_finish['backup_raw_sha256']
    deviation = event['actual_relative_db'] - CHIME['relative_db']
    report = {'song': root.name, 'style': style, 'revision': REVISION, 'parent_revision': PARENT, 'base_revision': base_revision, 'change_vs_parent': CHANGE, 'primary_mp3': name, 'sha256': plan_io.digest(mp3), 'duration_s': manifest['duration_s'],
              'selected_raw': raw.name, 'selected_raw_sha256': raw_sha, 'selected_raw_matches_base_record': True, 'base_headroom_sha256': base_sha, 'base_headroom_matches_base_record': True,
              'backup_raw': backup.name, 'backup_raw_sha256': base_finish['backup_raw_sha256'], 'new_AI_generation': False, 'gate_status': f'{base_revision} gates (unchanged base)',
              'source_verified': True, 'technical_pass': True, 'ready_for_listening': True, 'listener_accepted': False, 'release_approved': False, 'audition_only': True,
              'instrument_retention': 'unverified', 'absence_of_extra_AI_gestures': 'unverified',
              'before_global_fixed_gain': pre, 'base_headroom_attenuation_db': LOUD['base_headroom_db'], 'global_fixed_gain_db': gain, 'encoded': encoded, 'attempts': attempts,
              'inserted_events': manifest['accents'], 'replaced_event': parent_manifest['accents'][0], 'chime_requested_relative_db': CHIME['relative_db'], 'chime_level_deviation_db': deviation, 'chime_level_deviation_over_1db': abs(deviation) > 1,
              'mix_manifest_sha256': plan_io.digest(Path(str(mixed) + '.json')), 'finished_wav_sha256': manifest['output_sha256'], 'alignment': base_finish['alignment'], 'alignment_source': f'{base_revision} actual-cover alignment of the identical base (sha256 verified)',
              'processing': f'Unchanged {base_revision} selected AI cover (fixed headroom copy); one post-cover additive recorded chime at {onset} s; global fixed gain only. No base EQ, compression, ducking, limiting, splice or time stretch.'}
    plan_io.save(work / 'finishing.json', report)
    for path in [work / 'mix-plan.json', Path(str(mixed) + '.json'), work / 'finishing.json']:
        copy_file(path, delivery / 'evidence' / style / path.name)
    for path in [base_dir / 'actual-cover-alignment.json', base_dir / 'key_gate.json', base_dir / 'picks.json', base_dir / 'eval_a.json', base_dir / 'eval_b.json']:
        copy_file(path, delivery / 'evidence' / style / f'{base_revision}-{path.name}')
    copy_file(parent_dir / 'mix-plan.json', delivery / 'evidence' / style / f'{PARENT}-mix-plan.json')
    for role, path in [('primary', raw), ('backup', backup)]:
        copy_file(path, delivery / 'raw' / f'{style}-{role}-{path.name}')
        copy_file(path.with_suffix('.json'), delivery / 'raw' / f'{style}-{role}-{path.stem}.json')
    proof = delivery / 'proof' / style
    for source_name in ['src_A.mid', 'track-plan.json', 'cover-revision.json']:
        copy_file(base_dir / source_name, proof / source_name)
    copy_file(work / 'mix-plan.json', proof / 'mix-plan.json')
    copy_file(work / 'finishing.json', proof / 'finishing.json')
    copy_file(Path(str(mixed) + '.json'), proof / 'mix-manifest.json')
    for path in [raw, backup]:
        copy_file(path.with_suffix('.json'), proof / f'ace-request-{path.stem}.json')
    plan_io.save(proof / 'hashes.json', {'mp3': name, 'mp3_sha256': report['sha256'], 'selected_raw': raw.name, 'selected_raw_sha256': raw_sha, 'backup_raw': backup.name, 'backup_raw_sha256': report['backup_raw_sha256'],
                                        'src_A_mid_sha256': plan_io.digest(base_dir / 'src_A.mid'), 'src_A_wav_sha256': plan_io.digest(base_dir / 'src_A.wav'), 'track_plan_sha256': plan_io.digest(base_dir / 'track-plan.json'),
                                        'finished_wav_sha256': report['finished_wav_sha256'], 'mix_manifest_sha256': report['mix_manifest_sha256']})
    print(style, json.dumps({'encoded': encoded, 'onset_s': event['onset_s'], 'tail_end_s': event['tail_end_s'], 'actual_relative_db': event['actual_relative_db'], 'limited_by': event['gain_limited_by']}), flush=True)
    return report


reports = {style: remix_style(style) for style in STYLES}
first = STYLES[0]
base_revision = reports[first]['base_revision']
proof = delivery / 'proof'
melody = plan_io.load(root / 'melody-source.json')
track = plan_io.load(root / first / base_revision / 'track-plan.json')
copy_file(root / 'melody-source.json', proof / 'melody-source.json')
copy_file(root / f'{base_revision}-pm' / 'arrangement-plan.json', proof / 'arrangement-plan.json')
lines = [f'# Public-domain basis: {melody["title"]}', '', f'- Tune: {melody.get("tune", "")}', f'- Composer / origin and date: {melody["pd_basis"]}',
         f'- Melody + chord file: melody-source.json (sha256 {plan_io.digest(root / "melody-source.json")}), verification confidence: {melody.get("confidence", "")}', '', '## Sources checked', '']
lines += [f'- {item}' if isinstance(item, str) else f'- {json.dumps(item, ensure_ascii=False)}' for item in melody.get('sources', [])]
lines += ['', f'Verification note: {melody.get("verified", "")}', '']
(proof / 'PD-BASIS.md').write_text('\n'.join(lines))
copy_file(license_page, proof / 'chime' / license_page.name)
plan_io.save(proof / 'chime' / 'chime-manifest.json', {'asset_id': CHIME['asset_id'], 'parent_asset_id': CHIME['parent_asset_id'], 'gesture': 'bar_chime_sweep', 'direction': CHIME['direction'], 'source_page': CHIME['source'], 'recordist': CHIME['recordist'], 'license': CHIME['license'],
                                                      'license_evidence_file': license_page.name, 'license_evidence_sha256': CHIME['license_evidence_sha256'], 'parent_recording_sha256': CHIME['parent_sha256'], 'extracted_child_sha256': CHIME['child_sha256'], 'extract_s': CHIME['extract_s'],
                                                      'treatment': CHIME['treatment'], 'mixed_sample_sha256': CHIME['sha256'], 'mix_lowpass_hz': CHIME['lowpass_hz'], 'requested_relative_db': CHIME['relative_db'],
                                                      'insertions': {style: {'onset_s': r['inserted_events'][0]['onset_s'], 'tail_end_s': r['inserted_events'][0]['tail_end_s'], 'actual_relative_db': r['inserted_events'][0]['actual_relative_db']} for style, r in reports.items()},
                                                      'replaces': {'revision': PARENT, 'by_style': {style: {'asset_id': r['replaced_event'].get('asset_id'), 'onset_s': r['replaced_event'].get('onset_s')} for style, r in reports.items()}}})
produced = datetime.fromtimestamp(Path(root / first / base_revision / reports[first]['selected_raw']).stat().st_mtime, timezone.utc).date().isoformat()
remixed = datetime.now(timezone.utc).date().isoformat()
text = [f'Content ID dispute: "{melody["title"]}" ({track["meta"]["key"]} opening key, {track["meta"]["meter"]}, {track["meta"]["tempo"]} BPM)', '',
        f'1. The composition "{melody["title"]}" is in the public domain: {melody["pd_basis"]}. The melody and chords we used are transcribed in melody-source.json, with the public-domain editions we checked listed in PD-BASIS.md.',
        f'2. This recording is our own arrangement and production. We wrote the arrangement as MIDI ourselves (src_A.mid: piano melody and left hand, pad, and a decorative support part where present; statements lifted step by step). We rendered that MIDI with sample instruments into our own audio, then processed our own audio with the open-source ACE-Step 1.5 model on {produced} (audio-to-audio cover of our own render; model, seed and settings in the ace-request files). The final mix with one added chime was made on {remixed}.',
        f'3. No third-party recording of this song was used. The only external audio is one bar chime sweep released under {CHIME["license"]}: {CHIME["source"]} by {CHIME["recordist"]}; see chime/chime-manifest.json and the saved source page.',
        '4. Evidence files in this folder (SHA-256):', '']
for style, report in reports.items():
    hashes = plan_io.load(proof / style / 'hashes.json')
    text.append(f'   - {hashes["mp3"]}: {hashes["mp3_sha256"]}')
    text.append(f'     source MIDI {style}/src_A.mid: {hashes["src_A_mid_sha256"]}; arrangement {style}/track-plan.json: {hashes["track_plan_sha256"]}; selected generation output: {hashes["selected_raw_sha256"]}')
text += [f'   - melody-source.json: {plan_io.digest(proof / "melody-source.json")}', f'   - arrangement-plan.json: {plan_io.digest(proof / "arrangement-plan.json")}', '',
         'We therefore dispute the claim: the underlying work is public domain and this sound recording is our own original production.', '']
(proof / 'DISPUTE.txt').write_text('\n'.join(text))

listening_map = {'schema_version': 1, 'song_slug': root.name, 'title': melody['title'], 'revision': REVISION, 'parent': PARENT, 'base_revision': base_revision, 'change_vs_parent': CHANGE,
                 'quarter_note_bpm': track['meta']['tempo'], 'meter': track['meta']['meter'], 'opening_key': track['meta']['key'], 'timing_basis': 'post_cover_mix',
                 'source_timing_status': f'Section times are {base_revision} DTW diagnostics on the identical base; accent onset/tail are exact output facts from the {REVISION} mix manifest',
                 'perceptual_retention': 'unverified', 'listener_accepted': False, 'release_approved': False, 'variants': {}, 'feedback': []}
for style, report in reports.items():
    event = report['inserted_events'][0]
    listening_map['variants'][style] = {'label': LABEL[style], 'mp3': report['primary_mp3'], 'mp3_sha256': report['sha256'], 'duration_s': report['duration_s'], 'encoded_worker': report['encoded'], 'ready_for_listening': True,
                                        'base': {'raw_file': report['selected_raw'], 'raw_sha256': report['selected_raw_sha256'], 'raw_path_local': f'raw/{style}-primary-{report["selected_raw"]}', 'backup_raw_local': f'raw/{style}-backup-{report["backup_raw"]}', 'backup_raw_sha256': report['backup_raw_sha256'], 'new_AI_generation': False},
                                        'sections_actual_DTW': report['alignment']['sections'], 'musical_end_s': report['alignment']['musical_end_s'],
                                        'accents': [{'asset_id': CHIME['asset_id'], 'gesture': 'bar_chime_sweep', 'direction': 'up', 'boundary': f'A1->{track["form"]["chime"]["section"] if "form" in track else "A2"} (statement 1 -> statement 2)', 'onset_s': event['onset_s'], 'tail_end_s': event['tail_end_s'], 'actual_fraction_of_musical_end': event['onset_s'] / report['alignment']['musical_end_s'], 'requested_relative_db': CHIME['relative_db'], 'actual_relative_db': event['actual_relative_db'], 'gain_limited_by': event['gain_limited_by'], 'lowpass_hz': event['lowpass_hz'], 'harmony_context_verified': False}],
                                        'listener_accepted': False}
plan_io.save(delivery / 'listening-map.json', listening_map)
plan_io.save(delivery / 'delivery-report.json', reports)
for path in sorted(Path(__file__).resolve().parent.iterdir()):
    if path.is_file() and path.suffix in ('.py', '.sh', '.json'):
        copy_file(path, delivery / 'tools' / path.name)
rows = ['| File | Chime (onset → hết đuôi) | Mức chime thật | LUFS / dBTP |', '|---|---|---|---|']
for style, report in reports.items():
    event = report['inserted_events'][0]
    rows.append(f'| {report["primary_mp3"]} | {mmss(event["onset_s"])} → {mmss(event["tail_end_s"])} | {event["actual_relative_db"]:.1f} dB ({event["gain_limited_by"]}) | {report["encoded"]["integrated_lufs"]:.2f} / {report["encoded"]["true_peak_dbtp"]:.2f} |')
lines = [f'# {melody["title"]} {REVISION}: chỉ đổi chime', '',
         f'Đổi so với {PARENT}: {CHANGE}', '',
         f'Chime mới: {CHIME["license"]}, {CHIME["source"]} ({CHIME["recordist"]}), giữ đúng mốc chime của {PARENT}, mức yêu cầu {CHIME["relative_db"]} dB so với nền tại chỗ, lowpass {CHIME["lowpass_hz"]} Hz.', '',
         f'Nền nhạc **không đổi**: cùng file AI {base_revision}, không tạo lại AI. MP3 nhắm {LOUD["target_lufs"]} LUFS, gain cố định, không limiter.', ''] + rows + ['',
         '**Chưa kiểm:** chime có hợp ngữ cảnh không (chỉ có số đo). Chưa ai nghe; listener_accepted = false.', '',
         'Bằng chứng kháng Content ID: `proof/` (DISPUTE.txt tiếng Anh).']
(delivery / 'NGHE_THU.md').write_text('\n'.join(lines) + '\n')
plan_io.write_checksums(delivery)
print('DELIVERY', str(delivery), flush=True)
