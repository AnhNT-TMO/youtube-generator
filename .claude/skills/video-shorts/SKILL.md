---
name: video-shorts
description: Make the one YouTube Short of a finished album (release package = 1 album video + 1 Short, Related video → the album) - cut from the song's `short` segment that audio-song-naming already chose in its song card (channel/<ch>/songs/<type>/<slug>.md, default song = album.md brief.short.song, else track 1), written as short.md + short.json in the exact format video-generator `video.py short` reads (audio, in/out, lyric lines timed from the Short's 0:00, hook, CTA), in the album's own `short/` folder (channel/<ch>/albums/NNN-slug/short/; the old channel/<ch>/shorts/NNN-slug/ is still read and `shorts.py migrate` moves it), then a NEW vertical 9:16 image (thumbnail-prompt on the Short folder), a Short-only 1080×1920 render on the GPU server (video-generator `video.py frame` / `short`), youtube.md (title, description, tags, pinned comment, Studio steps incl. Related video + AI = Yes) and `shorts.py check`; the Short is never zipped alone - the PM packages the album, which puts the Short in the album's one S3 zip (`video.py package <album>`). Use when the PM or the owner says "làm short", "shorts cho album NNN", "cắt short", "video dọc", "Shorts", or after an album video is delivered. Does NOT pick the segment (audio-song-naming does), upload (the owner does) or spend Suno credits.
---

# YouTube Short (một Short cho mỗi album)

Gói đăng mỗi album = **1 video album + 1 Short** (không còn single). Short là một phần của album (CEO 2026-09-28): nằm
trong thư mục của album, `albums/NNN-slug/short/`, mỗi album đúng một Short. Short cắt từ một bài đã có trong kho: không
Suno, không ghép audio, không Whisper. Đoạn cắt (`short.start_s/end_s`, lời theo câu `short.lines`, câu `hook`) do skill
**audio-song-naming** chọn và ghi trong song card; skill này chỉ đọc. Mỗi Short có ảnh dọc riêng và bản render riêng.
Chính sách + nghiên cứu phía sau mọi luật ở đây: `docs/seo-youtube/09-shorts.md` (đọc §4 một lần).

```bash
S=.claude/skills/video-shorts/scripts/shorts.py         # gốc repo; new/spec tự chạy lại bằng .venv của skill (PyYAML)
# lần đầu: python3.12 -m venv .claude/skills/video-shorts/.venv && .claude/skills/video-shorts/.venv/bin/pip install -r .claude/skills/video-shorts/requirements.txt
python3 $S new   <album> [--song <slug>] [--hook "…"] [--cta "…"] [--version V] [--force]
                                                 # → <album>/short/short.md + short.json (đã có: --force mới ghi lại)
python3 $S spec  <short>                         # ghi lại short.json sau khi sửa hook_text / cta_text, đoạn của bài, hoặc bài đổi tên
python3 $S check <short>                         # short.md, short.json, ảnh 9:16, video đã render, youtube.md
python3 $S list  --channel <ch>                  # mọi Short: album, bài, đoạn, hook, ảnh, video, S3, URL
python3 $S migrate --channel <ch> [--yes]        # bố cục cũ shorts/NNN-slug/ → albums/<album>/short/ (mặc định chỉ in)
V=.claude/skills/video-generator/scripts/video.py
python3 $V frame   <short> --at 5                # một khung 1080×1920 của hiệu ứng, để chỉnh <short>/video.json
python3 $V short   <short>                       # chỉ render trên GPU server (~1–2 phút) → check_hook/mid/cta.png
python3 $V package <album>                       # PM: MỘT zip cho album + Short (short/ trong zip) → S3; không zip Short riêng
```

`<short>` = `channel/<ch>/albums/NNN-slug/short`. Bố cục cũ `channel/<ch>/shorts/NNN-slug/` vẫn đọc được (`check` ⚠️ nhắc
chuyển); `migrate` chuyển từng thư mục vào album ghi ở `short.md` → `album`, sửa `track` (đường tương đối từ thư mục Short)
và mọi đường `../…` + chữ `shorts/NNN-slug` trong các file text của nó (`short.json` dùng đường từ gốc repo: không đổi), từ
chối khi album đã có `short/`. Short đã render trên server trước khi chuyển: job server đổi tên theo thư mục, `migrate` nhắc
render lại (`video.py short`, ~1–2 phút) trước khi PM đóng gói album. Không chạy `migrate` khi một worker đang làm Short đó.

