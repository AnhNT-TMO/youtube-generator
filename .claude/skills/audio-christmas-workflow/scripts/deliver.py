import json
from pathlib import Path
import shutil
import sys

import plan_io

CHIME = plan_io.CHIME
LABEL = plan_io.STYLE_LABEL


def mmss(seconds):
    return f'{int(seconds // 60)}:{seconds % 60:04.1f}'


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def proof_for(root, revision, delivery, reports, melody, plan, produced):
    proof = delivery / 'proof'
    copy(root / 'melody-source.json', proof / 'melody-source.json')
    copy(root / f'{revision}-pm/arrangement-plan.json', proof / 'arrangement-plan.json')
    sources = melody.get('sources', [])
    lines = [f'# Public-domain basis: {melody["title"]}', '', f'- Tune: {melody.get("tune", "")}', f'- Composer / origin and date: {melody["pd_basis"]}',
             f'- Melody + chord file: melody-source.json (sha256 {plan_io.digest(root / "melody-source.json")}), verification confidence: {melody.get("confidence", "")}', '', '## Sources checked', '']
    for item in sources:
        lines.append(f'- {json.dumps(item, ensure_ascii=False)}' if not isinstance(item, str) else f'- {item}')
    lines += ['', f'Verification note: {melody.get("verified", "")}', '']
    (proof / 'PD-BASIS.md').write_text('\n'.join(lines))
    chime_dir = proof / 'chime'
    copy(root.parent / CHIME['license_evidence_server'], chime_dir / Path(CHIME['license_evidence_server']).name)
    files = []
    for style, report in reports.items():
        if 'primary_mp3' not in report:
            continue
        work = root / style / revision
        target = proof / style
        for name in ['src_A.mid', 'track-plan.json', 'cover-revision.json', 'mix-plan.json', 'finishing.json']:
            copy(work / name, target / name)
        copy(work / f'{report["selected_raw"][:-5]}.json', target / f'ace-request-{report["selected_raw"][:-5]}.json')
        copy(work / f'{report["backup_raw"][:-5]}.json', target / f'ace-request-{report["backup_raw"][:-5]}.json')
        copy(work / 'finished-with-accents.wav.json', target / 'mix-manifest.json')
        hashes = {'mp3': report['primary_mp3'], 'mp3_sha256': report['sha256'], 'selected_raw': report['selected_raw'], 'selected_raw_sha256': report['selected_raw_sha256'], 'backup_raw': report['backup_raw'], 'backup_raw_sha256': report['backup_raw_sha256'], 'src_A_mid_sha256': plan_io.digest(work / 'src_A.mid'), 'src_A_wav_sha256': plan_io.digest(work / 'src_A.wav'), 'track_plan_sha256': plan_io.digest(work / 'track-plan.json'), 'finished_wav_sha256': report['finished_wav_sha256'], 'mix_manifest_sha256': report['mix_manifest_sha256']}
        plan_io.save(target / 'hashes.json', hashes)
        files.append((style, hashes))
    event_rows = {style: report['inserted_events'][0] for style, report in reports.items() if 'primary_mp3' in report}
    plan_io.save(chime_dir / 'chime-manifest.json', {'asset_id': CHIME['asset_id'], 'parent_asset_id': CHIME['parent_asset_id'], 'gesture': 'bar_chime_sweep', 'direction': CHIME['direction'], 'source_page': CHIME['source'], 'recordist': CHIME['recordist'], 'license': CHIME['license'], 'license_evidence_file': Path(CHIME['license_evidence_server']).name, 'license_evidence_sha256': CHIME['license_evidence_sha256'], 'parent_recording_sha256': CHIME['parent_sha256'], 'extracted_child_sha256': CHIME['child_sha256'], 'extract_s': CHIME['extract_s'], 'treatment': CHIME['treatment'], 'mixed_sample_sha256': CHIME['sha256'], 'mix_lowpass_hz': CHIME['lowpass_hz'], 'requested_relative_db': CHIME['relative_db'], 'insertions': {style: {'onset_s': event['onset_s'], 'tail_end_s': event['tail_end_s'], 'actual_relative_db': event['actual_relative_db']} for style, event in event_rows.items()}})
    title = melody['title']
    text = [f'Content ID dispute: "{title}" ({plan["meta"]["key"]} opening key, {plan["meta"]["meter"]}, {plan["meta"]["tempo"]} BPM)', '',
            f'1. The composition "{title}" is in the public domain: {melody["pd_basis"]}. The melody and chords we used are transcribed in melody-source.json, with the public-domain editions we checked listed in PD-BASIS.md.',
            f'2. This recording is our own arrangement and production, made on {produced}. We wrote the arrangement as MIDI ourselves (src_A.mid: piano melody and left hand, pad, and for two versions a celesta or vibraphone part; three statements each a whole step higher). We rendered that MIDI with sample instruments into our own audio, then processed our own audio with the open-source ACE-Step 1.5 model (audio-to-audio cover of our own render; model, seed and settings in the ace-request files).',
            f'3. No third-party recording of this song was used. The only external audio is one bar chime sweep released under {CHIME["license"]}: {CHIME["source"]} by {CHIME["recordist"]}; see chime/chime-manifest.json and the saved source page.',
            '4. Evidence files in this folder (SHA-256):', '']
    for style, hashes in files:
        text.append(f'   - {hashes["mp3"]}: {hashes["mp3_sha256"]}')
        text.append(f'     source MIDI {style}/src_A.mid: {hashes["src_A_mid_sha256"]}; arrangement {style}/track-plan.json: {hashes["track_plan_sha256"]}; selected generation output: {hashes["selected_raw_sha256"]}')
    text += [f'   - melody-source.json: {plan_io.digest(proof / "melody-source.json")}', f'   - arrangement-plan.json: {plan_io.digest(proof / "arrangement-plan.json")}', '',
             'We therefore dispute the claim: the underlying work is public domain and this sound recording is our own original production.', '']
    (proof / 'DISPUTE.txt').write_text('\n'.join(text))


