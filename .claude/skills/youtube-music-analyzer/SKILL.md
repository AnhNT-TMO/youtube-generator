---
name: youtube-music-analyzer
description: R&D measuring lab + idea writer. Measure the music of trend reference videos (the outliers youtube-trend-research picks, or a link the owner sends) with six simple criteria that give our Suno album its frame - 1 video length + number of songs, 2 song length, 3 tempo + meter (felt BPM, our QC unit), 4 voice (male/female, low/mid/high), 5 the first 15 s of the video (when the voice and the first lyric come, how loud vs the body), 6 lyric density (words per sung minute) - plus background from metadata (views, channel strategy, title, thumbnail, what not to copy); combine 3-5 measured videos into one reference set (medians, refset.py) so no single video is copied; then write the album idea from a brief (a trend topic from R&D, or a CEO/PM story: who, where, what they long for) + the reference set + our channel: channel/<name>/ideas/NNN-slug/idea.yaml for album-plan (music) and thumbnail-prompt / video-generator (picture). Use whenever a youtube.com / youtu.be link must be measured ("phân tích video/kênh", "tempo bao nhiêu", "bài đầu tiên thế nào"), when R&D hands over reference videos for a topic ("đo nhạc các video nổi bật", "reference set"), or when an idea must be written from a trend or a brief ("lên ý tưởng album", "làm idea từ trend", "idea từ brief của CEO").
---

# YouTube music analyzer

**Goal:** the album idea comes from a **brief** (what the album is about: a trend topic chosen by the PM, or a CEO/PM
story) and a **reference set** (the music frame: medians of 3–5 videos that are winning on that topic), never from
copying one video. This skill does two jobs for that: measure videos (§1–§5) and write the idea (§6).
Music is an art: numbers cannot say which song is good, and the more criteria we measure the harder it is to decide
anything. So each video gets **six criteria only**, each one number or a few words that go straight into a plan field
or a Suno input:

| # | Criterion | Result (example) | Goes to |
|---|---|---|---|
| 1 | Video length + number of songs | 1:13:10, 14 songs | `target.duration_min`, `track_count` |
| 2 | Song length | median 5:18 (3:18-8:00) | `track_duration` → Suno duration |
| 3 | Tempo + meter | 53.3 felt BPM (47-87), 6/8·12/8 | `target.tempo` → `{bpm}` in the Style prompt → verify.py |
| 4 | Voice | male, high (f0 288 Hz) | voice words of the Style prompt, persona question |
| 5 | First 15 s of the video | voice at 3.6 s, first lyric 20 s, 0-15 s level -6.2 dB vs body | `track01` opening (CLAUDE.md) |
| 6 | Lyric density | 75 words per sung minute (medium) | `target.vocal.words_per_min`, lyric length |

**Background** (metadata, not measured audio): views, channel scan (launch order, singles first? is the opener one
of its singles?), title, tags, thumbnail, and `copy_guard` (their titles, channel name, numbered sources such as scripture chapters they used). The plan
and publish steps need it.

Genre, instruments, the emotional arc, the joins, the key and the mix are **not** taken from the reference: they
come from our channel (`channel/<ch>/rules.md`, `channel.md`, the latest album's Style prompt).

```
URL ──▶ fetch (metadata, captions, audio) ──▶ channel scan
    ──▶ song split: chapters | description timestamps | segments.yaml | audio dips + caption words   (criteria 1, 2)
    ──▶ measure.py on the GPU box: felt tempo + meter, voice, song 1 first voice/lyric           (criteria 3, 4, 5, 6)
    ──▶ reference.yaml `criteria` ──▶ analysis.md (Claude)                                       (one per video)
3–5 videos ──▶ refset.py ──▶ research/<set>/reference.yaml (medians) + analysis.md
brief + set + channel ──▶ idea.py seed ──▶ idea.yaml (Claude fills) ──▶ validate_idea.py OK
```

`SK=.claude/skills/youtube-music-analyzer`. Private venv `$SK/.venv` (yt-dlp, librosa, yaml; `scripts/setup.sh`).
The measurements use verification-audio's `scripts/qc` + `.venv` (Demucs, beat_this, pYIN, Whisper, AudioSet for male/female)
on the GPU box in `~/youtube-qc` (`.claude/skills/verification-audio/scripts/remote.sh setup`; remote.sh pushes its code).

## 1. Run

Slug: the one `trend.py refs` prints (`<channel>-<topic>-<id6>`), else `<reference-channel>-<topic>` kebab-case.
Our channel dir: `channel/<ch>`. The channel's vocabulary (intro types, genre words that are not branding, numbered
lyric sources to guard) comes from `channel/<ch>/rules.md` → `research` and `sources`.

