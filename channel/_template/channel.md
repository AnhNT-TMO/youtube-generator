# <Channel Name>

- **Thể loại:** <genre / subgenre>
- **Vocal persona:** <giọng>
- **Hình ảnh:** <thế giới hình, một câu>
- **Chưa chốt:** <những gì còn mở>

## Hợp đồng kênh

Ranh giới không experiment nào được vượt; bên trong ranh giới các skill được tự do sáng tạo.

- **Dòng nhạc:** <dòng nhạc rộng + ngôn ngữ lời; nhánh nào làm được bằng album experiment, khi nào phải sang kênh mới>
- **Danh tính:** <tên kênh, logo, những gì không bao giờ đổi>
- **Còn lại là mặc định, experiment được đổi:** giọng, persona, tempo (`rules.md`); hình (`visual.md`); title, description (`publish.md`).
- Luật YouTube (chính sách, giới hạn cứng) và luật chung ở `CLAUDE.md` gốc §5 không bao giờ phá.

## Tài nguyên

| Đường dẫn | Nội dung |
|---|---|
| `image_source/logo.png` | Logo kênh vuông ≥ 512px nền trong suốt (vẽ bằng `video-generator/scripts/make_logo.py --title … --sub … --out …` hoặc ảnh có sẵn) |
| `video.json` | Phong cách video của kênh (skill `video-generator`, `references/config.md`) |
| `model/` | Ảnh tham chiếu nhân vật cho ChatGPT (`model/README.md`: file nào góc nào) |
| `ideas/`, `albums/`, `singles/`, `library/` | sinh ra khi làm video (chỉ trên máy) |