plan_io.require_server()
root = Path(sys.argv[1]).resolve()
revision = sys.argv[2]
delivery = Path(sys.argv[3]).resolve()
reports = plan_io.load(root / f'{revision}-run' / 'finish-report.json')
pm = plan_io.load(root / f'{revision}-pm' / 'arrangement-plan.json')
plain = plan_io.load(root / plan_io.styles_for(root, revision)[0] / revision / 'track-plan.json')
melody = plan_io.load(root / 'melody-source.json')
beat_s = plan_io.beat_seconds(plain)
for style, report in reports.items():
    work = root / style / revision
    evidence = delivery / 'evidence' / style
    for path in sorted(work.iterdir()):
        if path.is_file() and (path.suffix in ('.json', '.mid', '.log') or path.name == 'src_A.wav'):
            copy(path, evidence / path.name)
    if 'primary_mp3' not in report:
        continue
    for role, name in [('primary', report['selected_raw']), ('backup', report['backup_raw'])]:
        copy(work / name, delivery / 'raw' / f'{style}-{role}-{name}')
        copy(work / f'{name[:-5]}.json', delivery / 'raw' / f'{style}-{role}-{name[:-5]}.json')
for path in sorted((root / f'{revision}-run').glob('*.json')) + sorted((root / f'{revision}-run').glob('*.log')):
    copy(path, delivery / 'evidence' / 'run' / path.name)
copy(plan_io.server_path('calibration') / 'renderer-calibration.json', delivery / 'evidence' / 'run' / 'renderer-calibration.json')
for path in sorted(Path(__file__).resolve().parent.iterdir()):
    if path.is_file() and path.suffix in ('.py', '.sh', '.json'):
        copy(path, delivery / 'tools' / path.name)
proof_for(root, revision, delivery, reports, melody, plain, pm['date'])

sections = plain['form']['sections']
delivered = {style: report for style, report in reports.items() if 'primary_mp3' in report}
listening_map = {'schema_version': 1, 'song_slug': plain['meta']['slug'], 'title': plain['meta']['title'], 'revision': revision, 'batch': pm['batch'], 'source_fix': pm.get('source_fix'), 'quarter_note_bpm': plain['meta']['tempo'], 'meter': plain['meta']['meter'], 'opening_key': plain['meta']['key'],
                 'form': [{'section_id': item['section'], 'kind': item['kind'], 'key': item.get('key'), 'source_start_s': item['start_seconds'], 'source_end_s': item['end_seconds']} for item in sections], 'chime_plan': plain['form']['chime'],
                 'timing_basis': 'post_cover_mix', 'source_timing_status': 'Section times per variant are DTW diagnostics on the selected cover; chime onset/tail are exact output facts from the mix manifest',
                 'perceptual_retention': 'unverified', 'listener_accepted': False, 'release_approved': False, 'variants': {}, 'not_delivered': {}, 'feedback': []}
for style, report in reports.items():
    if style not in delivered:
        listening_map['not_delivered'][style] = report.get('status')
        continue
    event = report['inserted_events'][0]
    track = plan_io.load(root / style / revision / 'track-plan.json')
    listening_map['variants'][style] = {'label': LABEL[style], 'mp3': report['primary_mp3'], 'mp3_sha256': report['sha256'], 'duration_s': report['duration_s'], 'encoded_worker': report['encoded'], 'gate_status': report['gate_status'], 'ready_for_listening': report['ready_for_listening'],
                                        'base': {'raw_file': report['selected_raw'], 'raw_sha256': report['selected_raw_sha256'], 'raw_path_local': f'raw/{style}-primary-{report["selected_raw"]}', 'backup_raw_local': f'raw/{style}-backup-{report["backup_raw"]}', 'backup_raw_sha256': report['backup_raw_sha256'], 'backup_passes_same_gates': report['backup_passes_same_gates']},
                                        'sections_actual_DTW': report['alignment']['sections'], 'musical_end_s': report['alignment']['musical_end_s'],
                                        'accents': [{'asset_id': CHIME['asset_id'], 'gesture': 'bar_chime_sweep', 'direction': 'up', 'boundary': f'A1->{plain["form"]["chime"]["section"]} (statement 1 -> statement 2)', 'onset_s': event['onset_s'], 'tail_end_s': event['tail_end_s'], 'actual_fraction_of_musical_end': event['onset_s'] / report['alignment']['musical_end_s'], 'requested_relative_db': CHIME['relative_db'], 'actual_relative_db': event['actual_relative_db'], 'gain_limited_by': event['gain_limited_by'], 'lowpass_hz': event['lowpass_hz'], 'harmony_context_verified': False}],
                                        'key_gate_primary': report['key_gate'][report['selected_raw']], 'support_pattern': track['support_pattern'].get('per_verse') if style != 'plain' else 'none', 'listener_accepted': False}
