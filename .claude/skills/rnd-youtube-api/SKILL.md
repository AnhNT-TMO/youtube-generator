---
name: rnd-youtube-api
description: R&D guide + small CLI for the YouTube Data API v3 (API key, no login) to search and understand channels and videos - find the channels of a niche, a channel's overview (subs, created date, uploads playlist, video count), its videos ranked by views per day, the fast-growing videos across a list of channels (views/day against that channel's own median, so an old video with a big total does not count as fast), one video's details, top comments, thumbnails from i.ytimg.com (no quota) tiled into a contact sheet so Claude can read the text on them, Shorts vs long videos; plus the phrase bank in research/phrase-bank/ (title + thumbnail text of fast-growing niche videos that our titles and thumbnail text draw on - common prayer phrases may be used verbatim, other channels' names/branding never) - list, mark as used, add new entries. The PM and the CEO research a topic together; this skill is how to get the data, it decides nothing. Use when asked "tìm kênh", "kênh nào trong ngách", "phân tích kênh", "kênh này thế nào", "video nào đang lên nhanh", "view/ngày", "lấy title thumbnail", "đọc chữ trên thumbnail", "kho câu", "thêm vào kho câu", "câu nào chưa dùng", "comment của video", "Shorts của kênh", "research youtube", "quét youtube".
---

# YouTube Data API for R&D

A basic guide + `scripts/yt.py`. R&D is the PM and the CEO working on a topic; this skill fetches the numbers, pictures
and words, they decide. The API only shows public data (views, likes, comments, titles, tags, descriptions, durations,
dates, thumbnails): never CTR, impressions, retention or traffic sources of another channel.

```bash
SK=.claude/skills/rnd-youtube-api
bash $SK/scripts/setup.sh                        # once: .venv with PyYAML + Pillow
Y() { $SK/.venv/bin/python $SK/scripts/yt.py "$@"; }
```

API key: `~/.config/yt-research/api_key` (chmod 600) or `YT_API_KEY`. Never print, echo or copy the key anywhere
(logs, JSON, notes, commands shown to the user).

## Quota: 10 000 units / day per key, reset at midnight Pacific, shared by every session

| API call | Units |
|---|---|
| `search.list` (≤ 50 results) | **100** |
| `channels.list`, `videos.list` (≤ 50 ids per call) | 1 per call |
| `channels.list forHandle=@x` (@handle → id) | 1 per handle |
| `playlistItems.list` (a channel's uploads, 50 per page) | 1 per page |
| `commentThreads.list` (100 per page) | 1 per page |
| thumbnails `i.ytimg.com/vi/<id>/…` | 0 (not the API) |

Per command: `search` ≈ 102 · `channel` 1 (+1 per @handle) · `videos` / `fast` ≈ 2 per channel per 50 uploads (+1 when a
`--kind` playlist is missing) · `video` 1 per 50 · `comments` 1 per video · `sheet`, `bank` 0. Every run appends
`<Pacific date> <time> <command> <units>` to `research/yt/units.log` and prints the day's total; `yt.py` refuses a call
that would pass 9 000 logged units in a day. A call made outside `yt.py` (curl) → add its line to the log by hand.
One search costs as much as scanning 50 channels: keep the niche's channel ids in a text file and reuse it.

## Commands

```bash
Y search "<words>" [--days 30] [--duration any|short|medium|long] [--order viewCount|date|relevance] [--lang en]
Y channel <ref>…                              # ref = UC… id, @handle or channel URL
Y videos <ref>… [--n 50] [--kind all|long|short|live] [--sort vpd|x|views|date] [--top 50]
Y fast [<ref>…] [--file F]… [--days 30] [--kind long|short|all] [--min-x 2] [--per-channel 3] [--top 30] [--name N]
Y video <id|url>…
Y comments <id|url>… [--show 20]
Y sheet [<id>…] [--from <json|yaml>] [--top 6] [--vertical] [--name N]
Y bank list [--unused] [--todo] [--theme T]
Y bank use <id> --by channel/<ch>/albums/NNN-slug
Y bank add --from research/yt/fast/<date>-<name>.json [<id>…] [--top N]
```

Every command takes `--json` (result as JSON on stdout; data files are saved anyway). Video ids that start with `-`
go after `--`: `Y sheet --name x -- -AbC12xyz_Q Xy12AbCdEfG`.

## Numbers

- `vpd` = views ÷ days since upload (under 1 day counts as 1).
- `vpd_x` = vpd ÷ the median vpd of the same channel's scanned uploads of the same kind (long or Short; needs ≥ 5 of
  them, else `x-`). It removes channel size: 200/d on a channel whose median is 20/d (x10) beats 2 000/d on a channel
  whose median is 3 000/d.
