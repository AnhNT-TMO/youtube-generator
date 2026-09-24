---
name: youtube-translate
description: Translate ONLY the title of videos already on YouTube into the channel's target languages and write them through the YouTube Data API as video localizations (viewers whose YouTube is set to that language see the translated title; everyone else keeps the original). Never touches the original title, description, tags, thumbnail or anything else. Languages, words kept verbatim and the per-language genre glossary come from channel/<ch>/translate.yaml; Claude writes the translations into <dir>/title-translations.yaml, the script checks them (≤ 100 chars, kept words, emoji, stale source) and pushes only after a dry run. Use when the user says "dịch title", "dịch tiêu đề", "translate title", "title nhiều ngôn ngữ", "localize video", "thêm bản dịch tiêu đề", "video nào chưa dịch", or after a video is uploaded and its Video URL is in youtube.md. Does NOT write the English title (youtube-publish), translate descriptions or add subtitles.
---

# YouTube translate (title only)

Runs **after upload** (the video must exist on YouTube; CLAUDE.md step 8). Generic skill: every channel-specific choice
(which languages, which words never change, how the genre is said in each language) lives in
`channel/<ch>/translate.yaml`. Output: `<dir>/title-translations.yaml` (the record of what was written) + the titles on YouTube.

```bash
SK=.claude/skills/youtube-translate; PY=$SK/.venv/bin/python; T=$SK/scripts/yt_translate.py   # repo root, runs on the Mac
# first run: python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt
$PY $T auth  --channel <ch>                  # once per channel (browser login); fills channel_id in translate.yaml
$PY $T list  --channel <ch>                  # every upload: languages present / missing, repo folder
$PY $T pull  <dir>... | <video-id> --channel <ch>    # live title → title-translations.yaml with empty slots
$PY $T apply <dir>...                        # checks + shows what would change (dry run, writes nothing)
$PY $T apply <dir>... --yes                  # writes, then reads back every language
$PY $T pull  --missing --channel <ch>        # instead of <dir>: every upload still missing a language
$PY $T apply --missing --channel <ch> --yes
```

`<dir>` = `channel/<ch>/albums/NNN-slug` or `singles/NNN-slug`; the video id comes from the `Video URL` line of its
`youtube.md`. A video not in the repo: pass its id/URL + `--channel`; its file goes to `channel/<ch>/translations/<id>.yaml`.
Several targets in one call = one batch.

## Steps

1. **Target.** Default = `--missing --channel <ch>`: every upload of the channel still missing a language (the owner wants
   every video translated). "Dịch title video X" → its folder. A video on YouTube whose folder's `youtube.md` has no
   Video URL → fill it in (`list` shows the ids + titles; match by title) so `keep` gets the song title.
2. **Pull.** `pull --missing --channel <ch>` (or `pull <dir>`). It records the live title (the truth, not `youtube.md`), the video's default language, what is
   already on YouTube, and `keep` (song title + channel name when they appear in the title).
3. **Translate** (Claude, directly into `titles:` of the yaml), following **How to translate** below. Read
   `translate.yaml` `glossary` first and reuse its terms; add a term there when you choose a new one.
4. **Dry run.** `apply` without `--yes`. Fix every ❌ (usually > 100 chars: shorten, don't drop meaning).
5. **Write** without asking (owner 2026-09-24: "bỏ qua bước xác nhận, video nào tôi cũng muốn dịch"): `apply … --yes`.
   It re-reads until YouTube shows the new titles (the first read right after an update can be stale), checks the
   original title/description/tags did not move, and reads each language with `hl=<code>`.
6. **Tell the owner** what was written: one table video · language · title · Vietnamese gloss. Where to see it: Studio →
   Subtitles → Title & description column. The yaml is the record.

- **Never send a partial `localizations`**: `videos.update part=localizations` REPLACES the whole set, so a request with
  one language deletes all the others (happened once while debugging, 2026-09-24). Only go through `apply`, which
  merges with what is live (including the `en` entry YouTube creates for the default language).
- Translated entries have an empty description on purpose. The API then returns `snippet.localized.description` empty
  for that `hl`, but the watch page shows the original English description (measured 2026-09-24, watch page `hl=ko`):
  do not copy the description in.

The English title changes later (A/B test, fixing a typo) → translations are stale: `pull` moves them to `old_titles`,
translate again, `apply`. `apply` refuses a file whose `source_title` is not the live title.

## How to translate

Same title, other language: same facts, same order, nothing added. The goal is that a viewer in that language
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

## translate.yaml (per channel)

```yaml
channel_id:            # UC…; filled by `auth`; the script refuses to write to any other channel
source_language: en    # set as the video's defaultLanguage when it has none (YouTube requires one for localizations)
keep_song_title: true  # song title (Track 01 of an album, the track of a single) stays in the source language
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

Quota: 10,000 units/day free. Per video ≈ 1 (read) + 50 (update) + 1 per language (read-back) ≈ 60 → ~150 videos/day.
`quotaExceeded` → continue tomorrow (resets at midnight Pacific).

## Principles

- **Title only.** Original title, description, tags, category, thumbnail are sent back unchanged or not at all; the
  read-back fails loudly if any of them moved. Other languages already on the video (e.g. entered by hand in Studio)
  are kept.
- **The live video is the truth**: translate the title YouTube has now, not the draft in `youtube.md`.
- **Inspired, not copied** (CLAUDE.md) applies to translations too: no phrasing lifted from reference channels'
  localized titles.
- **Why not leave it to YouTube:** YouTube machine-translates some titles for some viewers (undocumented, tested since
  2021, often clumsy) and viewers can turn it off; a creator's localization is what YouTube serves for that UI language
  (`snippet.localized`). Which one wins when both exist is not documented: the read-back shows what `hl=<code>` gets.
