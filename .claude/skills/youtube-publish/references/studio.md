# YouTube Studio: chọn gì ở từng màn hình

Thứ tự theo luồng upload (Details → Video elements → Checks → Visibility). Lập cho kênh mới, 1 video/album,
giữ đúng tới 2026-09. Chính sách có thể đổi: với câu hỏi về policy (AI, kids, bản quyền), kiểm tra lại trang Help
đang chạy trước khi trả lời.

## 1. Details

| Mục / nút | Chọn | Vì sao |
|---|---|---|
| Title | khối Title trong `youtube.md` | format ở SKILL.md |
| Description | khối Description (đã có TRACKLIST) | chapters chỉ được tạo từ description |
| Thumbnail → Upload file | `thumbnail.png` (≤ 2 MB) | không dùng ảnh tự trích từ video |
| Playlists | `<Channel Name> · Full Albums` (tạo lần đầu; tên ở `publish.md`) | gom album, có trang playlist để trỏ end screen/cards sau này |
| Audience | **No, it's not made for kids** | "made for kids" tắt comments, end screen, cards, thông báo |
| Age restriction | No | |
| **AI use** ("Was AI used to generate or edit your content…?") | **Yes** | YouTube liệt kê "AI generated music" trong *Examples of content creators need to disclose*. Ba gạch đầu dòng trên form chỉ là ví dụ; dòng dưới ghi rõ *realistic sounds made or edited with AI*. Nhãn chỉ nằm trong phần mô tả mở rộng với chủ đề thường; không khai báo có thể bị YouTube tự gắn nhãn, gỡ video hoặc ảnh hưởng YPP. Nguồn: https://support.google.com/youtube/answer/14328491 |

**Show more:**

| Mục | Chọn | Vì sao |
|---|---|---|
| Paid promotion | No | |
| Automatic chapters | **Bỏ tick** | đã có chapters đo trên file thật; để YouTube tự tạo có thể đè/lệch |
| Featured places / Automatic concepts | bỏ qua | |
| Tags | khối Tags trong `youtube.md` | |
| Language and captions certification | Video language: **English**; certification: None | |
| Recording date and location | bỏ qua | |
| License | Standard YouTube License | |
| Distribution | Allow embedding: **Có**; Publish to subscriptions feed: **Có** | |
| Shorts remixing | Để mặc định (cho phép) | người khác làm Shorts từ nhạc của mình = thêm đường dẫn về video |
| Category | **Music** | |
| Comments and ratings | Comments On (không giữ lại để duyệt hết); Sort by **Top**; Show like count: Có | |

## 2. Video elements

| Mục | Chọn | Vì sao |
|---|---|---|
| Subtitles | **Bỏ qua** lúc upload | YouTube tự tạo phụ đề tiếng Anh nhưng với nhạc thường sai. Nếu muốn phụ đề lời bài: nhờ Claude tạo `.srt` bằng Whisper (skill verification-audio có sẵn) từ ĐÚNG audio của video, upload sau |
| End screen | **Add → chỉ Subscribe**, trong 20 s cuối | kênh chưa có video khác để trỏ. Không đặt ở **góc dưới phải** (video có sẵn hiệu ứng like/subscribe) hay **góc trên phải** (logo). Đặt giữa hoặc dưới trái |
| End screen: Import from video | Bỏ qua cho tới khi có video khác | |
| End screen (khi có album sau) | quay lại video cũ, thêm **Video → Most recent upload** hoặc playlist Full Albums | kéo người nghe cũ sang album mới |
| Cards | **Bỏ qua** cho tới khi có album/playlist khác | sau này: 1 card trỏ album mới, đặt khoảng giữa album (vd. phút 25–30) |

## 3. Checks

- Chờ chạy xong: cần **"Checks complete. No issues found."**
- Nếu có **Copyright claim** (Content ID): chưa publish. Bấm xem đoạn nào bị khớp, báo lại để kiểm tra
  (nhạc Suno hiếm khi bị khớp, nhưng nếu có thì phải xử lý trước).

## 4. Visibility

1. Chọn **Unlisted** trước → Save.
2. Mở video bằng link Unlisted:
   - bấm thử các chapter, nhất là dòng "ước lượng" của `publish.py chapters`, xem có rơi đúng đầu bài không;
   - nghe 15 giây đầu như người lạ (Gate Track 01, CLAUDE.md);
   - kiểm tra nhãn AI đã hiện trong mô tả mở rộng.
3. Sửa nếu cần (sửa description ngay trong Studio, không phải upload lại), rồi chuyển **Public** (hoặc **Schedule**).
   Premiere: không cần cho kênh mới chưa có người đăng ký.

## 5. Sau khi publish

- Đăng **comment đầu tiên** bằng chính tài khoản channel (khối Pinned comment trong `youtube.md`), rồi bấm
  ⋮ → **Pin**, và bấm ❤️ (heart). Comment của chủ kênh có badge tên kênh, ghim lên đầu; timestamps trong đó bấm được.
- Điền Video URL, ngày upload vào `youtube.md`; cập nhật trạng thái `album.md` và dòng album ở CLAUDE.md.
- Sau 48 giờ và 7 ngày: ghi CTR, retention 0:15 / 0:30 / 1:00, avg view duration vào bảng Analytics
  (Studio → video → Analytics → Engagement → Audience retention).

## 6. Bài đăng riêng (single)

Giống mục 1–5, chỉ khác những dòng dưới. Mục đích chính của video bài lẻ là **kéo người nghe sang video album**.

| Mục | Chọn | Vì sao |
|---|---|---|
| Description | không có TRACKLIST; có FULL ALBUM (link album) + LYRICS | một bài thì không có chapters; lời bài giúp tìm kiếm theo câu hát |
| Thumbnail | `thumbnail.jpg` nếu `thumbnail.png` > 2 MB (`thumb.py fit` tự tạo) | PNG 1920×1080 thường 3–4 MB |
| Playlists | `<Channel Name> · Songs` (tạo lần đầu; tên ở `publish.md`) | tách khỏi Full Albums, người xem playlist album không gặp bài lẻ lặp lại |
| Automatic chapters | Bỏ tick | |
| End screen | **Video → chọn video album** + **Subscribe**, 20 s cuối | điểm đến của bài lẻ là album. Album chưa lên: chỉ Subscribe, quay lại thêm sau |
| Cards | 1 card **Video → video album**, sau điệp khúc đầu (xem `vocal_start` + cấu trúc bài, thường ~1:30–2:00) | người đang thích bài thì thấy lời mời nghe cả album. Album chưa lên: bỏ qua |
| Subtitles | tùy chọn: `.srt` lời bài bằng Whisper trên đúng audio của video | video ngắn, có phụ đề giúp người xem không bật tiếng |

**Thứ tự đăng:** nên đăng album trước để link, end screen và card có chỗ trỏ tới. Nếu đăng bài lẻ trước (làm teaser) thì để trống
`album_video_url`, sau khi album lên thì sửa description, comment, end screen và card của bài lẻ ngay trong Studio.
