import json, os, re, sys

D = sys.argv[1]
NOTE = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}


def midi(name, octave):
    return 12 * (int(octave) + 1) + NOTE[name.lower()]


def sfz_regions(path):
    rows = {}
    for block in open(path).read().split('<region>')[1:]:
        kv = dict(re.findall(r'^(\w+)=(.+?)\s*$', block, re.M))
        if 'sample' in kv:
            rows[os.path.basename(kv['sample'])] = (int(kv.get('tune', 0)), float(kv.get('volume', 0)))
    return rows


index = {'celeste': [], 'chorus': [], 'tubular': [], 'handchimes': []}
cel = sfz_regions(f'{D}/sso/Celeste.sfz')
for f in sorted(os.listdir(f'{D}/sso/Celeste')):
    m = re.match(r'celeste-([a-g]#?)(\d)-(soft|hard)\.flac', f)
    tune = cel.get(f, cel.get(f.replace('soft', 'hard'), (0, 0)))[0]
    index['celeste'].append({'file': f'sso/Celeste/{f}', 'midi': midi(m[1], m[2]), 'tune': tune, 'layer': 0 if m[3] == 'soft' else 1})
cho = sfz_regions(f'{D}/sso/mixed-chorus.sfz')
for f in sorted(os.listdir(f'{D}/sso/Chorus')):
    m = re.match(r'chorus-(female|male)-([a-g]#?)(\d)\.wav', f)
    tune, vol = cho.get(f, (0, 0))
    index['chorus'].append({'file': f'sso/Chorus/{f}', 'midi': midi(m[2], m[3]), 'tune': tune, 'layer': 0, 'volume': vol})
for f in sorted(os.listdir(f'{D}/vcsl/tubular')):
    m = re.match(r'chimes_([A-G]#?)(\d)_', f)
    index['tubular'].append({'file': f'vcsl/tubular/{f}', 'midi': midi(m[1], m[2]) + 12, 'tune': 0, 'layer': 0})
for f in sorted(os.listdir(f'{D}/vcsl/handchimes')):
    m = re.match(r'sus_([A-G]#?)(\d)_', f)
    index['handchimes'].append({'file': f'vcsl/handchimes/{f}', 'midi': midi(m[1], m[2]) + 12, 'tune': 0, 'layer': 0})
json.dump(index, open(f'{D}/index.json', 'w'), indent=1)
print({k: (len(v), min(r['midi'] for r in v), max(r['midi'] for r in v)) for k, v in index.items()})
