---
name: youtube-publish
description: Write everything needed to upload an album video to YouTube and walk the user through YouTube Studio - title (format + length rules), description built on the channel's fixed template with only the "ABOUT THIS VIDEO" part written per album, a TRACKLIST of chapters measured on the exact file being uploaded, tags (channel defaults + ~10 album tags, ≤ 500 chars as YouTube counts them), thumbnail check, pinned comment, and what to choose on every Studio screen (AI use / altered content, audience, chapters, end screen, cards, subtitles, visibility). Writes <album>/youtube.md and checks it with scripts/publish.py before the user pastes. Use when the user says "upload", "đăng video", "soạn title/description", "viết description", "tags", "chapters/timestamps/tracklist", "thumbnail", "YouTube Studio chọn gì", "AI use chọn Yes hay No", "end screen", "cards", "subtitles", "visibility", or asks what to put in any YouTube upload field. Also for a single song released on its own (channel/<ch>/singles/NNN-slug: song title, no chapters, lyrics, links back to the album video) - "đăng riêng bài", "upload single". Does NOT render video (video-generator) or mix audio (album-assembly).
---

# YouTube publish

PUBLISH step of CLAUDE.md (step 7). Input: a finished album folder `channel/<channel>/albums/<NNN-slug>/`
(`album.md`, `tracks/*.md`, `thumbnail.png`, the video file to upload) and the channel's defaults in
`channel/<channel>/channel.md` (sections **Description YouTube mặc định** and **Tags YouTube mặc định**).
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
   are wrong for it** (Album 001: video 50:16 from the old CapCut mix, assembly 49:03). Say so. If the video's
   opening is weaker than the current mix (CLAUDE.md §3), recommend re-rendering with video-generator step 2 first.
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
   CLAUDE.md §6, add the pinned comment, and after 48 h / 7 days note retention at 0:15 / 0:30 / 1:00 in the
   Analytics table (CLAUDE.md §3). Translated titles: skill youtube-translate (needs the Video URL).

## Title format

```
<Title Track> <1 emoji> <Genre phrase> for <Use-case> & <Feeling> | Full Album
```

- Album 001: `When The Night Is Long 🕯️ Slow Gospel Blues for Late-Night Prayer & Peace | Full Album` (86 chars).
- **Title track first** (CLAUDE.md §4: Track 01 = video title), then genre keywords + use-case, as the reference
  channels do (they stack keywords; we keep that but lead with our own song name).
- ≤ 100 chars (hard limit). Keywords that matter within the first ~70 chars (search results cut there).
- One emoji at most, in the channel's world (🕯️ lamp, 🙏 prayer). No `<` or `>` (YouTube refuses them).
- Only claim a length that is true: no "1 Hour" for a 50-minute album. English only (CLAUDE.md §5).
- Give 1 recommendation + 2 alternatives. Start from `idea.yaml packaging.video_title_candidates` when present
  (rewrite them into this format; they were written before the tracklist was final) and check them against
  `differentiation.copy_guard` / `packaging.title_rules`.

## Description format

The channel template in `channel.md` is used **verbatim**. Per album, write only:

1. **ABOUT THIS VIDEO**: replace `[Write 3–5 sentences here …]` with 3–5 English sentences (use the points in
   `idea.yaml packaging.description_outline` if any; older ideas may list scripture/AI/use-case lines there, which
   this format leaves out):
   - (1) album name, length, number of songs, and the arc in one line ("a 50-minute journey through one long night of the soul, told in ten original songs");
   - (2) quote the title track's **real hook** (`hook_phrase` in its track file, which is not always the title) and name the journey through the key songs' themes;
   - (3) the sound: same singer + lead instruments + one image of the room ("one intimate service in a small church after midnight");
   - (4, optional) how it ends: the closer's title and feeling.
   - Do **not** repeat what the template already says (quiet nights, praying through a difficult night, comfort, hope).
     Keep it specific to this album.
2. **TRACKLIST**: right after ABOUT THIS VIDEO, one line per song, from step 2:
   ```
   TRACKLIST
   0:00 When The Night Is Long
   5:24 You Found Me In The Valley
   ...
   ```
   YouTube rules (else no chapters): first line `0:00`, ≥ 3 chapters, each ≥ 10 s, ascending, timestamp at line
   start then a space then the title (no dash, no "01."), no blank or other lines between them, no other timestamps
   anywhere in the description. Titles exactly as in `tracks/*.md` (including punctuation, e.g. "Stay With Me, Lord").

Nothing else is added: no scripture line, no use-case lists, no AI line (AI is declared with the Studio toggle,
`references/studio.md`), no copyright line, unless the user asks. Limits: 5000 chars, ≤ 15 hashtags (the template's
5 are already there; the first 3 show above the title).

## Tags format

`channel.md` defaults (12, always all of them) + **~10 album tags**, none duplicating a default, one per bucket:

| Bucket | Album 001 |
|---|---|
| album / title track name | when the night is long |
| use-cases (2–3) | late night prayer music, gospel music for sleep, prayer music for anxiety |
| album theme (1–2) | night worship songs, gospel songs of hope |
| subgenre | southern gospel soul |
| lead instrument | hammond organ gospel |
| format (1–2) | christian blues playlist, slow gospel full album |

