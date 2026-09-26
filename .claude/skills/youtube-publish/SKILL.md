---
name: youtube-publish
description: Write everything needed to upload an album video to YouTube and walk the user through YouTube Studio - title (format, ≤ 70 chars), description built on the channel's fixed template with only the "ABOUT THIS VIDEO" part written per album, a TRACKLIST of chapters measured on the exact file being uploaded, tags (channel defaults + 5–12 album tags researched with YouTube autocomplete, ≤ 500 chars as YouTube counts them), thumbnail check, pinned comment, and what to choose on every Studio screen (AI use / altered content, audience, chapters, end screen, cards, subtitles, visibility). Writes <album>/youtube.md and checks it with scripts/publish.py before the user pastes. Use when the user says "upload", "đăng video", "soạn title/description", "viết description", "tags", "chapters/timestamps/tracklist", "thumbnail", "YouTube Studio chọn gì", "AI use chọn Yes hay No", "end screen", "cards", "subtitles", "visibility", or asks what to put in any YouTube upload field. Also for a single song released on its own (channel/<ch>/singles/NNN-slug: song title, no chapters, lyrics, links back to the album video) - "đăng riêng bài", "upload single". Does NOT render video (video-generator) or mix audio (album-assembly).
---

# YouTube publish

Step 8 *Đăng* of CLAUDE.md §3. Input: a finished album folder `channel/<channel>/albums/<NNN-slug>/`
(`album.md`, `tracks/*.md`, `thumbnail.png`, the video file to upload) and the channel's packaging rules in
`channel/<channel>/publish.md` (description template, default tags, title formats, emoji, pinned comment). This skill is
the procedure; every wording choice of the channel comes from `publish.md`. No `publish.md` → write one with the owner
first (template: `channel/_template/publish.md`).
**The PM's brief is binding** (CLAUDE.md §0): `plan.yaml` → `brief.decisions.title_direction` and `description_angle` (and
`production/<ch>/direction.md`) decide the title's voice and what ABOUT THIS VIDEO says; `publish.md` gives the fixed template
and limits. Brief and `publish.md` disagree → ask the PM, don't choose.
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
$PY $P tags --expand "<seed>, <seed>"                      # what people type after each seed (tag candidates)
$PY $P tags     <album> --trends                           # verify the ## Tags block: typed? search volume? reference channel name?
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
3. **Research tags** (`publish.py tags --expand`, section Tags) before writing them, then **write `youtube.md`** from
   `templates/youtube.md`, following the formats below, and verify with `publish.py tags <album>`.
4. **Check.** `publish.py check --video <video>`. Fix every ❌. A remaining placeholder is fine only if the user
   still has to choose (e.g. chapters A or B); say what they must paste.
5. **Walk the Studio screens** with `references/studio.md` when the user uploads. They send screenshots and ask
   "chọn gì": answer per that file. Verify policy questions against the live YouTube Help page (WebFetch) when
   they could have changed.
6. **After upload:** fill Video URL + date in `youtube.md`, set status in `album.md`, add the pinned comment, and after 48 h / 7 days note retention at 0:15 / 0:30 / 1:00 in the
   Analytics table (CLAUDE.md). Translated titles + descriptions: skill youtube-translate (needs the Video URL).

## Title

Format, examples, genre phrases and emoji: `channel/<ch>/publish.md` → *Title* (album and single). Rules for every channel:

- **Follow the channel's title formula** (`publish.md` → Title) and the PM's `title_direction`; it decides whether the title leads
  with the song name or with a hook line, and whether `| Full Album` is used.
- **≤ 70 chars** (`check` refuses more; YouTube allows 100 but cuts search results and mobile at ~60–70, and vidIQ
  warns). Count with `len()` in Python, emoji included. Still say the whole idea: song name + genre + use-case.
  When too long, cut in this order and stop as soon as it fits:
  1. filler words: "a", "the", "and", "your" ("for a Hard Season" → "for Hard Seasons");
  2. the second use-case / feeling (`& <Feeling>`);
  3. `| <Channel>` on singles (the channel name is shown under every title anyway);
  4. a shorter genre phrase (drop a modifier; keep one of the phrases `publish.py tags` found typed; examples in `publish.md`).
  Never cut the part the channel formula leads with. Prefer a genre/use-case phrase people actually type (check it with
  `publish.py tags --try "<phrase>"`).
