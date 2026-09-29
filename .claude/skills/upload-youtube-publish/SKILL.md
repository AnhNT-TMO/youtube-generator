---
name: upload-youtube-publish
description: Write everything needed to upload an album video to YouTube and walk the owner through YouTube Studio - title (from the PM's album.md brief, drawing on an entry of the R&D phrase bank research/phrase-bank/ - common prayer phrases may be verbatim, other channels' names/branding never - ≤ 70 chars), description = the channel's fixed template in channel/<ch>/publish.md with only its fill-in slots written per album (ABOUT THIS VIDEO when the template has one) + a TRACKLIST of chapters read from the album's assembly.json, tags (channel defaults + album tags researched with YouTube autocomplete, filled up to the 500-char limit as YouTube counts it), thumbnail check, pinned comment, and what to choose on every Studio screen (AI use / altered content, audience, chapters, end screen, cards, subtitles, visibility). Writes <album>/youtube.md and checks it with scripts/publish.py (video-generator `video.py package` runs the same check before zipping). Use when the PM or the owner says "upload", "đăng video", "soạn youtube", "soạn title/description", "viết description", "tags", "chapters/timestamps/tracklist", "thumbnail", "YouTube Studio chọn gì", "AI use chọn Yes hay No", "end screen", "cards", "subtitles", "visibility", or asks what to put in any YouTube upload field. Does NOT render video (video-generator), mix audio (audio-album-assembly) or write the Short's youtube.md (video-shorts).
---

# YouTube publish (video album)

