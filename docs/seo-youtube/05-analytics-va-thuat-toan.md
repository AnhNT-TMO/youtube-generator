# 05. YouTube Studio, Analytics và thuật toán

Nguồn: Module 3 §2 "YouTube Studio và số liệu phân tích", §3 "Thuật toán của YouTube". Phần đọc số liệu trong tài liệu gốc do trưởng nhóm dạy
trực tiếp; ở đây giữ khung, thêm cách đọc kết quả 48 giờ / 7 ngày của xưởng.

## 1. YouTube Studio

Quản lý video và kênh: số liệu theo thời gian thực, upload và sửa video, cấp quyền cho người khác, playlist, comment, phụ đề.
Phần quan trọng nhất: **Analytics**, dùng để đánh giá chất lượng từng video, so sánh video / khoảng thời gian, tìm xu hướng và thói quen khán giả.

## 2. Ba nhóm chỉ số

### A. Thu hút: video có nổi bật, có tới đúng người không?

| Chỉ số | Ý nghĩa | Ghi chú |
|---|---|---|
| **Watch time** (thời gian xem) | tổng phút người xem đã xem | YouTube coi watch time cao = hấp dẫn → đề xuất và xếp hạng tìm kiếm tốt hơn |
| **Average percentage viewed** | trung bình xem được bao nhiêu % video | với album 60–90 phút, % sẽ thấp; so giữa các album cùng độ dài |
| **Demographics** | tuổi, giới tính, vị trí, ngôn ngữ; giờ khán giả online; video/kênh khác họ xem | chọn giờ đăng, ngôn ngữ dịch (`translate.yaml`), ý tưởng album |
| **Impressions CTR** | % lượt hiển thị thumbnail được bấm | phản ánh độ liên quan, sức hút, tò mò, cảm xúc của thumbnail + title. Ví dụ: 121.300 impressions → ~7.000 view từ impressions ≈ 6 %. CTR thường cao vọt ngay sau khi đăng (người đăng ký bấm), rồi giảm và ổn định khi video lan ra ngoài |
| **Traffic sources** | view đến từ đâu: **Browse** (trang chủ), **Suggested** (cạnh/sau video khác), **Search**, playlist, bên ngoài | cho biết nên tối ưu gì (§4) |
| **YouTube search terms** | từ khóa người ta gõ để tìm ra video | khác chủ đề video → bổ sung từ khóa đó vào metadata; khác hẳn → cân nhắc làm video mới cho từ khóa đó |

### B. Tiếp nhận: có giữ được người xem không?

| Chỉ số | Ý nghĩa |
|---|---|
| **Average view duration** | tổng thời gian xem / số lượt xem (tính cả xem lại); phản ánh chất lượng + độ phù hợp với người được tiếp cận |
| **Audience retention** | thời điểm người xem ở lại / rời đi. YouTube khuyên chú ý **15 giây đầu**. Ví dụ tốt: còn 73 % ở 0:30 |
| **Returning viewers** | người xem quay lại kênh; cao = nội dung gây "nghiện", tạo fan trung thành, được đề xuất nhiều hơn (trang chủ, end screen, autoplay). Video nào làm người mới quay lại nhiều → làm thêm loại đó |

### C. Phản hồi: người xem có gắn kết, hài lòng không?

- **Tương tác**: comment, share, like/dislike → chủ đề nào hợp khán giả, video có tạo cảm xúc và kêu gọi hành động không.
- **Người đăng ký**: nhận thông báo video mới, video hiện ở trang chủ của họ → thêm view sớm (đẩy CTR ban đầu).

## 3. Thuật toán

Mục tiêu duy nhất: **giữ người dùng trên nền tảng càng lâu càng tốt**. Quy trình: thu thập dữ liệu người dùng → lọc video → chọn video hợp người dùng → xếp hạng.

