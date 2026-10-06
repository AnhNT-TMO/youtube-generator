import argparse
import datetime
import json
from pathlib import Path

import plan_io

REPO = plan_io.repo_root()
DELIVERIES = REPO / plan_io.PIPELINE['deliveries']
USAGE = REPO / plan_io.CONFIG['paths']['accent_library_usage']
POOL = REPO / plan_io.CONFIG['paths']['pool_state']
WORKDIR = REPO / plan_io.PIPELINE['workdirs']


def rel(path):
    return str(Path(path).relative_to(REPO))


def usage_rows(slug, revision, delivery, listening, plan):
    earlier = {row['sample_sha256']: row for row in map(json.loads, USAGE.read_text().splitlines()) if row.get('sample_sha256')}
    rows = []
    for style, variant in listening['variants'].items():
        evidence = delivery / 'evidence' / style
        manifest = plan_io.load(evidence / 'finished-with-accents.wav.json')
        for slot, (accent, planned) in enumerate(zip(manifest['accents'], manifest['plan']['accents']), start=1):
            static = earlier.get(accent['sample_sha256'], {})
            rows.append({
                'date': datetime.date.today().isoformat(), 'song': slug, 'style': style, 'revision': revision, 'accent_slot': slot,
                'asset_id': planned['asset_id'], 'performance_id': static.get('performance_id', planned['asset_id']),
                'source_group': static.get('source_group'), 'performer': static.get('performer'), 'gesture': accent['gesture'],
                'direction': static.get('direction'), 'onset_s': accent['onset_s'], 'tail_end_s': accent['tail_end_s'],
                'parent_recording': static.get('parent_recording'), 'sample_sha256': accent['sample_sha256'],
                'mix_manifest': rel(evidence / 'finished-with-accents.wav.json'),
                'reuse_reason': f'batch {listening["batch"]}: the chime in {plan_io.CONFIG_PATH.name} pipeline.chime is used on every version by standard',
                'mix_approval': f'batch {listening["batch"]} standard (chime {accent["requested_relative_db"]} dB, lowpass {accent["lowpass_hz"]}, A1->A2 boundary); worker technical QA pass; listener approval pending',
                'output_mp3': rel(delivery / variant['mp3']), 'output_mp3_sha256': variant['mp3_sha256'], 'mix_output_sha256': manifest['output_sha256'],
                'finishing_manifest': rel(evidence / 'finishing.json'), 'actual_relative_db': accent['actual_relative_db'],
                'cover_key': planned.get('tonal_compatibility', {}).get('cover_key'), 'audition_only': True, 'listener_accepted': False, 'release_approved': False,
                'base_sha256': manifest['plan']['base']['sha256'],
            })
    return rows


def append_usage(rows):
    known = {(row.get('output_mp3'), row.get('accent_slot')) for row in map(json.loads, USAGE.read_text().splitlines())}
    fresh = [row for row in rows if (row['output_mp3'], row['accent_slot']) not in known]
    with USAGE.open('a') as handle:
        for row in fresh:
            handle.write(json.dumps(row, separators=(',', ':')) + '\n')
    return len(fresh)


def update_pool(slug, revision, delivery, listening, plan):
    pool = plan_io.load(POOL)
    songs = pool.setdefault('new_flow_songs', [])
    song = next((s for s in songs if s['slug'] == slug), None)
    if song is None:
        song = {'slug': slug, 'title': listening['title'], 'batch_id': listening['batch'], 'brief': plan.get('authority'), 'revision': revision,
                'plan': rel(WORKDIR / slug / f'{revision}-pm' / 'arrangement-plan.json'), 'quarter_note_bpm': listening['quarter_note_bpm'], 'meter': listening['meter'],
                'length_seconds': plan['length'].get('seconds'), 'chime': plan['chime'], 'listener_accepted': False, 'release_approved': False, 'styles': {}}
        songs.append(song)
    for style in plan.get('styles') or [s for s in plan_io.STYLE_ORDER if (WORKDIR / slug / s / revision / 'track-plan.json').is_file()]:
        row = song['styles'].setdefault(style, {})
        variant = listening['variants'].get(style)
        if variant:
            finishing = plan_io.load(delivery / 'evidence' / style / 'finishing.json')
            if row.get('revision') and row.get('revision') != revision:
                row['previous'] = {'revision': row['revision'], 'status': row.get('status'), 'delivery': row.get('delivery')}
            row.update({'revision': revision, 'status': 'ready_for_listening' if variant['ready_for_listening'] else variant['gate_status'], 'ready_for_listening': variant['ready_for_listening'],
                        'technical_pass': finishing['technical_pass'], 'backup_passes_same_gates': finishing['backup_passes_same_gates'],
                        'track_plan': rel(WORKDIR / slug / style / revision / 'track-plan.json'), 'delivery': rel(delivery), 'mp3': variant['mp3'], 'mp3_sha256': variant['mp3_sha256'],
                        'selected_raw': finishing['selected_raw'], 'listener_accepted': False, 'release_approved': False})
            if listening.get('source_fix'):
                row['source_fix'] = listening['source_fix']
        elif row.get('revision') in (None, revision):
            row.update({'revision': revision, 'status': 'BLOCKED_no_take_passes_all_gates', 'ready_for_listening': False})
    ready = song['styles'] and all(r.get('ready_for_listening') for r in song['styles'].values())
    song['status'] = 'delivered_ready_for_listening' if ready else 'delivered_partial'
    plan_io.save(POOL, pool)
    return song['status'], {style: (r.get('revision'), r.get('status')) for style, r in song['styles'].items()}


def main():
    parser = argparse.ArgumentParser(description='Record a pulled delivery in pool-state.json and accent-library/usage.jsonl')
    parser.add_argument('slug')
    parser.add_argument('revision', nargs='?', default=plan_io.PIPELINE['default_revision'])
    args = parser.parse_args()
    delivery = DELIVERIES / args.slug / args.revision
    listening = plan_io.load(delivery / 'listening-map.json')
    plan = plan_io.load(WORKDIR / args.slug / f'{args.revision}-pm' / 'arrangement-plan.json')
    added = append_usage(usage_rows(args.slug, args.revision, delivery, listening, plan))
    status, styles = update_pool(args.slug, args.revision, delivery, listening, plan)
    print(f'RECORDED {args.slug} {args.revision}: usage rows +{added}; pool {status} {styles}')


if __name__ == '__main__':
    main()
