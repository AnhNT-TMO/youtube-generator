---
album: <NNN-album>                 # album nguồn; zip S3 vào thư mục album này
track: ../../albums/<NNN-album>/tracks/<NN-slug>.md   # file bài gốc (tương đối từ thư mục Short) = nguồn lời + audio
role: <A | B>                      # A = bài 1 → video đích là album (gói đăng, CLAUDE.md §3); B = bài khác → video đích là single của bài đó (dự phòng)
related_video: ../../albums/<NNN-album>   # thư mục video đích; Video URL lấy từ youtube.md của nó
length: [25, 65]                   # cửa sổ độ dài (giây) cho `shorts.py pick`
pick:                              # (tùy chọn) số ứng viên trong bảng pick thay cho lựa chọn tự động
segment:                           # in-out (giây trong file audio), `pick` ghi
hook_text: ""                      # câu 0–3 s, viết từ chính lời bài này (tiếng Anh), không dùng câu mẫu
cta_text: ""                       # chữ 4 s cuối, trỏ xuống link Related video (mẫu: channel/<ch>/publish.md → Shorts)
version: ""                        # version đóng gói đang thử (một trục mỗi lần; CLAUDE.md §0)
---

# Short — <Song Title> (<role>)

- [ ] `shorts.py new` → thư mục này
- [ ] Đoạn: viết `hook_text`, `cta_text` → `shorts.py pick <thư mục>` → `short.json`
- [ ] Ảnh dọc: skill `thumbnail-prompt` (Short) → `thumbnail.png` 2160×3840
- [ ] Video: `video.py short <thư mục> --no-package` → đọc `video/check_hook.png`, `check_mid.png`, `check_cta.png`
- [ ] YouTube: `youtube.md` (mẫu `templates/youtube-short.md`) → `shorts.py check <thư mục>` → `video.py package <thư mục>`
- [ ] Sau upload: Video URL + ngày trong `youtube.md`, Related video đã gắn trong Studio
