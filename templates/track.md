---
track_no: <NN>
title: <Song Title>
slug: <song-slug>
type: <spoken|sung>
audio: ../../songs/<type>/<song-slug>.wav
duration_s: <float>
clip_id: <suno clip uuid>
---

# <NN> — <Song Title>

Sinh bởi `pm-production/scripts/album.py build` từ `channel/<ch>/songs/<type>/<song-slug>.md` theo `album.md` → `tracklist`.
Không sửa tay: đổi `album.md` rồi build lại. audio-album-assembly và upload-youtube-publish đọc file này;
`audio` tính từ thư mục album.

## Lyrics

```
<lyrics>
```
