# YouTube: <Song Title> (Short)

<!-- Soạn bằng skill video-shorts (.claude/skills/video-shorts/SKILL.md). File này ở albums/NNN-slug/short/youtube.md.
     Kiểm tra: shorts.py check <album>/short -->

- **Trạng thái:** chưa upload
- **Video URL:**
- **Ngày upload:**
- **Giờ đăng dự kiến:** <theo channel/<ch>/publish.md → Giờ đăng>
- **Video:** 1080×1920, <độ dài> s, đoạn <in>–<out> của bài `<song-slug>` (`short.json`); file trên GPU server, nằm trong zip S3 của album (`short/`, ghi ở `../s3-package.json`)
- **Video đích (Related video):** album `<NNN-slug>` · <Video URL của album, hoặc "chưa upload: đăng album trước">
- **Version đóng gói:** <trục đang thử, hoặc "mặc định">
- **Kho câu (phrase bank):** <id câu R&D mà title / hook dùng, hoặc "không">

## Title

Đề xuất (<n>/60 ký tự):

```
<công thức title Short trong channel/<ch>/publish.md → Shorts>
```

## Description

```
<mẫu description Short trong channel/<ch>/publish.md → Shorts, đã điền, có link album>
```

## Tags

```
<tags mặc định của kênh>, <Song Title>, <Album Title>
```

## Pinned comment

```
<mẫu pinned comment Short trong channel/<ch>/publish.md → Shorts, có link album>
```

## YouTube Studio (chủ kênh làm khi upload)

1. Upload file `short/<NNN-slug>-short.mp4` từ zip của album `<NNN-slug>-<time>.zip` (một zip cho album + Short; dọc,
   ≤ 3 phút → YouTube tự xếp vào Shorts; không cần #shorts).
2. Title, description, tags: dán từ `short/upload/*.txt` trong zip.
3. **Altered or synthetic content = Yes** (nhạc do AI tạo). Audience: **No, it's not made for kids**.
4. **Related video:** chọn video album ở trên (Studio desktop → Content → Short → Related video → Save).
5. Visibility: Schedule theo giờ đăng dự kiến; album phải public trước giờ này.
6. Sau khi public: đăng pinned comment bằng tài khoản kênh → Pin; điền Video URL + ngày vào file này.

## Analytics (sau 48 giờ và 7 ngày)

| Ngày | Views | Engaged views | Viewed vs swiped away | Avg % viewed | Subs | Click Related video | Ghi chú |
|---|---|---|---|---|---|---|---|
