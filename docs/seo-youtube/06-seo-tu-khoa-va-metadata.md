# 06. SEO: từ khóa, title, description, tags, đẩy kênh

Nguồn: Module 4 "Các phương pháp đẩy kênh trên YouTube" + slide cùng tên (28 slide: nghiên cứu từ khóa, phương pháp đẩy kênh, tối ưu title/mô tả/tag).
Quy trình cụ thể của xưởng khi soạn metadata: `.claude/skills/youtube-publish/SKILL.md`; nội dung riêng kênh: `channel/<ch>/publish.md`.

## 1. SEO YouTube là gì

Tối ưu các yếu tố của video (từ khóa, title, mô tả, tag, thumbnail, tương tác, phân phối) để video **lên cao trong tìm kiếm, được đề xuất**
và thu hút đúng khán giả. Mục tiêu: tăng view, người đăng ký, tương tác, xây thương hiệu và tầm ảnh hưởng.

**5 chiến lược:**

| Chiến lược | Cách làm | Độ khó |
|---|---|---|
| SEO từng video | mỗi video một nhóm từ khóa riêng | dễ nhất, cho người mới |
| SEO đề xuất | dùng nhóm từ khóa + tag thống nhất để video nằm cạnh các video liên quan | trung bình |
| SEO playlist | gom video vào playlist; playlist lên top kéo view cho mọi video trong đó. Hiệu quả với phim nhiều tập, **list nhạc** | cần kế hoạch |
| SEO kênh | tên kênh + từ khóa kênh để kênh lên top khi tìm | khó nhất, cần nền tảng |
| SEO tổng thể | kết hợp tất cả | giữ top bền lâu |

Với xưởng: mỗi album là một video SEO riêng (từ khóa theo chủ đề album) + playlist Full Albums / Songs + tags mặc định kênh
làm lớp SEO đề xuất + single (bài điểm nhấn) dẫn về album.

## 2. Nghiên cứu từ khóa

**Từ khóa** = từ/cụm từ người dùng gõ vào ô tìm kiếm, và là cụm mình muốn video xếp hạng.

### vidIQ (extension Chrome)

1. Cài extension, đăng nhập bằng tài khoản YouTube (gói free hoặc trả phí).
2. Xem trên kênh: tổng quan, video, đối thủ, từ khóa, giờ đăng tốt nhất.
3. Nhập **từ khóa gốc** (từ chủ đề, nội dung, mục tiêu, đối tượng video) → Search. Đọc:

| Số liệu | Nghĩa |
|---|---|
| Search Volume | lượng tìm kiếm trung bình/tháng trên YouTube |
| Competition | độ khó để lên top |
| Optimization Strength | các video hiện có đã tối ưu tốt tới đâu (thấp = cơ hội) |
| Overall Score | điểm tổng hợp, tiềm năng SEO |

4. **Chọn từ khóa Overall cao, volume cao, competition và optimization thấp.**
5. Dùng chúng cho title, mô tả, tag; tham khảo gợi ý title/mô tả/tag của vidIQ; A/B test title/thumbnail; theo dõi CTR, watch time, người đăng ký.

### Google Trends: tìm "giờ vàng" đăng video

1. https://trends.google.com → nhập từ khóa.
2. Chọn quốc gia, **7 ngày qua**, nguồn **YouTube Search**.
3. Đỉnh cao nhất = lúc tìm nhiều nhất. **Giờ vàng = 1–2 giờ trước đỉnh** (để video kịp được index và có view ban đầu).
4. Chỉ nhận từ khóa có đồ thị **hình sin đều hoặc đang đi lên**; đồ thị không quy luật hoặc **dưới 25 điểm** → không đạt.

**Ở xưởng:** `publish.py tags --expand` (autocomplete = cụm người ta gõ thật) + `--trends` (Google Trends YouTube Search, 5 năm) đã làm phần
"typed + volume"; phần giờ vàng (7 ngày theo giờ) làm tay trên Google Trends cho thị trường chính của kênh (vd. US), ghi kết quả vào
`publish.md` của kênh. Nếu Studio có **Analytics → Research** (search volume, content gap) thì ưu tiên số của YouTube.

## 3. Title

- Chứa **từ khóa chính**, ≥ 5 từ, không nhồi từ khóa.
- **Hấp dẫn, gây tò mò**: con số, câu hỏi, lợi ích, điều bất ngờ; khác các video cùng chủ đề.
- **Ngắn gọn**: tài liệu gốc ≤ 80 ký tự; không viết hoa toàn bộ, không lạm dụng dấu chấm than, tránh từ khó hiểu.
- **Thử nghiệm**: A/B test (vidIQ, TubeBuddy; YouTube nay có **Test & compare** cho thumbnail, và title ở một số kênh) và theo dõi CTR, watch time.