plan_io.save(delivery / 'listening-map.json', listening_map)

fix = pm.get('source_fix')
margin = plan_io.PIPELINE['key_gate']['min_margin']
loud = plan_io.LOUDNESS
lines = [f'# {plain["meta"]["title"]} {revision} (lô {pm["batch"]})', '',
         f'**{plain["meta"]["meter"]}, {plain["meta"]["tempo"]} BPM (phách đen), dài {mmss(plan_io.length_beats(plain) * beat_s)} theo nguồn.** Bản: {", ".join(LABEL[style] for style in reports)}; cùng piano, pad và giọng. MP3 nhắm {loud["target_lufs"]} LUFS bằng gain cố định; bản nào chạm trần true peak {loud["true_peak_max_dbtp"]} dBTP thì nhỏ hơn (số thật ở bảng), không dùng limiter.', '']
if fix:
    lines += [f'**Sửa nguồn so với {fix["from_revision"]}:** {fix["reason"]}', '']
lines += ['**Giọng theo thời gian** (giờ nguồn; bản AI lệch vài trăm ms, giờ thật từng bản trong `listening-map.json`):', '']
for item in sections:
    lines.append(f'- {item["section"]} ({item["kind"]}): {mmss(item["start_seconds"])}–{mmss(item["end_seconds"])}' + (f', {item["key"]}' if item.get('key') else ''))
for style in [style for style in reports if style != 'plain']:
    track = plan_io.load(root / style / revision / 'track-plan.json')
    lines += ['', f'**Pattern {style} theo lượt:**', '']
    for section, verse in track['support_pattern']['per_verse'].items():
        lines.append(f'- {section}: {verse["pattern_name"]}, {verse["notes"]} nốt' + (f', mật độ {verse["density"]["percent"]:.1f} %' if verse.get('density') else ''))
lines += ['', '| MP3 | Take chính / dự phòng | Chime (onset → hết đuôi) | Mức chime thật | LUFS / dBTP | Trạng thái |', '|---|---|---|---|---|---|']
for style, report in reports.items():
    if style not in delivered:
        lines.append(f'| {LABEL[style]} | — | — | — | — | {report.get("status")} |')
        continue
    event = report['inserted_events'][0]
    status = 'sẵn sàng nghe' if report['ready_for_listening'] else f'chờ PM: {report["gate_status"]}'
    lines.append(f'| {report["primary_mp3"]} | {report["selected_raw"]} / {report["backup_raw"]}{"" if report["backup_passes_same_gates"] else " (không đạt cổng, chỉ để tham khảo)"} | {mmss(event["onset_s"])} → {mmss(event["tail_end_s"])} | {event["actual_relative_db"]:.1f} dB ({event["gain_limited_by"]}) | {report["encoded"]["integrated_lufs"]:.2f} / {report["encoded"]["true_peak_dbtp"]:.2f} | {status} |')
deviations = [f'{style}: {report["chime_level_deviation_db"]:+.2f} dB' for style, report in delivered.items() if report['chime_level_deviation_over_1db']]
lines += ['', f'Chime: {CHIME["license"]}, {CHIME["source"]} ({CHIME["recordist"]}); {CHIME["treatment"]}; mix lowpass {CHIME["lowpass_hz"]} Hz, yêu cầu {CHIME["relative_db"]} dB so với nền tại chỗ, đặt ở ranh giới lượt 1 → 2 thật của bản AI (DTW).' + ('' if CHIME.get('credit_required') else ' Không cần ghi credit.'),
          'Trần transient kéo mức chime lệch > 1 dB: ' + ('; '.join(deviations) if deviations else 'không bản nào.'), '',
          f'**Chưa kiểm (unverified):** AI có giữ đúng nhạc cụ và pattern support từng lượt hay không; có cử chỉ lạ hay không; chime có hợp ngữ cảnh hay không (chỉ có số đo chroma). Cổng giọng: giọng ước lượng tốt nhất trong các giọng đã lên kế hoạch phải đúng giọng từng lượt, cách biệt ≥ {margin}. listener_accepted = false tới khi CEO nghe.', '',
          'Bằng chứng kháng Content ID: `proof/` (DISPUTE.txt tiếng Anh dán thẳng vào form).']
(delivery / 'NGHE_THU.md').write_text('\n'.join(lines) + '\n')
plan_io.write_checksums(delivery)
print('DELIVERY', str(delivery), json.dumps({style: report.get('primary_mp3', report.get('status')) for style, report in reports.items()}), flush=True)
