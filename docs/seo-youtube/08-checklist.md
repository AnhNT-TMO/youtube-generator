# 08. Checklist

Gộp từ các file 01–07. Việc đã có công cụ trong repo ghi kèm lệnh/skill.

## A. Kênh mới

**Nội dung kênh (repo)**
- [ ] `cp -R channel/_template channel/<tên>`, điền theo `channel/README.md`.
- [ ] Nghiên cứu dòng nhạc (02 §1): định nghĩa, phân loại theo chủ đề, khán giả theo khu vực, 10 kênh tiêu biểu (view/tháng, từ khóa, chủ đề, giờ đăng, hình).
      Số liệu kênh/video: skill rnd-youtube-api (`yt.py channel/videos/fast`).
- [ ] Câu chuyện hình một câu (Ai · Làm gì · Ở đâu), hằng số + trục biến thể, tone màu chủ đạo → `visual.md` (03).
- [ ] `publish.md`: mẫu description (200 ký tự đầu có tên kênh + cụm thể loại chính), công thức title ≤ 70, tags mặc định đã research
      (`publish.py tags --try "<tags>" --trends`), pinned comment (06).
- [ ] Giờ vàng đăng video trên Google Trends (YouTube Search, 7 ngày, thị trường chính), ghi vào `publish.md` (06 §2).
- [ ] `translate.yaml`: ngôn ngữ theo thị trường mục tiêu.

**Trên YouTube (04)**
- [ ] Tạo kênh (Brand Account), tên + handle không gần kênh tham khảo.
- [ ] Ảnh đại diện + banner đúng kích thước, cùng câu chuyện hình.
- [ ] General: USD · Channel: keywords, country · Advanced: **not made for kids**.
- [ ] **Xác minh số điện thoại** (upload > 15 phút, thumbnail tùy chỉnh).
- [ ] Upload defaults: description mẫu, tags mặc định, visibility Private, Standard License, category Music, language English,
      comments "hold potentially inappropriate", (khi YPP) bật mọi loại quảng cáo.
- [ ] Community: chặn/giữ comment có link, giữ chat không phù hợp.
- [ ] About + email liên hệ; playlist `<Kênh> · Full Albums`.
- [ ] Video đầu tiên trong vòng 7 ngày.

## B. Mỗi video

**Trước khi upload** (upload-youtube-publish)
- [ ] Title ≤ 70, lời cầu xin theo `brief.title_direction` (câu kho R&D, id trong `brief.phrase_bank`), có cụm thể loại người ta gõ thật,
      không tên/branding kênh khác, không hứa sai (thời lượng, "lyrics"…).
- [ ] Description: mẫu kênh nguyên văn, chỉ điền TRACKLIST (chapters từ `assembly.json` của đúng master video dùng; ABOUT THIS VIDEO nếu mẫu có).
- [ ] Tags: mặc định + tag riêng của album đã research lấp tới sát 500 ký tự, tag quan trọng nhất đầu tiên.
- [ ] Thumbnail 16:9, ≤ 2 MB, tương phản đủ khi thu nhỏ, không đứt mạch câu chuyện kênh, chữ đọc được trên điện thoại.
- [ ] 15 giây đầu video có "chữ ký" (CLAUDE.md §6); hình đẹp nhất ở đầu.
- [ ] `publish.py check` sạch ❌.

**Khi upload** (`references/studio.md`)
- [ ] Private trước; altered/synthetic content = Yes; not made for kids.
- [ ] Màn hình **Checks**: không claim (kênh chưa bật kiếm tiền: bắt buộc).
- [ ] End screen + card dẫn sang video/playlist liên quan; thêm vào playlist.
- [ ] Public / schedule vào giờ vàng.

**Sau khi đăng**
- [ ] Pinned comment (tracklist, câu hỏi, CTA), ❤️.
- [ ] Video URL vào `youtube.md`; dịch title + description (upload-youtube-translate).
- [ ] Trả lời comment thật trong 1–2 ngày đầu.
- [ ] 48 h và 7 ngày: CTR, retention 0:15 / 0:30 / 1:00, average view duration, traffic sources, search terms → pm-production `results.py` (05 §5).

## C. Hằng tuần

- [ ] Studio: Copyright (claim mới), Monetization, strikes, email YouTube (07).
- [ ] So sánh các album mới nhất theo bảng đọc số liệu (05 §5); ghi điều học được vào file kênh, không vào skill.
- [ ] Analytics → Audience: kênh/video khác khán giả xem → PM tra bằng rnd-youtube-api, câu hay vào kho câu.
- [ ] Search terms của video đã đăng: từ khóa lạ đáng thêm vào metadata hoặc thành ý tưởng album.
- [ ] Lịch mùa (Halloween, Giáng Sinh, Tết…): album theo mùa đã plan trước vài tuần chưa?

## D. Khi có sự cố (07)

- [ ] **Không xóa video** bị gậy / bị claim.
- [ ] Ghi lại trong ≤ 2 h: kênh, video, loại (claim / TKT / BKT xịt / gậy cộng đồng / gậy bản quyền), lý do Studio nêu.
- [ ] Hỏi Creator Support để xác nhận lý do (TKT/BKT xịt).
- [ ] Gom bằng chứng: `songs/manifest.json` (lượt Suno, clip id, prompt, ngày tạo), `songs/<bài>.md`, `album.md`, `tracks/*.md`, `assembly.json`.
- [ ] Dispute / appeal / counter notification đúng kênh, trong 24–48 h; theo dõi 2 ngày/lần.
- [ ] Đóng case → ghi bài học vào file kênh.
