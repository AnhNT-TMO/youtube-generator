import json
from pathlib import Path
import sys

import plan_io
from alignment import align, decode, estimate_key, key_chroma

MIN_MARGIN = plan_io.PIPELINE['key_gate']['min_margin']


SHARP_SPELLING = {'Cb': 'B', 'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'E#': 'F', 'B#': 'C'}


def profile_key(label):
    tonic, mode = label.rsplit(' ', 1)
    tonic = SHARP_SPELLING.get(tonic, tonic)
    return f'{tonic} major' if mode == 'mixolydian' else f'{tonic} minor' if mode in ('minor', 'dorian', 'aeolian') else label


def canonical_profile(label):
    tonic, mode = label.rsplit(' ', 1)
    tonic = SHARP_SPELLING.get(tonic, tonic)
    return f'{tonic} {mode}'


def sections_for(samples, spans, statements):
    times, chroma = key_chroma(samples)
    candidates = sorted({key for _, _, _, key in statements})
    profiles = {key: profile_key(key) for key in candidates}
    canonical = {key: canonical_profile(value) for key, value in profiles.items()}
    rows = []
    for (name, _, _, expected), (start, end) in zip(statements, spans):
        selected = (times >= start) & (times < end)
        profile = chroma[:, selected].sum(axis=1)
        ranking = estimate_key(profile)
        expected_profile = profiles[expected]
        expected_score = next((score for score, key in ranking if canonical_profile(key) == canonical_profile(expected_profile)), -1e9)
        among = sorted(((score, key) for score, key in ranking if canonical_profile(key) in canonical.values()), reverse=True)
        margin = among[0][0] - among[1][0] if len(among) > 1 else None
        winning_profile = among[0][1] if among else None
        winning = next((label for label, profile in canonical.items() if profile == canonical_profile(winning_profile)), winning_profile)
        official = winning == expected and (margin is None or margin >= MIN_MARGIN)
        rows.append({'section_id': name, 'expected': expected, 'span_s': [start, end], 'frames': int(selected.sum()),
                     'estimated': winning, 'candidates': candidates, 'margin_vs_next_candidate': margin, 'min_margin': MIN_MARGIN, 'pass': official,
                     'absolute_diagnostic': {'estimated': ranking[0][1], 'score': ranking[0][0], 'expected_score': expected_score, 'runner_up': ranking[1][1], 'runner_up_score': ranking[1][0], 'margin_vs_runner_up': ranking[0][0] - ranking[1][0], 'pass': ranking[0][1] == expected},
                     'pitch_class_profile': (profile / profile.sum()).tolist()})
    return rows


plan_io.require_server()
work = Path(sys.argv[1]).resolve()
plan = plan_io.load(work / 'track-plan.json')
beat_s = plan_io.beat_seconds(plan)
statements = plan_io.statement_spans(plan)
source = work / 'src_A.wav'
source_spans = [(start * beat_s, end * beat_s) for _, start, end, _ in statements]
report = {'method': f'Krumhansl-Kessler key correlation on STFT chroma (16 kHz mono, 8192-sample window, 0.1 s hop, 60-2100 Hz folded to pitch classes) summed over each statement; cover spans mapped from source beats by source/cover chroma DTW (0.1 s frames, max 2 s warp). Official pass (PM 2026-10-05): the best key among the planned statement keys of this song equals the planned key with margin >= {MIN_MARGIN} over the next planned key. The unrestricted 24-key estimate is kept as absolute_diagnostic. Spans exclude the pivot dominant before each lift and the interlude.',
          'min_margin': MIN_MARGIN, 'sections': [{'section_id': n, 'source_beats': [s, e], 'expected': k} for n, s, e, k in statements], 'files': {}}
source_rows = sections_for(decode(source), source_spans, statements)
report['files'][source.name] = {'role': 'source_method_check', 'sections': source_rows, 'pass': all(row['pass'] for row in source_rows)}
report['method_valid_on_source'] = report['files'][source.name]['pass']
report['absolute_method_valid_on_source'] = all(row['absolute_diagnostic']['pass'] for row in source_rows)
for cover in sorted(work.glob('cov_*.flac')):
    map_time, cosine, _ = align(source, cover)
    spans = [(map_time(start), map_time(end)) for start, end in source_spans]
    rows = sections_for(decode(cover), spans, statements)
    report['files'][cover.name] = {'role': 'take', 'dtw_mean_cosine': cosine, 'sections': rows, 'pass': all(row['pass'] for row in rows), 'absolute_pass': all(row['absolute_diagnostic']['pass'] for row in rows)}
plan_io.save(work / 'key_gate.json', report)
print(json.dumps({'method_valid_on_source': report['method_valid_on_source'], **{name: [(r['section_id'], r['estimated'], round(r['margin_vs_next_candidate'] or 0, 3), r['pass']) for r in item['sections']] for name, item in report['files'].items()}}), flush=True)