**Khác với xưởng:** title ≤ **70** ký tự (mobile và kết quả tìm kiếm cắt ~60–70), mở bằng **tên bài 1** rồi tới cụm thể loại + use-case
người ta gõ thật, tối đa 1 emoji, chỉ ghi thời lượng khi đúng. Công thức cụ thể: `publish.md` → *Title*. "Giật tít" chỉ theo nghĩa gây tò mò,
không hứa điều video không có.

## 4. Description

Giúp YouTube và Google hiểu ngữ cảnh → xếp hạng cao hơn, vào Suggested thường hơn.

1. **Khớp với title**, nêu rõ nội dung chính và mục đích.
2. **200 ký tự đầu** là quan trọng nhất (hiện ở kết quả tìm kiếm và trên trang xem trước khi bấm "thêm").
3. **Hashtag** giúp tìm video cùng chủ đề/kênh (≤ 15; 3 cái đầu hiện trên title).
4. **Nhắc lại từ khóa chính** một cách tự nhiên.
5. Thêm **từ khóa bổ sung** (thể loại, chủ đề, đối tượng).
6. **Hạn chế link**, chỉ để link bắt buộc.
7. **CTA**: like, share, comment, subscribe.
8. Dùng **mặc định upload** để nhất quán, tiết kiệm thời gian.
9. **Dễ đọc**: xuống dòng, chia phần, dấu phân cách.

**Ở xưởng:** mẫu cố định `publish.md` (đã có giới thiệu kênh, CTA, hashtag), mỗi album chỉ viết ABOUT THIS VIDEO + TRACKLIST (chapters).
Khi viết/sửa mẫu cho kênh mới, kiểm 200 ký tự đầu đã có tên kênh + cụm thể loại chính. Title + description được dịch bằng youtube-translate
(mục "dùng công cụ dịch để tiếp cận người xem toàn cầu" của tài liệu gốc).

## 5. Tags

1. **Tag đầu tiên = từ khóa mục tiêu** của video; các tag sau xếp theo mức quan trọng.
2. Trộn 3 loại: **rộng** (bao phạm vi chủ đề: "gospel music"), **cụ thể** (đúng nội dung: "best christmas songs of all time 2024"),
   **mở rộng** (gốc + biến thể: "instrumental christmas music").
3. Tài liệu gốc: **10–20 tag** mỗi video (upload default 20–25). Quá nhiều tag không liên quan / spam → YouTube coi là lừa đảo, hạ hạng.
4. Công cụ gợi ý: vidIQ.

**Ở xưởng:** tags mặc định kênh + 5–12 tag album, tổng ≤ 500 ký tự theo cách YouTube đếm. Mỗi tag phải là cụm người ta gõ thật
và đúng ý định người tìm (`publish.py tags --expand / --try --trends`, SKILL youtube-publish → Tags). Tag có trọng số thấp trong xếp hạng,
nên danh sách ngắn mà thật tốt hơn danh sách dài mà bịa. Thứ tự: tên album/bài 1 và cụm chính nhất lên đầu.

## 6. Phương pháp đẩy kênh

| Phương pháp | Nội dung | Xưởng |
|---|---|---|
| **SEO thô** | điền đủ title, mô tả, tag, thumbnail, playlist… trước khi đăng | ✅ `youtube.md` + `publish.py check` |
| **Seeding tương tác** | trả lời, like, **pin comment**; nhắc like/share/subscribe; giao lưu với kênh cùng chủ đề để hợp tác/quảng bá chéo | ✅ pinned comment (`publish.md`); trả lời comment thật, không dùng tài khoản ảo |
| **Nội dung chất lượng** | đầu tư hình, âm thanh, biên tập, thời lượng | ✅ toàn bộ quy trình xưởng |
| **Tối ưu SEO video** | từ khóa phổ biến, title tò mò, mô tả rõ, thumbnail đẹp, CTA (end screen, card) | ✅ |
| **Quảng cáo Google Ads** | TrueView in-stream, in-feed (discovery), bumper, sponsored cards; chọn kỹ đối tượng, ngân sách, thời gian | tùy chọn, khi có ngân sách; đo bằng retention/subscriber từ quảng cáo |
| **SEO VPS** (máy ảo cày view) | | ❌ vi phạm *Fake engagement* |
| **Mua view / like / sub** | | ❌ vi phạm *Fake engagement*, có thể chấm dứt kênh |
