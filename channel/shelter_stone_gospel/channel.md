# Shelter Stone Gospel

- **Thể loại:** Christian gospel blues, đánh sâu một house sound (CEO 2026-09-28): gospel blues có chút roots blues-rock,
  piano gospel dẫn, slide guitar, Hammond ở phần ba cuối, giọng nam bass-baritone phong trần, bè nữ trưởng thành đáp lại,
  12/8 shuffle ~88 BPM, giọng trưởng ấm (`prompt_suno.md`).
- **Khán giả:** người Mỹ theo đạo, phần lớn 65+, nghe trên điện thoại; tìm một giờ nhạc cầu nguyện khi mệt, buồn, cần che chở.
- **Công thức:** kho bài Suno làm sẵn (`songs/`), mỗi video là một album 60–80 phút chọn từ kho, xen kẽ bài có lời đọc và bài
  hát thẳng; title + chữ thumbnail là một lời cầu xin ngôi thứ nhất (kho câu R&D). Mỗi album + 1 Short.
- **Hình:** một người đàn ông lớn tuổi (nhân vật riêng, `model/`) hát hết lòng trong nhà nguyện đá, ánh vàng hổ phách, một
  thánh giá thật; chữ vàng rất to (`visual.md`).

## Hợp đồng kênh

Ranh giới không experiment nào được vượt; bên trong ranh giới PM được tự do sáng tạo.

- **Dòng nhạc:** Christian gospel blues, lời tiếng Anh, prompt Suno của kênh (`prompt_suno.md`). Đổi prompt = việc của CEO.
- **Danh tính:** tên "Shelter Stone Gospel", logo, nhân vật trong `model/`; nội dung đức tin Cơ Đốc; không mạo danh nghệ sĩ
  hay kênh có thật, không dùng tên/branding kênh khác.
- **Mặc định, PM đổi được khi có lý do ghi lại:** luật chọn bài mặc định (`album_rules.md` mục 5–9; mục 1–4 là của CEO), cách đặt tên bài (`naming.md`), title,
  description (`publish.md`), biến thể ảnh trong form cố định (`visual.md`).
- Luật YouTube và luật chung ở `CLAUDE.md` gốc §5 không bao giờ phá.

## Tài nguyên

| Đường dẫn | Nội dung |
|---|---|
| `prompt_suno.md` | 2 prompt Suno: `spoken` (có lời đọc đầu + cuối), `sung` (hát thẳng) |
| `naming.md` | cách đặt tên bài từ lời + chọn đoạn Short |
| `album_rules.md` | luật chọn bài vào album (máy đọc: `album.py check`) |
| `publish.md` | title, description (chờ mẫu CEO), tags, Shorts, giờ đăng |
| `visual.md`, `thumb_pool.json`, `video.json` | ảnh + chuyển động video (nhóm video) |
| `image_source/`, `model/`, `branding/` | logo, huy hiệu, ảnh nhân vật 9 góc; avatar/banner (chỉ trên máy) |
| `translate.yaml` | ngôn ngữ dịch title + description |
| `songs/spoken/`, `songs/sung/`, `albums/NNN-slug/` (+ `short/`) | kho bài theo loại, album và Short của nó (chỉ trên máy) |
