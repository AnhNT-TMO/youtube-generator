# Channels

Mỗi channel là một thư mục `channel/<tên>/` chứa **toàn bộ chi tiết riêng** của kênh. Các skill trong `.claude/skills/` chỉ là
quy trình dùng chung: chúng đọc những file dưới đây và không biết gì về một kênh cụ thể (CLAUDE.md gốc §2).

```
channel/<tên>/
├── CLAUDE.md          # chỉ mục + âm thanh/hình ảnh tóm tắt (đọc trước)
├── channel.md         # danh tính, hợp đồng kênh, tài nguyên
├── prompt_suno.md     # prompt Suno Simple mode, một prompt cho mỗi loại bài (front matter: mode, model, loại bài)
├── naming.md          # cách đặt tên bài từ lời + chọn đoạn Short
├── album_rules.md     # luật chọn bài vào album (front matter máy đọc)
├── visual.md          # luật hình: form thumbnail, khối CORE ChatGPT, biến thể, ảnh dọc Short
├── video.json         # phong cách video: chuyển động, ánh sáng, sóng nhạc, logo
├── publish.md         # mẫu description, tags, title, Shorts, pinned comment, giờ đăng
├── translate.yaml     # ngôn ngữ dịch title + description
├── image_source/logo.png, model/          # logo, ảnh nhân vật cho ChatGPT
└── songs/<type>/ albums/NNN/(short/)    # kho bài theo loại, album + Short của nó (sinh ra khi làm, chỉ trên máy)
```

| Nhóm | Skill | Đọc gì của kênh |
|---|---|---|
| PM | pm-production | `CLAUDE.md`, `channel.md`, `album_rules.md`, `songs/<type>/*.md` |
| R&D | rnd-youtube-api | `channel.md` (ngách để tìm) |
| Audio | audio-suno-generate | `prompt_suno.md` |
| Audio | audio-song-naming | `naming.md`, `songs/raw/` |
| Audio | audio-album-assembly | `album_rules.md` (`crossfade_s`), `albums/NNN/tracks/` |
| Video | thumbnail-prompt | `visual.md`, `model/` |
| Video | video-generator | `video.json`, `image_source/` |
| Video | video-shorts | `publish.md` → *Shorts*, `songs/<type>/<bài>.md` → `short` |
| Upload | upload-youtube-publish | `publish.md` |
| Upload | upload-youtube-translate | `translate.yaml` |

## Ba lớp cấu hình video

1. **Mặc định của tool** (`.claude/skills/video-generator/scripts/config.py`), giống nhau ở mọi channel.
2. **`channel/<tên>/video.json`**: phong cách riêng của channel, chỉ ghi phần khác mặc định.
3. **`<album hoặc short>/video.json`** (tuỳ chọn): phần phụ thuộc vào ảnh cụ thể.

## Thêm channel mới (CEO duyệt)

1. `cp -R channel/_template channel/<tên>`
2. Điền với CEO, theo thứ tự: `channel.md` → `prompt_suno.md` → `naming.md` + `album_rules.md` → `visual.md` + `model/` →
   `publish.md` → `video.json` + `image_source/logo.png` → `translate.yaml` → `CLAUDE.md`.
   Kiến thức nền + checklist thiết lập kênh trên YouTube: `docs/seo-youtube/` (04, 08 §A).
3. Kiểm: `python3 .claude/skills/pm-production/scripts/lint_skills.py` (skill không được nhắc tới kênh),
   `album.py board --channel <tên>`.
4. Thêm dòng vào bảng dưới.

## Channels hiện có

| Channel | Thể loại | Trạng thái |
|---|---|---|
| [shelter_stone_gospel](shelter_stone_gospel/CLAUDE.md) | Christian gospel blues (kho bài Suno, album 60–80 phút) | đang dựng, kênh chính |
| [lamplight_gospel](lamplight_gospel/CLAUDE.md) | Christian Gospel Blues / Southern Gospel Soul | **dừng** (CEO 2026-09-28: định hướng fail); giữ file và video đã đăng, không làm album mới; file kênh theo quy trình cũ |
