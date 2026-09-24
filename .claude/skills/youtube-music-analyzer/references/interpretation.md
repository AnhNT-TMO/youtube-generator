# Reading the six criteria

Sources: `audio/analysis.json` (split, song lengths, 0-15 s level, captions), `audio/qc.json` (measure.py, with
verification-audio's QC code - the same units that score our own Suno drafts), `reference.yaml` (`criteria` = both merged).

## 1-2. Video length, songs, song length

- Chapters / description timestamps are snapped to the deepest real dip within ±40 s; chapters under 90 s
  (Intro/Outro stings) are merged into the next song.
- Automatic split: level dips + timbre change + caption words changing, minus a penalty when the chords
  (chroma-repeat) or words (words-repeat) after the dip already occurred in the 4 min before it - a chorus coming
  back = an internal break, not a join. `segmentation.weak_joins` = joins close to the threshold: check `overview.png`.
- Use the median song length; a wrong join moves two songs by the same amount and barely moves the median.

## 3. Tempo + meter

- **Felt BPM** = dotted quarter in 6/8·12/8, quarter in 4/4 - the unit of `target.tempo`, the Style prompt's
  `{bpm}` and verify.py. From `qc.tempo.structural_felt`: eighth pulse × beat_this bar → eighths per bar;
  3/6/12 → compound (felt = eighth/3), 2/4/8 → simple (felt = eighth/2).
- `tempo_uncertain_songs`: bar structure unclear, the strongest 45-100 BPM peak was used. `felt_bpm_fast_candidate`
  (4/4 only): the 100-180 BPM level is as strong - an uptempo song may be read at half time.
- Quote the median and the range; name the songs outside the family (vintagegospel: two 4/4 songs at 79 and 87).
- Our Album 001 (prompt "70 BPM") measured ~63 in this unit. Do not bake a Suno correction into the idea: the
  prompt uses the target tempo; verification-audio measures real offsets.

## 4. Voice

- `gender` = majority of AudioSet Male/Female singing calls on the Demucs vocal stem, one per song (`calls`).
- `register` from the f0 median (pYIN on the vocal stem, backing vocals leak in): male low < 200 Hz, mid 200-270,
  high > 270; female low < 280, mid 280-400, high > 400. A baritone lead sits ~180-250 Hz, tenor-ish belting
  270-350 Hz. Semitones apart = 12·log2(f_ref/f_ours).

## 5. First 15 s of the video

- `voice_s` = first sung run ≥ 1.5 s on the Demucs vocal stem of song 1 (hums and ad-libs included; the
  CLAUDE.md / verify.py meaning). `first_lyric_s` = Whisper and the first caption line of ≥ 3 words, the earlier
  when they agree within 3 s, else the caption.
- `note` (voice well before the first lyric): a hum/ad-lib, or an instrument (slide guitar is voice-like) leaking
  into the stem. Say it is uncertain; do not build Track 01 on it as if certain.
- `level_0_15s_db` vs the body of song 1: around -3 dB = full; -6 to -10 dB = soft but present; below -12 dB or
  `quiet_start_s` > 2 = silence / long fade (weak by CLAUDE.md §3). A soft start with a voice in the first seconds
  is a valid, different strategy - name which it is. `gate.level_ok` = within 4 dB (the rule our ideas use).

## 6. Lyric density

Words per **sung** minute (first lyric line → last caption of each song), median over the songs; without captions,
Whisper on song 1. Same unit as album-plan's `target.words_per_min` check. `label`: sparse < 50, medium 50-90,
dense > 90. Auto-captions miss or add words on sung audio: a ± indication.

## Background

- Channel (`channel.json`): launch order (singles first?), views by kind, top-1 share, where this video sits.
  `opener_single` = a single whose title contains song 1's title; `opener_single_candidates` (no title) = singles
  of the same length ±2 s - inferred, say so.
- Heatmap = YouTube most replayed, only drawn in `overview.png` to check joins (not retention).
