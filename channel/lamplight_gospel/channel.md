# Lamplight Gospel

- **Trạng thái:** đang chạy (chi tiết: `album_plan.py board --channel lamplight_gospel`)
- **Thể loại:** Christian Gospel Blues / Southern Gospel Soul
- **Vocal persona:** giọng nam baritone ấm, hơi khàn (Voice mặc định ở `voices/README.md`)
- **Hình ảnh:** ánh sáng (đèn dầu, tông vàng ấm) đến với người nghèo, già, khốn khổ: ca sĩ luôn mặc đồ nghèo, cũ, sờn (5 loại trang phục ở `visual.md`), không tuxedo/vest sang (chủ kênh 2026-09-23/24), bối cảnh đơn sơ; chỉ ngọn đèn vàng và khuôn mặt là cố định, còn lại đổi theo vibe bài; logo tròn "LAMPLIGHT / GOSPEL" có ngọn lửa
- **Chưa chốt:** tagline, brand voice cho title/description, band profile chính thức

## Hợp đồng kênh

Ranh giới không experiment nào được vượt (chủ kênh 2026-09-25); bên trong ranh giới các skill được tự do sáng tạo.

- **Dòng nhạc:** gospel / Christian, lời tiếng Anh, mọi nhánh: gospel blues, soul gospel, southern gospel, hymn cổ, worship.
  Nhánh khác house sound là album experiment (`experiment` trong plan), không cần kênh mới. Đổi ngôn ngữ hoặc rời gospel → kênh mới.
- **Danh tính:** tên "Lamplight Gospel" và logo; nội dung đức tin Cơ Đốc; không mạo danh nghệ sĩ hay kênh có thật.
- **Còn lại là mặc định, experiment được đổi:** giọng, persona, ban nhạc, tempo (`rules.md`); nhân vật, ngọn đèn, trang phục,
  bố cục và chữ thumbnail, kể cả ảnh không có người (`visual.md`); title, description (`publish.md`).
- Luật YouTube (chính sách, giới hạn cứng) và luật chung ở `CLAUDE.md` gốc §5 không bao giờ phá.

## Tài nguyên

| Đường dẫn | Nội dung |
|---|---|
| `image_source/logo.png` | Logo kênh 1024px nền trong suốt. Sinh lại: `.claude/skills/video-generator/.venv/bin/python .claude/skills/video-generator/scripts/make_logo.py --title LAMPLIGHT --sub GOSPEL --out channel/lamplight_gospel/image_source/logo.png` |
| `video.json` | Phong cách video của kênh: bụi, ánh sáng, màu sóng nhạc, logo (xem skill `video-generator`, `references/config.md`) |
| `ideas/` | Idea album: ảnh + video loop 5 phút làm sẵn trước khi có nhạc |
| `albums/` | Album đang/đã làm |
| `singles/` | Bài nổi trội đăng riêng (trỏ về bài gốc trong album, có ảnh + video + youtube.md riêng), mẫu `templates/single.md` |
| `model/` | Ảnh tham chiếu nhân vật (8 góc, nền trong suốt), đính kèm khi tạo ảnh bằng ChatGPT |
| `library/catalog.md` | Thư viện bài hát của kênh (cùng persona) để tái sử dụng |
