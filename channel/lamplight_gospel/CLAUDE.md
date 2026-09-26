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
| `translate.yaml` | dịch title + description sau khi đăng |
| `research-queue.txt` | link YouTube chờ analyze (chỉ trên máy) |

## Âm thanh kênh

Christian Gospel Blues / Southern Gospel Soul, chậm 6/8–12/8, giọng nam baritone ấm, hơi khàn (Voice mặc định
"Midnight Gospel Soul - Male 01"; các Voice khác ở `voices/README.md` và `rules.md` → `voices`). Tránh: giọng trẻ hẳn đi,
country, pop worship hiện đại, guitar blues-rock, production sáng/pop, choir lớn/cinematic, drums hiện đại/punchy.
Lời có thể diễn giải Kinh Thánh (`rules.md` → `sources`: tránh chương mà video tham khảo đã dùng).

## Hình ảnh kênh

Ánh đèn dầu vàng đến với một người đàn ông nghèo, đã có tuổi; mặc định: ngọn đèn hổ phách và khuôn mặt nhân vật trong `model/`
(experiment được đổi; ranh giới kênh: `channel.md` → *Hợp đồng kênh*).
Chi tiết: `visual.md`. Logo tròn "LAMPLIGHT / GOSPEL" có ngọn lửa (`channel.md` → *Tài nguyên*).

## Trạng thái

Trạng thái thật luôn lấy từ `album_plan.py board --channel lamplight_gospel` (cột "Việc còn lại"), không từ mục này hay trường
`status` viết tay trong `single.md`. Ghi chú riêng của một album/single nằm trong thư mục của nó (`notes/`, `youtube.md`).