- **Fast ≠ many views.** An old video with a big total and a low vpd is a past hit. Fast = a recent upload (`--days`)
  with a high vpd and vpd_x ≥ 2. vpd falls as a video ages, so new uploads always sit a bit above the median: compare
  videos of similar age and treat an upload under ~3 days as a hint.
- Subscriber counts are rounded by YouTube; `created` = the channel's creation date (young channels that win = the door
  is still open).
- One video that explodes is mostly luck: judge a pattern by several videos and channels.

## Recipes

1. **Channels of a niche** (one search): `Y search "<niche words>" --days 30 --duration long` → the most-viewed recent
   videos (sorted by vpd) and a table of their channels (subs, created, results, best vpd), saved in
   `research/yt/search/<date>-<slug>.json`. Then `Y fast --file research/yt/search/<date>-<slug>.json`.
   `--duration`: short < 4 min, medium 4–20, long > 20.
2. **Channel overview:** `Y channel @handle` → title, handle, subs, total views, video count, created + age, country,
   uploads playlist (`UU…`), description → `research/yt/channels/<id>.json`.
3. **A channel's videos by views/day:** `Y videos @handle [--n 100]` → the last N uploads by vpd with vpd_x, duration,
   kind; median vpd per kind in the header. Each run saves a dated snapshot `research/yt/videos/<channel_id>/<date>[-kind].json`;
   two snapshots of the same channel give the views gained in between.
4. **Fast-growing videos across channels:** `Y fast <ref>…` or `--file <any file>` (every `UC…` id in it is used: a
   search JSON, a txt list, an old watchlist) → uploads of the last `--days` with vpd_x ≥ `--min-x`, at most
   `--per-channel` per channel, sorted by vpd (`--sort x` = most above their own channel) →
   `research/yt/fast/<date>-<name>.json`, the input of `sheet --from` and `bank add --from`.
5. **One video:** `Y video <url>` → title, channel, date + age, duration + kind, views / likes / comments, vpd, tags,
   description (full text in `research/yt/video/<id>.json`), thumbnail URL.
6. **Top comments:** `Y comments <id>` → 100 top-level comments by relevance (likes, replies, text) in
   `research/yt/comments/<id>.json`. They tell what listeners are going through and pray for: story angles. Summarise
   needs; never quote a commenter in our content.
7. **Thumbnails + contact sheet (0 units):** `Y sheet --from research/yt/fast/<file>.json [--top 6]` or `Y sheet <id>…`
   → `research/yt/sheets/<date>-<name>.jpg`: 2 columns of 640×360 tiles labelled `#n id vpd x`, legend printed in the
   same order. **Read the sheet image** and write down the text you see. A line too small → Read the original
   `research/yt/thumbs/<id>.jpg` (maxresdefault 1280×720, else sddefault / hqdefault). Direct URL:
   `https://i.ytimg.com/vi/<id>/maxresdefault.jpg`. The thumbnail text is often not the title: record both.
8. **Shorts vs long:** kind by duration: ≤ 180 s = `short` (Shorts can run 3 min), `live` = live / upcoming, the rest
   `long`. With `--kind short|long`, `videos` and `fast` read the channel's own Shorts / long-video playlist (uploads id
   with `UU` → `UUSH` / `UULF`; undocumented, worked 2026-09-28), so the kind is exact and 50 Shorts really are 50
   Shorts; a channel without that playlist falls back to all uploads, kind by duration. `sheet --vertical` tiles the
   Shorts' 9:16 frames (`oar2.jpg`). A short horizontal upload is still a normal video: `youtube.com/shorts/<id>`
   answering 200 (not a redirect to `/watch`) confirms a Short.

Other endpoints (not wrapped): https://developers.google.com/youtube/v3/docs — e.g. `search.list channelId=<id>
order=date` (one channel's uploads by keyword, 100 units), `playlists.list channelId=<id>` (1), `videos.list
part=topicDetails,localizations` (1). Call them with `curl -s "https://www.googleapis.com/youtube/v3/<endpoint>?…&key=$(cat
~/.config/yt-research/api_key)"` and log the units.