| Bề mặt | Dựa trên | Cách tối ưu |
|---|---|---|
| **Trang chủ (Browse)** | *hiệu suất* (video làm hài lòng người giống họ) + *cá nhân hóa* (lịch sử xem, kênh hay xem, chủ đề quan tâm) | thumbnail + title thắng CTR, video giữ chân tốt |
| **Đề xuất (Suggested)** | video hay được xem cùng nhau, độ liên quan, lịch sử xem | làm **chuỗi** video liên quan + playlist; end screen, card, CTA dẫn sang video khác; **title và thumbnail nhất quán kiểu** giữa các video; theo định dạng đang phổ biến |
| **Tìm kiếm** | độ liên quan từ khóa với title/mô tả/nội dung, tương tác, thời gian xem | nghiên cứu từ khóa người thật gõ; mô tả hữu ích; dịch metadata để tới người xem toàn cầu; xem tab thịnh hành để lấy ý tưởng |
| **Xu hướng + người đăng ký** | video phổ biến, người sáng tạo được yêu thích; tab Subscriptions | không mua được chỗ trên Trending; tăng người đăng ký là mục tiêu chính |

## 4. Mẹo tận dụng thuật toán

1. **Khai thác dữ liệu khán giả:** Analytics → Audience cho biết *kênh khác* khán giả xem (28 ngày) và *video khác* họ xem (7 ngày).
   Nghiên cứu các kênh/video đó: nội dung gì, xu hướng gì, đối thủ làm gì → PM + CEO tra bằng rnd-youtube-api (`yt.py channel/videos/fast`).
2. **Theo dõi thay đổi thuật toán:** có giai đoạn YouTube ưu tiên Live, có lúc video thường, có lúc trend "24h / 12h / 3h / 1h" (video dài nhiều giờ). Không cố định, phải quan sát.
3. **Tối ưu metadata** (title, tags, mô tả, thumbnail) + **chapters**: chia timeline thành mục lục, tăng trải nghiệm và giúp thuật toán hiểu từng phần video.
4. **Nội dung chất lượng**: hình, âm thanh, ánh sáng, biên tập; liên quan sở thích/nhu cầu người xem.
5. **Kêu gọi xem tiếp và tương tác**: pin comment dẫn tới video nổi bật; playlist theo chủ đề hoặc video xem nhiều nhất; **end screen** gợi ý video liên quan; nhắc like, comment, share, subscribe.
6. **Theo mùa và chủ đề nóng**: Halloween, Giáng Sinh, Tết… Lên kế hoạch album theo mùa trước vài tuần.

## 5. Đọc kết quả 48 giờ / 7 ngày của xưởng

CLAUDE.md §0 + §3: PM đọc kết quả 48 giờ / 7 ngày (pm-production `results.py` → `results.md`; retention 0:15 / 0:30 / 1:00, CTR), so sánh giữa các album. Cách đọc gợi ý
(suy ra từ các định nghĩa trên, không phải số chuẩn của YouTube):

| Hiện tượng | Nghĩa là | Việc nên thử |
|---|---|---|
| CTR thấp, retention tốt | người bấm vào thì ở lại, nhưng ít người bấm | đổi thumbnail/title (Studio **Test & compare** nếu có), không đổi nhạc |
| CTR cao, rơi mạnh trước 0:30 | thumbnail/title hứa khác cái người xem nghe thấy, hoặc 15 giây đầu yếu | kiểm cách mở bài 1 (CLAUDE.md §6), độ khớp thumbnail với nhạc |
| Retention đầu tốt, average view duration thấp | mở hay, thân album hụt | xem đồ thị retention: điểm rơi trùng chuyển bài nào (chapters) |
| View chủ yếu từ Search | từ khóa đúng nhưng chưa được đề xuất | tăng liên kết giữa các video: playlist, end screen, title/thumbnail nhất quán |
| View chủ yếu từ Suggested của một kênh khác | đang "ăn theo" kênh đó | xem kênh đó bằng rnd-youtube-api (`yt.py videos`); không lấy tên / branding của họ |
| Returning viewers tăng sau một album | album đó tạo fan | ghi lại đặc điểm (chủ đề, câu title/thumbnail, bài 1, thứ tự bài, biến thể hình) để làm biến thể tiếp |

Chỉ kết luận khi có ≥ vài album; một video lẻ nhiễu nhiều (CLAUDE.md §10).