## Ở đâu

| Cái gì | File |
|---|---|
| Bài nào, vì sao | `albums/NNN-slug/album.md` → `brief.short {song, why}` (PM); trống → bài 1 của `tracklist` |
| Đoạn cắt, lời theo câu, câu hook | song card `channel/<ch>/songs/<type>/<slug>.md` → `short` (bố cục cũ `songs/<slug>.md` vẫn đọc được) (audio-song-naming; luật chọn đoạn: `channel/<ch>/naming.md`) |
| Title / description / tags / pinned comment / chữ hook + CTA | `channel/<ch>/publish.md` → *Shorts* (+ *Giờ đăng*) |
| Luật ảnh dọc + khối CORE ảnh dọc | `channel/<ch>/visual.md` → *Ảnh dọc Shorts*, *Prompt ảnh dọc Shorts (ChatGPT)* (skill thumbnail-prompt đọc) |
| Font, màu, vị trí chữ; logo / sóng nhạc cho 1080×1920 | video-generator `config.py` `DEFAULTS["short"]` < `channel/<ch>/video.json` → `short` < `<short>/video.json` |
| Mỗi Short: album, bài, hook, CTA, version | `<short>/short.md` (mẫu `templates/short.md`) |
| Đoạn đã tính: audio, in/out, lời theo giờ của Short, hook, CTA | `<short>/short.json` (`new`/`spec` ghi, `video.py short` đọc) |
| Câu R&D cho hook, title (dùng nguyên văn hoặc sửa) | `research/phrase-bank/*.yaml` (rnd-youtube-api) |
| Ô upload + bước Studio + analytics | `<short>/youtube.md` (mẫu `templates/youtube-short.md`) |

`short.json` (định dạng `video-generator/scripts/short.py` đọc, đừng đổi tên khóa):
`audio` (đường dẫn từ gốc repo tới `songs/<type>/<slug>.wav`), `in`/`out` = `short.start_s`/`end_s` (giây trong file bài),
`fade_in` 0.03, `fade_out` 0.6, `captions [{t0, t1, text}]` = `short.lines` dời về 0:00 của Short (vào sớm 0.1 s, giữ
tới câu sau nếu cách ≤ 4 s, không thì thêm 1.2 s; câu cuối tới hết Short), `hook {text}` (hiện 0–3 s theo `config.py`),
`cta {text, t0}` (t0 = độ dài − 4 s). Thêm `song`, `track` để tra ngược; `short.py` bỏ qua.

**Bài đổi tên** (audio-song-naming `rename` không sửa Short): `short.md` giữ `clip_id` của bài (`new` ghi; `spec` thêm vào
short.md cũ). `check` báo ❌ kèm đúng lệnh `spec` khi song card không còn; `spec` tìm lại bài theo `clip_id` (short.md cũ
chưa có `clip_id`: theo `tracks/*.md` của album, rồi theo đoạn in/out + lời của `short.json`), ghi lại `song` / `title` /
`track` trong short.md + `audio` trong short.json và in những gì đã đổi. Audio không đổi nên không cần render lại; title
trong `youtube.md` của Short nhắc tên cũ thì sửa tay (`spec` cảnh báo). Song card chỉ chuyển thư mục (bố cục cũ
`songs/<slug>.md` → `songs/<type>/`, audio-song-naming `migrate` đã sửa sẵn `track` + `audio`): `check` báo ❌ nếu còn
đường cũ, `spec` tìm lại theo slug và ghi đường mới.

## Các bước

1. **Tạo.** `new <album>`. Bài = `--song`, không có thì `brief.short.song` (trống hoặc còn `<…>` của mẫu = chưa chọn), không có thì bài 1 (bài phải nằm trong
   `tracklist`: Related video là album). Script dừng khi: song card chưa có `short` (→ PM giao audio-song-naming chọn
   đoạn), album đã có Short (`--force` chỉ khi PM bảo), hoặc đúng đoạn đó của bài đã dùng ở một Short khác (bài dùng lại
   ở album sau → chọn bài khác bằng `--song`, hoặc audio-song-naming chọn đoạn khác). Album còn Short ở `shorts/` cũ →
   `migrate` trước. PM giao ý tưởng Short của R&D
   (kiểu hook, `version`) → `--hook`, `--version`.
