# Channels

Mỗi channel là một thư mục `channel/<tên>/`. Skill dùng chung (`.claude/skills/video-generator/`) đọc
cấu hình từ đây, nên thêm channel mới chỉ cần tạo thư mục theo mẫu dưới, không sửa code.

```
channel/<tên>/
├── channel.md          # danh tính: thể loại, persona, hình ảnh, brand voice
├── translate.yaml      # ngôn ngữ dịch title video (skill youtube-translate; mẫu: lamplight_gospel/translate.yaml)
├── rules.md            # luật làm nhạc: house Style + Exclude, mật độ lời, chữ/tên bài cần tránh, experiment (mẫu: lamplight_gospel/rules.md)
├── image_source/
│   └── logo.png        # logo kênh, nền trong suốt (vuông, ≥ 512px)
├── video.json          # phong cách video: loại/màu bụi, ánh sáng, màu sóng nhạc, logo
├── ideas/NNN-slug/     # idea: idea.yaml (nguồn chính, schema: templates/idea.yaml) + idea.md (tóm tắt)
│                       #   + thumbnail.png (+ video.json) → video/loop.mp4
├── albums/NNN-slug/    # album: album.md, tracks/, ... + thumbnail.png (+ thumbnail-prompt.md, video.json)
├── singles/NNN-slug/   # bài đăng riêng: single.md (trỏ tới tracks/NN-*.md của album gốc) + thumbnail + audio/master + video + youtube.md
├── model/              # ảnh tham chiếu nhân vật cho ChatGPT (skill thumbnail-prompt)
└── library/catalog.md  # thư viện bài hát của channel
```

## Ba lớp cấu hình video

1. **Mặc định của tool** (`.claude/skills/video-generator/scripts/config.py`), giống nhau ở mọi channel:
   logo góc trên phải, like/subscribe góc dưới phải khoảng 30–45 giây một lần, có sóng
   nhạc, có intro logo 4 giây, loop 5 phút.
2. **`channel/<tên>/video.json`**: phong cách riêng của channel, chỉ ghi phần khác mặc định.
3. **`<idea hoặc album>/video.json`** (tuỳ chọn): phần phụ thuộc vào ảnh cụ thể
   (chùm nắng rơi ở đâu, có cây đèn/nến nào để rung lửa, bụi dồn về phía nào).

Chạy: skill `video-generator`, gồm 2 bước: `video.py loop <thư mục>` (ảnh → video 5 phút) và `video.py album <thư mục> <nhạc>`
(loop → video dài bằng nhạc + sóng nhạc). Xem `.claude/skills/video-generator/SKILL.md`.

## Thêm channel mới

1. `mkdir -p channel/<tên>/{image_source,ideas,albums,singles,model,library}`
2. Đặt `image_source/logo.png` (hoặc sinh bằng `.claude/skills/video-generator/scripts/make_logo.py --title ... --sub ... --out ...`)
3. Copy `channel/lamplight_gospel/video.json`, đổi `logo.path` và phong cách
   (xem `.claude/skills/video-generator/references/example_snow.json` để có ví dụ tuyết trắng / ánh sáng lạnh)
4. Viết `channel.md`, gồm cả mục **Prompt ảnh mặc định (ChatGPT)** (khối style cố định cho mọi thumbnail, skill `thumbnail-prompt`)

## Channels hiện có

- [lamplight_gospel](lamplight_gospel/channel.md): Christian Gospel Blues
