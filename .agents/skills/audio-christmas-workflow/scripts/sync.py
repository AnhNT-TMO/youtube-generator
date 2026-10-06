import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import plan_io

HERE = Path(__file__).resolve().parent
REPO = plan_io.repo_root()
SERVER = plan_io.PIPELINE['server']
WORKDIR = Path(os.environ['CAROL_PLAN_DIR']).resolve() if os.environ.get('CAROL_PLAN_DIR') else REPO / plan_io.PIPELINE['workdirs']
WORK_ROOT = os.environ.get('CAROL_WORK_ROOT') or SERVER['work_root']
PUBLISHED_ROOT = os.environ.get('CAROL_PUBLISHED_ROOT') or SERVER['published_root']
DELIVERIES = REPO / plan_io.PIPELINE['deliveries']
GUARD_ENV = REPO / '.claude' / 'skills' / 'video-generator' / 'remote.env'


def remote():
    values = {}
    if GUARD_ENV.is_file():
        for line in GUARD_ENV.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, _, value = line.partition('=')
                values[key.strip().removeprefix('export ').strip()] = value.strip().strip('"\'')
    host = values.get('GUARD_REMOTE') or values.get('VG_REMOTE')
    if not host:
        raise SystemExit(f'no VG_REMOTE in {GUARD_ENV} (the same host guard.sh uses)')
    key = Path(os.path.expandvars(values.get('VG_KEY', '~/.ssh/id_rsa'))).expanduser()
    return host, key


HOST, KEY = remote()
SSH = f'ssh -i {shlex.quote(str(KEY))} -o BatchMode=yes -o ConnectTimeout=10'


def rsync(*args, check=True, capture=False):
    cmd = ['rsync', '-e', SSH, *args]
    result = subprocess.run(cmd, text=True, capture_output=capture)
    if check and result.returncode != 0:
        raise SystemExit(f'rsync failed ({result.returncode}): {" ".join(cmd)}\n{result.stderr if capture else ""}')
    return result


def remote_exists(path):
    return rsync('--list-only', f'{HOST}:{path}', check=False, capture=True).returncode == 0


def push_tools():
    tools = SERVER['tools']
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / 'tools'
        stage.mkdir()
        for path in sorted(HERE.glob('*.py')) + [HERE / 'run.sh']:
            (stage / path.name).write_bytes(path.read_bytes())
        (stage / 'WORKFLOW.json').write_bytes(plan_io.CONFIG_PATH.read_bytes())
        (stage / 'run.sh').chmod(0o755)
        rsync('-a', '--delete', '--checksum', f'{stage}/', f'{HOST}:{tools}/')
    print(f'TOOLS_SYNCED {tools} ({len(list(HERE.glob("*.py"))) + 2} files)')


def plan_files(slug, revision):
    root = WORKDIR / slug
    pm = root / f'{revision}-pm' / 'arrangement-plan.json'
    if not pm.is_file():
        raise SystemExit(f'no {pm}: run make_plan.py first')
    plan = plan_io.load(pm)
    files = [(pm, f'{revision}-pm/arrangement-plan.json')]
    for style in plan['styles']:
        track = root / style / revision / 'track-plan.json'
        if not track.is_file():
            raise SystemExit(f'no {track}')
        files.append((track, f'{style}/{revision}/track-plan.json'))
    melody = REPO / plan['notation_reference']['path']
    if plan_io.digest(melody) != plan['notation_reference']['sha256']:
        raise SystemExit(f'{melody} changed since the plan was written: rerun make_plan.py')
    files.append((melody, 'melody-source.json'))
    return files


def push_plans(slug, revision):
    base = f'{WORK_ROOT}/{slug}'
    files = plan_files(slug, revision)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / 'root'
        for src, rel in files:
            target = stage / slug / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read_bytes())
        started = remote_exists(f'{base}/{revision}-run/')
        dry = rsync('-a', '-n', '--checksum', '--out-format=%n', f'{stage}/', f'{HOST}:{WORK_ROOT}/', capture=True)
        changed = [line for line in dry.stdout.splitlines() if line and not line.endswith('/')]
        if f'{slug}/melody-source.json' in changed and remote_exists(f'{base}/melody-source.json'):
            raise SystemExit(f'{slug}: server melody-source.json differs from {files[-1][0]}; earlier revisions used the server copy, PM decides')
        if started and changed:
            raise SystemExit(f'{slug} {revision}: already started on the server ({revision}-run exists) and these plan files differ: {changed}; make a new revision')
        rsync('-a', '--checksum', f'{stage}/', f'{HOST}:{WORK_ROOT}/')
    print(f'PLANS_SYNCED {WORK_ROOT}/{slug} {revision}: {[rel for _, rel in files]}' + (' (unchanged, run already started)' if started else ''))


def pull(slug, revision):
    src = f'{PUBLISHED_ROOT}/{slug}/{revision}/'
    if not remote_exists(src + 'checksums.json'):
        raise SystemExit(f'{slug} {revision}: not published on the server (no checksums.json)')
    dest = DELIVERIES / slug / revision
    dest.mkdir(parents=True, exist_ok=True)
    rsync('-a', '--checksum', f'{HOST}:{src}', f'{dest}/')
    sums = plan_io.load(dest / 'checksums.json')
    bad = [name for name, value in sums.items() if not (dest / name).is_file() or plan_io.digest(dest / name) != value]
    extra = sorted(str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file() and p.name != 'checksums.json' and str(p.relative_to(dest)) not in sums)
    if bad or extra:
        raise SystemExit(f'PULL_CHECKSUM_FAIL {dest.relative_to(REPO)} bad {bad} extra {extra}')
    print(f'PULLED {dest.relative_to(REPO)} ({len(sums)} files, checksums OK)')


def main():
    parser = argparse.ArgumentParser(description='Mac side of run.sh: push tools/plans to the server, pull deliveries back')
    parser.add_argument('action', choices=['sync', 'pull'])
    parser.add_argument('slug', nargs='?')
    parser.add_argument('revision', nargs='?', default=plan_io.PIPELINE['default_revision'])
    args = parser.parse_args()
    if args.action == 'sync':
        push_tools()
        if args.slug:
            push_plans(args.slug, args.revision)
    else:
        if not args.slug:
            parser.error('pull needs a slug')
        pull(args.slug, args.revision)


if __name__ == '__main__':
    sys.exit(main())
