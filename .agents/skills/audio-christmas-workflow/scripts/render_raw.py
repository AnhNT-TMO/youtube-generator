import json
from pathlib import Path
import sys

import mido
import numpy as np
import plan_io
import source_audio as audio


def midi_notes(path):
    result = []
    for track in mido.MidiFile(path).tracks:
        tick = 0
        held = {}
        for message in track:
            tick += message.time
            if message.type == 'note_on' and message.velocity:
                key = (message.channel, message.note)
                assert key not in held, ('overlapping same-pitch notes', path, key, tick)
                held[key] = (tick, message.velocity)
            elif message.type == 'note_off' or (message.type == 'note_on' and not message.velocity):
                start, velocity = held.pop((message.channel, message.note))
                result.append((message.channel, message.note, start, tick - start, velocity))
        assert not held
    return sorted(result)


def expected_midi(notes):
    return sorted((note['channel'], note['pitch'], round(note['beat'] * 480), round((note['beat'] + note['duration']) * 480) - round(note['beat'] * 480), note['velocity']) for note in notes)


def configure():
    parts = plan_io.RENDER['parts']
    audio.LEAD, audio.LH = parts['melody'], parts['left_hand']
    audio.PROGRAMS = {int(channel): program for channel, program in plan_io.RENDER['programs_by_channel'].items()}
    assert audio.SR == plan_io.RENDER['sample_rate']


def render_part(plan, notes, path):
    np.save(path, audio.render(plan_io.events_for(notes, plan_io.beat_seconds(plan)), plan_io.dry_seconds(plan)))
    print('RAW_RENDERED', path.name, len(notes), flush=True)


def base_notes(plan):
    return [note for note in plan['note_plan']['events'] if note['part'] in ('melody', 'left_hand', 'pad')]


def song(root, revision):
    run = root / f'{revision}-run'
    raw = run / 'raw-source'
    raw.mkdir(parents=True)
    plans = {style: plan_io.load(root / style / revision / 'track-plan.json') for style in plan_io.styles_for(root, revision)}
    assert plans, f'no track-plan.json under {root}/*/{revision}'
    reference = next(iter(plans.values()))
    for style, plan in plans.items():
        assert plan['style'] == style and plan['revision'] == revision
        assert plan['meta'] == reference['meta'] and plan['form'] == reference['form'] and plan['key_plan'] == reference['key_plan']
        assert base_notes(plan) == base_notes(reference), f'{style}: piano/pad events differ from {reference["style"]}'
    for part in ('melody', 'left_hand', 'pad'):
        notes = [note for note in reference['note_plan']['events'] if note['part'] == part]
        assert all(note['channel'] == plan_io.RENDER['parts'][part] for note in notes)
        render_part(reference, notes, raw / f'{part}.npy')
    checks = {}
    for style, plan in plans.items():
        work = root / style / revision
        notes = plan['note_plan']['events']
        support_name = plan_io.support_part(plan)
        support = [note for note in notes if note['part'] == support_name] if support_name else []
        assert len(notes) == len(base_notes(plan)) + len(support)
        if support_name:
            assert all(note['channel'] == plan_io.RENDER['parts'][support_name] for note in support)
            render_part(plan, support, raw / f'{support_name}.npy')
        assert not (work / 'src_A.mid').exists()
        audio.write_midi(str(work / 'src_A.mid'), plan_io.events_for(notes, plan_io.beat_seconds(plan)), plan['meta']['tempo'])
        paired = midi_notes(work / 'src_A.mid')
        assert paired == expected_midi(notes)
        plan_io.save(work / 'actual-event-plan.json', notes)
        counts = {part: sum(n[0] == plan_io.RENDER['parts'][part] for n in paired) for part in ['melody', 'left_hand', 'pad'] + ([support_name] if support_name else [])}
        plan_io.save(work / 'midi-projection.json', {'paired_note_count': len(paired), 'counts': counts, 'note_plan_projection_exact': True, 'tpq': 480, 'bpm': plan['meta']['tempo'], 'events': paired})
        checks[style] = {'paired_notes': len(paired), 'counts': counts}
        print('MIDI_READY', style, json.dumps(counts), flush=True)
    plan_io.save(run / 'raw-render-checks.json', {'pass': True, 'song': reference['meta']['slug'], 'revision': revision, 'renderer_source_sha256': plan_io.digest(Path(audio.__file__)), 'programs_by_channel': plan_io.RENDER['programs_by_channel'], 'beat_seconds': plan_io.beat_seconds(reference), 'length_beats': plan_io.length_beats(reference), 'dry_duration_s': plan_io.dry_seconds(reference), 'styles': checks})


def calibrate(work_root, out):
    raw = out / 'raw-source'
    raw.mkdir(parents=True)
    plans = {style: plan_io.load(work_root / path / 'track-plan.json') for style, path in plan_io.RENDER['calibration']['plans'].items()}
    first = next(iter(plans.values()))
    for part in ('melody', 'left_hand', 'pad'):
        render_part(first, [note for note in first['note_plan']['events'] if note['part'] == part], raw / f'{part}.npy')
    for style, plan in plans.items():
        assert base_notes(plan) == base_notes(first)
        assert midi_notes(work_root / plan_io.RENDER['calibration']['plans'][style] / 'src_A.mid') == expected_midi(plan['note_plan']['events'])
        render_part(plan, [note for note in plan['note_plan']['events'] if note['part'] == style], raw / f'{style}.npy')
    plan_io.save(out / 'raw-render-checks.json', {'pass': True, 'mode': 'calibration', 'stored_midi_equals_generic_projection': True, 'beat_seconds': plan_io.beat_seconds(first), 'length_beats': plan_io.length_beats(first), 'dry_duration_s': plan_io.dry_seconds(first)})


plan_io.require_server()
configure()
if sys.argv[1] == 'song':
    song(Path(sys.argv[2]).resolve(), sys.argv[3])
elif sys.argv[1] == 'calibrate':
    calibrate(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
else:
    raise SystemExit('usage: render_raw.py song <song_root> <revision> | calibrate <work_root> <out_dir>')