```bash
SK=.claude/skills/youtube-music-analyzer
bash $SK/scripts/remote.sh "<URL>" research/<slug> --channel-dir channel/<ch>   # a few minutes for a 1 h mix
```

Run it in the background, at most 2 at once on the one GPU box (a reference set = 3–5 runs). Options: `--no-qc` (no GPU numbers), `--no-lyrics` (no Whisper); after `--` go
analyze_audio args (`--segments FILE`, `--expected-tracks N`, `--force-auto`, `--single`). Server down (`ssh`
timeout): stop and ask the user first (CLAUDE.md: heavy work on the Mac only with their yes); if yes,
`bash $SK/scripts/run.sh "<URL>" research/<slug>` runs everything locally (measure.py uses
verification-audio's `.venv`, slower on the Mac), then
`$SK/.venv/bin/python $SK/scripts/build_reference.py research/<slug> --channel-dir ...`.
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
  - {start: "0:00", title: "Song One", source: "chapter", confidence: high}
  - {start: "6:30", title: "Song Two", source: "1.3 s gap + words change", confidence: high}
```
`bash $SK/scripts/remote.sh "<URL>" research/<slug> ... -- --segments research/<slug>/segments.yaml`

Medians (tempo, length, density) survive a wrong join or two; song 1's numbers do not depend on later joins.
Tested on a 13-song mix without chapters: 11 of 13 joins exactly on the reviewed split, two ~30 s early.

## 3. Read the numbers

`references/interpretation.md`: felt tempo vs pulse, male/female + register, first sung sound (Demucs, hums
included) vs first lyric (Whisper/captions), the 0-15 s level, words per sung minute.

## 4. Song 1 and the first 15 s (criterion 5, CLAUDE.md)

The first seconds decide most of whether a viewer stays. From `criteria.opening` say: when the voice comes, when
the first lyric comes, how loud 0-15 s is vs the body, whether there is silence at 0:00 - and the gate for this
video (voice by 10 s, lyric by 15 s, level within 4 dB). If `note` says the "voice" may be an instrument leaking
into the stem, say it is uncertain. Then write a Track 01 opening for us (0-15 s timeline, when the voice and the
hook land, 2-3 generation variants) into the idea's `track01` and `slots[0].arrangement_note`.
Never ask the user to listen and judge.

## 5. Write `research/<slug>/analysis.md`

Template `references/analysis-template.md`: short, Vietnamese notes, Suno text in English, numbers with their tags.

## 6. Reference set, then the idea (the deliverable)

**Reference set.** After 3–5 videos of the chosen topic are measured (one per channel, ideally in our music branch):

```bash
$SK/.venv/bin/python $SK/scripts/refset.py research/set-<ch>-<topic>-<YYYYMMDD> research/<a> research/<b> research/<c> \
     --topic <topic> --trend research/trends/<ch>/reports/<date>.md --channel-dir channel/<ch>
```

It writes `reference.yaml` (schema `reference-set/v1`: members, median criteria, every member's tracks, union of their
copy guards) and warns when the set is too small, from one channel, or its tempos spread > 20 % (one album = one tempo
band: drop the outlier or make two sets). Write the set's `analysis.md` (what the members share, where they differ, their
first 15 s, what the thumbnails/titles do) — short.

**The brief.** One or two sentences of *what the album is about*, from the PM: a trend topic (a theme the niche is watching now) or a CEO/PM story (a person, a place, what they long for).
A story brief is placed inside a trend: pick the topic it serves and use that topic's set.

```bash
$SK/.venv/bin/python $SK/scripts/idea.py --refset research/<set> --idea-dir channel/<ch>/ideas/NNN-<slug> \
     --channel-dir channel/<ch> --brief "<brief>" --brief-source trend|ceo|pm [--topic <topic>]
```

**The PM decides, the idea worker writes** (CLAUDE.md §0): the brief comes with the PM's `brief.decisions` (music, title
direction, description angle, thumbnail concept, Shorts, version, success target). Implement them; what they leave open is
your creative room (e.g. `packaging.thumbnail_brief` is your detailed expansion of `brief.decisions.thumbnail_concept`, never a
different concept). Missing decisions → write your recommendation in `open_questions` for the PM, never decide silently.

Next idea number = highest in `ideas/` + 1. `idea.py` fills every derivable field (brief, provenance = the set + its
members, evidence, copy guard, set medians, our latest album as baseline, Voice, questions for the PM) and lists the
creative fields in `todo` — fill them and empty `todo`. `slots[0]` is authoritative for the title track (album-plan
reads slots). Intro vocabulary: the channel's `rules.md` → `research.intro_vocab`. Fill from the set's analysis.md,
the trend report (comments = what viewers pray for; the contact sheet), `channel/<name>/channel.md`,
`library/catalog.md`, the latest album, and the Suno facts in `.claude/skills/suno-generate/references/suno-research.md` + memory.
Schema: `templates/idea.yaml`.

- **The story is ours.** `brief.angle` says where the brief meets the trend (who sings to whom, the scene, why a viewer
  clicks). Titles, hooks and imagery come from the brief + what viewers wrote, never from the members' titles (copy guard).
- **Follow the set ~50 %** (`channel/<name>/rules.md` §1b): tempo = the set's median felt tempo, Voice = the channel Voice
  (rules.md `voices`, measured f0) closest to the set's f0, lyric density ≈ the set's. Suggest the album's highlight song
  (slot 4 or 7, one unusual axis, released as a single).
- **Variety over cloning** (`rules.md` §1): our house sound is only the default. When the set shares a trait that may
  explain its views (high voice, unusual tempo, dense lyrics, a different branch such as vintage hymns…), propose it as an
  `experiment` ({axes, what, why, measure}) instead of flattening it into the house sound.
- **Library first** (CLAUDE.md §0 budget): list library songs that fit the brief (`library_check`), up to the §7 limit.
- The prompt BPM is the target tempo itself - no guessed compensation; verification-audio measures real offsets.
- Persona and tempo go to `open_questions` with a recommendation; the PM answers them (CLAUDE.md §0).

Then `$SK/.venv/bin/python $SK/scripts/validate_idea.py <idea.yaml>` until OK (brief + reference set, TODOs, Style ≤ 1000
chars, copy-guard hits, avoided sources, energy steps ≤ 2, adjacent intro types, duplicate hooks, Track 01 rules, budget,
no official downloads). Write `idea.md` (human summary) and rename `idea.seed.yaml` → `idea.yaml` if the idea already existed.

A single video the owner sends (research queue) is measured the same way and joins a set; an idea from one video alone
is the old copy-one-video path: don't.

Downstream (keep these keys stable; contract in `.claude/skills/album-plan/references/bridge.md`):
- **Music:** album-plan `init` reads `idea.yaml` → `<album>/plan.yaml` (with `brief`) → generation.yaml / selection.yaml / tracks.
  Its `reference_follow` check reads `provenance.research[0]` = the set's medians.
- **Picture:** thumbnail-prompt reads `packaging.thumbnail_brief`; video-generator uses the idea's `thumbnail.png` + `video.json`.
- **Publish:** youtube-publish reads `packaging.video_title_candidates`, `title_rules`, `description_outline`
  (ABOUT THIS VIDEO only) and `differentiation.copy_guard`; chapters are measured on the uploaded video.

## Many videos at once

One slug per video, from `trend.py refs`. Start 2 runs in parallel on the one GPU box, the next when one finishes; build
the set when all members are done. `album_plan.py board --channel <ch>` lists every idea with what is still missing.

## Not measured on purpose

Emotional/energy curve, genre and instruments, intro/outro per song, drums entry, hook timing and repeats, lyric
structure (repeated lines, point of view), key/Camelot, chords, melody, bars, song form, stem levels, their joins,
their loudness, speaker similarity (ECAPA), comments, title-card OCR, singles matching, spectrograms.
Either they cannot be typed into Suno, or our own channel decides them (`channel/<ch>/rules.md`), or they were
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
