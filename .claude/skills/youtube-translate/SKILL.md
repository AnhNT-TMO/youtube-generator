---
name: youtube-translate
description: Translate the title and description of videos already on YouTube into the channel's target languages and write them through the YouTube Data API v3 as video localizations (viewers whose YouTube is set to that language see the translated title + description; everyone else keeps the original). Never touches the original title, description, tags, thumbnail or anything else. Languages, words kept verbatim, whether descriptions are translated and the per-language genre glossary come from channel/<ch>/translate.yaml; the description is translated line by line (chapters, hashtags, links and sung lyrics stay verbatim, lines already translated for an earlier video are pre-filled), Claude writes the translations into <dir>/title-translations.yaml, the script checks them (title ≤ 100 chars, description ≤ 5000 bytes and same line structure, kept words, emoji, stale source) and pushes only after a dry run. Use when the user says "dịch title", "dịch tiêu đề", "dịch description", "dịch mô tả", "translate title", "title nhiều ngôn ngữ", "localize video", "thêm bản dịch", "video nào chưa dịch", or after a video is uploaded and its Video URL is in youtube.md. Does NOT write the English title/description (youtube-publish), translate tags or add subtitles.
---

# YouTube translate (title + description)

Runs **after upload** (the video must exist on YouTube; CLAUDE.md step 8). Generic skill: every channel-specific choice
(which languages, which words never change, how the genre is said in each language) lives in
`channel/<ch>/translate.yaml`. Output: `<dir>/title-translations.yaml` (the record of what was written; the name predates
descriptions) + the titles and descriptions on YouTube. Descriptions only when `translate_description: true`.

```bash
SK=.claude/skills/youtube-translate; PY=$SK/.venv/bin/python; T=$SK/scripts/yt_translate.py   # repo root, runs on the Mac
# first run: python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt
$PY $T auth  --channel <ch>                  # once per channel (browser login); fills channel_id in translate.yaml
$PY $T list  --channel <ch>                  # every upload: title / description missing or stale per language, repo folder
$PY $T pull  <dir>... | <video-id> --channel <ch>    # live title + description → title-translations.yaml (empty slots, [[dịch]] lines)
$PY $T apply <dir>...                        # checks + shows what would change (dry run, writes nothing)
$PY $T apply <dir>... --yes                  # writes, then reads back every language
$PY $T pull  --missing --channel <ch>        # instead of <dir>: every upload missing a translation or with a stale one
$PY $T apply --missing --channel <ch> --yes
```

`<dir>` = `channel/<ch>/albums/NNN-slug` or `singles/NNN-slug`; the video id comes from the `Video URL` line of its
`youtube.md`. A video not in the repo: pass its id/URL + `--channel`; its file goes to `channel/<ch>/translations/<id>.yaml`.
Several targets in one call = one batch.

## Steps

1. **Target.** Default = `--missing --channel <ch>`: every upload of the channel missing a title or description in some
   language, or whose English title/description changed since it was translated (the owner wants every video translated). "Dịch title video X" → its folder. A video on YouTube whose folder's `youtube.md` has no
   Video URL → fill it in (`list` shows the ids + titles; match by title) so `keep` gets the song title.
2. **Pull.** `pull --missing --channel <ch>` (or `pull <dir>`). It records the live title and description (the truth,
   not `youtube.md`), the video's default language, what is already on YouTube, and `keep` (song title + channel name
   when they appear in the title). Per language, `descriptions:` gets a draft with the same lines as the original:
   lines kept verbatim are copied, lines translated before in any record of the channel (the fixed template of
   `publish.md`) are filled from that memory, every other line is `[[dịch]] <English line>`. Running `pull` again fills
   `[[dịch]]` lines that the memory learned since.
3. **Translate** (Claude, directly into `titles:` and `descriptions:` of the yaml), following **How to translate**
   below. Read `translate.yaml` `glossary` first and reuse its terms; add a term there when you choose a new one.
   Many videos × languages: translate the distinct `[[dịch]]` lines once per language (one sub-agent per language
   writing a line → translation JSON works), then fill every file; no two agents write the same yaml.
4. **Dry run.** `apply` without `--yes`. Fix every ❌ (title > 100 chars: shorten, don't drop meaning; description:
   line count, a kept line changed, `[[dịch]]` left, link changed, > 5000 bytes).
5. **Write** without asking (owner 2026-09-24: "bỏ qua bước xác nhận, video nào tôi cũng muốn dịch"): `apply … --yes`.
   It re-reads until YouTube shows the new titles (the first read right after an update can be stale), checks the
   original title/description/tags did not move, and reads each language with `hl=<code>`.
6. **Tell the owner** what was written: one table video · language · title · Vietnamese gloss. Where to see it: Studio →
   Subtitles → Title & description column. The yaml is the record.

- **Never send a partial `localizations`**: `videos.update part=localizations` REPLACES the whole set, so a request with
  one language deletes all the others (happened once while debugging, 2026-09-24). Only go through `apply`, which
  merges with what is live (including the `en` entry YouTube creates for the default language).
- A language with a title but no description (channel with `translate_description: false`): the API returns
  `snippet.localized.description` empty for that `hl`, but the watch page shows the original English description
  (measured 2026-09-24, watch page `hl=ko`). Never paste the English description into a localization.
- A localization needs a title: a description alone for a language with no title is refused.

