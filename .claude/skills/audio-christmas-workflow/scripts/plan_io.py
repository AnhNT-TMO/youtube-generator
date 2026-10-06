import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_config():
    if os.environ.get('CAROL_WORKFLOW'):
        return Path(os.environ['CAROL_WORKFLOW']).resolve()
    if (HERE / 'WORKFLOW.json').is_file():
        return HERE / 'WORKFLOW.json'
    for parent in HERE.parents:
        candidate = parent / 'research' / 'christmas-carols' / 'WORKFLOW.json'
        if candidate.is_file():
            return candidate
    raise SystemExit('WORKFLOW.json not found: set CAROL_WORKFLOW or run sync')


CONFIG_PATH = find_config()
CONFIG = json.loads(CONFIG_PATH.read_text())
PIPELINE = CONFIG['pipeline']
RENDER = PIPELINE['render']
CHIME = PIPELINE['chime']
LOUDNESS = PIPELINE['loudness']
STYLE_ORDER = PIPELINE['styles']
STYLE_LABEL = {style: item['label'] for style, item in CONFIG['arrangement_contract']['styles'].items()}
FILE_LABEL = PIPELINE['file_labels']
CHORD_QUALITY = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11], 'dim': [0, 3, 6], 'sus4': [0, 5, 7], 'sus2': [0, 2, 7], '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9]}
MINOR_QUALITIES = {'m', 'm7', 'm6', 'dim'}


def repo_root():
    for parent in HERE.parents:
        if (parent / 'research' / 'christmas-carols').is_dir():
            return parent
    raise SystemExit('repository root not found (Mac-only command)')


def server_path(key):
    return Path.home() / PIPELINE['server'][key]


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def write_checksums(root):
    root = Path(root)
    save(root / 'checksums.json', {str(path.relative_to(root)): digest(path) for path in sorted(root.rglob('*')) if path.is_file() and path.name != 'checksums.json'})


def styles_for(root, revision):
    return [style for style in STYLE_ORDER if (Path(root) / style / revision / 'track-plan.json').is_file()]


def beat_seconds(plan):
    return 60 / plan['meta']['tempo']


def beats_per_bar(meter):
    numerator, denominator = (int(part) for part in meter.split('/'))
    return numerator * 4 / denominator


def sections(plan):
    if 'form' in plan:
        return [{'id': item['section'], 'kind': item['kind'], 'start_beat': item['start_beat'], 'end_beat': item['end_beat'], 'key': item.get('key')} for item in plan['form']['sections']]
    bar = beats_per_bar(plan['meta']['meter'])
    return [{'id': item['id'], 'kind': None, 'start_beat': (item['start_bar'] - 1) * bar, 'end_beat': (item['start_bar'] - 1 + item['bars']) * bar, 'key': item.get('key')} for item in plan['phrase_plan']]


def length_beats(plan):
    return max(item['end_beat'] for item in sections(plan))


def dry_seconds(plan):
    return length_beats(plan) * beat_seconds(plan) + RENDER['dry_tail_seconds']


def support_part(plan):
    parts = [part for part in plan['base_parts'] if part not in ('piano', 'pad')]
    assert len(parts) <= 1 and parts == ([plan['style']] if plan['style'] != 'plain' else [])
    return parts[0] if parts else None


def melody_end_beat(plan):
    return max(note['beat'] + note['duration'] for note in plan['note_plan']['events'] if note['part'] == 'melody')


def statement_spans(plan):
    pivots = plan['key_plan'].get('pivots', [])
    rows = []
    for item in plan['form']['sections']:
        if item['kind'] != 'statement':
            continue
        start, end = item['start_beat'], item['end_beat']
        for pivot in pivots:
            if start < pivot['beat'] < end:
                end = min(end, pivot['beat'])
        rows.append((item['section'], start, end, item['key']))
    return rows


def events_for(notes, beat_s):
    return sorted([event for note in notes for event in [(note['beat'] * beat_s, 1, note['pitch'], note['velocity'], note['channel']), ((note['beat'] + note['duration']) * beat_s, 0, note['pitch'], 0, note['channel'])]], key=lambda event: (event[0], event[1]))


def file_title(plan):
    return '-'.join(''.join(ch for ch in word if ch.isalnum()) for word in plan['meta']['title'].split())


def on_server():
    import sys
    return sys.platform == 'linux' and 'youtube.slice' in Path('/proc/self/cgroup').read_text()


def require_server():
    assert on_server(), 'run on the GPU server inside youtube.slice (run.sh via guard.sh run)'


def home_path(path):
    return path if path.startswith('/') else f'$HOME/{path}'


def shell_env():
    server = PIPELINE['server']
    rows = {f'PY_{name.upper()}': f'$HOME/{path}' for name, path in server['python'].items()}
    rows.update({
        'WORK': home_path(os.environ.get('CAROL_WORK_ROOT') or server['work_root']),
        'CAL': f'$HOME/{server["calibration"]}',
        'PUBLISHED': home_path(os.environ.get('CAROL_PUBLISHED_ROOT') or server['published_root']),
        'ACE_HOME': f'$HOME/{server["pythonpath"]}',
        'REFSPLIT_DIR': f'$HOME/{server["refsplit"]["dir"]}',
        'REFSPLIT_VIDEOS': ' '.join(server['refsplit']['videos']),
        'REFSPLIT_TRACKS': str(server['refsplit']['expected_tracks']),
        'GPU_LOCK': server['gpu_lock'],
        'THREADS': str(server['threads']),
        'STYLES': ' '.join(STYLE_ORDER),
        'DEFAULT_REVISION': PIPELINE['default_revision'],
    })
    return '\n'.join(f'{key}="{value}"' for key, value in rows.items())


if __name__ == '__main__':
    print(shell_env())
