import sys
from pathlib import Path

import plan_io


def main():
    root = Path(sys.argv[1]).resolve()
    revision = sys.argv[2]
    checks = plan_io.load(root / f'{revision}-run' / 'source-checks.json')
    assert checks['all_pass'] and checks['source_ready_for_ACE']
    for style in plan_io.styles_for(root, revision):
        work = root / style / revision
        verification = plan_io.load(work / 'source-verification.json')
        assert verification['source_verified'] and verification['source_note_checks']['all_pass']
        files = {'src_A.wav': 'source_wav_sha256', 'src_A.mid': 'source_midi_sha256',
                 'track-plan.json': 'track_plan_sha256', 'actual-event-plan.json': 'actual_event_plan_sha256'}
        for name, field in files.items():
            assert plan_io.digest(work / name) == verification[field], f'{style}: immutable {name} differs'
        for name, digest in verification['dry_stem_sha256'].items():
            assert plan_io.digest(work / name) == digest, f'{style}: immutable {name} differs'
        print('SOURCE_REUSE_VERIFIED', style, revision, flush=True)


if __name__ == '__main__':
    plan_io.require_server()
    main()
