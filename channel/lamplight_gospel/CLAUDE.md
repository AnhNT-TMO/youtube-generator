# Lamplight Gospel: hướng dẫn kênh

Đọc file này trước khi làm bất cứ việc gì cho kênh. Luật chung của xưởng ở `CLAUDE.md` gốc; quy trình ở các skill.
Mọi chi tiết riêng của kênh nằm trong thư mục này:

| File | Dùng khi |
|---|---|
| `channel.md` | danh tính kênh, tài nguyên (logo, model, video.json) |
| `rules.md` | viết idea / plan / Style / lời (analyzer, album-plan); khối YAML cuối file là luật máy đọc |
| `voices/README.md` | chọn Suno Voice theo cao độ video tham khảo |
| `visual.md` | viết prompt thumbnail, chọn và kiểm ảnh |
| `publish.md` | soạn `youtube.md`: description, tags, title, pinned comment, playlist |
| `translate.yaml` | dịch title sau khi đăng |
| `research-queue.txt` | link YouTube chờ analyze (chỉ trên máy) |

## Âm thanh kênh

Christian Gospel Blues / Southern Gospel Soul, chậm 6/8–12/8, giọng nam baritone ấm, hơi khàn (Voice mặc định
"Midnight Gospel Soul - Male 01"; các Voice khác ở `voices/README.md` và `rules.md` → `voices`). Tránh: giọng trẻ hẳn đi,
country, pop worship hiện đại, guitar blues-rock, production sáng/pop, choir lớn/cinematic, drums hiện đại/punchy.
Lời có thể diễn giải Kinh Thánh (`rules.md` → `sources`: tránh chương mà video tham khảo đã dùng).

## Hình ảnh kênh

Ánh đèn dầu vàng đến với một người đàn ông nghèo, đã có tuổi; hằng số: ngọn đèn hổ phách và khuôn mặt nhân vật trong `model/`.
Chi tiết: `visual.md`. Logo tròn "LAMPLIGHT / GOSPEL" có ngọn lửa (`channel.md` → *Tài nguyên*).

## Trạng thái

Trạng thái thật luôn lấy từ `album_plan.py board --channel lamplight_gospel` (cột "Việc còn lại"), không từ mục này hay trường
`status` viết tay trong `single.md`.

- **Album 001 — When The Night Is Long:** đã đăng YouTube bằng bản ghép cũ (50:16, giọng vào ~giây 37), chủ kênh giữ nguyên.
  Còn: điền Video URL + retention 0:15 / 0:30 / 1:00 vào `youtube.md` (mốc so sánh cho album sau).
  Bản ghép mới `audio/master/001-when-the-night-is-long.wav` không dùng cho video đã đăng. Ghi chú gốc: `notes/suno_gospel_blues_workflow_context.txt`.
  File audio của album này vẫn giữ tên cũ `… [usesuno.com].wav`.
- **Singles 001–003:** có video + `youtube.md`, chưa đăng.
- **Album 002–006, singles 004–006:** đang làm dở ở nhiều bước (xem board).