Input: một album xong phần hình + tiếng `channel/<ch>/albums/<NNN-slug>/`: `album.md` (brief của PM, tracklist),
`tracks/*.md`, `assembly.json` (audio-album-assembly), `thumbnail.png`, video đã render (trên GPU server:
`video/video.mp4.json`, `video/remote.json`). Luật đóng gói của kênh: `channel/<ch>/publish.md` (mẫu description, tags
mặc định, công thức title, pinned comment). Skill này là quy trình; mọi câu chữ riêng của kênh nằm trong `publish.md`.
Output: `<album>/youtube.md` (mẫu `templates/youtube.md`), mỗi ô trong một khối ``` để dán.

- **Brief của PM là luật** (CLAUDE.md §0): `album.md` → `brief.title_direction` (giọng + lời cầu xin của title),
  `description_angle` (ABOUT THIS VIDEO nói gì, chỉ khi mẫu kênh có đoạn này), `thumbnail_text`, `phrase_bank` (id câu kho), `source` (`ceo` = PM + CEO
  chốt; `rnd` = từ số liệu R&D: rnd-youtube-api, kho câu `research/phrase-bank/`). Brief và `publish.md` mâu thuẫn, hoặc brief trống →
  hỏi PM (`BLOCKED`), không tự chọn.
- **Kho câu R&D** `research/phrase-bank/*.yaml` (+ `.md` để đọc): câu title / chữ thumbnail của các video đang lên nhanh
  trong ngách. Luật CEO (2026-09-28): câu cầu nguyện phổ biến / câu kinh điển **được dùng nguyên văn** (không ai sở hữu,
  như Kinh Thánh), kể cả khi nhiều kênh đã dùng; ưu tiên câu còn đang tăng (`fresh`, `vpd_x` cao); **không bao giờ** lấy
  tên, logo, branding, hình của kênh khác. Ghi id câu vào `album.md` → `brief.phrase_bank` và `youtube.md` → dòng
  **Kho câu (phrase bank)**. `check`: ❌ khi title / `brief.thumbnail_text` / `brief.bar_line` có tên một kênh trong kho
  (tên chỉ gồm chữ thể loại mà mẫu kênh mình cũng dùng thì chỉ ⚠️); ℹ️ mỗi câu kho trùng ≥ 4 chữ liền (bỏ lời gọi đầu
  câu) với phần lời xin của title hoặc chữ thumbnail, kèm vpd / vpd_x / fresh và số kênh có cụm đó trong title
  (`raw/videos-*.json`); ⚠️ khi trùng title ngoài kho. Đánh dấu `used_by` là việc của PM ngay sau `album.py build`
  (`yt.py bank use`); `check` cảnh báo khi id trong `brief.phrase_bank` chưa có album này trong `used_by`. Skill này
  không ghi kho.
- **Mẫu description của kênh** là `publish.md` → *Description YouTube mặc định*, dùng **nguyên văn**. Kênh mới chờ
  CEO gửi mẫu: khi khối mẫu còn chỗ `<…>`, `check` báo ❌ và `video.py package` không đóng gói. Không tự viết thay mẫu.

Chọn gì ở từng màn hình YouTube Studio, kèm lý do: `references/studio.md` (đọc khi chủ kênh hỏi một nút, hoặc trước khi
hướng dẫn upload).

```bash
SK=.claude/skills/upload-youtube-publish; PY=$SK/.venv/bin/python; P=$SK/scripts/publish.py   # gốc repo, chạy trên Mac
# lần đầu: python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt
$PY $P chapters <album>                        # dòng chapter từ assembly.json (bài i = floor(start_s), bài 1 = 0:00), không có dòng TRACKLIST
$PY $P check    <album> [--video <file>]       # mẫu kênh, chapters, độ dài master (album_rules.md), độ dài video, kho câu, tags, thumbnail
$PY $P tags --expand "<seed>, <seed>"          # người ta gõ gì sau mỗi seed (ứng viên tag)
$PY $P tags     <album> [--trends]             # kiểm khối ## Tags: có người gõ? lượng tìm? trùng tên kênh tham khảo?
```

## Các bước

1. **File nào được upload.** Video album render bởi video-generator bước 2 nằm trên GPU server: ffprobe của nó ở
   `<album>/video/video.mp4.json`, audio nó dùng ở `video/remote.json` → `audio` (phải là master trong `assembly.json`).
   `check` so độ dài video với `assembly.json` `duration_s`; lệch > 3 s = video dựng từ bản ghép khác, chapters sai →
   báo PM render lại từ master. File video có trên máy thì thêm `--video <file>`. `youtube.md` thường soạn trước khi
   render: chưa có video / thumbnail chỉ là ⚠️; master ngoài `length_min` của `channel/<ch>/album_rules.md` là ❌ (PM
   thêm/bớt bài).
2. **Chapters.** `publish.py chapters <album>` in khối các dòng chapter từ `assembly.json` (không đo audio: ghép nhẹ,
   crossfade ngắn, `start_s` là chỗ bài bắt đầu trong master). Khối không có dòng `TRACKLIST`: mẫu kênh đã có dòng đó,
   dán khối vào ngay dưới (`check` ❌ khi description có 2 dòng `TRACKLIST`). Luật YouTube (không thì không có chapters): dòng đầu `0:00`, ≥ 3
   chapters, mỗi chapter ≥ 10 s, tăng dần, timestamp đầu dòng + dấu cách + tên bài (không gạch, không "01."), không dòng
   khác xen giữa, không timestamp nào khác trong description. Tên bài đúng như `tracks/*.md`.
3. **Title** (mục Title), từ brief + kho câu.
4. **Description**: mẫu kênh nguyên văn, chỉ điền chỗ trống của mẫu (TRACKLIST; ABOUT THIS VIDEO khi mẫu có) (mục Description).
5. **Tags**: research trước (`tags --expand`), viết vào `youtube.md`, kiểm bằng `tags <album>` (mục Tags).
6. **Pinned comment** theo `publish.md` → *Pinned comment*.
7. **Check.** `publish.py check <album>` → sửa mọi ❌. Còn chờ CEO (mẫu description, câu pinned comment) → báo PM
   đúng dòng nào đang chờ, không điền bừa.
8. **Studio.** Hướng dẫn theo `references/studio.md` khi chủ kênh upload; câu hỏi chính sách (AI, kids, bản quyền) →
   kiểm lại trang YouTube Help đang chạy (WebFetch).
9. **Sau upload:** Video URL + ngày vào `youtube.md`; pinned comment;
   dịch title + description: skill upload-youtube-translate (cần Video URL). Số liệu 48 giờ / 7 ngày: PM
   (`pm-production` results).

## Title

Công thức, emoji, genre phrase: `channel/<ch>/publish.md` → *Title*. Luật chung:

- **Nguồn câu:** `brief.title_direction` (+ câu kho trong `brief.phrase_bank`) → dùng nguyên văn hoặc sửa, rồi đặt vào
  công thức của kênh. Tên / branding kênh khác = ❌ (`check`). Title và chữ thumbnail bổ sung nhau, không lặp y hệt.
- **≤ 70 ký tự** (`check` chặn; YouTube cho 100 nhưng cắt ở ~60–70 trên search và mobile). Đếm bằng `len()`, tính cả emoji.
  Dài quá thì bỏ theo thứ tự, dừng ngay khi vừa: (1) chữ đệm ("a", "the", "and", "your"); (2) cảm xúc / use-case thứ hai;
  (3) genre phrase ngắn hơn (giữ một cụm có người gõ: `publish.py tags --try "<cụm>"`). Không bao giờ cắt phần công thức
  kênh đặt đầu.
- Tối đa một emoji, trong bảng emoji của kênh. Không `<` `>` (YouTube từ chối).
- Chỉ ghi độ dài có thật: không "1 Hour" cho album 50 phút (`check` so với độ dài video). Tiếng Anh.
- Đưa 1 đề xuất + 2 phương án, đều ≤ 70, kèm số ký tự và id câu kho (vpd, vpd_x, fresh) mỗi phương án dựa trên.

## Description

Mẫu kênh trong `publish.md` → *Description YouTube mặc định* dùng **nguyên văn** (`check` so từng dòng; dòng mẫu bắt
đầu bằng `[` là chỗ điền, phải thay). Mỗi album chỉ viết:

1. **ABOUT THIS VIDEO** (chỉ khi mẫu kênh có chỗ này): thay `[Write 3–5 sentences here …]` bằng 3–5 câu tiếng Anh theo `brief.description_angle` (và
   `publish.md` → *ABOUT THIS VIDEO* nếu có: điều mẫu đã nói thì không lặp):
   (1) album nói về ai / nỗi gì / xin gì (câu chuyện của brief), độ dài, số bài; (2) một câu hát thật của bài 1 (từ
   `## Lyrics` của `tracks/01-*.md`), trong ngoặc kép; (3) âm thanh trong một dòng; (4, tùy chọn) bài kết và cảm giác cuối.
   Cụ thể cho album này, không hứa điều video không có.
2. **TRACKLIST**: vào chỗ `[` của mẫu (dưới dòng `TRACKLIST` của mẫu), dán nguyên khối của `publish.py chapters <album>`.

Không thêm gì khác: không dòng AI (AI khai báo bằng nút trong Studio, `references/studio.md`), không dòng bản quyền,
không điều `publish.md` cấm, trừ khi PM bảo. Giới hạn: 5000 ký tự, ≤ 60 hashtag (YouTube Help 6390658: quá 60 thì bỏ qua toàn bộ; 3 hashtag hiện trên title).

## Tags

`publish.md` → *Tags YouTube mặc định* (luôn đủ) + **tag riêng của album lấp cho tới sát 500** (`check` cảnh báo < 470), không trùng tag mặc định, theo các nhóm trong
`publish.md` → *Tags: các nhóm* nếu có (chủ đề / lời cầu xin của album, use-case, subgenre, nhạc cụ chính, format).
Tổng ≤ 500 ký tự **theo cách YouTube đếm**: dấu phẩy tính, tag có dấu cách tính thêm 2 (ngoặc kép). `check` tính.

**Research trước, không viết tag vì nghe hợp.** Tag tốt = cụm người ta thật sự gõ *và* người gõ muốn đúng loại nhạc này.
1. `publish.py tags --expand "<seed>, <seed>"` với 4–8 seed từ album (thể loại, chủ đề, use-case, nhạc cụ, "songs about
   <chủ đề>"): gợi ý autocomplete YouTube (US) = cụm người ta gõ, gõ nhiều nhất trước.
2. Chọn theo nhóm từ các gợi ý đó, giữ đúng dạng người ta gõ (số nhiều, thứ tự chữ, cả cụm).
3. Lượng tìm (tùy chọn): `publish.py tags <album> --trends` thêm cột Google Trends (YouTube Search, 5 năm), thang theo dòng
   `**Mốc Google Trends:** \`<cụm>\` = <số>` trong `publish.md` (kênh chưa có dòng này thì bỏ bước này). Giữ tag Trends ≥ 1;
   bỏ tag chung chung khổng lồ.
4. Kiểm cả danh sách: `publish.py tags <album>`. ✅ có người gõ · ⚠️ chỉ dạng dài hơn được gõ (dùng dạng đó), ra thứ khác,
   hoặc Trends ≈ 0 · ❌ không ai gõ, hoặc chứa tên kênh tham khảo (lấy từ `channel` của kho câu). Tên bài / album giữ
   làm tên riêng dù chưa ai gõ (một tag).
5. Đọc ý định (cột cuối; máy không đọc được): bỏ tag mà người gõ muốn thứ khác (beat, instrumental, podcast, ca sĩ khác,
   ngôn ngữ khác). Bẫy ý định đã gặp của kênh ghi ở `publish.md` → *Tags: các nhóm*.
6. Bảng trong youtube.md: `| Tag | Nhóm | Autocomplete / Trends |` (`check` cảnh báo khi thiếu cột bằng chứng).

## Pinned comment (comment đầu tiên của kênh)

Đăng bằng tài khoản kênh ngay sau khi publish → **Pin** + ❤️. Mẫu + emoji: `publish.md` → *Pinned comment* (kênh chưa có
mẫu → hỏi PM). Timestamp trong comment phải đúng chapters của description (`check` chặn); chỉ hứa điều có thật.

## Các ô khác trong youtube.md

- **Thumbnail:** `thumbnail.png` của album (skill thumbnail-prompt), 16:9, ≤ 2 MB (không thì `thumbnail.jpg`; `check`
  chọn). Xem ảnh, ghi chữ trên ảnh có đọc được ở cỡ điện thoại không, và chữ đó là `brief.thumbnail_text`.
- **Bảng cài đặt Studio** và **checklist trước khi Publish**: chép từ `templates/youtube.md`, chỉnh theo album.

## Nguyên tắc

- **Nguồn chapters là `assembly.json` của đúng master mà video dùng.** Video dựng từ bản khác → chapters sai: render lại.
- **Câu được, branding không** (CEO 2026-09-28): câu cầu nguyện phổ biến trong kho được dùng nguyên văn; không bao giờ
  lấy tên kênh, logo, branding, hình hay nguyên danh sách tag của kênh khác. Câu đã bị nhiều kênh chép mà không còn tăng
  (ℹ️ của `check`: không fresh, vpd_x thấp) → nói với PM.
- **Khai báo trung thực:** nhạc AI → AI use = Yes. Không bao giờ khuyên giấu.
- Claude không nghe được: sau khi upload Unlisted, nhờ chủ kênh bấm thử vài chapter.
