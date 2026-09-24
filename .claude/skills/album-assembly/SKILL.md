---
name: album-assembly
description: Join an album's selected Suno tracks (already in their final order) into one continuous ~1-hour audio - measure every track (where the vocal starts/ends, intro/outro length, beat grid, tempo, key, loudness), choose how each pair should be joined (crossfade, quick entry, natural ending, cold open, breathing gap, long build-up intro) so transitions vary and every song entry lands clearly, trim long Suno intros/outros on the beat, balance loudness, then write assembly.yaml + assembly.md (plan, cut points, timestamps, checks) and render audio/master/<album>.wav/.mp3 with a preview clip per join. Use when the user wants the album mixed/joined/assembled ("ghép album", "ghép audio", "nối bài", "chuyển bài mượt", "cắt intro", "crossfade", "làm bản liên tục", "timestamps/chapters từ bản ghép"), wants one transition changed, or wants assembly.md regenerated. Also prepares the audio of a single song released on its own (channel/<ch>/singles/NNN-slug: trim the Suno intro so the vocal lands at ~8 s, keep the natural ending, −14 LUFS) - "đăng riêng bài", "audio cho single", "cắt intro bài lẻ". Does NOT reorder tracks.
---

# Album assembly

The ASSEMBLE step of CLAUDE.md (step 6) for audio. Input: an album folder
`channel/<channel>/albums/<NNN-slug>/` whose `tracks/NN-*.md` front matter has `track_no`, `audio`
(the selected WAV), and ideally `energy` and `arc_role`. Output, in the album folder:

| File | What |
|---|---|
| `assembly.yaml` | the plan as data: per track `in`/`out`/fades/`gain_db` (seconds in the ORIGINAL file), per join `type`/`overlap`/`why`/`locked` |
| `assembly.md` | generated human view: opening, join table, cut table, YouTube chapters, post-render checks, warnings, preview list. Only its `## Ghi chú` section survives regeneration |
| `audio/master/<album>.wav` (+`.mp3`) | the continuous album, 48 kHz 24-bit, −14 LUFS, limiter −1.5 dBFS (gitignored) |
| `audio/master/previews/*.mp3` | 30 s opening + one clip per join, from ~6 s before the last line of song A to ~12 s after the first line of song B |

**Order is fixed** (`track_no`, decided at blueprint time from the reference research). Never reorder,
drop or swap tracks here; if the order looks wrong, say so and stop.

Claude cannot hear. Every claim about how a join sounds comes from measurements (vocal stem,
loudness curve, beat grid); say so, and list the previews worth a listen, but do not wait for anyone to listen
(CLAUDE.md): the album is done when `render`'s checks pass.

## Commands

