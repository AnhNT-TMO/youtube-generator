# Method: the numbers of `trend.py`

| Name | Definition | Why |
|---|---|---|
| `vpd` | views / days since upload | available from the first snapshot; favours old videos that were big once |
| `vel` | views gained per day between the latest snapshot and one 0.7–8 days older (videos newer than the gap: views / age) | the real "is it still being watched *now*" |
| `x` | views / median views of the channel's last 50 uploads | removes channel size: a 2 000-view video on a 300-median channel is a hit (x 6.7) |
| hit | `x ≥ 3` | the video beat its own channel clearly |
| `recent` | hits uploaded ≤ 14 days ago | the topic still produces hits today |
| `fresh` | hits of channels created ≤ 120 days ago | new channels can still win with it (our situation) |
| `% vel` / `% vpd` | the topic's share of all niche views per day | share, not totals: the watchlist grows over time |
| `status` | `% vel` vs the table ≥ 6 days older: ≥ ×1.2 rising, ≤ ×0.8 fading, else steady; without history `hits now` / `old hits only` / `no hits` | the PM's keep-or-switch signal |

Scope: videos of watchlist channels, ≤ `window_days` old, ≥ `min_minutes` long, not live. Topics and branches are
keyword matches on the title (`trends.yaml`), so a video can be in several; the keywords are the weakest link — when
a hit lands in "unlabeled", fix the keywords rather than trusting the table.

## Blind spots

- No CTR, impressions, retention or traffic sources for other channels (YouTube never exposes them).
- Titles only: the song content, thumbnail text and the music itself need the deep dive (analyzer, sheet).
- Watchlist bias: only channels we found. Discovery searches by view count, so it finds winners, not the quiet majority —
  that is fine for "what works", wrong for "how often it works"; `hit_rate` inside watchlist channels corrects part of it.
- Search results change by region/language (`relevanceLanguage`); run discovery with the same queries to compare weeks.

## Lifecycle seen in a niche (2026-09 scan, why `recent` and `fresh` exist)

A template appears (one title formula + one thumbnail look), the first channels get 100k+ views within weeks, dozens of
channels copy it, and within ~2–3 months new uploads on the same template get a few hundred views while the early
videos keep their totals. Totals and `vpd` look healthy long after the door has closed; `vel`, `recent` and `fresh` show it.
