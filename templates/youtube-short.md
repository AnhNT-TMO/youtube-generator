# YouTube — <Song Title> (Short <A|B>)

<!-- Soạn bằng skill youtube-shorts (.claude/skills/youtube-shorts/SKILL.md). Kiểm tra: shorts.py check <short> -->

- **Trạng thái:** chưa upload
- **Video URL:**
- **Ngày upload:**
- **Giờ đăng dự kiến:** <theo channel/<ch>/publish.md → Giờ đăng>
- **Video:** 1080×1920, <độ dài> s, đoạn <in>–<out> của `<track id>` (`short.json`); file trên GPU server, zip S3 ở `s3-package.json`
- **Video đích (Related video):** `<thư mục album hoặc single>` · <Video URL của video đích, hoặc "chưa upload: upload trước">
- **Version đóng gói:** <trục đang thử, hoặc "mặc định">

## Title

Đề xuất (<n>/60 ký tự):

```
<công thức title Short trong channel/<ch>/publish.md → Shorts>
```

## Description

```
<mẫu description Short trong channel/<ch>/publish.md → Shorts, đã điền>
```

## Tags

```
<tags mặc định của kênh>, <Song Title>, <Album Title>
```

## Pinned comment

```
<mẫu pinned comment Short trong channel/<ch>/publish.md → Shorts>
```

## YouTube Studio (chủ kênh làm khi upload)

1. Upload file `<slug>.mp4` từ zip (dọc, ≤ 3 phút → YouTube tự xếp vào Shorts; không cần #shorts).
2. Title, description, tags: dán từ `upload/*.txt` trong zip.
3. **Altered or synthetic content = Yes** (nhạc do AI tạo). Audience: **No, it's not made for kids**.
4. **Related video:** chọn video đích ở trên (Studio desktop → Content → Short → Related video → Save).
5. Visibility: Schedule theo giờ đăng dự kiến; video đích phải public trước giờ này.
6. Sau khi public: đăng pinned comment bằng tài khoản kênh → Pin; điền Video URL + ngày vào file này.

## Analytics (sau 48 giờ và 7 ngày)

| Ngày | Views | Engaged views | Viewed vs swiped away | Avg % viewed | Subs | Click Related video | Ghi chú |
|---|---|---|---|---|---|---|---|
