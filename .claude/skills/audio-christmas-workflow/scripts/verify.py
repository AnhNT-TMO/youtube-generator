import json
from pathlib import Path
import re
import subprocess
import sys

import plan_io

LOUD = plan_io.LOUDNESS
ACCENTS = plan_io.CONFIG['arrangement_contract']['accents']


def ebur128(path):
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path), '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    summary = result.stderr[result.stderr.rfind('Summary:'):]
    integrated = float(re.search(r'I:\s+(-?[\d.]+) LUFS', summary).group(1))
    peak = float(re.search(r'True peak:\s+Peak:\s+(-?[\d.]+) dBFS', summary).group(1))
    return {'integrated_lufs': integrated, 'true_peak_dbtp': peak, 'method': 'ffmpeg ebur128 peak=true on the delivered MP3 (separate process and filter from the finishing loudnorm pass)'}


def duration(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(path)], capture_output=True, text=True, check=True)
    return float(result.stdout)


delivery = Path(sys.argv[1]).resolve()
failures = []
checksums = {name: value for name, value in plan_io.load(delivery / 'checksums.json').items() if name != 'worker-qa.json'}
actual = {str(path.relative_to(delivery)) for path in delivery.rglob('*') if path.is_file() and path.name not in ('checksums.json', 'worker-qa.json')}
if actual != set(checksums):
    failures.append({'inventory_mismatch': sorted(actual ^ set(checksums))})
for name, expected in checksums.items():
    if plan_io.digest(delivery / name) != expected:
        failures.append({'checksum': name})
listening = plan_io.load(delivery / 'listening-map.json')
measured = {}
for style, variant in listening['variants'].items():
    mp3 = delivery / variant['mp3']
    row = ebur128(mp3)
    row['duration_s'] = duration(mp3)
    row['sha256_matches_map'] = plan_io.digest(mp3) == variant['mp3_sha256']
    row['lufs_ok'] = row['integrated_lufs'] <= LOUD['lufs_max']
    row['lufs_within_0p5_of_target'] = abs(row['integrated_lufs'] - LOUD['target_lufs']) <= 0.5
    row['true_peak_ok'] = row['true_peak_dbtp'] <= LOUD['true_peak_max_dbtp']
    row['duration_matches_base'] = abs(row['duration_s'] - variant['duration_s']) <= 0.1
    row['raw_files_present'] = (delivery / variant['base']['raw_path_local']).is_file() and (delivery / variant['base']['backup_raw_local']).is_file()
    row['raw_sha_matches'] = plan_io.digest(delivery / variant['base']['raw_path_local']) == variant['base']['raw_sha256'] and plan_io.digest(delivery / variant['base']['backup_raw_local']) == variant['base']['backup_raw_sha256']
    proof = delivery / 'proof' / style
    row['proof_complete'] = all((proof / name).is_file() for name in ['src_A.mid', 'track-plan.json', 'cover-revision.json', 'mix-manifest.json', 'finishing.json', 'hashes.json'])
    row['proof_hashes_match'] = plan_io.load(proof / 'hashes.json')['mp3_sha256'] == variant['mp3_sha256']
    row['chime_window_ok'] = all(min(abs(accent['actual_fraction_of_musical_end'] - target) for target in ACCENTS['target_fractions']) <= ACCENTS['max_shift_fraction'] and ACCENTS['relative_db_range'][0] <= accent['actual_relative_db'] <= ACCENTS['relative_db_range'][1] for accent in variant['accents'])
    measured[style] = row
    for key in ('sha256_matches_map', 'lufs_ok', 'true_peak_ok', 'duration_matches_base', 'raw_files_present', 'raw_sha_matches', 'proof_complete', 'proof_hashes_match', 'chime_window_ok'):
        if not row[key]:
            failures.append({style: key})
proof = delivery / 'proof'
for name in ['melody-source.json', 'PD-BASIS.md', 'DISPUTE.txt', 'arrangement-plan.json', 'chime/chime-manifest.json']:
    if not (proof / name).is_file():
        failures.append({'proof_missing': name})
media = [str(path.relative_to(proof)) for path in proof.rglob('*') if path.suffix.lower() in ('.wav', '.flac', '.mp3')]
if media:
    failures.append({'proof_contains_audio': media})
report = {'all_pass': not failures, 'failures': failures, 'measured': measured, 'files_checked': len(checksums)}
plan_io.save(delivery / 'worker-qa.json', report)
print(json.dumps({'all_pass': report['all_pass'], 'failures': failures, 'measured': {s: [round(r['integrated_lufs'], 2), round(r['true_peak_dbtp'], 2), round(r['duration_s'], 1)] for s, r in measured.items()}}), flush=True)
sys.exit(0 if report['all_pass'] else 5)
