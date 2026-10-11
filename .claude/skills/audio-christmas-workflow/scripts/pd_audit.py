#!/usr/bin/env python3
import argparse
import difflib
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAROLS = ROOT / 'research' / 'christmas-carols'
AUDIT = CAROLS / 'pd-audit'
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MELODY_STATUS = {'pd_confirmed', 'pd_differs', 'no_pd_source'}
CHORD_STATUS = {'pd_harmony', 'own', 'modern_source'}
SOURCE_KIND = {'scan', 'pd_edition'}
VERDICTS = ['clean', 'fix_chords', 'fix_melody', 'fix_both']
FAMILIAR = {'familiar', 'unfamiliar', 'unchecked'}


def note_name(p):
    return 'rest' if p == 0 else f'{NAMES[p % 12]}{p // 12 - 1}'


def melody_files():
    out = {}
    for f in sorted(glob.glob(str(CAROLS / 'melodies' / '*' / '*.json'))):
        d = json.load(open(f))
        if isinstance(d, dict) and 'slug' in d:
            out[d['slug']] = (Path(f), d)
    return out


def tiers():
    text = (CAROLS / 'songlist.md').read_text()
    out = {}
    for t in ('I', 'II', 'III'):
        m = re.search(r'^' + t + r': (.*)$', text, re.M)
        if m:
            for s in m.group(1).split(','):
                out[s.strip()] = t
    return out


def abc_tune(path, pick, x=None):
    text = Path(path).read_text(errors='replace')
    blocks = re.split(r'(?m)^(?=X:)', text)
    tunes = [b for b in blocks if b.startswith('X:')]
    if x is not None:
        hits = [b for b in tunes if re.match(r'X:\s*' + re.escape(str(x)) + r'\s*$', b.splitlines()[0])]
        if len(hits) != 1:
            sys.exit(f'--x {x} matches {len(hits)} tunes')
        return hits[0]
    if len(tunes) <= 1:
        return tunes[0] if tunes else text
    titles = [(b, re.findall(r'(?m)^T:\s*(.*)$', b)) for b in tunes]
    if not pick:
        sys.exit(f'{len(tunes)} tunes in this ABC file, use --pick with part of one title')
    hits = [(b, t) for b, t in titles if any(pick.lower() in x.lower() for x in t)]
    if len(hits) != 1:
        sys.exit(f'--pick "{pick}" matches {len(hits)} tunes (use --x <number>):\n' + '\n'.join(f'  {b.splitlines()[0]}  {" / ".join(t)}' for b, t in hits))
    return hits[0][0]


def abc_voice(tune, voice):
    voice_re = re.compile(r'^\s*(?:\[V:\s*([^\]\s]+)[^\]]*\]|V:\s*(\S+))(.*)$')
    lines = tune.splitlines()
    k = next((i for i, x in enumerate(lines) if x.startswith('K:')), None)
    if k is None:
        return tune
    head = [x for x in lines[:k + 1] if not x.startswith('V:') and not x.startswith('%%staves') and not x.startswith('%%score')]
    declared = [m.group(1) or m.group(2) for m in map(voice_re.match, lines) if m]
    if not declared:
        return tune
    want = voice or declared[0]
    if want not in declared:
        sys.exit(f'voice {want} not in this tune; voices: {sorted(set(declared))}')
    body, current = [], declared[0]
    for x in lines[k + 1:]:
        m = voice_re.match(x)
        if m:
            current = m.group(1) or m.group(2)
            x = m.group(3)
        if current == want and not x.startswith('w:') and not x.startswith('W:') and x.strip():
            body.append(x)
    return '\n'.join(head + body) + '\n'


QUALITY = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10), 'dim': (0, 3, 6),
           'sus4': (0, 5, 7), 'sus2': (0, 2, 7), '6': (0, 4, 7, 9), 'm6': (0, 3, 7, 9)}
PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
CHORD_RE = re.compile(r'^([A-G])([#b]?)(|m|7|maj7|m7|dim|sus4|sus2|6|m6)(?:/([A-G])([#b]?))?$')


