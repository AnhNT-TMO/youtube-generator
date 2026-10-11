#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mureka_source import variant_names

JS_DIR = Path(__file__).resolve().parent / 'js'
SOURCE_ROOT = Path('research/christmas-carols/mureka')
OUT_ROOT = Path('audio/christmas/mureka')
DOWNLOADS = Path.home() / 'Downloads'
FOLDER_ID = '165159201144833'
MODEL = 'V9'
DURATION_TOLERANCE_S = 0.3


def die(msg, code=1):
    print(f'✖ {msg}', file=sys.stderr)
    sys.exit(code)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def mmss(seconds, pad=True):
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}' if pad else f'{m}:{s:02d}'


def media_seconds(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout)


def upload_mp3(source_root, wav_path):
    mp3 = Path(source_root) / '_upload' / f'{wav_path.stem}.mp3'
    if not mp3.exists() or mp3.stat().st_mtime < wav_path.stat().st_mtime:
        mp3.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav_path), '-b:a', '320k', str(mp3)], check=True)
    return mp3


def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_styles(path):
    parts = re.split(r'^STYLE\s+(\d+)[^\n]*\n', path.read_text(), flags=re.M)
    return {int(n): body.strip() for n, body in zip(parts[1::2], parts[2::2])}


def same_prompt(a, b):
    norm = lambda s: ' '.join((s or '').split()).casefold()
    return norm(a) == norm(b)


class Ledger:
    def __init__(self, out_root):
        self.root = Path(out_root)
        self.path = self.root / 'manifest.json'
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'generations': []}

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + '\n')
        tmp.replace(self.path)

    @property
    def gens(self):
        return self.data['generations']

    def get(self, gid):
        for g in self.gens:
            if g['id'] == gid:
                return g
        die(f'không có lượt {gid} trong {self.path}')

    def evidence(self, g, kind):
        return self.root / g['slug'] / 'gen' / f'{g["id"]}.{kind}.json'

    def next_take(self, slug, variant):
        used = [t['take'] for g in self.gens if g['slug'] == slug and g['variant'] == variant for t in g.get('takes', [])]
        return max(used, default=0) + 1


def source_info(source_root, slug):
    src = Path(source_root) / slug
    meta_path, styles_path, wav_path = src / 'metadata.json', src / 'styles.md', src / f'{slug}.wav'
    for p in (meta_path, styles_path, wav_path):
        if not p.exists():
            die(f'thiếu {p} (chạy mureka_source.py trước)')
    meta = json.loads(meta_path.read_text())
    return meta, read_styles(styles_path), wav_path


def cmd_next(a):
    led = Ledger(a.out)
    meta, styles, wav_path = source_info(a.source, a.slug)
    if a.style not in styles:
        die(f'style {a.style} không có trong styles.md (có {sorted(styles)})')
    variant = variant_names(meta['support_instruments_for_styles'])[a.style - 1]
    open_gen = next((g for g in led.gens if g['slug'] == a.slug and g['style'] == a.style and g['status'] == 'prepared'
                     and not a.existing_feed), None)
    if open_gen:
        g = open_gen
    else:
        gid = f'm{len(led.gens) + 1:03d}'
        g = {
            'id': gid, 'slug': a.slug, 'song_title': meta['title'], 'style': a.style, 'variant': variant,
            'prompt': styles[a.style], 'instrumental': True, 'lyrics': '', 'mureka_title': a.title or f'{meta["title"]} {gid}'[:50],
            'source_wav': str(wav_path), 'source_name': wav_path.stem, 'source_duration_s': round(wav_seconds(wav_path), 3),
            'model': a.model, 'folder_id': a.folder_id, 'status': 'prepared', 'prepared_at': now(),
            'prepared_epoch': int(time.time()) - 60,
        }
        if a.existing_feed:
            g.update(feed_id=str(a.existing_feed), status='submitted', adopted=True, mureka_title=a.title or meta['title'])
        led.gens.append(g)
    mp3 = upload_mp3(a.source, wav_path)
    original = Path(a.out) / a.slug / 'original.mp3'
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mp3, original)
    g.update(upload_mp3=str(mp3), upload_duration_s=round(media_seconds(mp3), 3))
    led.save()
    print(f'GEN={g["id"]}  {g["slug"]} style {g["style"]} ({g["variant"]})  status {g["status"]}')
    print(f'  Mureka title: {g["mureka_title"]}')
    print('  Instrumental bật')
    print(f'  source: {g["source_wav"]} ({mmss(g["source_duration_s"])})  prompt {len(g["prompt"])} ký tự')
    print(f'  upload lên Mureka: {g["upload_mp3"]} (MP3, không upload WAV; xoá dòng cùng tên trong Upload trước khi upload lại)')
    if g['status'] == 'prepared':
        print('  tiếp: js attach → js fill (ok:true) → bấm Create một lần → js feed → complete')
    else:
        print('  tiếp: js feed → complete')


