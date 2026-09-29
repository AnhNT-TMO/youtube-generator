---
title: <Song Title - one per song, shared by both versions of a same-lyrics generation; never with V1/V2>
slug: <song-title-slug>_<version>, or <song-title-slug> when version is null
type: <spoken|sung>
clip_id: <suno clip uuid>
generation: <gNNN>
version: <v1|v2 - position of clip_id in songs/manifest.json generations[].clip_ids when the generation's other clip has the same lyrics; null = a song on its own (other clip has different lyrics or was dropped)>
sibling: <slug of the other version (same generation, same lyrics), or null>
suno_url: https://suno.com/song/<clip_id>
audio: <slug>.wav
duration_s: <float>
vocal_entry_s: <float>
sung_entry_s: <float>
named: <YYYY-MM-DD> audio-song-naming
short:
  start_s: <float>
  end_s: <float>
  lines:
    - {t0: <float>, t1: <float>, text: "<sung line>"}
  hook: "<line shown as the Short's hook text>"
  why: "<one line: why this part>"
---

# <Song Title>

Bài trong kho `channel/<ch>/songs/<type>/` (mỗi `type` của prompt_suno.md một thư mục). Lượt Suno có 2 clip cùng lời = một bài,
2 bản `v1` / `v2` cùng tên, file `<tên>_v1` / `<tên>_v2`, `sibling` nối hai bản; 2 clip khác lời = 2 bài riêng, mỗi bài tên riêng,
file `<tên>` (không `_vN`), `version` + `sibling` null.
`audio`: file wav nằm cạnh card này. Front matter: skill audio-song-naming ghi, không ai khác sửa.
Mọi thời gian tính bằng giây trong file `audio` của bài. `short`: đoạn cho video Short (video-shorts đọc).
Bài đang nằm trong album nào: `pm-production/scripts/album.py pool` tính từ `albums/*/album.md`, không ghi ở đây.

## Lyrics

```
<lyrics exactly as Suno stored them>
```