def parse_chord(sym):
    m = CHORD_RE.match(sym)
    if not m:
        sys.exit(f'bad chord symbol {sym}')
    acc = {'#': 1, 'b': -1, '': 0}
    root = (PC[m.group(1)] + acc[m.group(2)]) % 12
    bass = (PC[m.group(4)] + acc[m.group(5) or '']) % 12 if m.group(4) else root
    return root, m.group(3), bass


def load_score(path, pick, x=None):
    from music21 import converter, stream
    if Path(path).suffix.lower() == '.abc':
        tune = abc_tune(path, pick, x)
        voices = abc_voices(tune)
        if len(voices) > 1:
            sc = stream.Score()
            for v in voices:
                sc.insert(0, converter.parse(abc_voice(tune, v), format='abc').parts[0])
            return sc
        return converter.parse(abc_voice(tune, None), format='abc')
    obj = converter.parse(str(path))
    if isinstance(obj, stream.Opus):
        scores = list(obj.scores)
        titles = [(s.metadata.title if s.metadata else '') or '' for s in scores]
        if not pick:
            sys.exit('multi-tune file, use --pick with part of one title:\n' + '\n'.join(f'  {t}' for t in titles))
        hits = [s for s, t in zip(scores, titles) if pick.lower() in t.lower()]
        if len(hits) != 1:
            sys.exit(f'--pick "{pick}" matches {len(hits)} tunes:\n' + '\n'.join(f'  {t}' for t in titles if pick.lower() in t.lower()))
        obj = hits[0]
    return obj


def abc_voices(tune):
    voice_re = re.compile(r'^\s*(?:\[V:\s*([^\]\s]+)[^\]]*\]|V:\s*(\S+))')
    out = []
    for m in map(voice_re.match, tune.splitlines()):
        if m and (m.group(1) or m.group(2)) not in out:
            out.append(m.group(1) or m.group(2))
    return out


def melody_part(score, part):
    parts = list(score.parts) if score.parts else [score]
    if part >= len(parts):
        sys.exit(f'source has {len(parts)} parts, --part {part} does not exist')
    return parts[part]


def notes_with_onsets(part):
    src = part.stripTies()
    out = []
    for n in src.flatten().notes:
        if n.quarterLength <= 0:
            continue
        p = max(q.midi for q in n.pitches) if n.isChord else n.pitch.midi
        out.append((p, float(n.quarterLength), float(n.getOffsetInHierarchy(src))))
    return out


def our_notes(melody):
    out, t = [], 0.0
    for p, b in melody:
        if p:
            out.append((p, b, t))
        t += b
    return out


def tokens(seq, scale):
    out = []
    for i, n in enumerate(seq):
        step = 'start' if i == 0 else n[0] - seq[i - 1][0]
        out.append((step, round(n[1] * scale * 4) / 4))
    return out


def align(ours, src):
    ours_tok = tokens(ours, 1)
    best = None
    for scale in (1, 0.5, 2, 1.5, 2 / 3):
        sm = difflib.SequenceMatcher(None, ours_tok, tokens(src, scale), autojunk=False)
        same = sum(b.size for b in sm.get_matching_blocks())
        if best is None or same > best[0]:
            best = (same, scale, sm)
    same, scale, sm = best
    shift = 0
    for b in sm.get_matching_blocks():
        if b.size:
            shift = ours[b.a][0] - src[b.b][0]
            break
    return same, scale, shift, sm


def source_for(args):
    score = load_score(Path(args.source), args.pick, args.x)
    if Path(args.source).suffix.lower() == '.abc' and args.voice:
        from music21 import converter
        part = converter.parse(abc_voice(abc_tune(Path(args.source), args.pick, args.x), args.voice), format='abc').parts[0]
    else:
        part = melody_part(score, args.part)
    src = notes_with_onsets(part)
    if not src:
        sys.exit('no notes found in the source part')
    return score, src