- One emoji at most, from the channel's palette. No `<` or `>` (YouTube refuses them).
- Only claim a length that is true: no "1 Hour" for a 50-minute album. English only (CLAUDE.md).
- Give 1 recommendation + 2 alternatives, all ≤ 70 with their length. Start from `idea.yaml packaging.video_title_candidates` when present
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

`publish.md` → *Tags YouTube mặc định* (always all of them) + **5–12 album tags**, none duplicating a default, from the
buckets of `publish.md` → *Tags: các nhóm* (album / title track name, use-cases, theme, subgenre, lead instrument, format).
Total ≤ 500 chars **as YouTube counts**: commas count, and every tag containing a space counts 2 extra (quotes).
`check` computes it. Lowercase is fine.

**Research before choosing; never write a tag because it sounds right.** A good tag is a phrase people actually type
*and* whose searchers want this kind of music. Tags weigh little in ranking (YouTube says so), so a short list of real
phrases beats a long list of made-up ones; vidIQ scores made-up phrases low.

1. **Find candidates:** `publish.py tags --expand "<seed>, <seed>"` with 4–8 seeds from the album (genre, subgenre,
   theme, use-case, lead instrument, and open stems like "<genre> songs for", "songs about <theme>"). It
   prints what YouTube autocomplete (US) suggests after each seed = phrases people type, most typed first.
2. **Pick per bucket** from those suggestions, preferring the exact typed form (plural, word order, the full phrase as
   autocomplete shows it; not a shortened or singular variant).
3. **Measure volume:** `publish.py tags [<album>] --try "<candidates>" --trends [--channel <ch>]` adds a Google Trends column (YouTube Search,
   5 years, free, scaled to the channel's anchor term: `**Mốc Google Trends:**` line in `channel/<ch>/publish.md`). Typed is not enough: long story
   phrases (a genre + a specific story or theme) are typed but Trends < 1, and vidIQ scored them 0–32, while phrases
   with Trends ≥ ~4 scored 59–67 (checked on 11 tags, 2026-09-24; 10/11 agree). Keep tags with Trends ≥ 1, prefer the
   higher within a bucket; skip the huge generic ones (Trends in the thousands: too much competition, and the channel
   defaults already cover the genre). Autocomplete alone does not measure volume, and
   neither do view counts of the top search results (tried: a song nobody searches returns videos with tens of millions of views).
4. **Verify the list:** write it into `youtube.md`, then `publish.py tags <album> --trends`. Per tag: ✅ typed · ⚠️ only a longer /
   plural form is typed (use that form), the phrase leads elsewhere, or Trends ≈ 0 · ❌ nothing typed, or it contains a reference
   channel's name (from `research/`). Song or album name is kept as an own name even if nobody searches it yet
   (one tag; vidIQ always scores it 0).
5. **Read the intent** (last column; the script cannot): drop a ✅ tag whose searchers want something else — beats / type beats,
   instrumentals, podcasts or ministries, other artists' songs, another country's language, readings or liturgy
   instead of music. Also drop suggestions that are a reference channel or its titles (`copy_guard`; the script marks
   channel names). Intent traps already found for a channel live in `publish.md` → *Tags: các nhóm*; add new ones there.
6. **Table in youtube.md:** `| Tag | Nhóm | Trends |`, the last column the script's number (or "tên riêng").
   `check` warns while the table has no Trends / autocomplete column.

If the owner has YouTube Studio → Analytics → **Research** (search volume + content gaps), vidIQ Keywords, or search
terms from an earlier video (Analytics → Traffic source → YouTube search), prefer those numbers; autocomplete only tells
*typed or not*, not how much. The same method applies to the channel defaults in `publish.md` and the channel keywords
(Studio → Settings → Channel): re-run `publish.py tags --try "<defaults>"` when they are revised.

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
- **Title**: the single format in `publish.md` → *Title*, ≤ 70 chars like the album. Song title first, exactly as in the track file. Never
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
- **Tags**: channel defaults + 5–12 song tags (buckets for singles in `publish.md`), researched as in Tags above; the song
  name and hook go in even if nobody types them yet.
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
