# YouTube: <Album Title>

<!-- Soạn bằng skill upload-youtube-publish (.claude/skills/upload-youtube-publish/SKILL.md). Kiểm tra: publish.py check <album> -->

- **Trạng thái:** chưa upload
- **Video URL:**
- **Ngày upload:**
- **File video:** `video/video.mp4` trên GPU server (<độ dài>), dựng từ `audio/master/<NNN-slug>.wav` (`assembly.json`)
- **Brief:** `album.md` → brief (<ceo | rnd: báo cáo R&D nào>)
- **Kho câu (phrase bank):** <id câu kho mà title / chữ thumbnail dùng (nguyên văn hoặc chuyển thể), hoặc "không">

## Title

Đề xuất (<n>/70 ký tự, từ <id câu kho>):

```
<title theo công thức trong channel/<ch>/publish.md → Title>
```

Phương án khác:

- `...`
- `...`

## Description

Mẫu chung của kênh (`publish.md` → *Description YouTube mặc định*), nguyên văn; chỉ điền các chỗ `[` của mẫu (TRACKLIST; ABOUT THIS
VIDEO nếu mẫu có).

```
<mẫu description của kênh, nguyên văn, với chapters (khối `publish.py chapters`) ở chỗ TRACKLIST; ABOUT THIS VIDEO nếu mẫu có>
```

### Chapters

Sinh bởi `publish.py chapters <album>` (từ `assembly.json`).

```
0:00 <Track 01>
...
```

## Tags

Tags mặc định của kênh + tag theo chủ đề album lấp tới sát 500, đã research bằng `publish.py tags` (<n>/500 theo cách YouTube đếm):

```
<defaults>, <album tags>
```

| Tag | Nhóm | Autocomplete / Trends |
|---|---|---|

## Thumbnail

- File: `thumbnail.png` (<w>×<h>), <dung lượng> MB (≤ 2 MB, không thì `thumbnail.jpg`); chữ trên ảnh: <brief.thumbnail_text>.

## Cài đặt khi upload (YouTube Studio)

Chi tiết + lý do: `.claude/skills/upload-youtube-publish/references/studio.md`.

| Mục | Chọn |
|---|---|
| Playlist | `<Channel> · Full Albums` |
| Audience | No, it's not made for kids |
| AI use (altered or synthetic content) | **Yes** (AI generated music) |
| Paid promotion | No |
| Automatic chapters | Bỏ tick |
| Category | Music |
| Video language | English |
| License | Standard YouTube License |
| Allow embedding | Có |
| Comments | Bật, sort theo Top |
| Subtitles | Bỏ qua |
| End screen | Chỉ Subscribe, 20 s cuối, tránh góc dưới phải/trên phải |
| Cards | Bỏ qua cho tới khi có album khác |
| Visibility | Unlisted → kiểm tra → Public/Schedule |

## Pinned comment

Comment đầu tiên của chủ kênh: đăng bằng tài khoản kênh ngay sau khi publish → ⋮ → **Pin** → bấm ❤️.

```
<mẫu pinned comment trong channel/<ch>/publish.md → Pinned comment, đã điền>
```

## Kiểm tra trước khi bấm Publish

- [ ] `publish.py check <album>` không còn ❌
- [ ] Upload Unlisted, bấm thử vài chapter
- [ ] Nghe 15 giây đầu như người lạ (CLAUDE.md §6)
- [ ] Đã chọn AI use = Yes
- [ ] Đăng comment đầu tiên bằng tài khoản kênh → Pin → ❤️
- [ ] Sau upload: điền Video URL, ngày upload; đăng Short sau album

## Analytics (cập nhật sau upload)

| Ngày | Views | CTR | Retention 0:15 | Retention 0:30 | Retention 1:00 | Avg view duration | Ghi chú |
|---|---|---|---|---|---|---|---|
