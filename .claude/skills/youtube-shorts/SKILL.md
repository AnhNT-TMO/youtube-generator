---
name: youtube-shorts
description: Make the YouTube Shorts of a finished album - as many as CLAUDE.md §3's release package says (role A = the title track's chorus, Related video → the album; role B = another song's chorus, Related video → that song's single) - by finding the chorus from the song's lyrics aligned to the Whisper word timestamps verification-audio already cached (starts on the hook within 1 s, one whole chorus, ends at a line end so it loops, no long instrumental gap), getting a NEW vertical 9:16 image for each Short from ChatGPT (thumbnail-prompt, styled after the niche's most-watched Shorts from youtube-trend-research `trend.py shorts`), rendering a Short-only 1080×1920 video on the GPU server (video-generator `video.py short`: seamless loop as long as the clip, the channel's light effect, dust, spectrum, lyric lines, hook text, CTA), writing youtube.md (title, description, tags, pinned comment, Studio steps incl. Related video + AI = Yes) and zipping it to S3 next to the album. Use when the PM or the owner says "làm shorts", "shorts cho album NNN", "cắt short", "video dọc", "Shorts", or after an album and its singles are delivered. Does NOT upload (the owner does) and spends no Suno credits.
---

# YouTube Shorts

Shorts are cut from songs that already exist: no Suno, no new audio mixing. Each Short gets its own vertical picture and
its own render. Policy and growth research behind every rule here: `docs/seo-youtube/09-shorts.md` (read §4 once).

```bash
S=.claude/skills/youtube-shorts/scripts/shorts.py        # repo root; python3 stdlib, runs on this Mac
python3 $S new   <album> --slot N --role A|B [--related <album|single dir>]   # → channel/<ch>/shorts/NNN-slug/short.md
python3 $S pick  <short> [--pick K] [--length 25-65]     # chorus from lyrics + cached Whisper → short.json
python3 $S check <short>                                  # short.md, short.json, 9:16 image, render, youtube.md
python3 $S list  --channel <ch>                           # every Short: song, target video, segment, image, video, S3, URL
V=.claude/skills/video-generator/scripts/video.py
python3 $V frame <short> --at 5                           # one 1080×1920 still of the effects, to tune <short>/video.json
python3 $V short <short> [--no-package]                   # GPU server render (~1–2 min) → check frames; packages if youtube.md exists
python3 $V package <short>                                # zip (video, 9:16 thumbnail, youtube.md, paste fields) → S3 album folder
```

## Where things live

| What | File |
|---|---|
| Which songs, targets, release order, schedule | `CLAUDE.md` §3 *Gói đăng mỗi album* + `channel/<ch>/publish.md` → *Giờ đăng* |
| Title / description / tags / pinned comment / hook + CTA wording | `channel/<ch>/publish.md` → *Shorts* |
| Vertical image rules + the vertical CORE prompt block | `channel/<ch>/visual.md` → *Ảnh dọc Shorts*, *Prompt ảnh dọc Shorts (ChatGPT)* |
| Text fonts, colours, positions; logo / bars placement for 1080×1920 | `video-generator/scripts/config.py` `DEFAULTS["short"]` < `channel/<ch>/video.json` → `short` < `<short>/video.json` |
| Per Short: song, target, length window, hook, CTA, version | `<short>/short.md` (template `templates/short.md`) |
| Computed clip: audio, in/out, lyric lines with times | `<short>/short.json` (written by `pick`, read by `video.py short`) |
| Upload fields + Studio steps + analytics | `<short>/youtube.md` (template `templates/youtube-short.md`) |

## Steps (per Short of the release package; role A first)

1. **Inputs.** The album's tracks are accepted (`tracks/NN-*.md` with `audio:` and lyrics) and verification-audio has
   cached Whisper words for them (it always has after `verify.py check`). A role B Short needs its single (its `youtube.md`),
   since it is the Related video. No highlight song → the song with the best verify numbers, as for singles.
2. **Create.** Role A: `new <album> --slot 1 --role A` (target = album). Role B (only when the package or the PM asks for it):
   `new <album> --slot <N> --role B --related channel/<ch>/singles/<NNN-slug>`.
   When the PM passes an R&D Short idea (format, part of the song, hook angle, picture pattern, `version`), follow it and
   write its `version` in `short.md`; otherwise the defaults above.
3. **Words on screen.** In `short.md` write `hook_text` and `cta_text` by `publish.md` → *Shorts*: the hook is a new line
   from this song's lyrics, spoken to the viewer. Never reuse an earlier Short's hook (`list` + grep the other `short.md`).
4. **Clip.** `pick <short>`. It aligns every sung line to the Whisper words and offers one candidate per chorus: starts
   0.25 s before the chorus's first word, ends at the end of a section (+ a short tail, faded) so the loop back to the
   start is musical, never spans a vocal gap > 6 s, 20 s minimum. Score = whole chorus, fits `length`, clean silence after,
   alignment quality, earlier chorus. Read the table and the printed lyric lines; pick another with `--pick K` (or `pick:`
   in `short.md`) when the chosen one misses lines or ends mid-thought. Two Shorts of one album use different songs, and a
   segment already used by an earlier Short of the same song is never used again. Rerun `pick` after editing hook/CTA.
5. **Picture.** R&D sheet first: when `research/trends/<ch>/shorts/` has nothing from the last 7 days, run
   youtube-trend-research `trend.py shorts --channel <ch>` (0 quota on a fresh snapshot). Then thumbnail-prompt on the
   Short folder: it detects `shorts/` and uses the vertical CORE block, the vertical checks and `fit` → 2160×3840. The scene
   comes from this Short's lyric lines and differs from the album's and the single's image of the same song. Write under
   *Ý tưởng* which trending patterns you followed.
6. **Effects.** `video.py frame <short> --at 5`, Read it, write `<short>/video.json` for this image only (`lantern.center`
   from `thumb.py check`, `light.shapes`, particle `lanes`), as in video-generator step 1. Text positions are fixed per
   channel; the image, not the text, must fit them.
7. **Render.** `video.py short <short> --no-package`. Read `video/check_hook.png` (hook + first lyric), `check_mid.png`,
   `check_cta.png`: text never over the face or the flame, readable at phone size, nothing important in the covered zones
   (`docs/seo-youtube/09-shorts.md` §1). `video/overlays.json` gives each text block's top/bottom (fraction of height).
   Something off → fix the image or `<short>/video.json`, never move the channel's text layout for one Short.
8. **YouTube text.** `youtube.md` from `templates/youtube-short.md`, filled by `publish.md` → *Shorts*, with the target's
   Video URL when it is uploaded (else leave the placeholder line out and note "upload the target first").
   `shorts.py check <short>` → no ❌. Then `video.py package <short>`: the zip goes next to the album's
   (`short-<slug>-<time>.zip`), recorded in `<short>/s3-package.json`.
9. **Hand-off.** The owner uploads by the schedule and sets the Related video. After upload: Video URL + date in
   `youtube.md`. After 48 h and 7 days: the analytics row (engaged views, viewed vs swiped away, avg % viewed, subs, Related
   video clicks); the PM compares medians per `version`, one axis at a time (CLAUDE.md §0).

## Rules (policy, see `docs/seo-youtube/09-shorts.md` §4)

- Every Short differs for real: its own song, its own chorus, its own new vertical image, its own hook line. Never a crop
  of the album/single image, never the same segment twice, never delete-and-reupload a weak Short.
- ≤ 180 s and vertical, or YouTube does not treat it as a Short. Voice within 1 s of 0:00 (`check` enforces).
- AI use = Yes on every Short; no AI/Suno line in the description; not made for kids; 3–5 relevant hashtags.
- Title and hook never promise what the video or its target does not deliver.
- Rendering and upscaling run on the GPU server (CLAUDE.md §5); `pick`, `check`, `list` and `frame` are light and run here.
- Something learned about one channel's Shorts (a hook style that works, a text colour that disappears): one line in that
  channel's `publish.md` / `visual.md`, not here.