def cmd_compare(args):
    files = melody_files()
    if args.slug not in files:
        sys.exit(f'no melody file for {args.slug}')
    ours = our_notes(files[args.slug][1]['melody'])
    _, src = source_for(args)
    same, scale, shift, sm = align(ours, src)
    pitch_sm = difflib.SequenceMatcher(None, [t[0] for t in tokens(ours, 1)], [t[0] for t in tokens(src, scale)], autojunk=False)
    pitch_same = sum(b.size for b in pitch_sm.get_matching_blocks())
    print(f'{args.slug} vs {Path(args.source).name}' + (f' [{args.pick or args.x}]' if args.pick or args.x else '') + f' part {args.part}')
    print(f'notes: ours {len(ours)}, source {len(src)}; source note values x{scale:g}; transposed by {shift} semitones')
    print(f'pitch+rhythm match: {same}/{len(ours)} of ours ({100 * same / len(ours):.0f}%), {same}/{len(src)} of source ({100 * same / len(src):.0f}%)')
    print(f'pitch-only match: {pitch_same}/{len(ours)} of ours ({100 * pitch_same / len(ours):.0f}%)')
    diffs = [op for op in sm.get_opcodes() if op[0] != 'equal']
    if not diffs:
        print('differences: none')
        return
    print('differences (beat = quarter beats from our melody start, rests included):')

    def show(seq, i, j, sc, sh):
        return ' '.join(f'{note_name(n[0] + sh)}:{n[1] * sc:g}' for n in seq[i:j]) or '-'

    for tag, i1, i2, j1, j2 in diffs[:args.limit]:
        at = ours[i1][2] if i1 < len(ours) else ours[-1][2] + ours[-1][1]
        print(f'  beat {at:g} {tag}: ours [{show(ours, i1, i2, 1, 0)}] source [{show(src, j1, j2, scale, shift)}]')
    if len(diffs) > args.limit:
        print(f'  ... {len(diffs) - args.limit} more (use --limit)')


def sonorities(score):
    out = []
    for c in score.chordify().flatten().getElementsByClass('Chord'):
        if c.quarterLength > 0:
            out.append((float(c.offset), float(c.offset + c.quarterLength), sorted(p.midi for p in c.pitches)))
    return out


def cmd_chords(args):
    files = melody_files()
    if args.slug not in files:
        sys.exit(f'no melody file for {args.slug}')
    d = files[args.slug][1]
    ours = our_notes(d['melody'])
    score, src = source_for(args)
    same, scale, shift, sm = align(ours, src)
    pairs = [(ours[b.a + k][2], src[b.b + k][2]) for b in sm.get_matching_blocks() for k in range(b.size)]
    if not pairs:
        sys.exit('melody does not line up with the source; run compare first')
    son = sonorities(score)

    def to_src(beat):
        o, s = pairs[0]
        for po, ps in pairs:
            if po <= beat + 1e-6:
                o, s = po, ps
        return s + (beat - o) / scale

    def sounding(t):
        for a, b, ps in son:
            if a - 1e-6 <= t < b - 1e-6:
                return ps
        return []

    print(f'{args.slug} vs {Path(args.source).name}: melody match {same}/{len(ours)}, source x{scale:g}, transposed by {shift}')
    t, bad, total = 0.0, 0, 0
    for i, (sym, beats) in enumerate(d['chords']):
        root, qual, bass = parse_chord(sym)
        chord_tones = {(root + iv) % 12 for iv in QUALITY[qual]}
        tones = chord_tones | ({bass} if bass is not None else set())
        third = next(((root + iv) % 12 for iv in QUALITY[qual] if iv in (3, 4)), None)
        samples = [t + k * 0.5 for k in range(max(1, int(beats / 0.5)))]
        verdicts = []
        for b in samples:
            ps = sounding(to_src(b))
            pcs = {(p + shift) % 12 for p in ps}
            low = (ps[0] + shift) % 12 if ps else None
            rooted = root in pcs and (third is None or third in pcs)
            rootless = len(chord_tones) == 4 and len(pcs & chord_tones) >= 3
            fit = bool(ps) and (rooted or rootless) and low in tones and len(pcs - tones) <= 1
            verdicts.append((fit, ps))
        total += 1
        if not any(v[0] for v in verdicts):
            bad += 1
            ps = verdicts[0][1]
            names = ' '.join(note_name(p + shift) for p in ps) or 'nothing sounding'
            print(f'  chord {i} beat {t:g} {sym} ({beats:g} beats): source sounds [{names}]')
        t += beats
    print(f'{total - bad}/{total} chords agree with the source harmony at some half beat; {bad} to check by eye')