def js_params(led, g, name, take):
    if name == 'attach':
        seconds = g.get('upload_duration_s', g['source_duration_s'])
        return {'name': g['source_name'], 'upload': g.get('upload_mp3'),
                'durations': sorted({mmss(seconds), mmss(seconds + 1)})}
    if name == 'fill':
        return {'prompt': g['prompt'], 'title': g['mureka_title'], 'source': g['source_name'],
                'instrumental': g.get('instrumental', True), 'lyrics': g.get('lyrics', '')}
    if name == 'feed':
        return {'feed_id': g.get('feed_id'), 'title': g['mureka_title'], 'after_s': g['prepared_epoch'],
                'folder_id': g['folder_id'], 'timeout_s': 240}
    if name == 'download':
        t = find_take(g, take)
        return {'share_key': t['share_key'], 'page_url': downloader_url(t['share_key']), 'filename': t['file'],
                'expect': mmss(t['duration_ms'] / 1000, pad=False)}
    die(f'không có snippet {name}')


def downloader_url(share_key):
    return 'https://murekadownloader.com/download?type=mureka&url=' + quote(f'https://www.mureka.ai/song-detail/{share_key}', safe='')


def find_take(g, take):
    if not take:
        die('cần --take vN')
    n = int(str(take).lstrip('v'))
    for t in g.get('takes', []):
        if t['take'] == n:
            return t
    die(f'{g["id"]} không có take v{n} (chạy complete trước)')


