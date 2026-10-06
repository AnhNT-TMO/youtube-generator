---
name: audio-christmas-workflow
description: Runbook for producing gentle instrumental Christmas carols (piano + pad, plus celesta / vibraphone versions) from a public-domain melody file through a MIDI source, ACE-Step covers on the GPU server and one recorded chime. Use to plan, render, deliver or revise songs of a Christmas batch. Album assembly is a separate skill.
---

# Christmas carol runbook

Everything runs from the repo root on the Mac; `scripts/` below means `.claude/skills/audio-christmas-workflow/scripts/` and `run.sh` means `bash scripts/run.sh <phase> <slug> [revision]`. Mac phases run locally; every other phase is forwarded to the GPU server through `guard.sh run`. Never run audio work on the Mac, never edit `guard.json`, `CLAUDE.md` or `AGENTS.md`.

## Read first

- `research/christmas-carols/STANDARD.md`: what a finished song is (CEO standard). `WORKFLOW.json`: every number, path, style, gate, chime and the pattern library. Change neither on your own.
- The batch brief named by the PM and `research/christmas-carols/batches/<batch>/songs.json` (one entry per song) and `PLAN_REVIEW.md` (decision log for the batch).
- `research/christmas-carols/pool-state.json`: what is delivered, ready or blocked. Resume from it; do not redo delivered revisions.

## Ambient render (CEO 2026-10-05)

ACE-Step is retired. Carols are rendered from `track-plan.json` with real-recorded virtual instruments on the GPU server (`~/music-tools`: DawDreamer, Salamander piano, VSCO-2-CE, `sfz/real` celeste/chorus/tubular bells, Dragonfly Hall). Vibes: `snowglobe` (piano, harp, cello + viola, celesta, sleigh bells) and `church` (piano, organ, choir, tubular bell).

- `scripts/ambient_batch.sh <root> [slug...]`: for each `<root>/<slug>/track-plan.json`, renders every vibe in `VIBES` to `<slug>-<vibe>.mp3/.mid/.json`, finished at −18 LUFS with true peak ≤ −1.6 dBFS. Run it through `guard.sh run`. Output goes to `audio/christmas/<slug>/`.
- `scripts/ambient_render.py`: arranges and mixes. `scripts/ambient_harmony.py`: chord colours with a melody-fit check, and a slight ritardando at every 4-bar phrase end.
  - Plan sections `A1_2`/`A2_2`/`A3_2` merge into their pass, and `A2F` plays as pass 3.
  - The three passes are forced to 0 / +0.5 / +1.0 dB: no climax, no lead swap.
- `scripts/ambient_album.py <order.json> <root> <out> [--target S] [--wav] [--intro-fade 12]`: joins `<root>/<slug>/<slug>-<vibe>.mp3` in the order given, with an equal-power crossfade and no loudness change. `--target` solves the crossfade so the master is exactly the video montage length (it refuses outside 1–4 s: add or remove tracks instead). The album always opens with a slow fade-in (`afade curve=hsin`, 12 s, the same rule as audio-album-assembly, CEO 2026-10-05) under the video's opening intro. Writes `<out>.mp3`, `<out>.wav` (48 kHz 24-bit, with `--wav`) and `<out>.json` (start_s per track). Run it on the server and keep the master there for the video join.
- `scripts/ambient_index_vsco.py` and `scripts/ambient_index_real.py` rebuild the sample indexes. Sources and licences are in [references/ambient-samples.md](references/ambient-samples.md).

## Command order

