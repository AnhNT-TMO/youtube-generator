---
name: youtube-trend-research
description: R&D department - watch a channel's YouTube niche and report which trends are rising, holding or fading, so the production manager can decide what to make next. Daily cheap pulse (watchlist channels, views gained per day between snapshots, our own channel's views/subs), discovery of new channels a few times a week (search), a topic + music-branch table (hits, fresh channels, recent hits, share of niche views, status vs a week ago), then a deep dive on the chosen topic (outlier videos to measure with youtube-music-analyzer, top comments = what viewers pray/ask for, a thumbnail contact sheet), a weekly thumbnail-trend table (sheets of each branch's hits vs flops, labelled by Claude: subject, setting, text role, lettering, palette, props → which patterns win, which are saturated) and a Shorts scan (Shorts-first channels too; the niche's most-watched Shorts by format and topic + a sheet of their vertical frames); every report ends with thumbnail and Shorts ideas the production team can make. Writes research/trends/<ch>/reports/YYYY-MM-DD.md + state.md (the living summary the PM reads) and research/trends/new-channels.md (trends outside the channel contract). Uses the YouTube Data API v3 with an API key, no login. Use when the PM or the owner asks for "research trend", "quét trend", "R&D", "trend hôm nay", "trend nào đang lên", "có nên đổi trend", "chủ đề nào đang nổ", "kênh mới trong niche", "pulse", "Shorts trong ngách", "thumbnail đang thắng", "ý tưởng thumbnail", "ý tưởng Shorts", or before planning a new idea.
---

# YouTube trend research (R&D)

**Goal:** tell the PM, in one short report, *what the niche is watching now* and *what that means for us*: keep the
current topic, switch, or test something. R&D reports; the PM decides (CLAUDE.md §0). Trend research only sees public
numbers (views, likes, comments, titles, thumbnails), never CTR or retention: it gives hypotheses, our own channel's
results decide.

```bash
SK=.claude/skills/youtube-trend-research
T() { $SK/.venv/bin/python $SK/scripts/trend.py "$@"; }      # bash $SK/scripts/setup.sh once
T pulse    --channel <ch>                                    # daily: snapshot watchlist + own channel (~2 units / channel)
T topics   --channel <ch>                                    # table: topics + music branches + own channel
T discover --channel <ch> [--max-queries N]                  # 2-3x / week: search → new channels into the watchlist
T prune    --channel <ch>                                    # re-check the watchlist against trends.yaml (no API)
T refs     --channel <ch> --topic <topic> [<branch>] --n 5   # outlier videos to measure (1 per channel)
T comments --channel <ch> --video <id> [<id>…]               # top comments (1 unit / video)
T sheet    --channel <ch> --video=<id>,<id>… --name <topic>  # thumbnail contact sheet (Claude looks at it; ids may start with '-')
T shorts   --channel <ch> [--days N] [--top N] [--per-channel N] [--fetch]   # niche's top Shorts + formats + vertical-frame sheet (§4)
T discover --channel <ch> --shorts                           # Shorts-first channels into the watchlist (§4)
T thumbs   --channel <ch> [--n 6] [--min-x 3] [--topic …]    # thumbnail sheets per branch + label file (§5); then --summarize
```

Config (channel content, in git): `channel/<ch>/trends.yaml` — language, own channel id, window, discovery queries,
niche filter (core keywords, exclude words, other-language share, max subs), `topics` (story / prayer themes) and
`branches` (music branches). Template: `channel/_template/trends.yaml`. API key: `~/.config/yt-research/api_key`
(chmod 600) or `YT_API_KEY`; never print it or write it anywhere else.

Data (only on this machine): `research/trends/<ch>/` — `watchlist.json`, `candidates.json` (channels already checked,
skipped for 30 days), `snapshots/`, `discover/`, `topics/<date>.json|md`, `comments/`, `sheets/`, `shorts/`, `reports/`, `state.md`,
`units.log`. Company-wide: `research/trends/new-channels.md`.

## 1. Quota (10 000 units / day, resets midnight Pacific)

| Job | Units | When |
|---|---|---|
| `pulse` | ~2 per watchlist channel (150 channels ≈ 300) | daily |
| `discover` | 100 per query + ~2 per new candidate channel (16 queries ≈ 1 600–2 500) | 2–3x / week, or when pulse shows nothing new for days |
| `comments` | 1 per video | deep dive |
| `refs`, `topics`, `prune`, `sheet` | 0 | any time |
| `shorts` | 0 on the latest snapshot (≤ 2 days old); otherwise it runs `pulse` first | weekly, before a Short's image |

