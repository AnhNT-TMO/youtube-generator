#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from mureka_stems import OUT_ROOT, REPO, SOURCE_ROOT, take_style

TIE_MARGIN = 5.0


def flags_for(take, stems):
    flags = []
    opening = take['opening']
    if not opening['recognizable']:
        flags.append(f"mở đầu không nhận ra bài ({opening['margin']:+.0f} < +{opening['min_margin']:g})")
    if take['transpose_semitones']:
        flags.append(f"đổi giọng {take['transpose_semitones']:+d}")
    if stems['percussion']:
        flags.append(f"có bộ gõ ({stems['percussion_energy_pct']} % năng lượng)")
    if stems['voice_in_passes']:
        flags.append(f"có giọng ở lượt {stems['voice_in_passes']}")
    return flags


def rank(takes):
    takes = sorted(takes, key=lambda t: -t['opening_margin'])
    if len(takes) > 1 and takes[0]['opening_margin'] - takes[1]['opening_margin'] < TIE_MARGIN:
        takes = sorted(takes[:2], key=lambda t: t['extra_per_ref_note']) + takes[2:]
    return takes


def pick(slug):
    out = REPO / OUT_ROOT / slug
    load = lambda name: {t['file']: t for t in json.loads((out / name).read_text())['takes']} if (out / name).exists() else {}
    fidelity, stems = load('fidelity.json'), load('stems.json')
    takes = []
    for path in sorted(out.glob(f'{slug}_*.wav')):
        style = take_style(slug, path.name)
        row = {'file': path.name, 'style': style}
        take, stem = fidelity.get(path.name), stems.get(path.name)
        if not take or 'opening' not in take or not stem or 'ok' not in stem:
            row.update(status='unmeasured', flags=['chưa đo: chạy mureka_fidelity.py rồi mureka_stems.py'])
        else:
            flags = flags_for(take, stem)
            sidecar = path.with_suffix('.json')
            accepted = json.loads(sidecar.read_text()).get('ceo_accepted') if sidecar.exists() else None
            status = 'clean' if not flags else 'accepted' if accepted else 'listen'
            row.update(status=status, flags=flags, ceo_accepted=accepted,
                       opening_margin=take['opening']['margin'], extra_per_ref_note=take['extra_per_ref_note'])
        takes.append(row)
    styles = {}
    for style in sorted({t['style'] for t in takes if t['style']}):
        mine = [t for t in takes if t['style'] == style]
        clean = rank([t for t in mine if t['status'] == 'clean']) + rank([t for t in mine if t['status'] == 'accepted'])
        styles[str(style)] = {'pick': clean[0]['file'] if clean else None,
                              'spare': [t['file'] for t in clean[1:]],
                              'listen': [t['file'] for t in mine if t['status'] == 'listen'],
                              'regenerate_after_listen': not clean and any(t['status'] == 'listen' for t in mine)}
    report = {'slug': slug, 'checked': date.today().isoformat(),
              'tie_margin': TIE_MARGIN, 'styles': styles, 'takes': takes}
    (out / 'picks.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
    return report


def show(report):
    print(report['slug'])
    for t in report['takes']:
        verdict = {'clean': 'sạch', 'listen': 'CẦN NGHE: ' + '; '.join(t['flags']),
                   'unmeasured': '; '.join(t['flags']),
                   'accepted': f"CEO nhận dù có cờ ({'; '.join(t['flags'])}): {t.get('ceo_accepted')}"}[t['status']]
        margin = f"{t['opening_margin']:+.0f}" if t.get('opening_margin') is not None else '-'
        print(f"  {t['file']:52} style {t['style']}  mở đầu {margin:>4}  {verdict}")
    for style, s in report['styles'].items():
        if s['pick']:
            line = f"dùng {s['pick']}" + (f", dự phòng {', '.join(s['spare'])}" if s['spare'] else '')
        elif s['regenerate_after_listen']:
            line = 'không bản nào sạch: CEO nghe các bản cần nghe trước, bỏ thì tạo lại'
        else:
            line = 'chưa có bản đo xong'
        if s['listen'] and s['pick']:
            line += f"; CEO nghe: {', '.join(s['listen'])}"
        print(f"  style {style}: {line}")


def main():
    ap = argparse.ArgumentParser(description='Xếp bản Mureka theo từng style từ fidelity.json + stems.json: bản sạch được dùng trước, rồi bản CEO đã nhận (mureka_web.py accept); bản có cờ khác chờ CEO nghe (không tự xoá).')
    ap.add_argument('slugs', nargs='+')
    args = ap.parse_args()
    for slug in args.slugs:
        if not (REPO / SOURCE_ROOT / slug / 'metadata.json').exists():
            sys.exit(f'không có nguồn {SOURCE_ROOT / slug}')
        show(pick(slug))


if __name__ == '__main__':
    main()
