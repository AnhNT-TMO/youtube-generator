---
id: <channel-prefix>-sNNN      # vd. lg-s001; ổn định, không đổi
track: ../../albums/<NNN-album>/tracks/<NN-slug>.md   # file bài gốc (tương đối từ thư mục single) = nguồn chính metadata + lyrics
track_id: <track id>           # vd. <album-prefix>-01, để tra catalog
album: <NNN-album>             # album gốc
album_video_url:               # link video album (description, pinned comment, end screen trỏ về); trống nếu album chưa lên
status: plan                   # plan / có thumbnail / có audio / có video / đã upload
---

# Single — <Song Title>

Bài đăng riêng lấy từ album gốc. Không chép metadata/lyrics sang đây; mọi thứ về bài nằm ở file `track`.

- **Vì sao đăng riêng:** <bài nổi trội ở điểm nào: hook, retention trong album, comment nhắc tới…>
- **Khác ảnh album thế nào:** <cảnh / thời điểm / tư thế / màu, để người xem không tưởng là video album>

## Việc cần làm

- [ ] Ảnh: skill `thumbnail-prompt` → `thumbnail-prompt.md` → ChatGPT → `thumbnail.png` (`thumb.py fit` + `check`)
- [ ] Audio: skill `album-assembly` → `assemble.py single <thư mục này>` → `audio/master/<thư mục>.wav` + `assembly.md` (render checks quyết)
- [ ] YouTube: skill `youtube-publish` (chế độ single) → `youtube.md` → `publish.py check <thư mục>` (không `--video`: video nằm trên server)
- [ ] Video: skill `video-generator` → `video.py loop <thư mục>` → `video.py album <thư mục> audio/master/<thư mục>.wav` (chạy trên server; có youtube.md nên tự đóng gói S3)
- [ ] Sau upload: điền `album_video_url` ở đây nếu cần, thêm thư mục này vào `singles:` trong front matter của bài gốc, cập nhật `library/catalog.md`
