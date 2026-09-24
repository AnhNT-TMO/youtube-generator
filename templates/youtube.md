# YouTube — <Album Title>

<!-- Soạn bằng skill youtube-publish (.claude/skills/youtube-publish/SKILL.md). Kiểm tra: publish.py check <album> --video <file> -->

- **Trạng thái:** chưa upload
- **Video URL:**
- **Ngày upload:**
- **File video:** `video/<NNN-slug>.mp4` (<độ dài>), dựng từ `<file audio>`

## Title

Đề xuất (<n> ký tự):

```
<Title Track> <emoji> <Genre phrase> for <Use-case> & <Feeling> | Full Album
```

Phương án khác:

- `...`
- `...`

## Description

Mẫu chung của channel (`channel.md`), chỉ viết ABOUT THIS VIDEO + TRACKLIST.

```
<mẫu description của channel, nguyên văn, với ABOUT THIS VIDEO (3–5 câu) và TRACKLIST đã điền>
```

### Chapters

Sinh bởi `publish.py chapters <album> --audio <file video>`.

```
0:00 <Track 01>
...
```

## Tags

12 tags mặc định của channel + ~10 tags theo chủ đề album (<n>/500 theo cách YouTube đếm):

```
<defaults>, <album tags>
```

| Tag | Vì sao |
|---|---|

## Thumbnail

- File: `thumbnail.png` (<w>×<h>), <dung lượng> MB (≤ 2 MB).

## Cài đặt khi upload (YouTube Studio)

Chi tiết + lý do: `.claude/skills/youtube-publish/references/studio.md`.

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
| Subtitles | Bỏ qua (tùy chọn: .srt lời bài bằng Whisper) |
| End screen | Chỉ Subscribe, 20 s cuối, tránh góc dưới phải/trên phải |
| Cards | Bỏ qua cho tới khi có album khác |
| Visibility | Unlisted → kiểm tra → Public/Schedule |

## Pinned comment

Comment đầu tiên của chủ kênh: đăng bằng tài khoản channel ngay sau khi publish → ⋮ → **Pin** → bấm ❤️.

```
<emoji kênh> Welcome to <Channel>. <câu cảm ơn theo publish.md> <emoji kênh>

<emoji> <câu hỏi mời bình luận>

🎶 TRACKLIST 🎶
1️⃣ 0:00 <Track 01>
...

✨ Don't miss
🔥 <ts> <bài cao trào> · <tagline>
🌅 <ts> <bài chuyển sang hy vọng> · <tagline>
🌙 <ts> <bài kết> · <tagline>

💛 If this music brought you peace:
👍 Like · 🔔 Subscribe · 🔁 Share it with someone <…>

<emoji> <câu kết>
```

## Kiểm tra trước khi bấm Publish

- [ ] `publish.py check <album> --video <file>` không còn ❌
- [ ] Upload Unlisted, bấm thử các chapter (nhất là dòng "ước lượng")
- [ ] Nghe 15 giây đầu như người lạ (Gate Track 01, CLAUDE.md §3)
- [ ] Đã chọn AI use = Yes
- [ ] Đăng comment đầu tiên bằng tài khoản channel → Pin → ❤️
- [ ] Sau upload: điền Video URL, ngày upload; retention 0:15 / 0:30 / 1:00 sau 48 giờ và 7 ngày

## Analytics (cập nhật sau upload)

Thử nghiệm của album (plan.yaml `experiment`, trống = house sound): …
Bài điểm nhấn (plan.yaml `highlight`): slot …, mốc thời gian trong video …–… (đọc retention đúng đoạn này), single: `singles/NNN-slug`

| Ngày | Views | CTR | Retention 0:15 | Retention 0:30 | Retention 1:00 | Avg view duration | Ghi chú |
|---|---|---|---|---|---|---|---|
