---
name: youtube-music-analyzer
description: Break down a successful YouTube music video (usually a long album / playlist mix, or a whole channel) into six simple criteria that give our Suno album its frame - 1 video length + number of songs, 2 song length, 3 tempo + meter (felt BPM, our QC unit), 4 voice (male/female, low/mid/high), 5 the first 15 s of the video (when the voice and the first lyric come, how loud vs the body), 6 lyric density (words per sung minute) - plus background from metadata (views, channel strategy, title, thumbnail, what not to copy). Then write research/<slug>/analysis.md + reference.yaml and seed channel/<name>/ideas/NNN-slug/idea.yaml for album-plan (music) and thumbnail-prompt / video-generator (picture). Can run for many videos ahead of time. Use whenever the user sends a youtube.com / youtu.be link (video or channel) and wants it analyzed, researched, "phân tích video/kênh", "xem vibe", "bài đầu tiên thế nào", "tempo bao nhiêu", "làm idea từ video này", or wants a reference broken down for the RESEARCH/DECONSTRUCT/BLUEPRINT steps.
---

# YouTube music analyzer

**Goal:** from one YouTube link, an `idea.yaml` that album-plan can start from. Music is an art: numbers cannot say
which song is good, and the more criteria we measure the harder it is to decide anything. So the analyzer measures
**six criteria only**, each one number or a few words that go straight into a plan field or a Suno input:

| # | Criterion | Result (example) | Goes to |
|---|---|---|---|
| 1 | Video length + number of songs | 1:13:10, 14 songs | `target.duration_min`, `track_count` |
| 2 | Song length | median 5:18 (3:18-8:00) | `track_duration` → Suno duration |
| 3 | Tempo + meter | 53.3 felt BPM (47-87), 6/8·12/8 | `target.tempo` → `{bpm}` in the Style prompt → verify.py |
| 4 | Voice | male, high (f0 288 Hz) | voice words of the Style prompt, persona question |
| 5 | First 15 s of the video | voice at 3.6 s, first lyric 20 s, 0-15 s level -6.2 dB vs body | `track01` opening (CLAUDE.md §3) |
| 6 | Lyric density | 75 words per sung minute (medium) | `target.vocal.words_per_min`, lyric length |

**Background** (metadata, not measured audio): views, channel scan (launch order, singles first? is the opener one
of its singles?), title, tags, thumbnail, and `copy_guard` (their titles, channel name, scripture used). The plan
and publish steps need it.