def load_audits():
    out = {}
    for f in sorted(AUDIT.glob('*.json')):
        out[f.stem] = json.load(open(f))
    return out


def audit_errors(slug, a):
    err = []
    if a.get('slug') != slug:
        err.append('slug does not match file name')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(a.get('checked', ''))):
        err.append('checked must be YYYY-MM-DD')
    mel = a.get('melody') or {}
    if mel.get('status') not in MELODY_STATUS:
        err.append(f'melody.status must be one of {sorted(MELODY_STATUS)}')
    srcs = mel.get('pd_sources') or []
    if mel.get('status') == 'pd_confirmed' and not srcs:
        err.append('pd_confirmed needs at least one pd_sources entry')
    for s in srcs:
        for k in ('url', 'title', 'year', 'kind', 'compared', 'differences'):
            if k not in s:
                err.append(f'pd_sources entry missing {k}')
        if s.get('kind') not in SOURCE_KIND:
            err.append(f'pd_sources kind must be one of {sorted(SOURCE_KIND)}')
        if isinstance(s.get('year'), int) and s['year'] > 1930:
            err.append(f'pd source year {s["year"]} is after 1930')
    ch = a.get('chords') or {}
    if ch.get('status') not in CHORD_STATUS:
        err.append(f'chords.status must be one of {sorted(CHORD_STATUS)}')
    if not ch.get('source'):
        err.append('chords.source is empty')
    ok_mel = mel.get('status') == 'pd_confirmed'
    ok_ch = ch.get('status') in ('pd_harmony', 'own')
    expect = 'clean' if ok_mel and ok_ch else 'fix_chords' if ok_mel else 'fix_melody' if ok_ch else 'fix_both'
    if a.get('verdict') != expect:
        err.append(f'verdict should be {expect}')
    if expect != 'clean' and not a.get('fix'):
        err.append('fix is empty for a non-clean song')
    fam = a.get('familiar') or {}
    if fam.get('status', 'unchecked') not in FAMILIAR:
        err.append(f'familiar.status must be one of {sorted(FAMILIAR)}')
    if fam.get('status') in ('familiar', 'unfamiliar') and not fam.get('compared'):
        err.append('familiar.compared is empty')
    return err


def cmd_check(args):
    files = melody_files()
    audits = load_audits()
    bad = 0
    for slug, a in audits.items():
        if slug not in files:
            print(f'{slug}: audit without melody file')
            bad += 1
        for e in audit_errors(slug, a):
            print(f'{slug}: {e}')
            bad += 1
    missing = [s for s in files if s not in audits]
    print(f'{len(audits)} audits, {len(missing)} melody files without audit, {bad} problems')
    if args.missing:
        for s in missing:
            print(f'  missing: {s}')
    sys.exit(1 if bad else 0)


def album_slugs(path, known):
    text = Path(path).read_text()
    found = []
    for w in re.findall(r'[a-z0-9_]+', text):
        if w in known and w not in found:
            found.append(w)
    return found


