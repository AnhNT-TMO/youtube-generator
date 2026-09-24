---
name: verification-audio
description: Pick one of the Suno clips generated for an album slot (usually the 2 clips of one generation, 4 for the title track) with four simple measured criteria - not broken (length, cut-off ending, silence gap), sings the lyrics (Whisper on the mix, % of lines heard), tempo closest to the prompt BPM, lyrics start earlier - or send the slot back to be generated again when every clip is broken. Then, after the user accepts, copy the chosen clip from audio/raw_tracks/ into audio/tracks/ and fill the track metadata. Whether a song is good is judged by real listeners after upload (retention), not by this skill. Use after new clips land in raw_tracks, or when the user asks "verify", "kiểm tra bản nháp", "chọn bài nào", "bài nào tốt hơn", "2 bài Suno này", "có cần tạo lại không", "đưa bài vào tracks".
---

# Verification audio

Budget is tight: each slot usually gets one generation (2 clips), the title track two (4 clips). The job is only to
**pick the more usable clip**, not to grade music. Whether a song works is decided by real listeners after upload
(retention in `youtube.md`), never by us listening. So: four cheap criteria, one decision, one question to the user.

```bash
SK=.claude/skills/verification-audio; PY=$SK/.venv/bin/python   # run from the repo root
```

## The four criteria (`scripts/verify.py`, details in `references/criteria.md`)

| # | Criterion | Measured by | Broken when |
|---|---|---|---|
| 1 | **Not broken** | ffmpeg | length outside `rules.duration_range` (selection.yaml) · last second still loud (cut off) · silence ≥ 2 s mid-song |
| 2 | **Sings the lyrics** | Whisper on the mix, fuzzy match per line of `## Lyrics` | fewer than 60 % of the lines heard |
| 3 | **Tempo closest to the prompt** | BPM on the mix (onset autocorrelation, `qc/tempo.felt`, ~1 s) vs the BPM typed in the clip's prompt | (never broken: ranking only) |
| 4 | **Lyrics start earlier** | second of the first lyric line heard | (never broken: last tie-break) |

**Decision:** drop broken clips → keep those within 10 points of the best lyric % → keep those whose tempo is within
3 points of the closest to the prompt → the one whose lyrics start earliest wins. None left → `REGENERATE` with hints.
Tempo only ranks, never rejects: Suno often renders slower than the prompt (Album 001: prompt 70 → 57–67), so a
tempo gate would burn credits on re-rolls of the same prompt. Prompt BPM = manifest `settings.bpm`, else the track
md `target_bpm`, else selection.yaml `tempo.target_bpm`.

Two clips of one generation share Style, Voice and lyrics, so genre, singer and production rarely differ between
them; what does differ is a cut or short take, skipped/garbled lyrics, the tempo (two clips of one Album 001
generation: 63 vs 55 BPM) and the intro length. That is all this measures. Loudness and intro trimming are
album-assembly's job.

## Steps

1. **Check every slot that has new clips in one call** (runs on the GPU server):
   ```bash
   $PY $SK/scripts/verify.py check --album <album-dir> --slot 6 7 8 9 10     # or --slot all (every slot with draft clips)
   ```
   It pushes the album to the server (`scripts/remote.sh`, mirror `~/youtube-qc`), measures all clips of all slots in
   parallel there (`--jobs`, default 4 at a time, one Whisper per process), pulls back `notes/verify-slot-NN.{md,json}`
   and the measurement cache, then records each clip's result in the local manifest (status unchanged). Album 002,
   18 clips / 9 slots: 41 s, ~0 CPU on the Mac. One call, not one subagent per slot: parallel subagents would each
   push the same album and write `manifest.json` at the same time (lost updates), and only the main conversation can
   ask the user. Server unreachable → the command stops; ask the user before `--local` (Whisper on the Mac, ~30–80 s
   per clip, heats the Mac; CLAUDE.md §4).
2. **SELECT** → ask the user to accept with AskUserQuestion, **several slots per call** (one question per slot, up to 4
   per call; or one question "accept all N picks" when every slot is a clean SELECT): the `reasons` in plain Vietnamese (e.g. "hát đúng 100 %
   lời, bản kia 72 %", "bản kia bị cắt ngang ở cuối", "tempo 57, sát prompt 58; bản kia 49", "vào lời ở giây 12, bản kia giây 31"). Options: accept /
   use the other clip / stop.
3. **REGENERATE** (every clip broken) → one question, three options:
   1. *Tạo lại 1 lượt (N credits, from `generation.yaml`)* — the yes is the credit OK; suno-generate runs
      `next --slot N --purpose regenerate --reason "<hints>"`. Hints marked `[cả N clip]` come from the prompt/lyrics
      (fix them first); `[1/N clip]` are random (re-run as is).
   2. *Dùng bản ít lỗi nhất* (`best_available`) — say what is wrong with it, then step 4 with `--why`.
   3. *Dừng slot này.*
   After 3 rounds without a SELECT, recommend option 2 or changing Style/lyrics instead of another identical round.
4. **Accept** only after an explicit yes:
   ```bash
   $PY $SK/scripts/verify.py accept --album <album-dir> --slot N --clip "<album-dir>/audio/raw_tracks/<file>" [--why "..."]
   ```
   Copies the clip to `audio/tracks/` without the clip id (CLAUDE.md naming), marks it `selected` and the slot's
   other drafts `rejected`, fills the track md front matter (`audio`, `suno_url`, `bpm` measured, `duration`, `lufs_integrated`,
   `true_peak`, `outro_type`, `vocal_entry_seconds` = first lyric), and for slot 1 writes `anchor` in selection.yaml.
   A clip verify did not pick is accepted too and recorded as `accept_override` (with `--why`).
   Refuses to overwrite an existing track unless `--replace` (keeps the old file as `.replaced-<date>`).

## Rules

- Never copy into `tracks/` or change a clip's status without the user's explicit yes.
- Never delete drafts from `raw_tracks/`. Never trigger a generation without asking (credits). Never use Suno's own
  Download (monthly quota); downloads go through usesuno.
- Never ask the user to listen and judge. Don't add criteria before real listener data (retention) shows a need.

## Files

| Path | What |
|---|---|
| `scripts/verify.py` | `check` (4 criteria → decision; many slots at once, on the server) and `accept` (local, uses the pulled cache) |
| `scripts/qc/` | measurement library. verify.py uses `basic` (ffmpeg), `lyrics` (Whisper) and `tempo.felt` on the mix. youtube-music-analyzer (`measure.py`) uses `rhythm`, `stems`, `tempo`, `vocal`, `lyrics` through `qc.pipeline` |
| `scripts/remote.sh` | GPU server (host / key / mirror in `remote.env`, template `remote.env.example`): `setup` venv, `push` skill + albums, `exec` a command, `pull` notes + cache (verify.py and youtube-music-analyzer call it) |
| `references/criteria.md` | the four criteria, thresholds, test result, what was dropped and why |
| `.venv/`, `.cache/` | private venv and feature cache (gitignored). Setup: `python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt` |