Genre, instruments, the emotional arc, the joins, the key and the mix are **not** taken from the reference: they
come from our channel (`channel.md`, the latest album's Style prompt, CLAUDE.md §4 / §7.2).

```
URL ──▶ fetch (metadata, captions, audio) ──▶ channel scan
    ──▶ song split: chapters | description timestamps | segments.yaml | audio dips + caption words   (criteria 1, 2)
    ──▶ measure.py on the GPU box: felt tempo + meter, voice, song 1 first voice/lyric           (criteria 3, 4, 5, 6)
    ──▶ reference.yaml `criteria` ──▶ analysis.md (Claude) ──▶ idea.yaml (Claude) ──▶ validate_idea.py OK
```

`SK=.claude/skills/youtube-music-analyzer`. Private venv `$SK/.venv` (yt-dlp, librosa, yaml; `scripts/setup.sh`).
The measurements use verification-audio's `scripts/qc` + `.venv` (Demucs, beat_this, pYIN, Whisper, AudioSet for male/female)
on the GPU box in `~/youtube-qc` (`.claude/skills/verification-audio/scripts/remote.sh setup`; remote.sh pushes its code).

## 1. Run

Slug: `<channel>-<topic>` kebab-case. Our channel dir: `channel/lamplight_gospel` unless the user says otherwise.
Next idea number = highest in `ideas/` + 1.

```bash
SK=.claude/skills/youtube-music-analyzer
bash $SK/scripts/remote.sh "<URL>" research/<slug> --channel-dir channel/lamplight_gospel \
     --idea channel/lamplight_gospel/ideas/NNN-<idea-slug>          # a few minutes for a 1 h mix
```

Run it in the background. Options: `--no-qc` (no GPU numbers), `--no-lyrics` (no Whisper); after `--` go
analyze_audio args (`--segments FILE`, `--expected-tracks N`, `--force-auto`, `--single`). Server down (`ssh`
timeout): stop and ask the user first (CLAUDE.md §4: heavy work on the Mac only with their yes); if yes,
`bash $SK/scripts/run.sh "<URL>" research/<slug>` runs everything locally (measure.py uses
verification-audio's `.venv`, slower on the Mac), then
`$SK/.venv/bin/python $SK/scripts/build_reference.py research/<slug> --channel-dir ... --idea-dir ...`.
A video under 10 min is analysed as one song.

**Whole channel** (a channel URL, or the channel matters): `$SK/.venv/bin/python $SK/scripts/channel.py <channel_url> research/<channel-slug>`
→ `channel.md` (top videos, launch order, singles vs compilations, title patterns), then run step 1 on its best
compilation. Join date / links / AI disclosure are only on the About page: read it with agent-browser if it matters.

Outputs in `research/<slug>/` (media stays on the server under `~/yt-analyzer/runs/<slug>/raw`):
`reference.yaml` (`criteria` + background, machine-readable) · `audio/report.md` + `audio/vocals.md` (split, captions)
· `audio/qc.json` (measure.py) · `audio/overview.png` (level + joins + most-replayed, to check the split) ·
`channel.json/.md` · `thumbnail.jpg`. Never `cat raw/video.info.json` (huge): pull fields with the venv python.

## 2. Check the song split

`report.md` names the source. Chapters / description timestamps are snapped to the real join; chapters under 90 s
(Intro/Outro stings) are merged into the next song. Without them the split is automatic (level dips + timbre change,
caption words changing, a penalty when both sides share the same chords or words = a chorus coming back, a
2.5-8 min song-length prior). Look at `overview.png`; a song < 2.5 min or > 8 min or a `segmentation.weak_joins` entry
needs a look. To fix: write `research/<slug>/segments.yaml` and re-run (audio and stems are cached):

```yaml
segments:   # start = song start in the video; source = your evidence; confidence high|medium|low
  - {start: "0:00", title: "Psalm 91", source: "chapter", confidence: high}
  - {start: "6:30", title: "Psalm 23", source: "1.3 s gap + words change", confidence: high}
```
`bash $SK/scripts/remote.sh "<URL>" research/<slug> ... -- --segments research/<slug>/segments.yaml`

Medians (tempo, length, density) survive a wrong join or two; song 1's numbers do not depend on later joins.
Tested on the vintagegospel mix (no chapters): 11 of 13 joins exactly on the reviewed split, two ~30 s early.

## 3. Read the numbers

`references/interpretation.md`: felt tempo vs pulse, male/female + register, first sung sound (Demucs, hums
included) vs first lyric (Whisper/captions), the 0-15 s level, words per sung minute.

## 4. Song 1 and the first 15 s (criterion 5, CLAUDE.md §3)

The first seconds decide most of whether a viewer stays. From `criteria.opening` say: when the voice comes, when
the first lyric comes, how loud 0-15 s is vs the body, whether there is silence at 0:00 - and the gate for this
video (voice by 10 s, lyric by 15 s, level within 4 dB). If `note` says the "voice" may be an instrument leaking
into the stem, say it is uncertain. Then write a Track 01 opening for us (0-15 s timeline, when the voice and the
hook land, 2-3 generation variants) into the idea's `track01` and `slots[0].arrangement_note`.
Never ask the user to listen and judge.

## 5. Write `research/<slug>/analysis.md`

Template `references/analysis-template.md`: short, Vietnamese notes, Suno text in English, numbers with their tags.

## 6. Write the idea (the deliverable)

`--idea` seeds `idea.yaml` with every derivable field (provenance, evidence, copy guard, reference numbers, our
latest album as baseline, Voice, open questions); creative fields are null and listed in `todo` - fill them and
empty `todo`. `slots[0]` is authoritative for the title track (album-plan reads slots). Intro vocabulary: vocal_hum,
vocal, choir, hammond, piano, acoustic_guitar, slide_guitar, electric_guitar, full_band, strings. Fill from
analysis.md, `reference.yaml`, `channel/<name>/channel.md`, `library/catalog.md`, the latest album, and the Suno facts
in `.claude/skills/suno-generate/references/suno-research.md` + memory. Schema: `templates/idea.yaml`.

- Keep the spirit (tempo family, song length, opening strategy, lyric source), change the identity (our persona, titles,
  imagery, arc); their titles/branding/look/scripture go in `copy_guard`.
- The prompt BPM is the target tempo itself - no guessed compensation; verification-audio measures real offsets.
- Persona and tempo decisions go to `open_questions` (blocking) with a recommendation, never decided silently.
- **Follow the reference ~50 %** (`channel/<name>/rules.md` §1b): the idea's tempo = the reference's felt tempo (no nudging toward
  our older albums), the Voice = the channel Voice (rules.md `voices`, measured f0) closest to the reference's f0, lyric density ≈
  the reference's. Suggest the album's highlight song (slot 4 or 7, one unusual axis, released as a single).
- **Variety over cloning** (`channel/<name>/rules.md` §1): our house sound is only the default. When the reference has
  a distinctive trait that may explain its views (high voice, unusual tempo, dense lyrics, energy spikes…), propose it
  as an `experiment` ({axes, what, why, measure}) in the idea + an open question with a recommendation, instead of
  flattening it into the house sound. The goal is what listeners play, not what we like.

Then `$SK/.venv/bin/python $SK/scripts/validate_idea.py <idea.yaml>` until OK (TODOs, Style ≤ 1000 chars, copy-guard
hits, scripture avoided, energy steps ≤ 2, adjacent intro types, duplicate hooks, Track 01 rules, budget, no official
downloads). Write `idea.md` (human summary) and rename `idea.seed.yaml` → `idea.yaml` if the idea already existed.

Downstream (keep these keys stable; contract in `.claude/skills/album-plan/references/bridge.md`):
- **Music:** album-plan `init` reads `idea.yaml` → `<album>/plan.yaml` → generation.yaml / selection.yaml / tracks.
- **Picture:** thumbnail-prompt reads `packaging.thumbnail_brief`; video-generator uses the idea's `thumbnail.png` + `video.json`.
- **Publish:** youtube-publish reads `packaging.video_title_candidates`, `title_rules`, `description_outline`
  (ABOUT THIS VIDEO only) and `differentiation.copy_guard`; chapters are measured on the uploaded video.

## Many videos at once

Give every link its idea number **before** starting (next free number + i) so parallel runs never collide; one slug
per video. Start 2 runs in parallel on the one GPU box, the next when one finishes. Seed ideas stay `proposed` until
their `todo` is empty; then write analysis.md + fill each idea one by one. `album_plan.py board --channel <ch>`
lists every idea with what is still missing.

## Not measured on purpose

Emotional/energy curve, genre and instruments, intro/outro per song, drums entry, hook timing and repeats, lyric
structure (repeated lines, point of view), key/Camelot, chords, melody, bars, song form, stem levels, their joins,
their loudness, speaker similarity (ECAPA), comments, title-card OCR, singles matching, spectrograms.
Either they cannot be typed into Suno, or our own channel decides them (CLAUDE.md §4 / §7.2), or they were
unreliable. Our own drafts are checked by verification-audio. **Add a criterion only when a named consumer needs it
and the user agrees** - the list stays at six.

## Rules

- **Inspired, not copied.** Never store or paste lyrics: caption files stay on the server (only timing and word
  counts come back); Whisper text stays in memory (numbers only). Never propose their titles, branding,
  melodies or a celebrity-lookalike face.
- Media (audio, WAV cuts) stays on the server or in `research/*/raw/` (gitignored).
- Most-replayed ≠ retention. Measured values plainly; model/inferred values with their tag and a confidence word.

## When something fails

- `Sign in to confirm you're not a bot` / 403 on metadata: `$SK/.venv/bin/pip install -U "yt-dlp[default]"`, then add
  `--cookies-from-browser chrome` to BASE in `scripts/fetch.py`.
- `measure failed`: check `~/youtube-qc/.claude/skills/verification-audio/.venv` exists
  (`bash .claude/skills/verification-audio/scripts/remote.sh setup`); `--no-lyrics` if Whisper runs out of memory.
  If the song split changed, build_reference ignores the old qc.json (bounds check): re-run. Without qc,
  reference.yaml lacks tempo/voice: say so.
- No captions: the split has no word evidence and lyric density falls back to Whisper on song 1 - say so.