def cmd_js(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    params = js_params(led, g, a.name, a.take)
    if a.name == 'download':
        print(f'// navigate_page tab murekadownloader tới: {params["page_url"]}', file=sys.stderr)
    src = (JS_DIR / f'mureka_{a.name}.js').read_text()
    print(src.replace('/*PARAMS*/null', json.dumps(params, ensure_ascii=False)))


def cmd_complete(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    path = Path(a.feed) if a.feed else led.evidence(g, 'feed')
    if not path.exists():
        die(f'thiếu {path}: evaluate_script với js feed, filePath = {path}')
    raw = json.loads(path.read_text())
    feed = raw.get('feed') if isinstance(raw, dict) and 'feed' in raw else raw
    if not feed or not raw.get('done', True):
        die(f'feed chưa xong ({path}): chạy lại js feed')
    songs = feed['songs']
    problems = []
    if len(songs) != 2:
        problems.append(f'feed có {len(songs)} bài, cần 2')
    for s in songs:
        if not same_prompt(s.get('description'), g['prompt']) and not g.get('adopted'):
            problems.append(f'{s["song_id"]}: prompt Mureka lưu khác prompt đã điền')
        if s.get('model') and s['model'] != g['model']:
            problems.append(f'{s["song_id"]}: model {s["model"]}, cần {g["model"]}')
        if s.get('generate_state') != 3:
            problems.append(f'{s["song_id"]}: generate_state {s.get("generate_state")} (3 = xong)')
    if problems and not a.pm_ok:
        for p in problems:
            print(f'  ✖ {p}')
        die('feed lệch spec: báo PM; nhận vẫn được với --pm-ok "<quyết định>"', 2)
    if g.get('takes'):
        print(f'{g["id"]}: đã complete trước đó, giữ số take cũ')
    else:
        first = led.next_take(g['slug'], g['variant'])
        g['takes'] = []
        for i, s in enumerate(songs):
            n = first + i
            g['takes'].append({
                'take': n, 'song_id': s['song_id'], 'share_key': s['share_key'],
                'mureka_url': f'https://www.mureka.ai/song-detail/{s["share_key"]}',
                'duration_ms': s['duration_ms'], 'bpm': s.get('bpm'), 'liked': s.get('is_liked'),
                'file': f'{g["slug"]}_{g["variant"]}_v{n}.wav', 'status': 'to_download',
            })
    g.update(status='complete', feed_id=feed['feed_id'], feed_model=feed.get('model'), completed_at=now(),
             stored_prompt=songs[0].get('description'), feed_problems=problems or None, pm_ok=a.pm_ok)
    led.save()
    for t in g['takes']:
        print(f'  v{t["take"]}: {t["file"]}  {t["duration_ms"] / 1000:.2f} s  liked={t["liked"]}  {t["mureka_url"]}')


def cmd_ingest(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    t = find_take(g, a.take)
    want = t['duration_ms'] / 1000
    src = Path(a.file) if a.file else Path(a.downloads) / t['file']
    deadline = time.time() + a.wait
    while not src.exists() or Path(str(src) + '.crdownload').exists():
        if time.time() > deadline:
            die(f'chưa thấy {src} sau {a.wait:g} s')
        time.sleep(2)
    got = wav_seconds(src)
    if abs(got - want) > DURATION_TOLERANCE_S:
        die(f'{src.name} dài {got:.2f} s, Mureka ghi {want:.2f} s: sai file, không nhận')
    dest_dir = led.root / g['slug']
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / t['file']
    if dest.exists() and not a.force:
        die(f'{dest} đã có (--force để ghi đè)')
    sidecar = {
        'generation': g['id'], 'slug': g['slug'], 'song_title': g['song_title'], 'style': g['style'],
        'variant': g['variant'], 'take': f'v{t["take"]}', 'prompt': g.get('stored_prompt') or g['prompt'], 'model': g['model'],
        'feed_id': g['feed_id'], 'song_id': t['song_id'], 'share_key': t['share_key'], 'mureka_url': t['mureka_url'],
        'duration_ms': t['duration_ms'], 'file_duration': round(got, 3), 'sha256': file_sha256(src),
        'source_wav': g['source_wav'], 'downloaded_via': 'murekadownloader.com', 'downloaded_at': now(),
    }
    dest.with_suffix('.json').write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + '\n')
    shutil.move(str(src), dest)
    t.update(status='downloaded', path=str(dest), file_duration=sidecar['file_duration'], sha256=sidecar['sha256'])
    led.save()
    print(f'✔ {dest}  {got:.2f} s (Mureka {want:.2f} s)')


def cmd_skip(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    t = find_take(g, a.take)
    t.update(status='skipped', skip_reason=a.reason)
    led.save()
    print(f'{g["id"]} v{t["take"]}: bỏ ({a.reason})')


def take_files(led, g, t):
    wav = led.root / g['slug'] / t['file']
    return [wav.with_suffix(ext) for ext in ('.wav', '.json', '.mp3') if wav.with_suffix(ext).exists()]


def cmd_drop(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    t = find_take(g, a.take)
    if t['status'] != 'downloaded':
        die(f'{g["id"]} v{t["take"]} đang {t["status"]}, không có file để xoá')
    for path in take_files(led, g, t):
        path.unlink()
        print(f'  xoá {path}')
    t.update(status='deleted', delete_reason=a.reason, deleted_at=now())
    led.save()
    print(f'{g["id"]} v{t["take"]}: đã xoá ({a.reason})')


def cmd_accept(a):
    led = Ledger(a.out)
    g = led.get(a.gen)
    t = find_take(g, a.take)
    if t['status'] != 'downloaded':
        die(f'{g["id"]} v{t["take"]} đang {t["status"]}, không có file để nhận')
    sidecar = led.root / g['slug'] / Path(t['file']).with_suffix('.json').name
    data = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    data.update(ceo_accepted=a.reason, ceo_accepted_at=now())
    sidecar.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    t.update(ceo_accepted=a.reason)
    led.save()
    print(f'{g["id"]} v{t["take"]}: CEO nhận dù có cờ ({a.reason})')


def cmd_status(a):
    led = Ledger(a.out)
    if not led.gens:
        print(f'chưa có lượt nào ({led.path})')
        return
    for g in led.gens:
        if a.slug and g['slug'] != a.slug:
            continue
        line = f'{g["id"]}  {g["slug"]}  style {g["style"]} {g["variant"]}  {g["status"]}'
        takes = g.get('takes', [])
        if takes:
            line += '  ' + ' '.join(f'v{t["take"]}:{t["status"]}' for t in takes)
        print(line)
        if g['status'] == 'prepared':
            print('    tiếp: js attach → js fill → Create → js feed → complete')
        elif g['status'] == 'submitted':
            print('    tiếp: js feed → complete')
        for t in takes:
            if t['status'] == 'to_download':
                print(f'    tải v{t["take"]}: navigate {downloader_url(t["share_key"])} → js download → ingest')


def main():
    ap = argparse.ArgumentParser(description='Mureka web (Remix) lane: spec, page scripts, feed check, WAV ingest.')
    ap.add_argument('--out', default=str(OUT_ROOT), help='thư mục kết quả; file vào <out>/<slug>/, sổ <out>/manifest.json')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('next', help='tạo (hoặc lấy lại) một lượt cho bài + style')
    p.add_argument('slug')
    p.add_argument('--style', type=int, required=True, help='số STYLE trong styles.md')
    p.add_argument('--source', default=str(SOURCE_ROOT))
    p.add_argument('--title', help='title trên Mureka (mặc định "<tên bài> <gen>")')
    p.add_argument('--model', default=MODEL)
    p.add_argument('--folder-id', default=FOLDER_ID, help='folder "My workspace" trong feed API')
    p.add_argument('--existing-feed', help='nhận một lượt đã tạo tay trên web (feed_id) thay vì tạo mới')
    p.set_defaults(fn=cmd_next)

    p = sub.add_parser('js', help='in page script đã gắn tham số cho evaluate_script')
    p.add_argument('name', choices=['attach', 'fill', 'feed', 'download'])
    p.add_argument('--gen', required=True)
    p.add_argument('--take', help='vN (cho download)')
    p.set_defaults(fn=cmd_js)

    p = sub.add_parser('complete', help='kiểm feed và đặt tên take v1/v2')
    p.add_argument('--gen', required=True)
    p.add_argument('--feed', help='JSON của js feed (mặc định <out>/<slug>/gen/<gen>.feed.json)')
    p.add_argument('--pm-ok', help='quyết định của PM khi nhận feed lệch spec')
    p.set_defaults(fn=cmd_complete)

    p = sub.add_parser('ingest', help='chuyển WAV đã tải từ ~/Downloads vào <out>/<slug>/')
    p.add_argument('--gen', required=True)
    p.add_argument('--take', required=True)
    p.add_argument('--file', help='file WAV đã tải (mặc định ~/Downloads/<tên take>.wav)')
    p.add_argument('--downloads', default=str(DOWNLOADS))
    p.add_argument('--wait', type=float, default=120, help='chờ file tải xong tối đa N giây')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser('skip', help='đánh dấu một take không tải')
    p.add_argument('--gen', required=True)
    p.add_argument('--take', required=True)
    p.add_argument('--reason', required=True)
    p.set_defaults(fn=cmd_skip)

    p = sub.add_parser('drop', help='xoá một take đã tải (chỉ khi CEO bảo bỏ), ghi lý do vào sổ')
    p.add_argument('--gen', required=True)
    p.add_argument('--take', required=True)
    p.add_argument('--reason', required=True)
    p.set_defaults(fn=cmd_drop)


    p = sub.add_parser('accept', help='CEO nghe bản có cờ và nhận dùng: ghi ceo_accepted vào sidecar, mureka_pick coi là dùng được')
    p.add_argument('--gen', required=True)
    p.add_argument('--take', required=True)
    p.add_argument('--reason', required=True)
    p.set_defaults(fn=cmd_accept)

    p = sub.add_parser('status', help='các lượt và việc còn lại')
    p.add_argument('--slug')
    p.set_defaults(fn=cmd_status)

    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
