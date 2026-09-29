---
album: <NNN-slug>
channel: <ch>
brief:
  source: <ceo|rnd>
  topic: "<topic / trend>"
  story: "<who, what they carry, what they ask God for>"
  phrase_bank: ["<bank entry id the title / thumbnail text adapts, if any>"]
  title_direction: "<title voice / the plea>"
  thumbnail_text: "<main text on the image>"
  bar_line: "<bottom bar line, e.g. 1 HOUR OF …>"
  thumbnail_concept: "<scene, framing, light, palette>"
  description_angle: "<what ABOUT THIS VIDEO says; only if the channel template has that slot>"
  short: {song: <slug>, why: "<why this song>"}
  version: "<packaging version being tested, one axis at a time>"
  experiment: null
  target: {views_48h: null, views_7d: null}
tracklist:
  - <song-slug>
  - <song-slug>
waivers: {}
---

# <Album working title>

Album = PM + CEO lên kế hoạch trực tiếp (không có plan.yaml). PM chọn bài từ kho `channel/<ch>/songs/` theo
`channel/<ch>/album_rules.md`, ghi `tracklist` (thứ tự = thứ tự phát), rồi `album.py check` → `album.py build`
(sinh `tracks/NN-<slug>.md` cho audio-album-assembly và upload-youtube-publish). Short của album nằm trong thư mục này,
`short/` (video-shorts `shorts.py new <album>`; bài = `brief.short.song`).

## Ghi chú của PM

- Vì sao chủ đề này, vì sao bài 1 này, bài nào để dành cho album sau.