`units.log` sums the day; stop discovery when the day passes ~7 000 (other sessions share the key).

## 2. Daily run (what the PM orders)

1. `pulse`, then `topics`. The first snapshot has no views-per-day (`vel`): tables use `median vpd` (views per day since
   upload) until a second snapshot ≥ 0.7 day later exists; status vs a week ago needs a table ≥ 6 days old.
2. Read `topics/<date>.md` and compare with `state.md`. Look for:
   - **Rising / fading:** `status` (share of the niche's daily views vs a week ago: ≥ +20 % rising, ≤ −20 % fading).
     Before a week of data: `hits now` (hits uploaded ≤ 14 days ago) vs `old hits only` (the topic peaked).
   - **Fresh channels winning** (`fresh` = hits of channels created ≤ 120 days ago): the clearest sign a door is open to
     a new channel like ours.
   - **Unlabeled hits:** name them; a new theme → add a topic with its keywords to `trends.yaml`.
   - **Our channel:** views and views/day of our recent videos, subs.
3. Classify each finding (CLAUDE.md §0 "Xếp một trend"): topic → album idea; music branch inside the channel contract
   → album experiment; presentation (title, thumbnail, Shorts, length) → packaging version; outside the contract
   (language, other genre) → `research/trends/new-channels.md` with evidence.
4. Write `reports/<date>.md` (template `references/report-template.md`) and update `state.md`. Keep both short; the PM
   reads them, not the tables.

Only when something changed or the PM needs a new idea: the deep dive (§3). A quiet day is a two-line report.

## 3. Deep dive on one topic (before an idea)

1. `refs --topic <topic> [<branch>]` → 3–5 outlier videos, one per channel, recent and still gaining. Prefer ones in our
   music branch (so the measured frame fits the channel); drop videos over ~2.5 h (server time) and live streams.
2. Measure their music on the GPU server with **youtube-music-analyzer** (6 criteria per video, then `refset.py` → one
   reference set = medians). R&D hands the PM the set path; the idea is written from it (analyzer SKILL.md §6).
3. `comments` on the 2–3 strongest: what people write (who they pray for, what they are going through, where they
   listen: night shift, hospital, grieving). This is the richest source of *our own* story angles and thumbnail/title
   phrases, and it never copies a competitor's title. Summarise needs, never quote a commenter in our content.
4. `sheet` of the refs + the topic's top videos → look at it: layout, text, faces or no faces, palette. Write what the
   niche expects vs what nobody does yet (for the packaging version), and their marks for `copy_guard.visual/branding`.

## 4. Shorts scan (weekly, and before writing a Short's image prompt)

`shorts` reads the latest pulse snapshot (last 50 uploads per watchlist channel + our own channel). A Short = ≤ 180 s
(`shorts.max_seconds`) and `youtube.com/shorts/<id>` answers 200 (a redirect to `/watch` = a normal video); the answer
is cached in `shorts/is_short.json`, a failed check keeps the video as `?` (length only). It writes:

- `shorts/<date>.md` + `.json`: top N niche Shorts published ≤ `days` ago, ranked by views/day since upload (max
  `per_channel` per channel), with views, likes, comments, length, age, link; per channel: Shorts in window, Shorts/week,
  median views/day of its Shorts vs its normal videos; our own Shorts separately.
- `shorts/<date>-sheet.jpg`: the top N portrait frames (`oar2.jpg`, `(hq)` = cropped from the 4:3 thumbnail), same
  order, labelled rank · views/day · length.

Optional `shorts:` block in `trends.yaml` (`days` default `window_days`, `top` 20, `per_channel` 3, `max_seconds` 180).

Shorts-first channels (no long videos, titles without genre words) are missed by the long-video niche filter:
`discover --shorts` searches `shorts.discover_queries` (videoDuration=short) and admits a channel by `shorts.niche_keywords`
+ `shorts.music_keywords` (≥ 20 % of titles: a music channel, not sermons/tarot/motivation, `shorts.exclude_extra`); the
watchlist entry is `kind: shorts` and `prune` keeps checking it that way. Run it with the weekly scan.

The report also has **Loại Short** (`shorts.formats`, title keywords: lyric card, prayer/blessing, testimony, classic hymn,
scripture, live/choir, night comfort) and **Chủ đề trên Shorts** (`topics`), with hits measured against the channel's
own Shorts median (a Shorts channel's normal level is not a long-video channel's).

Then look at the sheet and write below the table, in 3–6 bullets, what the Shorts people watch most share: framing
(close face / half body / scene / lyric card), subject, text on the image (yes/no, how many words, where, style),
palette + light, motion or format hinted by titles and length; which channels win with Shorts vs only long videos; and
their marks (text, logo, characters) for the copy guard. The Shorts pipeline takes composition ideas from this,
never a copy of one frame. Off-contract Shorts (language, genre) are noise here and a hint for `new-channels.md`.

**Shorts ideas for the production team** (report section *Ý tưởng Shorts*, 2–4 ideas, the PM picks): each idea =
format (from the tables + sheet) · topic · which of our songs / which part (chorus, bridge, first line; album + slot or a
library id) · the hook line's angle (0–3 s) · the picture pattern · the `version` name for `short.md` · and whether
youtube-shorts can make it today (**yes** / **needs**: what is missing, e.g. a non-chorus segment, text-only cards, a
second voice). Ideas that need a new capability go to the PM as a proposal, never silently into production.

## 5. Thumbnail trends (weekly, and in every deep dive)

Titles say *what* wins; thumbnails say *how it is shown*. `thumbs` takes, per music branch (or `--topic`), the 6 strongest
recent hits (≤ 30 days, x ≥ `--min-x`, one per channel, a video only in its first group) and 2 flops of the same channels
(x < 0.5): same channel, same template, different result is the control. It writes one sheet per group
(`sheets/<date>-thumbs-<group>.jpg`) and `thumbs/<date>.yaml` with empty labels. Look at every sheet and fill each video's
labels (the allowed values are in the file's header): subject, setting, text words, text style, text role (plea, promise
/ benefit, nostalgia, song list, none), palette, props, mood. Then `thumbs --summarize` → `thumbs/<date>.md`: for every
value its share among hits vs flops. Read it this way:
- a value common in **both** hits and flops = entry ticket or saturated (e.g. one lettering style everybody uses);
- a value found in hits and **not** in flops = a candidate ingredient; with < 5 hits carrying it, say "weak";
- compare with the previous week's table: patterns spreading to many channels are closing, patterns only a few new
  channels use are opening.

**Thumbnail ideas for the production team** (report section *Ý tưởng thumbnail*, 3–5 concepts, the PM puts one into each
idea's `packaging.thumbnail_brief` or a packaging version): each = scene · subject (person / objects / scene) · text role +
roughly how many words · palette + light · which winning ingredient it takes · **how it differs from the niche's saturated
pattern and from our last 3 albums** (`thumbnail-prompt/scripts/thumb.py list channel/<ch>`). Every concept stays inside the
channel contract and its visual world (`channel.md`, `visual.md`); take an ingredient (a home at night, objects without
a person, a promise line), never another channel's layout.

## 6. Rules

- **Report, don't decide.** Recommend with the numbers; the PM chooses the topic, the CEO a new channel.
- **Inspired, not copied** (CLAUDE.md §1): their titles, thumbnail text, channel names go into copy guards, not into ideas.
  Many niche channels copy each other's titles; don't join them.
- **A hit is mostly luck + topic** (within one channel, the same template gets 5 or 5 000 views/day): judge a topic by many
  videos and channels (`videos`, `channels`, `hit_rate`, `share`), never by one viral video.
- **Creativity first** (CLAUDE.md §6): trends are ingredients (a topic, what viewers need, a pattern that wins), not a
  template. Every idea and concept R&D hands over must be clearly different from the last ones of our channel while
  keeping its vibe; a niche where every channel looks the same is exactly where a different picture stands out.
- **Late is worthless:** a topic whose hits are all old (`old hits only`, `fading`) is not a trend to enter.
- Keep `trends.yaml` inside the channel contract (`channel.md` → *Hợp đồng kênh*); the niche filter keeps other
  languages and label-size artists out of the watchlist.

## Files

| File | What |
|---|---|
| `scripts/trend.py` | all commands (stdlib + PyYAML + Pillow) |
| `references/method.md` | the numbers: definitions, why each exists, known blind spots |
| `references/report-template.md` | daily report + `state.md` layout (incl. Shorts + thumbnail ideas) |