2. **Chữ trên màn hình.** `hook_text` mặc định = `short.hook` của bài; `cta_text` mặc định = `cta_text` trong
   `publish.md` → *Shorts*. Hook là một câu nói thẳng với người xem, từ lời của đoạn này; có thể lấy một câu trong kho câu
   `research/phrase-bank/`: câu cầu nguyện phổ biến / câu kinh điển được dùng nguyên văn (CEO 2026-09-28), ưu tiên câu còn
   đang tăng (`fresh`, `vpd_x` cao); không bao giờ lấy tên / branding kênh khác; ghi id câu vào `youtube.md` → *Kho câu*.
   Không trùng hook của Short trước (`check` chặn). Sửa trong `short.md` → `spec <short>`.
3. **Ảnh dọc.** Skill thumbnail-prompt trên thư mục Short, như nó đang làm: nó nhận ra thư mục `short/` trong album (và
   `shorts/` cũ), dùng khối CORE ảnh dọc,
   các bước kiểm ảnh dọc và `fit` → 2160×3840. Cảnh lấy từ lời của đoạn Short (`short.json` `captions`, song card ở
   `short.md` → `track`), khác ảnh album. Không chữ trên ảnh (chữ do video vẽ).
4. **Hiệu ứng.** `video.py frame <short> --at 5`, xem ảnh, viết `<short>/video.json` cho riêng ảnh này nếu cần (ánh sáng,
   hạt bụi), như video-generator bước 1. Vị trí chữ cố định theo kênh: ảnh phải hợp với chữ, không dời chữ cho một Short.
5. **Render.** `video.py short <short>` (chỉ render, không đóng gói). Xem `video/check_hook.png` (hook + câu đầu), `check_mid.png`,
   `check_cta.png`: chữ không đè mặt/nguồn sáng, đọc được ở cỡ điện thoại, không có gì quan trọng trong vùng giao diện
   che (`docs/seo-youtube/09-shorts.md` §1). `video/overlays.json` cho top/bottom từng khối chữ.
6. **youtube.md** từ `templates/youtube-short.md`, điền theo `publish.md` → *Shorts*. Related video = album: có Video URL
   của album thì đưa link vào description + pinned comment; chưa có thì ghi "đăng album trước" (Short đăng sau album).
7. **Kiểm.** `shorts.py check <short>` → không còn ❌. Bước cuối: **PM đóng gói album**: `video.py package <album>` (một zip
   cho cả gói: album + `short/<album>-short.mp4`, ảnh 9:16, youtube.md, ô dán; README ghi thứ tự đăng; `package` chạy lại
   `shorts.py check` và chặn khi còn ❌; ghi ở `<album>/s3-package.json`). Không đóng gói Short riêng (`video.py package
   <short>` từ chối).
8. **Bàn giao.** Chủ kênh upload theo giờ đăng và gắn Related video. Sau upload: Video URL + ngày vào `youtube.md`. Sau 48 giờ
   và 7 ngày: dòng analytics (engaged views, viewed vs swiped away, avg % viewed, subs, click Related video); PM so trung vị
   theo `version`, mỗi lần một trục (CLAUDE.md §0).

## Luật (chính sách, xem `docs/seo-youtube/09-shorts.md` §4)

- Mỗi Short khác thật: bài riêng hoặc đoạn riêng, ảnh dọc mới, câu hook riêng. Không cắt từ ảnh album, không dùng lại một
  đoạn, không xóa rồi đăng lại Short yếu.
- ≤ 180 s và dọc, không thì YouTube không coi là Short. Giọng vào trong 1 s đầu (`check` chặn).
- AI use = Yes cho mọi Short; không ghi dòng AI/Suno trong description; không phải nội dung cho trẻ em; 3–5 hashtag đúng
  chủ đề (`check` ⚠️ ngoài 3–5, ❌ > 60: YouTube bỏ qua toàn bộ hashtag, Help 6390658).
- Title và hook không hứa điều video hay album không có.
- Render và upscale chạy trên GPU server (CLAUDE.md §5); `new`, `spec`, `check`, `list`, `frame` nhẹ, chạy trên Mac.
- Học được điều gì về Short của một kênh (kiểu hook ăn, màu chữ bị chìm): một dòng trong `publish.md` / `visual.md` của
  kênh đó, không ghi ở đây.