| # | Command | Where | Done when |
|---|---|---|---|
| 1 | `python3 scripts/spec.py <batch> <slug>... --write` | Mac | entry in `songs.json`, exit 0 (exit 2 = BLOCKED, read the reason) |
| 2 | `python3 scripts/make_plan.py <batch> <slug> [--revision rNNN]` | Mac | `work/<slug>/<rev>-pm/arrangement-plan.json` + `work/<slug>/<style>/<rev>/track-plan.json` |
| 3 | `python3 scripts/check_plan.py <batch> <slug> [--revision rNNN]` | Mac | 0 FAIL (exit 1 on any FAIL); WARN lines are read and logged |
| 4 | `run.sh sync <slug> [rev]` | Mac | `TOOLS_SYNCED` + `PLANS_SYNCED` |
| 5 | `run.sh source <slug> [rev]` | server | `SOURCE_COMPLETE`; buzz ≤ limit; key check `method_valid` on source |
| 6 | `run.sh covers <slug> [rev]` | server | `EVALUATION_COMPLETE` per style; `BLOCKED_STYLES` lists styles with no passing take |
| 7 | `run.sh finish <slug> [rev]` | server | chime + loudness finish written to the published dir |
| 8 | `run.sh deliver <slug> [rev]` | server | `DELIVERED`, `all_pass` in qa |
| 9 | `run.sh pull <slug> [rev]` | Mac | `PULLED ... checksums OK` into `ace-steps/christmas-carols/<slug>/<rev>/` |
| 10 | `run.sh record <slug> [rev]` | Mac | pool-state.json and `accent-library/usage.jsonl` updated |

Other phases: `status` (pick per style), `gate` (re-run picks + key gate on existing covers), `refsplit` (rebuild the copy-gate reference set), `calibrate` (renderer calibration, once per server), `remix <slug> <parent> <new> <reason>` (re-finish a delivered revision after a mix-only change, no new AI generation). The default revision is `r001`. A revision is final once its sources exist or it is published: any change means the next revision (`r002`, ...) declared under `revisions` in the song entry.

## What each step decides

- **spec.py** writes the default entry: tempo = median of category-1 relaxed piano references (beat unit checked), first key so the final statement top note ≤ the configured ceiling, three statements with a whole-step lift, whole-bar interlude/outro, length 2–4 min with the chime near 1/3, a pattern set rotated by meter so adjacent songs differ, captions from the template. Extra rules the PM adds for the remaining pool (tempo density cap, statement groups, half-plus-full form, minor/modal lifts) live in `research/christmas-carols/batches/SPEC_RULES.md`; build them into `spec.py` before running the queue `batches/QUEUE.json`. It refuses (BLOCKED) only what those rules cannot place.
- **make_plan.py** turns the entry into notes: piano melody + spacious left hand, pad, support patterns from the library on the beat grid, pivots, dropped/shifted support notes with reasons.
- **check_plan.py** checks the plan against the standard (range, clashes, chime window, density, lengths).
- **source** renders MIDI → stems → `src_A.wav` per style and measures buzz and the planned keys on the source.
- **covers** runs the ACE-Step take matrix (seed × noise from WORKFLOW.json), evaluations (copy gate, HF/opening, vocal proxy), picks primary/backup and the key gate. Key gate rule: the best of the planned keys for each statement with margin ≥ 0.3; the 24-key result is diagnostic only.
- **finish** adds the one configured chime at the real A1 → A2 boundary of the selected cover and applies fixed gain under the true-peak ceiling. Quieter than −18 LUFS because of the ceiling is accepted; no limiter.
- **deliver** writes `NGHE_THU.md`, `listening-map.json`, `proof/`, `evidence/`, runs `verify.py` and seals `checksums.json`.

## Logs to read

- Server run logs: `~/ace-step/christmas-v5/<slug>/<rev>-run/{raw-render,source,source-buzz,finish,deliver,qa}.log`.
- Per style: `~/ace-step/christmas-v5/<slug>/<style>/<rev>/{source-key-check,cover,eval-a,eval-b,select,key-gate}.log` and `picks.json`.
- After pull everything needed for review is in the delivery: `evidence/run/*.log`, `evidence/<style>/*.log`, `worker-qa.json`.

## Delivery layout

`ace-steps/christmas-carols/<slug>/<rev>/` on the Mac, `~/youtube-qc/ace-steps/christmas-carols/<slug>/<rev>/` on the server, identical by `checksums.json`. The batch name goes in `NGHE_THU.md` / `listening-map.json`, never in the path.

