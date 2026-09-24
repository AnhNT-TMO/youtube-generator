# Channels

Mỗi channel là một thư mục `channel/<tên>/` chứa **toàn bộ chi tiết riêng** của kênh. Các skill trong `.claude/skills/` chỉ là
quy trình dùng chung: chúng đọc những file dưới đây và không biết gì về một kênh cụ thể (CLAUDE.md gốc §2).

```
channel/<tên>/
├── CLAUDE.md           # chỉ mục + âm thanh/hình ảnh tóm tắt + trạng thái (đọc trước)
├── channel.md          # danh tính: thể loại, persona, thế giới hình, tài nguyên
├── rules.md            # luật nhạc; khối YAML cuối file = luật máy đọc (validate, analyzer)
├── visual.md           # luật hình: hằng số, khối CORE ChatGPT, trục biến thể, điều phải kiểm
├── publish.md          # mẫu description, tags mặc định, title, emoji, pinned comment
├── translate.yaml      # ngôn ngữ dịch title (youtube-translate)
├── video.json          # phong cách video: bụi, ánh sáng, màu sóng nhạc, logo
├── research-queue.txt  # link YouTube chờ analyze (chỉ trên máy)
├── image_source/logo.png
├── model/              # ảnh tham chiếu nhân vật cho ChatGPT + README.md
├── voices/README.md    # Suno Voice + cao độ đo được
├── ideas/ albums/ singles/ library/   # sinh ra khi làm video (chỉ trên máy)
```

| Skill | Đọc gì của kênh |
|---|---|
| youtube-music-analyzer | `rules.md` (`research`, `sources`, `voices`), `channel.md`, album gần nhất |
| album-plan | `rules.md` (toàn bộ khối YAML + §1–§9), `voices/README.md`, `library/catalog.md` |
| suno-generate, verification-audio, album-assembly | chỉ file của album (`generation.yaml`, `selection.yaml`, `tracks/`) |
| thumbnail-prompt | `visual.md`, `model/` |
| video-generator | `video.json`, `image_source/logo.png` |
| youtube-publish | `publish.md` |
| youtube-translate | `translate.yaml` |
| production-manager | `CLAUDE.md`, `research-queue.txt` |

## Ba lớp cấu hình video

1. **Mặc định của tool** (`.claude/skills/video-generator/scripts/config.py`), giống nhau ở mọi channel:
   logo góc trên phải, like/subscribe góc dưới phải khoảng 30–45 giây một lần, có sóng nhạc, có intro logo 4 giây, loop 5 phút.
2. **`channel/<tên>/video.json`**: phong cách riêng của channel, chỉ ghi phần khác mặc định.
3. **`<idea hoặc album>/video.json`** (tuỳ chọn): phần phụ thuộc vào ảnh cụ thể
   (chùm sáng rơi ở đâu, nguồn sáng nào để rung lửa, bụi dồn về phía nào).

## Thêm channel mới

1. `cp -R channel/_template channel/<tên>`
2. Điền với chủ kênh, theo thứ tự: `channel.md` → `rules.md` (house Style, Voices, khối YAML) → `visual.md` + `model/` →
   `publish.md` → `video.json` + `image_source/logo.png` → `translate.yaml` → `CLAUDE.md`.
3. Kiểm: `python3 .claude/skills/production-manager/scripts/lint_skills.py` (skill không được nhắc tới kênh),
   `album_plan.py board --channel <tên>`.
4. Thêm dòng vào bảng dưới.

## Channels hiện có

| Channel | Thể loại |
|---|---|
| [lamplight_gospel](lamplight_gospel/CLAUDE.md) | Christian Gospel Blues / Southern Gospel Soul |
