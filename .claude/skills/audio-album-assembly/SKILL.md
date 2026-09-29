---
name: audio-album-assembly
description: Join an album's songs (tracks/NN-*.md in play order, built by pm-production from album.md; audio ../../songs/<type>/<slug>.wav) into one continuous master with a light equal-power crossfade and NO cutting or editing - only digital silence at each file's two edges is dropped, every song is matched to the same integrated loudness, master −14 LUFS, true peak ≤ −1.5 dBTP, 48 kHz 24-bit WAV + MP3 - on the GPU server (ffmpeg), then writes assembly.json (start_s of every song in the master = the chapters upload-youtube-publish reads) and assembly.md (tracklist with chapter times, length vs album_rules length_min, loudness, clipping). Use when the PM or the owner says "ghép album", "ghép audio", "nối bài", "crossfade", "làm bản liên tục", "master album", "chapters từ bản ghép", or wants assembly.md regenerated. Does NOT choose or reorder songs (pm-production), trim intros/outros or change anything inside a song.
---

# Album assembly

CEO 2026-09-28: bài nối nhau bằng **crossfade nhẹ, không cắt, không sửa gì trong bài**. Thứ tự = `track_no` (PM quyết trong
`album.md` → `album.py build`); skill này không đổi thứ tự, không bỏ bài.

| Vào | Ra (trong thư mục album) |
|---|---|
| `tracks/NN-<slug>.md`: `track_no`, `title`, `slug`, `type`, `audio: ../../songs/<type>/<slug>.wav` (tính từ thư mục album; bố cục cũ `../../songs/<slug>.wav` vẫn chạy) | `audio/master/<album>.wav` (48 kHz 24-bit) + `.mp3` (320k) |
| `channel/<ch>/album_rules.md`: `crossfade_s`, `length_min` | `assembly.json` (hợp đồng: `start_s`/`end_s` từng bài trong master, `in_s`/`out_s`/`gain_db` trong file bài) |
| | `assembly.md` (sinh từ json: tracklist + chapters, độ dài, kiểm tra) |

## Lệnh

```bash
A=.claude/skills/audio-album-assembly/scripts/assemble.py   # gốc repo; chỉ cần python3 + ffmpeg, không venv
python3 $A render <album> [--crossfade S] [--no-mp3]        # trên GPU server: đẩy → ghép → kéo về
python3 $A report <album>                                   # sinh lại assembly.md từ assembly.json (trên Mac, không đo)
```

`<album>` = thư mục hoặc tên `NNN-slug`. Crossfade mặc định = `crossfade_s` của `album_rules.md`; `--crossfade` chỉ khi PM
ghi lý do trong album.md. Exit 0 = mọi kiểm ✅; **exit 4 = đã ghép nhưng có ❌** (đọc assembly.md); khác = lỗi, không có master.

**Chạy trên GPU server** (CLAUDE.md §5: ghép + đo loudness cả bài). `render` đẩy qua `scripts/remote.sh`: script, album_rules,
`tracks/*.md` (thư mục `tracks/` trên server được đồng bộ `--delete`, không còn bài cũ sót), `album.md`, và **chỉ các file bài
album dùng** (rsync bỏ qua file đã có trên server); chạy `render --local` trên server trong `youtube.slice` + youtube-guard
(khối `LIMIT`); kéo về master WAV/MP3 + `assembly.json` + `assembly.md`, kiểm master trên máy (header WAV đủ, dài =
`assembly.json`, có MP3) rồi **xoá master WAV/MP3 trên server** (cũng qua `exec` trong `LIMIT`); file bài trong `songs/` giữ
lại trên server cho album sau (không phải đẩy lại). Đường trên server = đường trong repo (`rsync --files-from`, tự tạo
`songs/<type>/`): bài chuyển thư mục (audio-song-naming `migrate`) thì lần ghép sau tự đẩy lại theo đường mới. Kiểm không đạt → giữ master trên server, in lệnh `remote.sh pull`.
video-generator đẩy master từ máy này lên thư mục riêng của nó. Server: system `python3` + `ffmpeg` (soxr), không cần
cài gì; `remote.env` giống audio-song-naming (`QC_REMOTE`, `~/youtube-qc`). Thử 4 bài / 17.6 phút: 1 phút 43 giây tổng,
phần lớn là đẩy bài + kéo master; album 1 giờ kéo về ~1 GB WAV. `--local` trên Mac: chỉ khi server không lên được **và** CEO
đồng ý.

## Ghép thế nào (không có lựa chọn nào khác để chỉnh)

1. Mỗi bài: `silencedetect` < −60 dBFS → chỉ bỏ im lặng số dính ở **đầu và cuối file** (`in_s`, `out_s`); intro, outro,
   fade của Suno giữ nguyên. `ebur128` đo loudness tích hợp + true peak của file gốc.
2. `gain_db` = −14 − loudness gốc: mọi bài cùng −14 LUFS.
3. Nối: `acrossfade` `c1=qsin:c2=qsin` (equal-power) dài `crossfade_s`; `crossfade_s = 0` → nối thẳng.
4. Limiter an toàn chạy ở 4× (192 kHz, soxr) tại −2.0 dB rồi về 48 kHz → true peak ≤ −1.5 dBTP. Đo lại master; lệch
   > 0.5 LU hoặc true peak vượt → chỉnh gain / hạ limiter, ghép lại (tối đa 3 lần, `measured.renders`).
5. `start_s` bài i = Σ(độ dài bài trước − crossfade); bài 1 = 0; chapter = floor(start_s). Độ dài master =
   Σ(out_s − in_s) − (n − 1) × crossfade (kiểm tra ±0.05 s). Thử nghiệm: tương quan chéo master với file gốc tại `start_s`
   cho lệch 0 ms, mức = `gain_db`.

## Đọc kết quả, báo PM

Kiểm trong assembly.md: độ dài trong `length_min` · loudness −14 ± 0.5 LUFS · true peak ≤ −1.5 dBTP (không clip) · độ dài
khớp công thức · chapters YouTube (≥ 3 bài, bài 1 ở 0:00, mỗi chapter ≥ 10 s). Cảnh báo ⚠️ (không chặn): im lặng số > 2 s ở mép
một file (đã bỏ, có thể Suno lỗi), limiter ép đỉnh > 3 dB ở một bài (bài gốc quá nhỏ).

- Độ dài ngoài `length_min` → không giao video: báo PM thiếu/thừa bao nhiêu phút; PM thêm/bớt bài trong album.md rồi
  `album.py build` → `render` lại. Không kéo dài crossfade, không cắt bài.
- Loudness / true peak vẫn ❌ sau 3 lần → báo PM kèm `measured` trong assembly.json.
- Báo PM: độ dài, số bài, loudness, true peak, cảnh báo, đường dẫn master. Không ai phải nghe.

Giao tiếp: video-generator làm video từ `audio/master/<album>.wav`; upload-youtube-publish lấy chapters từ `assembly.json`
(`start_s`). Đổi tên một bài của album (audio-song-naming `rename --update-albums`) sửa `assembly.json` → chạy `report`.