Everything lives in this skill dir (`SK=.claude/skills/album-assembly`): `scripts/assemble.py` (CLI),
`scripts/assembly/` (planner, render, report), `scripts/measure/` (a trimmed copy of the verification-audio measurement
modules: loudness, Demucs stems, vocal activity, key, tempo, beat_this grid), its own venv `$SK/.venv` and feature cache
`$SK/.cache/features/` (keyed by audio content hash, same format as verification-audio's).

**Runs on the GPU server.** `plan`, `set`, `render` and `single` push the skill + album/single folders to the server
(`scripts/remote.sh`, mirror `~/youtube-qc`), run the same command there and pull back `assembly.yaml`, `assembly.md`
(+ `audio/master/` for `render` / `single`). The feature cache lives on the server. A 10-track album: `plan` 2 min
the first time (Demucs + beat_this), `render` ~3.5 min including the ~850 MB master download. `unlock` / `report` run
here (no measuring). `--local` runs everything on this Mac (Demucs ~1 min per track, heats the Mac): only when the server
is unreachable **and the user said yes** (CLAUDE.md).

Setup once: local venv (only light imports are used here) `python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt`;
server: `cp $SK/remote.env.example $SK/remote.env` and fill `QC_REMOTE` (host, key, mirror dir), then venv
`bash $SK/scripts/remote.sh setup` (torch cu128).

```bash
SK=.claude/skills/album-assembly; PY=$SK/.venv/bin/python; A=$SK/scripts/assemble.py   # repo root; one word per var (zsh)
$PY $A plan   <album>                     # measure + choose join types → assembly.yaml + assembly.md (~20 s cached)
$PY $A render <album>                     # mix → master WAV/MP3 + previews, re-measure, fill timestamps & checks (~1 min)
$PY $A set    <album> <join> --type T [--a-tail S --a-fade S --b-keep S --overlap S --b-fade S]   # change one join, locks it
$PY $A unlock <album> <join|all>          # let `plan` choose again
$PY $A report <album>                     # regenerate assembly.md from the yaml (after hand edits)
$PY $A single <single>                    # one song released on its own: measure + trim intro + −14 LUFS + render (~5 s cached)
```

`<album>` is a folder path or just its name (`<NNN-slug>`). `plan --vocal-at S` sets the second
of the video where the first vocal of track 01 lands, `--target-lufs` the master loudness. Without them, `plan` reads the
album's `plan.yaml` (skill album-plan): `target.vocal.vocal_at_s`, else min(8, `first_voice_max_s.track01`), and
`target.loudness.master_lufs`; no plan → 8 s and −14 LUFS (YouTube's reference). It prints which source it used.
verification-audio's Track 01 gate uses the same `vocal_at`, so its "lyric at second N of the video" matches this cut.
A hand edit of cut numbers in `assembly.yaml` goes straight to `render`; a re-`plan` recomputes every join that is not
`locked: true`.

## Join types

`join N` = between track N and N+1. The recipes live in `$SK/scripts/assembly/planner.py` `RECIPES`:

| type | What the listener hears | B's intro kept |
|---|---|---|
| `crossfade` | A's instrumental outro melts into B's intro (equal-power, ~6 s overlap, B's first downbeat lands on one of A's) | ~10 s |
| `quick` | A fades fast right after its last line, B sings almost at once | ~3–4 s |
| `natural` | A plays its whole Suno ending, B starts under the last ring (only if A's outro ≤ 22 s) | ~6 s |
| `cold_open` | A fades out, ~0.8 s of silence, B opens straight on the vocal | < 2 s |
| `breath` | A fades long to silence, a 1 s rest, B's long intro | ~14 s |
| `build` | A steps back fast, B's long intro builds before the vocal (for the peak track) | ~18 s |

How `plan` picks: each join gets a fit score from energy change, B's `arc_role` (peak → `build`, closer → `breath`),
A's real outro length and ending type, B's intro length, and tempo difference (> 5 %: prefer a break over stacking two
grooves). Then one DP over the whole album maximises the score under variety rules: never the same type twice in a row,
each type capped (~⅓ of joins; `cold_open`/`breath`/`build` at most 2), and a bonus for using every intro-length
bucket (ngay / ngắn / vừa / dài). The first two joins avoid long intros because listeners are still deciding.

Cut points: A's fade never starts before its last sung line (vocal stem from Demucs); B never loses its first line;
A is silent at least 1.5 s before B sings; B's start is snapped to a downbeat (to a beat for `cold_open`).
Track 01 starts on a downbeat so its vocal lands at `--vocal-at` seconds, moved later if that spot is > 8 dB under the
song body (CLAUDE.md). The last track keeps its natural ending, trailing silence trimmed, plus 2 s.

## Workflow

1. **Check inputs.** All `tracks/*.md` have `track_no` 1..N and an existing `audio` file. `energy`/`arc_role` missing
   → joins are chosen on audio alone; say so.
2. **`plan`**, then read `assembly.md`. Review it as a producer, against CLAUDE.md:
   - Opening: vocal at ≤ 10–12 s of the video, first seconds not much quieter than the body.
   - Variety: the sequence of types and intro lengths should not be predictable; no near vocal-to-vocal run.
   - Each entry makes an impression: B does not enter much quieter than the body (`b_entry_level_db`), and a long
     instrumental gap (> 30 s without vocals) has a reason (e.g. before the closer).
   - Warnings: tempo jumps (> 8 %) are joined with a break, not a long overlap; key distance.
   If a choice is poor, fix it with `set` (e.g. `set <album> 9 --type breath --b-keep 12`) and explain why.
3. **`render`**. Read the new `assembly.md` sections *Kiểm tra sau khi ghép* and *Cảnh báo*:
   - *Chênh* (loudness of B's first sung 20 s minus A's last sung 20 s): a few LU down is normal (final chorus → first
     verse); > +1.5 LU up is jarring, < −5 LU loses the entry.
   - *Lặng* longer than planned, or *Hụt* at a join with no planned silence → the fade is too deep; shorten it with `set`.
   - Duration: 10 Suno songs of ~5:30 give ~49–51 min after trimming. Say so if the user expects a full hour;
     the fix is more or longer tracks, not stretching transitions.
4. **Report** to the user: the join table in a few lines, warnings, where the WAV is, and which previews to listen to
   first (the warned joins, the opening). Ask them to write listening notes in `assembly.md` → `## Ghi chú`; after they
   listen, apply their notes with `set`, re-render.
5. **Hand off.** The video is made by the `video-generator` skill from `audio/master/<album>.wav` (whenever the
   user gets to it; the loop may already exist). *Timestamps* here are a preview: youtube-publish measures the final
   chapters on the video file that is uploaded. If an older master is still in `audio/master/`, name the file to use instead of guessing.

## Singles (one song released on its own)

`<single>` = `channel/<ch>/singles/NNN-slug/` (template `templates/single.md`); its `single.md` field `track` points to the
song's `tracks/NN-*.md` in the origin album, whose `audio` is the selected WAV. `single` measures that WAV (cache shared with
the album), cuts in on a bar so the vocal lands at `--vocal-at` (default 8 s, moved earlier if that spot is > 8 dB under the
body, same rule as an album's track 01), keeps the natural ending, sets gain to −14 LUFS and renders
`<single>/audio/master/<NNN-slug>.wav` + `previews/00-opening.mp3`, with `assembly.yaml` (`kind: single`, no joins) and
`assembly.md` in the single folder. Hand edits: change `in`/`fade_in`/`gain_db` in the yaml, set `opening.locked: true` /
`gain_locked: true` so the next `single` keeps them, then `render`. Report the vocal entry + opening loudness and ask the user
to listen to the opening preview (CLAUDE.md matters even more when the whole video is one song). The video is then made by
video-generator step 2 from that WAV.

## Notes

- `assembly.yaml` numbers are seconds in the original Suno file, so they stay valid if the WAV is re-exported with the
  same content. Replacing a track's audio needs a new `plan` for its two joins (`unlock` them first).
- Vocal detection is Demucs + an energy threshold: humming or ad-libs in an outro count as vocals (fades start after
  them), and a very quiet first line can be missed. If the preview shows a clipped line, move the cut with `set`.
- beat_this sometimes returns a downbeat every 2 bars in slow compound meters (6/8); snapping is then coarser but still on a bar line.
- The old hand-written plan, if any, was saved to `notes/assembly-v0.md` on the first run.