## Phrase bank

`research/phrase-bank/<niche>.yaml` (machine) + `<niche>.md` (readable), local only, one bank per niche. `yt.py bank`
uses `--bank <file>`, else `YT_PHRASE_BANK`, else the only `*.yaml` in `research/phrase-bank/`. YAML top level:
`updated`, `source_note`, `channels` (list), `entries` (list); `yt.py` reads and appends only `entries` and writes the
other keys (and leading `#` comment lines) back untouched. One entry per video, `id` = the 11-character video id:

| Field | Value |
|---|---|
| `id`, `url` | YouTube video id, watch URL |
| `channel`, `channel_id` | the source channel |
| `published`, `age_days` | upload date; age when measured |
| `views`, `vpd`, `vpd_x` | when measured: views, views/day since upload, vpd ÷ that channel's median vpd |
| `duration_min` | length in minutes |
| `title` | the title as published |
| `thumb_text` | the exact lines on the thumbnail, top to bottom, joined by ` / ` (read by Claude on the sheet) |
| `addressee` | Lord / Jesus / God / Father / none; also Yahweh / Yeshua / Abba / Holy Spirit when the video calls on them |
| `theme` | list: storm, burden, healing, protection, … (`bank list --theme T` matches any item) |
| `pattern` | plea / praise / promise / testimony / command |
| `fresh` | optional: `true` when the video was ≤ 30 days old when measured (`bank add` fills it from `age_days`) |
| `branch` | optional: the source channel's branch (gospel_blues, worship_prayer, …); `bank add` leaves it empty |
| `used_by` | our album dirs that used it (`[]` = unused) |

**Rule (CEO 2026-09-28):** these prayer phrases are common, owned by nobody (like Scripture). Verbatim is allowed for
common prayer phrases / classic quotes, even when many channels copied them; prefer phrases still growing (`fresh`,
high `vpd_x`). Other channels' names, logos, branding and images: never. Record the entry id in `album.md` →
`brief.phrase_bank`.

Using it: `Y bank list --unused [--theme storm]` (best vpd_x first) → the PM picks (as it is or reworded); the line goes
into `album.md` → `brief` (`title_direction` / `thumbnail_text`, the entry id in `phrase_bank`) → right after
`album.py build`: `Y bank use <id> --by channel/<ch>/albums/NNN-slug` (appends to `used_by`, never twice;
upload-youtube-publish `publish.py check` warns while it is missing).

Growing it (R&D, whenever the niche is scanned):
1. `Y fast --file <niche channel ids> --name <niche>` → fast long videos of the last 30 days.
2. `Y bank add --from research/yt/fast/<date>-<niche>.json [--top N]` → adds only ids not in the bank yet (an id is never
   duplicated), numbers + `fresh` filled, `thumb_text` / `addressee` / `theme` / `pattern` / `branch` empty; prints the
   `sheet` command for the new ids.
3. Run that `sheet` command and Read the sheet (originals where a line is small).
4. Edit the YAML: fill `thumb_text` (exact lines, in the form the bank already uses), `addressee`, `theme`, `pattern`,
   `branch` (from the bank's `channels` list).
   Drop an entry only when neither its title nor its thumbnail carries a phrase (both are just a genre label or a
   channel name); a phrase on one of the two is enough to keep it. `Y bank list --todo` lists
   what is still empty.
5. Bring `<niche>.md` in line with the YAML.

## Data (local only: `research/` is not in git)

`research/yt/`: `units.log`, `search/`, `channels/<id>.json`, `videos/<channel_id>/<date>[-kind].json`,
`fast/<date>-<name>.json`, `video/<id>.json`, `comments/<id>.json`, `thumbs/<id>[-v].jpg`, `sheets/<date>-<name>.jpg`.

## Rules

- **Facts, not decisions.** Hand over numbers, sheets and what was seen; the PM (with the CEO) decides.
- **Phrases yes, branding no** (CEO 2026-09-28): common prayer phrases in other channels' titles / thumbnails may become
  our text as they are; their channel names, logos, branding and images never.
- **Late is worthless:** a pattern whose fast videos are all old is closing; look at what grows now.