def cmd_summary(args):
    files = melody_files()
    audits = load_audits()
    tier = tiers()
    slugs = album_slugs(args.album, files) if args.album else list(files)
    rows = {}
    for s in slugs:
        rows[s] = audits[s]['verdict'] if s in audits else 'not_audited'
    cols = VERDICTS + ['not_audited']
    print('| tier | ' + ' | '.join(cols) + ' |')
    print('|---|' + '---|' * len(cols))
    for t in ('I', 'II', 'III', '-'):
        group = [s for s in slugs if tier.get(s, '-') == t]
        if group:
            print(f'| {t} | ' + ' | '.join(str(sum(rows[s] == c for s in group)) for c in cols) + ' |')
    print(f'| all | ' + ' | '.join(str(sum(v == c for v in rows.values())) for c in cols) + ' |')
    fam = {s: (audits[s].get('familiar') or {}).get('status', 'unchecked') for s in slugs if rows[s] == 'clean'}
    print(f'\nclean songs by ear: ' + ', '.join(f'{k} {sum(v == k for v in fam.values())}' for k in sorted(FAMILIAR)))
    odd = [s for s, v in fam.items() if v != 'familiar']
    if odd and args.album:
        print('not familiar: ' + ', '.join(f'{s} ({fam[s]})' for s in odd))
    todo = [s for s in slugs if rows[s] != 'clean']
    if todo:
        print('\nnot clean:')
        for s in todo:
            fix = audits[s].get('fix', '') if s in audits else ''
            print(f'- {s} ({tier.get(s, "-")}): {rows[s]}' + (f': {fix}' if fix else ''))


def cmd_dispute(args):
    files = melody_files()
    audits = load_audits()
    if args.slug not in audits:
        sys.exit(f'{args.slug} has no audit; audit it first (references/pd-audit.md)')
    a = audits[args.slug]
    if a['verdict'] != 'clean':
        print(f'WARNING: verdict {a["verdict"]}: {a.get("fix", "")}', file=sys.stderr)
    m = files[args.slug][1]
    prints = '; '.join(f'{s["title"]} ({s["year"]}), {s["url"]}' for s in a['melody']['pd_sources'])
    chords = {
        'pd_harmony': f'The harmony follows the public-domain setting in {a["chords"]["source"]}.',
        'own': 'The harmony is our own simple arrangement written for this recording.',
        'modern_source': '',
    }[a['chords']['status']]
    text = (
        f'This segment is our own original instrumental recording of "{m["title"]}". '
        f'The melody is in the public domain: {m["pd_basis"]}. '
        f'Our notes were transcribed from public-domain prints: {prints}. '
        f'{chords} '
        'No lyrics are used. The audio was rendered entirely by us from MIDI with royalty-free virtual instruments; it contains '
        'no recording, sample or modern arrangement owned by the claimant. A melody match on a public-domain tune does not '
        'establish ownership of a copyrighted composition. Please release this claim.'
    )
    print(re.sub(r'\s+', ' ', text).strip())


def main():
    ap = argparse.ArgumentParser(description='Public-domain audit of Christmas melody files')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('compare', help='compare our melody with a downloaded source file')
    c.add_argument('slug')
    c.add_argument('source', help='ABC, MIDI, MusicXML or Humdrum file')
    c.add_argument('--pick', help='part of the tune title in a multi-tune file')
    c.add_argument('--part', type=int, default=0, help='part index holding the melody (0 = top)')
    c.add_argument('--x', help='ABC tune number (X:) when titles repeat')
    c.add_argument('--voice', help='ABC voice id holding the melody (default: first voice)')
    c.add_argument('--limit', type=int, default=40, help='max differences to print')
    c.set_defaults(func=cmd_compare)
    h = sub.add_parser('chords', help='check our chords against the harmony of a machine-readable SATB source')
    h.add_argument('slug')
    h.add_argument('source', help='ABC (all voices), MIDI, MusicXML or Humdrum file')
    h.add_argument('--pick', help='part of the tune title in a multi-tune file')
    h.add_argument('--x', help='ABC tune number (X:) when titles repeat')
    h.add_argument('--voice', help='ABC voice id holding the melody (default: first voice)')
    h.add_argument('--part', type=int, default=0, help='part index holding the melody (0 = top)')
    h.set_defaults(func=cmd_chords)
    k = sub.add_parser('check', help='validate audit files')
    k.add_argument('--missing', action='store_true', help='list melody files without audit')
    k.set_defaults(func=cmd_check)
    s = sub.add_parser('summary', help='verdict counts and songs to fix')
    s.add_argument('--album', help='album.md whose songs to summarise')
    s.set_defaults(func=cmd_summary)
    d = sub.add_parser('dispute', help='print the English dispute rationale for a song')
    d.add_argument('slug')
    d.set_defaults(func=cmd_dispute)
    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
