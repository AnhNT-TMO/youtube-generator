# <Channel Name>

- **Thể loại:** <genre / subgenre, house sound một câu>
- **Khán giả:** <ai nghe, nghe khi nào, trên thiết bị gì>
- **Công thức:** <kho bài Suno → album 60–80 phút chọn từ kho → 1 album + 1 Short mỗi lần đăng>
- **Hình:** <thế giới hình, một câu>

## Hợp đồng kênh

Ranh giới không experiment nào được vượt; bên trong ranh giới PM được tự do sáng tạo.

- **Dòng nhạc:** <dòng nhạc + ngôn ngữ lời; prompt Suno ở `prompt_suno.md`, đổi prompt = việc của CEO>
- **Danh tính:** <tên kênh, logo, nhân vật, những gì không bao giờ đổi>
- **Mặc định, PM đổi được khi có lý do ghi lại:** `album_rules.md` (phần mặc định; luật cứng là của CEO), `naming.md`, `publish.md`, biến thể ảnh trong `visual.md`.
- Luật YouTube và luật chung ở `CLAUDE.md` gốc §5 không bao giờ phá.

## Tài nguyên

| Đường dẫn | Nội dung |
|---|---|
| `image_source/logo.png` | Logo kênh vuông ≥ 512px nền trong suốt |
| `video.json` | Phong cách video của kênh (skill `video-generator`, `references/config.md`) |
| `model/` | Ảnh tham chiếu nhân vật cho ChatGPT (`model/README.md`: file nào góc nào) |
| `songs/<type>/`, `albums/NNN-slug/` (+ `short/`) | kho bài theo loại, album và Short của nó (sinh ra khi làm, chỉ trên máy) |
