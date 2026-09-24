---
name: youtube-publish
description: Write everything needed to upload an album video to YouTube and walk the user through YouTube Studio - title (format + length rules), description built on the channel's fixed template with only the "ABOUT THIS VIDEO" part written per album, a TRACKLIST of chapters measured on the exact file being uploaded, tags (channel defaults + ~10 album tags, ≤ 500 chars as YouTube counts them), thumbnail check, pinned comment, and what to choose on every Studio screen (AI use / altered content, audience, chapters, end screen, cards, subtitles, visibility). Writes <album>/youtube.md and checks it with scripts/publish.py before the user pastes. Use when the user says "upload", "đăng video", "soạn title/description", "viết description", "tags", "chapters/timestamps/tracklist", "thumbnail", "YouTube Studio chọn gì", "AI use chọn Yes hay No", "end screen", "cards", "subtitles", "visibility", or asks what to put in any YouTube upload field. Also for a single song released on its own (channel/<ch>/singles/NNN-slug: song title, no chapters, lyrics, links back to the album video) - "đăng riêng bài", "upload single". Does NOT render video (video-generator) or mix audio (album-assembly).
---

# YouTube publish

PUBLISH step of CLAUDE.md (step 7). Input: a finished album folder `channel/<channel>/albums/<NNN-slug>/`
(`album.md`, `tracks/*.md`, `thumbnail.png`, the video file to upload) and the channel's packaging rules in
`channel/<channel>/publish.md` (description template, default tags, title formats, emoji, pinned comment). This skill is
the procedure; every wording choice of the channel comes from `publish.md`. No `publish.md` → write one with the owner
first (template: `channel/_template/publish.md`).
An album planned from an idea also has `<album>/idea.yaml` (snapshot): its `packaging.video_title_candidates` and
`description_outline` are the analyzer's starting points (see Title / Description below); `copy_guard` lists the
reference channel's titles and branding to stay away from. Runs any time after the video exists, in any session.
Output: `<album>/youtube.md` (template: `templates/youtube.md`), every field in its own ``` block ready to paste.

What to choose on each YouTube Studio screen, with reasons: `references/studio.md`. Read it when the user asks
about any button, or before walking them through an upload.

```bash
SK=.claude/skills/youtube-publish; PY=$SK/.venv/bin/python; P=$SK/scripts/publish.py   # repo root
# first run: python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt
$PY $P chapters <album> --audio <album>/video/<file>.mp4   # timestamps measured on the file being uploaded
$PY $P check    <album> --video <album>/video/<file>.mp4   # lengths, placeholders, template, tags, chapters vs video
```

## Steps

1. **Which video file?** Find the file that will be uploaded and check its duration (`ffprobe`). Videos rendered by
   video-generator step 2 stay on the GPU server: their ffprobe is `<album>/video/video.mp4.json`, their audio is
   `<album>/video/remote.json` `audio` (the master), so measure chapters with `--audio <that master.wav>` and run
   `check` without `--video`; after youtube.md passes, `video.py package <album>` zips everything and uploads it to
   S3 (video-generator step 3). Compare it with
   `assembly.yaml`'s `output`: if they differ, the video was built from another mix and **`assembly.md`'s timestamps
   are wrong for it** (e.g. a video made from an older hand-made mix). Say so. If the video's
   opening is weaker than the current mix (CLAUDE.md), recommend re-rendering with video-generator step 2 first.
2. **Chapters.** Run `publish.py chapters --audio <video>`. It aligns every selected track (from `tracks/*.md`
   `audio`) against the video's audio and puts each chapter where the new song becomes audible, before its first
   line. Rows marked "ước lượng" (song B enters under song A's loud outro) or "khớp yếu" (maybe a different take in the
   video) must be clicked and checked after upload. If the user may still re-render, give both chapter sets (A =
   current video, B = new mix) and let them pick.
3. **Write `youtube.md`** from `templates/youtube.md`, following the formats below.
4. **Check.** `publish.py check --video <video>`. Fix every ❌. A remaining placeholder is fine only if the user
   still has to choose (e.g. chapters A or B); say what they must paste.
5. **Walk the Studio screens** with `references/studio.md` when the user uploads. They send screenshots and ask
   "chọn gì": answer per that file. Verify policy questions against the live YouTube Help page (WebFetch) when
   they could have changed.
6. **After upload:** fill Video URL + date in `youtube.md`, set status in `album.md` and the album line of
   `channel/<ch>/CLAUDE.md` (state), add the pinned comment, and after 48 h / 7 days note retention at 0:15 / 0:30 / 1:00 in the
   Analytics table (CLAUDE.md). Translated titles: skill youtube-translate (needs the Video URL).

## Title

Format, examples, genre phrases and emoji: `channel/<ch>/publish.md` → *Title* (album and single). Rules for every channel:

- **Title track first** (CLAUDE.md: Track 01 = video title), then genre keywords + use-case, as the reference channels do
  (they stack keywords; we keep that but lead with our own song name).
- ≤ 100 chars (hard limit). Keywords that matter within the first ~70 chars (search results cut there).
- One emoji at most, from the channel's palette. No `<` or `>` (YouTube refuses them).
- Only claim a length that is true: no "1 Hour" for a 50-minute album. English only (CLAUDE.md).
- Give 1 recommendation + 2 alternatives. Start from `idea.yaml packaging.video_title_candidates` when present
  (rewrite them into the channel's format; they were written before the tracklist was final) and check them against
  `differentiation.copy_guard` / `packaging.title_rules`.

## Description

The channel template in `publish.md` → *Description YouTube mặc định* is used **verbatim** (`check` compares every line).
Per album, write only:

1. **ABOUT THIS VIDEO**: replace `[Write 3–5 sentences here …]` with 3–5 English sentences (use the points in
   `idea.yaml packaging.description_outline` if any; follow `publish.md` → *ABOUT THIS VIDEO* for what the channel's
   template already says and must not be repeated):
   - (1) album name, length, number of songs, and the arc in one line;
   - (2) quote the title track's **real hook** (`hook_phrase` in its track file, which is not always the title) and name the journey through the key songs' themes;
   - (3) the sound: same artist + lead instruments + one image of the room;
   - (4, optional) how it ends: the closer's title and feeling.
   Keep it specific to this album.
2. **TRACKLIST**: right after ABOUT THIS VIDEO, one line per song, from step 2:
   ```
   TRACKLIST
   0:00 <Track 01 title>
   5:24 <Track 02 title>
   ...
   ```
   YouTube rules (else no chapters): first line `0:00`, ≥ 3 chapters, each ≥ 10 s, ascending, timestamp at line
   start then a space then the title (no dash, no "01."), no blank or other lines between them, no other timestamps
   anywhere in the description. Titles exactly as in `tracks/*.md` (including punctuation).

Nothing else is added: no AI line (AI is declared with the Studio toggle, `references/studio.md`), no copyright line,
and nothing `publish.md` forbids, unless the owner asks. Limits: 5000 chars, ≤ 15 hashtags (the first 3 show above the title).

## Tags

`publish.md` → *Tags YouTube mặc định* (always all of them) + **~10 album tags**, none duplicating a default, one per
bucket of `publish.md` → *Tags: các nhóm* (album / title track name, use-cases, theme, subgenre, lead instrument, format).
Total ≤ 500 chars **as YouTube counts**: commas count, and every tag containing a space counts 2 extra (quotes).
`check` computes it. Lowercase is fine. Present in `youtube.md` as one block to paste plus a small table "tag → why".

## Pinned comment (the channel's own first comment)

Posted from the channel account right after publishing, then **Pin** + ❤️. Template and emoji palette:
`publish.md` → *Pinned comment*. Structure for every channel: greeting → one question inviting replies → tracklist
(keycap 1️⃣…🔟 + the SAME timestamps as the description; > 10 songs: ▸) → 3 highlights (the peak, the turn, the closer;
own emoji + a 3–6 word tagline each) → call to action → closing line. English.

- Timestamps in comments are clickable, so the tracklist is repeated here (people read comments more than
  descriptions). They must be the description's chapters exactly; `check` enforces it.
- Promise only what is true.

## Other fields in youtube.md

- **Thumbnail:** `thumbnail.png` in the album folder (made in the idea folder instead → `album_plan.py sync <album>`
  copies it over; `album_plan.py board` shows "ở idea (chưa sync)"), 16:9, ≥ 1280×720, ≤ 2 MB (else
  `sips -s format jpeg -s formatOptions 90 thumbnail.png --out thumbnail.jpg`). Look at it and note whether the
  title text reads at phone size.
- **Studio settings table** and **pre-publish checklist**: copy from `templates/youtube.md`, adjust per album.

## Single mode (one song released on its own)

Folder `channel/<ch>/singles/NNN-slug/` with `single.md` (template `templates/single.md`): `track` → the song's
`tracks/NN-*.md` in the origin album (title, `hook_phrase`, lyrics, emotion), `album_video_url`. `publish.py` switches to
single mode when `single.md` exists. Write `youtube.md` from `templates/youtube-single.md`. Everything above applies except:

- **Video file**: `video/<NNN-slug>.mp4`, made by video-generator step 2 from `audio/master/<NNN-slug>.wav`
  (album-assembly `single`). `check --video` warns if their lengths differ. No `chapters` step.
- **Title**: the single format in `publish.md` → *Title*. Song title first, exactly as in the track file. Never
  "Full Album", "Playlist" or an hour count (`check` refuses). Say "Lyrics" only if the lyrics are on screen, not just in
  the description. 1 recommendation + 2 alternatives, and not the album video's title with a word changed.
- **Description**: the channel template verbatim, minus the `TRACKLIST` line and its placeholder. After ABOUT THIS VIDEO:
  - ABOUT THIS VIDEO, 3–4 sentences: (1) the song and where it sits in the album ("the song that opens…", "the peak of…");
    (2) its real hook in quotes (`hook_phrase`) and the one picture it paints; (3) the sound in one line (same artist + lead
    instruments + the room). Not the album's ABOUT text again.
  - `🎧 FULL ALBUM` block: `"<Album Title>" · <n> original songs · <length>: <album_video_url>` (omit the block until the
    album is live; `check` warns while `album_video_url` is empty).
  - `LYRICS` block: only the sung lines from the track file, stanzas separated by one blank line; drop every `[...]` tag
    and every arrangement instruction under it (instrument or mix directions). If the track file has no
    lyrics, leave the block out rather than guessing; verification-audio's Whisper transcript can
    fill it, marked as checked by ear. No timestamps anywhere (`check` refuses them).
- **Tags**: channel defaults + ~10 song tags (buckets for singles in `publish.md`).
- **Pinned comment**: `publish.md` → *Pinned comment* (single): greeting with the song title → one question tied to the hook → the hook line quoted →
  `🎧 The full album "<Album Title>" (<n> songs · <length>): <album_video_url>` → CTA → closing line. **No bare timestamps**:
  in this video they would jump inside the single. To point at the song's place in the album use the album link with
  `&t=<seconds>` (seconds from the album's chapters). `check` enforces both.
- **Studio**: `references/studio.md` section 6 (playlist Songs, end screen + card → album video).
- **After upload**: also add the folder name to `singles:` in the origin track's front matter and set `single.md` `status`.

## Principles

- **The file being uploaded is the truth.** Chapters come from measuring that file, never from a plan or another mix.
- **Inspired, not copied** (CLAUDE.md): no wording, titles, tag lists or source choices taken from the
  reference channels. Mention a title overlap with a reference so the owner decides.
- **Honest disclosure:** AI-generated music is declared (AI use = Yes). Never advise hiding it, even though the
  reference channels do.
- Claude cannot hear: say which chapter points are measured and which are estimates, and ask the user to click-test
  them on the Unlisted upload.
