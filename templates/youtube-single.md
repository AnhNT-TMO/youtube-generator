# YouTube — <Song Title> (bài đăng riêng)

<!-- Soạn bằng skill youtube-publish, chế độ single (.claude/skills/youtube-publish/SKILL.md). Kiểm tra: publish.py check <single> --video <file> -->

- **Trạng thái:** chưa upload
- **Video URL:**
- **Ngày upload:**
- **File video:** `video/<NNN-slug>.mp4` (<độ dài>), dựng từ `audio/master/<NNN-slug>.wav`
- **Bài gốc:** `<track id>` · Track <NN> của album `<Album Title>` (<link video album hoặc "album chưa lên">)

## Title

Đề xuất (<n>/70 ký tự):

```
<công thức title single trong channel/<ch>/publish.md>
```

Phương án khác:

- `...`
- `...`

## Description

Mẫu chung của channel (`channel.md`), bỏ khối TRACKLIST; viết ABOUT THIS VIDEO + FULL ALBUM (+ LYRICS).

```
<mẫu description của channel, nguyên văn, trừ dòng TRACKLIST và placeholder chapters; thay vào đó:>
🎵 ABOUT THIS VIDEO
<3–4 câu>

🎧 FULL ALBUM
"<Album Title>" · <n> original songs · <độ dài>: <link video album>

LYRICS
<chỉ các dòng được hát, không tag [..], không chỉ dẫn nhạc cụ>
```

## Tags

Tags mặc định của channel + 5–12 tags theo bài, đã research bằng `publish.py tags` (<n>/500 theo cách YouTube đếm):

```
<defaults>, <song tags>
```

| Tag | Nhóm | Autocomplete |
|---|---|---|

## Thumbnail

- File upload: `thumbnail.jpg` (hoặc `thumbnail.png` nếu ≤ 2 MB), <w>×<h>, <dung lượng> MB. Prompt: `thumbnail-prompt.md`.

## Cài đặt khi upload (YouTube Studio)

Chi tiết + lý do: `.claude/skills/youtube-publish/references/studio.md` (mục *Bài đăng riêng*).

| Mục | Chọn |
|---|---|
| Playlist | `<Channel> · Songs` |
| Audience | No, it's not made for kids |
| AI use (altered or synthetic content) | **Yes** (AI generated music) |
| Paid promotion | No |
| Automatic chapters | Bỏ tick |
| Category | Music |
| Video language | English |
| License | Standard YouTube License |
| Allow embedding | Có |
| Comments | Bật, sort theo Top |
| Subtitles | Tùy chọn: .srt lời bài (Whisper) |
| End screen | **Video → video album** + Subscribe, 20 s cuối, tránh góc dưới phải/trên phải. Album chưa lên: chỉ Subscribe |
| Cards | 1 card **Video → video album** ở ~ sau điệp khúc đầu (<m:ss>). Album chưa lên: bỏ qua |
| Visibility | Unlisted → kiểm tra → Public/Schedule |

## Pinned comment

Comment đầu tiên của chủ kênh: đăng bằng tài khoản channel ngay sau khi publish → ⋮ → **Pin** → bấm ❤️.
Không ghi timestamp trần (nó nhảy trong video này); muốn trỏ tới đúng bài trong album thì dùng link `?t=<giây>`.

```
<emoji kênh> Thank you for spending these minutes with "<Song Title>". <emoji kênh>

<emoji> <câu hỏi mời bình luận, gắn với hook của bài>

💬 "<câu hook, đúng lời hát>"

🎧 The full album "<Album Title>" (<n> songs · <độ dài>): <link video album>

💛 If this song brought you peace:
👍 Like · 🔔 Subscribe · 🔁 Share it with someone <…>

<emoji> <câu kết>
```

## Kiểm tra trước khi bấm Publish

- [ ] `publish.py check <single> --video <file>` không còn ❌
- [ ] Nghe 15 giây đầu như người lạ (CLAUDE.md §3): `audio/master/previews/00-opening.mp3`
- [ ] Đã chọn AI use = Yes
- [ ] End screen + card trỏ đúng video album (nếu album đã lên)
- [ ] Đăng comment đầu tiên bằng tài khoản channel → Pin → ❤️
- [ ] Sau upload: điền Video URL, ngày; `singles:` trong front matter bài gốc; retention 0:15 / 0:30 / 1:00 sau 48 giờ và 7 ngày

## Analytics (cập nhật sau upload)

| Ngày | Views | CTR | Retention 0:15 | Retention 0:30 | Retention 1:00 | Avg view duration | Click sang album | Ghi chú |
|---|---|---|---|---|---|---|---|---|