Total ≤ 500 chars **as YouTube counts**: commas count, and every tag containing a space counts 2 extra (quotes).
`check` computes it (Album 001: 22 tags, 464/500). Lowercase is fine. Present in `youtube.md` as one block to paste
plus a small table "tag → why".

## Pinned comment format (the channel's own first comment)

Posted from the channel account right after publishing, then **Pin** + ❤️. It must stand out like the big music
channels' pinned comments: emoji on every line, clickable timestamps, short lines. English. Blocks in this order:

```
🕯️ Welcome to Lamplight Gospel. Thank you for spending this night with us. 🕯️      ← greeting, channel icon both ends

🙏 Which song spoke to your heart tonight? Tell us in the comments. We read every one.   ← one question inviting replies

🎶 TRACKLIST 🎶
1️⃣ 0:00 When The Night Is Long                   ← keycap 1️⃣…🔟 + SAME timestamps as the description
...                                                 (> 10 songs: use ▸ instead of keycaps)
🔟 45:14 Stay With Me, Lord

✨ Don't miss                                       ← 3 highlights: the peak (arc_role peak), the turn to hope,
🔥 29:43 You Never Let Me Go · the peak of the night       and the closer; own emoji + a 3–6 word tagline each
🌅 35:22 Morning Is Coming · when the light returns
🌙 45:14 Stay With Me, Lord · the last prayer before rest

💛 If this music brought you peace:
👍 Like · 🔔 Subscribe · 🔁 Share it with someone carrying a heavy heart tonight   ← call to action

✝️ You are not alone. Even in the darkest night, the light still shines.            ← closing line from the template's "May these songs remind you"
```

- Timestamps in comments are clickable, so the tracklist is repeated here (people read comments more than
  descriptions). They must be the description's chapters exactly; `check` enforces it.
- Emoji palette of the channel: 🕯️ lamp · 🙏 prayer · 🎶 music · ✨ highlights · 🔥 peak · 🌅 hope/morning ·
  🌙 night/rest · 💛 warmth · ✝️ faith. Pick the highlight emoji from the song's imagery.
- Promise only what is true ("We read every one", not "we pray for each of you" unless the user does).

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
- **Title**: `<Song Title> <1 emoji> <Genre phrase> for <Use-case> | Lamplight Gospel`, e.g.
  `Stay With Me, Lord 🙏 Slow Gospel Blues Prayer for a Restless Night | Lamplight Gospel`. Song title first, exactly as in
  the track file. Never "Full Album", "Playlist" or an hour count (`check` refuses). Say "Lyrics" only if the lyrics are on
  screen, not just in the description. 1 recommendation + 2 alternatives, and not the album video's title with a word changed.
- **Description**: the channel template verbatim, minus the `TRACKLIST` line and its placeholder. After ABOUT THIS VIDEO:
  - ABOUT THIS VIDEO, 3–4 sentences: (1) the song and where it sits in the album ("the song that opens…", "the peak of…");
    (2) its real hook in quotes (`hook_phrase`) and the one picture it paints; (3) the sound in one line (same singer + lead
    instruments + the room). Not the album's ABOUT text again.
  - `🎧 FULL ALBUM` block: `"<Album Title>" · <n> original songs · <length>: <album_video_url>` (omit the block until the
    album is live; `check` warns while `album_video_url` is empty).
  - `LYRICS` block: only the sung lines from the track file, stanzas separated by one blank line; drop every `[...]` tag
    and every arrangement instruction under it ("Warm Hammond organ…", "No dramatic ending"). If the track file has no
    lyrics (Album 001 tracks 03–10), leave the block out rather than guessing; verification-audio's Whisper transcript can
    fill it, marked as checked by ear. No timestamps anywhere (`check` refuses them).
- **Tags**: channel defaults + ~10 song tags: song title, hook phrase (if different), album title, 2–3 use-cases,
  1–2 themes from the song, subgenre, lead instrument, format ("gospel blues song", "christian soul single").
- **Pinned comment**: greeting with the song title → one question tied to the hook → the hook line quoted →
  `🎧 The full album "<Album Title>" (<n> songs · <length>): <album_video_url>` → CTA → closing line. **No bare timestamps**:
  in this video they would jump inside the single. To point at the song's place in the album use the album link with
  `&t=<seconds>` (seconds from the album's chapters). `check` enforces both.
- **Studio**: `references/studio.md` section 6 (playlist Songs, end screen + card → album video).
- **After upload**: also add the folder name to `singles:` in the origin track's front matter and set `single.md` `status`.

## Principles

- **The file being uploaded is the truth.** Chapters come from measuring that file, never from a plan or another mix.
- **Inspired, not copied** (CLAUDE.md §1): no wording, titles, tag lists or scripture choices taken from the
  reference channels. Mention a title overlap with a reference (Album 001: "You Never Let Me Go" is also
  stillworship's anchor title) so the user decides.
- **Honest disclosure:** AI-generated music is declared (AI use = Yes). Never advise hiding it, even though the
  reference channels do.
- Claude cannot hear: say which chapter points are measured and which are estimates, and ask the user to click-test
  them on the Unlisted upload.
