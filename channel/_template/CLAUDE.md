# <Channel Name>: hướng dẫn kênh

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

<thể loại, meter/tempo family, giọng (Voice mặc định), ban nhạc, những gì tránh>

## Hình ảnh kênh

<hằng số của mọi ảnh (nhân vật, vật/ánh sáng đặc trưng), chi tiết ở visual.md>

## Trạng thái

Trạng thái thật luôn lấy từ `album_plan.py board --channel <ch>`.