The English title changes later (A/B test, fixing a typo) → translations are stale: `pull` moves them to `old_titles`,
translate again, `apply`. The English description changes (album link added to a single, typo) → `pull` rebuilds the
draft, unchanged lines keep their translation, changed lines become `[[dịch]]`. `apply` refuses a file whose
`source_title` / `source_description` is not the live one; `list` and `--missing` show these videos.

## How to translate

Same text, other language: same facts, same order, nothing added. The goal is that a viewer in that language
understands it at a glance and that it contains the words they would search.

- **Kept verbatim** (the check enforces `keep`): the song title (it is what they hear sung and what the chapters say),
  the channel name, and every word listed in `translate.yaml keep_verbatim`. Emoji stay, in the same place.
- **Translate** the rest: genre phrase, use-case, feeling, format ("Full Album", "Playlist"). Use the words native
  speakers really use for this music, not a word-for-word rendering: many languages use the English loanword
  (the channel's genre words) or its transliteration; the glossary records the choice so every video says it the same way.
- Keep the English separators and structure (`🕯️`, `|`, `&` may become the local "and"). No `<` `>`.
- ≤ 100 characters (hard limit); the translated keywords that matter in the first ~70.
- Never claim what the original does not (no "1 hour" if the original doesn't say it, no "lyrics" unless the original does).
- Capitalisation follows the language (title case is English; pt/es/fr capitalise less, de nouns only).
- Scripts: write the language's own script (ko Hangul, ja kana/kanji, hi Devanagari…), except words in `keep`.
- Claude is not a native speaker of every language: prefer plain, common phrasing over clever phrasing.

**Description** (line by line: translation line N = original line N; blank lines stay blank):
- Kept verbatim and checked: lines starting with a timestamp (chapters: YouTube builds chapters from them), lines of
  only hashtags, and, with `keep_lyrics: true`, every sung lyric line (from `## Lyrics` of the track files; the listener
  hears them in English). Every link stays identical in its line.
- Translate headers (`🎵 ABOUT THIS VIDEO`, `LYRICS`, `TRACKLIST`) and prose. Inside prose, song / album titles and
  quoted sung lines stay in English.
- ≤ 5000 bytes (UTF-8: Hangul / kana ≈ 3 bytes a character; a long single with lyrics can get close).
- The fixed template lines are translated once per language; the memory reuses the most common translation of a line,
  so correct a bad one in every record (or in the newest few) rather than in one video only.

## translate.yaml (per channel)

```yaml
channel_id:            # UC…; filled by `auth`; the script refuses to write to any other channel
source_language: en    # set as the video's defaultLanguage when it has none (YouTube requires one for localizations)
keep_song_title: true  # song title (Track 01 of an album, the track of a single) stays in the source language
translate_description: true   # also translate descriptions (line by line)
keep_lyrics: true      # sung lyric lines in the description stay in the source language
keep_verbatim: [<Channel Name>]
languages:             # order = priority; codes as YouTube Studio's translation language list uses them
  - code: pt-BR
    also: [pt]         # optional: the same translation also written under these codes
    name: Portuguese (Brazil)
    why: <one line + source>
glossary:              # per language, the terms chosen once and reused
  pt-BR: {<Genre Phrase>: <translation>, Full Album: Álbum Completo}
```

A new channel copies `channel/_template/translate.yaml` and chooses its own languages from where its music is
actually listened to. After a few weeks of real data, YouTube Analytics → Audience (top geographies, **viewer
languages**) beats any research: add or drop languages there and note the date + numbers in `why`.

## Setup (once, the owner in a browser)

1. Google Cloud Console → new project → **APIs & Services → Library → YouTube Data API v3 → Enable**.
2. **Google Auth Platform → Get started**: External, app name anything, own email. **Stay in "Testing"** (Publish needs
   a homepage + privacy policy on an owned domain, not worth it): **Audience → Test users → Add** the Google account that
   manages the channel (else login says "Access blocked"). Cost of Testing: the login expires every 7 days → the script
   says "chạy lại auth", one click in the browser. The "Google hasn't verified this app" screen is expected → continue.
3. **Clients → Create client → Desktop app** → download the JSON → save as
   `.claude/skills/youtube-translate/.cache/client_secret.json` (gitignored; one client serves every channel).
4. `auth --channel <ch>`: pick the Google account **and then the channel** (brand account) that owns the channel.
   The script checks the channel id; a wrong pick is refused and nothing is saved. Token: `.cache/tokens/<ch>.json`.

Quota: 10,000 units/day free. Per video ≈ 1 (read) + 50 (update) + 1 per language (read-back) ≈ 60 → ~150 videos/day
(one update writes title + description of every language).
`quotaExceeded` → continue tomorrow (resets at midnight Pacific).

## Principles

- **Localizations only.** Original title, description, tags, category, thumbnail are sent back unchanged or not at all;
  the read-back fails loudly if any of them moved. Other languages already on the video (e.g. entered by hand in Studio)
  are kept.
- **The live video is the truth**: translate the title YouTube has now, not the draft in `youtube.md`.
- **Inspired, not copied** (CLAUDE.md) applies to translations too: no phrasing lifted from reference channels'
  localized titles.
- **Why not leave it to YouTube:** YouTube machine-translates some titles for some viewers (undocumented, tested since
  2021, often clumsy) and viewers can turn it off; a creator's localization is what YouTube serves for that UI language
  (`snippet.localized`). Which one wins when both exist is not documented: the read-back shows what `hl=<code>` gets.
