# SEO YouTube: tài liệu tổng hợp

Tóm tắt, sắp xếp lại và đối chiếu với xưởng từ một chương trình đào tạo nhân viên SEO YouTube nội bộ của một công ty MCN nhạc
ở Việt Nam (5 module + tài liệu phụ: quy định chạy kênh, quy trình xử lý sự cố, slide "Tối ưu hóa nội dung",
slide "Các phương pháp đẩy kênh", bài "Định hướng hình ảnh kênh"). Bản crawl gốc từ 2026-09-22; số liệu trong đó chủ yếu từ 2022–2023.

Tài liệu gốc là tài liệu nội bộ: ở đây chỉ giữ kiến thức, không giữ tên người, email, Skype, link tool nội bộ hay link Drive.

## Thứ tự ưu tiên khi các nguồn nói khác nhau

1. **Chính sách YouTube hiện hành** (Help Center, howyoutubeworks). Chính sách đổi thường xuyên: trước khi ra quyết định
   về kiếm tiền, bản quyền hay gậy, kiểm lại trang chính thức.
2. **`CLAUDE.md` gốc + `channel/<ch>/`** (luật của xưởng và của từng kênh) + SKILL.md của skill liên quan.
3. **Tài liệu này**: nền kiến thức, checklist, cách đọc số liệu.

Chỗ nào tài liệu gốc khác luật của xưởng, file tương ứng có mục **"Khác với xưởng"** ghi rõ bên nào được dùng và vì sao.

## Các file

| File | Nội dung | Dùng khi |
|---|---|---|
| [01-nen-tang-va-chinh-sach.md](01-nen-tang-va-chinh-sach.md) | YouTube, 3 nhóm chính sách, mô hình kiếm tiền, MCN/network, Content ID, claim, whitelist, gậy | cần hiểu luật chơi, trước khi bật kiếm tiền hay vào network |
| [02-san-xuat-noi-dung.md](02-san-xuat-noi-dung.md) | nghiên cứu dòng nhạc, tiêu chí chọn/mix nhạc, tiêu chuẩn thumbnail và video | lên kênh mới, research, lên album, làm hình |
| [03-dinh-huong-hinh-anh.md](03-dinh-huong-hinh-anh.md) | storytelling cho kênh, bố cục, tone màu và ý nghĩa | viết `visual.md` cho kênh mới, chọn biến thể thumbnail |
| [04-thiet-lap-kenh-moi.md](04-thiet-lap-kenh-moi.md) | tạo kênh, ảnh kênh, từng mục Settings, mặc định upload | tạo kênh mới |
| [05-analytics-va-thuat-toan.md](05-analytics-va-thuat-toan.md) | chỉ số Analytics (3 nhóm), thuật toán theo từng bề mặt, mẹo tận dụng | đọc kết quả 48 giờ / 7 ngày (pm-production `results.py`), so sánh album |
| [06-seo-tu-khoa-va-metadata.md](06-seo-tu-khoa-va-metadata.md) | chiến lược SEO, nghiên cứu từ khóa (vidIQ, Google Trends), title / description / tags, cách đẩy kênh | soạn `youtube.md`, chọn giờ đăng, sửa `publish.md` |
| [07-van-hanh-va-xu-ly-su-co.md](07-van-hanh-va-xu-ly-su-co.md) | luật bắt buộc khi chạy kênh, quy trình claim, tắt/bật kiếm tiền bị từ chối, gậy cộng đồng, gậy bản quyền | có sự cố trên kênh |
| [08-checklist.md](08-checklist.md) | checklist gộp: kênh mới, mỗi video, định kỳ, sự cố | dùng hằng ngày |
| [09-shorts.md](09-shorts.md) | Shorts: thông số, thuật toán, chính sách (mass-production, inauthentic), Related video, cách cắt nhạc, đo | làm / đăng Shorts |

## Không áp dụng cho xưởng

| Trong tài liệu gốc | Lý do không dùng |
|---|---|
| Mua view / like / sub (dịch vụ SMM), "SEO VPS" (máy ảo cày view) | Vi phạm chính sách *Fake engagement* của YouTube: view bị lọc, video bị gỡ, kênh có thể bị chấm dứt. Số liệu giả cũng làm hỏng việc đọc kết quả 48 giờ / 7 ngày (retention thật là thước đo duy nhất, CLAUDE.md §5). |
| Lặp title 3 lần trong description | Nhồi từ khóa, rơi vào chính sách *Spam, deceptive practices* (metadata gây hiểu lầm / lặp từ khóa). Description dùng mẫu cố định của `publish.md`. |
| Title "giật tít" gây hiểu lầm | Metadata phải đúng nội dung (vd. không ghi "1 Hour" cho album 50 phút, SKILL upload-youtube-publish). Gây tò mò thì được, sai sự thật thì không. |
| Tool nội bộ (kho tài nguyên, quản lý biên tập, quản lý kênh), mã biên tập, quy chế phạt lương | Quy trình riêng của công ty đó. Ở xưởng, vai trò này là các file của album (`manifest.json`, `tracks/`, `youtube.md`) và ledger `production/`. |
| Nguồn nhạc stock / kho nhạc mua quyền, whitelist nhạc, nhạc free ≤ 50 % | Xưởng chỉ dùng nhạc tự làm bằng Suno. Phần Content ID / claim vẫn cần hiểu (file 01, 07). |
| "Rating 5*" khi đăng | YouTube đã bỏ đánh giá sao từ lâu. |

## Liên kết với quy trình của xưởng

| Việc (CLAUDE.md §3) | Tài liệu liên quan |
|---|---|
| Kênh mới (`channel/_template/`: `prompt_suno.md`, `album_rules.md`, `visual.md`, `publish.md`) | 04, 03, 02 §1, 08 §A |
| R&D: kênh, video tăng nhanh, kho câu (rnd-youtube-api) | 02 §1, 06 §2 |
| Kho bài + lên album: chọn bài theo `album_rules.md` (pm-production `album.py`) | 02 §2 |
| Hình: thumbnail album + ảnh dọc Short (thumbnail-prompt, video-generator) | 02 §3, 03 |
| Đăng: `youtube.md` (upload-youtube-publish), Short (video-shorts) | 06 §3–5, 04 §4, 08 §B, 09 |
| Dịch title + description (upload-youtube-translate) | 06 §3 (tiếp cận người xem toàn cầu) |
| Kết quả 48 giờ / 7 ngày (pm-production `results.py`) | 05 |
| Sự cố (claim, gậy, kiếm tiền) | 01 §5, 07 |