- `<Title>_<Style>_<rev>.mp3` per ready style, `NGHE_THU.md`, `listening-map.json`, `worker-qa.json`, `checksums.json`.
- `raw/<style>-primary-*.flac` and `raw/<style>-backup-*.flac` with request sidecars.
- `proof/`: what a Content ID dispute needs: `PD-BASIS.md`, `DISPUTE.txt`, `melody-source.json`, `arrangement-plan.json`, `chime/` (manifest + license page), and per style `src_A.mid`, `track-plan.json`, `ace-request-*.json`, `cover-revision.json`, `mix-plan.json`, `mix-manifest.json`, `finishing.json`, `hashes.json`.
- `evidence/`: run logs, source checks, evaluations, picks, key gate, alignment and chime manifests per style. `tools/`: the exact scripts used.

## Worker decides alone (log the reason in the batch `PLAN_REVIEW.md`)

- Rounding interlude or outro to whole bars.
- Swapping a pattern for another from the library (density, clash or chime-beat reasons).
- Adding or removing a statement, or using the chorus / second half, to reach the length or the chime window.
- Rerunning a job the guard killed: `guard.sh kills`, then the same `run.sh` command again.
- One source fix of 1–2 bars after an HF / opening fail (for example `revisions.rNNN.source_fix.drop_support_bars`), then the next revision with the same seeds and noise.
- Fixing a small bug in a script (keep one copy, in `scripts/`, then `run.sh sync`).

## Stop and write BLOCKED for the PM

Write `BLOCKED <slug> <rev>: <reason, numbers, logs>` in `PLAN_REVIEW.md` and in the report, then continue with other songs.

- Tempo would move more than ±10 % from the reference median.
- Any standard would change: instruments, arrangement rules, chime, finish level, gates or their thresholds.
- A version still fails after one source fix.
- The melody file looks wrong (notes, chords, meter, pickup, or it does not match the public-domain tune).
- The server is unreachable (do not fall back to the Mac).

## Common errors

| Message | Fix |
|---|---|
| `copy-gate reference set missing` | `run.sh refsplit`, then `covers` again |
| exit 65 `... exists` / `already started` | revision is final: declare the next revision and plan it |
| `no ... run sync from the Mac first` / `no sources` / `no calibration` | run the missing earlier phase |
| `another carol worker is active` (73) | another job holds the song: wait, do not start a second one |
| `SOURCE_BUZZ_FAIL` (4) | source too bright: change the source (support register / pattern), next revision |
| job killed, no output | `guard.sh kills`, then the same command |
| `PULL_CHECKSUM_FAIL` | pull again; if it persists the server package changed: report |
| `server melody-source.json differs` | the melody file changed after earlier revisions: PM decides |

## After delivery

- `run.sh record` adds one usage row per chime to `accent-library/usage.jsonl` (skips rows already there) and sets each style in `pool-state.json` to `ready_for_listening` or `BLOCKED_no_take_passes_all_gates`.
- `source_verified`, `technical_pass`, `ready_for_listening`, `listener_accepted` and `release_approved` stay separate. Only the CEO's listening sets `listener_accepted`; record feedback as `use_now`, `small_revision` or `rearrange` ([listener feedback](references/listener-feedback.md)). Accent-only feedback uses `remix`; source feedback needs a new revision.

## Hard rules

- Melody, rhythm, meter and harmony of the public-domain tune stay intact; piano plays every melody note.
- Instruments are exactly those of the style (piano, pad, optional celesta or vibraphone). No voice, strings, choir, percussion, glockenspiel.
- Two takes per style (seed and noise from WORKFLOW.json); no seed search. Both fail → fix the source.
- Chime only in finishing, never in source or caption. Raw covers are never edited, cut or limited.
- Claude/Codex cannot judge sound by ear: report measurements, never claim it sounds good.
- One worker per song at a time; all server commands through `.claude/skills/pm-production/scripts/server_guard/guard.sh run`.

References: [ACE-Step operations](references/ace-step.md), [recorded chime](references/real-accents.md), [listener feedback](references/listener-feedback.md).
