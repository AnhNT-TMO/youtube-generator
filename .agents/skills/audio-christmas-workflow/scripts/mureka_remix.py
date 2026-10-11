#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = 'https://api.mureka.ai'
KEY_FILE = Path.home() / '.config' / 'mureka' / 'api_key'
PROMPT_LIMIT = 1024
INSTRUMENTAL_LYRICS = '[Instrumental]'
COMPACT = [
    (', reharmonize the melody, rewrite notes, add a pickup, change the meter, repeat the melody, or create a new BPM.',
     ', reharmonize, rewrite notes, add a pickup or repeat the melody.'),
    ('Keep this an instrumental Christmas cover with no lead vocal, no lyrics, no drums, no bass, no guitar, no brass, and no cinematic orchestration.',
     'Instrumental Christmas cover: no lead vocal, lyrics, drums, bass, guitar, brass or cinematic orchestration.'),
]
DONE = {'succeeded', 'failed', 'timeouted', 'cancelled'}


def api_key():
    key = os.environ.get('MUREKA_API_KEY') or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else '')
    if not key:
        sys.exit(f'no Mureka API key: set MUREKA_API_KEY or write it to {KEY_FILE}')
    return key


def call(method, path, key, body=None, content_type='application/json'):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={'Authorization': f'Bearer {key}'})
    if data is not None:
        req.add_header('Content-Type', content_type)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        sys.exit(f'{method} {path} -> HTTP {err.code}: {err.read().decode(errors="replace")}')


def upload_audio(path, purpose, key):
    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\n{purpose}\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f'Content-Type: audio/mpeg\r\n\r\n'.encode() + path.read_bytes() + b'\r\n',
        f'--{boundary}--\r\n'.encode(),
    ]
    return call('POST', '/v1/files/upload', key, b''.join(parts), f'multipart/form-data; boundary={boundary}')


def read_styles(path):
    parts = re.split(r'^STYLE\s+(\d+)[^\n]*\n', path.read_text(), flags=re.M)
    return {int(n): ' '.join(body.split()) for n, body in zip(parts[1::2], parts[2::2])}


def fit_prompt(text):
    for old, new in COMPACT:
        text = text.replace(old, new)
    if len(text) > PROMPT_LIMIT:
        sys.exit(f'prompt is {len(text)} chars after compaction, Mureka limit is {PROMPT_LIMIT}: shorten styles.md')
    return text


def to_mp3(wav, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-codec:a', 'libmp3lame', '-b:a', '320k', str(out)],
                   check=True)


def download(url, dest):
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, 'wb') as handle:
        handle.write(resp.read())


def poll(task_id, key, interval, timeout):
    start = time.time()
    while True:
        task = call('GET', f'/v1/song/query/{task_id}', key)
        status = task.get('status')
        print(f'  task {task_id}: {status} ({int(time.time() - start)} s)', flush=True)
        if status in DONE:
            return task
        if time.time() - start > timeout:
            sys.exit(f'task {task_id} still {status} after {timeout} s; rerun with --resume to keep waiting')
        time.sleep(interval)


def save_choices(task, out_dir, stem):
    files = []
    for choice in task.get('choices') or []:
        suffix = '' if len(task['choices']) == 1 else f'-{choice.get("index", len(files))}'
        for field, ext in (('url', 'mp3'), ('wav_url', 'wav')):
            if choice.get(field):
                dest = out_dir / f'{stem}{suffix}.{ext}'
                download(choice[field], dest)
                files.append(dest.name)
    return files


def main():
    ap = argparse.ArgumentParser(description='Mureka cover of a PD carol piano source, one call per style.')
    ap.add_argument('--mode', choices=['track', 'remix'], default='track',
                    help='track = /v1/track/generate over the piano (works for instrumental input); '
                         'remix = /v1/song/remix (Mureka refuses audio without sung lyrics)')
    ap.add_argument('--track-type', default='Instrumental', help='generate_type for --mode track')
    ap.add_argument('slug', help='song folder in --source, e.g. deck_the_halls')
    ap.add_argument('--source', default='research/christmas-carols/mureka', help='folder holding <slug>/<slug>.wav + styles.md')
    ap.add_argument('--out', default='mureka', help='output root; files land in <out>/<slug>/')
    ap.add_argument('--styles', default='1,2,3', help='style numbers from styles.md, comma separated')
    ap.add_argument('-n', type=int, default=1, help='songs per call (Mureka max 3, billed per song)')
    ap.add_argument('--interval', type=int, default=10, help='seconds between status polls')
    ap.add_argument('--timeout', type=int, default=900, help='max seconds to wait per task')
    ap.add_argument('--force', action='store_true', help='call again even if <out>/<slug>/style<N>.json already succeeded')
    ap.add_argument('--dry-run', action='store_true', help='print the prompts that would be sent and stop')
    args = ap.parse_args()

    src = Path(args.source) / args.slug
    styles = read_styles(src / 'styles.md')
    wanted = [int(s) for s in args.styles.split(',')]
    missing = [s for s in wanted if s not in styles]
    if missing:
        sys.exit(f'styles {missing} not in {src / "styles.md"} (has {sorted(styles)})')
    prompts = {s: fit_prompt(styles[s]) for s in wanted}
    if args.dry_run:
        for s, text in prompts.items():
            print(f'--- style {s} ({len(text)} chars)\n{text}')
        return

    key = api_key()
    out_dir = Path(args.out) / args.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    purpose = 'audio' if args.mode == 'track' else 'remix'
    upload_record = out_dir / f'upload-{purpose}.json'
    source_wav = src / f'{args.slug}.wav'
    upload = json.loads(upload_record.read_text()) if upload_record.exists() else None
    if not upload or upload.get('source_mtime') != source_wav.stat().st_mtime:
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / f'{args.slug}.mp3'
            to_mp3(source_wav, mp3)
            upload = upload_audio(mp3, purpose, key)
        upload['source_mtime'] = source_wav.stat().st_mtime
        upload_record.write_text(json.dumps(upload, indent=2))
        print(f'uploaded {source_wav} -> {upload.get("id")}')

    for s in wanted:
        record_path = out_dir / f'style{s}.json'
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        if record.get('status') == 'succeeded' and not args.force:
            print(f'style {s}: already done ({", ".join(record.get("files", []))}), --force to redo')
            continue
        task_id = record.get('task_id') if record.get('status') not in DONE else None
        if not task_id:
            if args.mode == 'track':
                endpoint = '/v1/track/generate'
                body = {'upload_audio_id': upload['id'], 'generate_type': args.track_type, 'prompt': prompts[s]}
            else:
                endpoint = '/v1/song/remix'
                body = {'upload_audio_id': upload['id'], 'prompt': prompts[s], 'lyrics': INSTRUMENTAL_LYRICS,
                        'n': args.n}
            task = call('POST', endpoint, key, body)
            task_id = task['id']
            record = {'style': s, 'endpoint': endpoint, 'request': body, 'task_id': task_id,
                      'status': task.get('status')}
            record_path.write_text(json.dumps(record, indent=2))
            print(f'style {s}: task {task_id}')
        task = poll(task_id, key, args.interval, args.timeout)
        record.update(status=task['status'], model=task.get('model'), failed_reason=task.get('failed_reason'),
                      choices=task.get('choices'))
        if task['status'] == 'succeeded':
            record['files'] = save_choices(task, out_dir, f'style{s}')
            print(f'style {s}: saved {record["files"]}')
        else:
            print(f'style {s}: {task["status"]} {task.get("failed_reason") or ""}')
        record_path.write_text(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
