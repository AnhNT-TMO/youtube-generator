---
album: <NNN-album>                 # album chứa Short này (thư mục cha) = Related video; Short nằm trong zip S3 của album này
song: <song-slug>                  # bài trong kho channel/<ch>/songs/ (album.md brief.short.song, mặc định bài 1)
title: <Song Title>                # tên bài (song card)
clip_id: <suno clip uuid>          # để tìm lại bài khi bài bị đổi tên (`shorts.py spec`)
track: ../../../songs/<type>/<song-slug>.md  # song card (tương đối từ thư mục Short albums/NNN-slug/short/): lời, audio, đoạn short.start_s/end_s/lines
hook_text: ""                      # chữ 0–3 s; mặc định = short.hook của song card; mỗi Short một câu riêng (tiếng Anh)
cta_text: ""                       # chữ 4 s cuối, trỏ tới album (mặc định: `cta_text` trong channel/<ch>/publish.md → Shorts)
version: ""                        # version đóng gói đang thử (một trục mỗi lần; R&D / PM)
---

# Short: <Song Title>

Sửa `hook_text` / `cta_text` ở đây rồi `shorts.py spec <thư mục>`; đoạn cắt (in/out, lời theo câu) lấy từ song card,
không sửa tay trong `short.json`.

- [ ] `shorts.py new <album>` → thư mục này (`<album>/short/`) + `short.json`
- [ ] Ảnh dọc: skill `thumbnail-prompt` (Short) → `thumbnail.png` 2160×3840
- [ ] Video: `video.py frame <thư mục> --at 5` → `video.py short <thư mục>` → đọc `video/check_hook.png`,
      `check_mid.png`, `check_cta.png`
- [ ] YouTube: `youtube.md` (mẫu `templates/youtube-short.md`) → `shorts.py check <thư mục>` → PM đóng gói album: `video.py package <album>` (một zip: album + Short)
- [ ] Sau upload: Video URL + ngày trong `youtube.md`, Related video = album đã gắn trong Studio
