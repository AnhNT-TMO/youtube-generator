# 02. Sản xuất nội dung: nhạc, thumbnail, video

Nguồn: Module 2 "Sản xuất nội dung trên YouTube" + slide "Tối ưu hóa nội dung video" (23 slide).

Tối ưu nội dung mang lại: dễ được tìm thấy (từ khóa, mô tả, tags), tăng lượt xem và giữ chân, xây thương hiệu + niềm tin,
tăng tương tác (comment, like, share, đăng ký). Nội dung trên kênh nhạc = **nhạc + hình**.

## 1. Hiểu dòng nhạc trước khi làm (bài nghiên cứu dòng nhạc)

Trước khi phát triển một dòng nhạc, nhân viên mới phải nộp bản nghiên cứu (2 ngày) gồm:

1. **Định nghĩa** dòng nhạc, kèm ví dụ.
2. **Phân loại theo chủ đề**, kèm ví dụ (vd. Deep house → Deep house summer, Deep house đen trắng).
3. **Đối tượng nghe**, chia theo khu vực địa lý.
4. **10 kênh tiêu biểu**: view/tháng, từ khóa, chủ đề, **giờ đăng video**, phân tích hình ảnh (thumbnail, video, hiệu ứng).

**Áp dụng cho xưởng:** đây là khung để điền `channel/<ch>/channel.md` (thể loại, persona, khán giả) và `rules.md` (từ vựng research)
khi mở kênh mới. Phần 10 kênh tiêu biểu làm bằng youtube-music-analyzer (mỗi kênh/video một lần analyze); giờ đăng lấy từ
ngày giờ đăng các video của họ + Google Trends (file 06 §2). Nhớ copy guard: học vibe, không chép tên, chữ, hình (CLAUDE.md §1).

## 2. Nhạc

**Tiêu chí chọn bài:** thời lượng > 3 phút · giai điệu hay, bắt tai · âm thanh tốt, không rè, không nhiễu · có bản quyền.
Mẹo: nghe nhiều lần các bản mix nhiều view nhất của dòng nhạc để hình thành khái niệm "hay".

**Trước khi mix:**

- Hiểu dòng nhạc đang khai thác và các bài đang thịnh hành; hiểu kho nhạc đang có, cập nhật thường xuyên.
- **Mood**: các bài trong một bản mix cùng mood, hoặc đổi **có tuần tự** (vd. mở vui và nhanh, dần sang nhẹ nhàng, sâu lắng).
  Cảm xúc lên xuống thất thường là điều tối kỵ.
- **Cắt ghép**: bỏ phần thừa, không để khoảng lặng dài, nối bài mượt.
- **Số bài**: nhạc thư giãn 1–4 bài là đủ; nhạc có lời (vd. deep house) 10–20 bài.
- Nhạc thư giãn (relax, sóng âm, jazz) có thể trộn âm thanh thiên nhiên (nước, chim, sóng), âm lượng vừa, không át nhạc.

**Các bước mix:**

1. **Chọn bài đầu tiên**: quyết định người nghe có ở lại hay không. Thường là bài hot, vào nhanh, ít nhạc dạo.
2. **Dựng mạch cảm xúc theo bài đầu** ("dồn dập", "vui", "buồn", "phấn khởi", "nhẹ nhàng"…) và liên kết chặt giữa các bài.

**Tiêu chuẩn nhạc trên kênh:** hợp thị hiếu khán giả mục tiêu · có bản quyền · MP3/WAV ≥ 192 kbps · mix để tạo cái mới ·
cập nhật nhạc mới thường xuyên · **không dùng một bản mix cho nhiều video** (trùng lặp nội dung) · **không quá nhiều vibe trên một kênh**.

**4 lỗi thường gặp:** chọn bài dở · mix các bài không cùng mood · để khoảng trắng giữa bài quá dài · sound effect quá to/nhỏ, bị ngắt.

**Tiêu chuẩn cập nhật kho:** phân loại bài hay nhất làm chủ lực · giữ bài hay và tạm được để đa dạng, loại bài dở ·
theo dõi album mới · đề xuất mua bài từ nền tảng bán nhạc.

**Đối chiếu với xưởng:** các nguyên tắc này đã có (và chặt hơn) trong CLAUDE.md §6: bài 1 là bài mới, mạnh nhất, là title video;
15 giây đầu có "chữ ký"; arc energy lên tới cao trào rồi hạ; chuyển bài đa dạng; một Style prompt, một nghệ sĩ cho cả album.
"Không quá nhiều vibe trên một kênh" tương ứng house sound trong `rules.md`; album khác vibe phải khai báo `experiment`.
"Không dùng một bản mix cho nhiều video" tương ứng giới hạn tái sử dụng library (CLAUDE.md §7).
Khác duy nhất: xưởng chọn clip bằng số đo (verification-audio), không nghe để chấm (CLAUDE.md §5).

## 3. Hình ảnh

Các loại hình trên kênh: thumbnail, hình trong video, ảnh đại diện (profile), ảnh bìa (banner).

### Thumbnail

Hình đầu tiên người xem thấy trước khi bấm; đại diện nội dung, gợi tò mò, tạo nhận diện thương hiệu. Quyết định lớn tới CTR (file 05).

**Tiêu chí:** độ tương phản cao hơn bình thường (vẫn rõ khi thu nhỏ) · bố cục rõ ràng · màu hài hòa, hợp chủ đề.

**Tiêu chuẩn:**

| | |
|---|---|
| Kích thước | 16:9, 1920×1080 (tối thiểu 1280×720), **≤ 2 MB** khi upload; không bắt buộc là khung hình trong video |
| Chất lượng | hình đẹp nhất thể hiện nội dung, sắc nét, có bố cục |
| Bản quyền | hình mình có quyền dùng; không lấy thumbnail kênh khác (dễ bị gậy) |
| Sáng tạo | thumbnail mới cho từng video, tránh trùng lặp |

Mẹo: nghiên cứu thumbnail của thị trường/dòng nhạc trước khi làm.

**Lỗi thường gặp:** ảnh không hợp dòng nhạc · không có bố cục rõ · chỉnh màu quá đà (cháy sáng, chất lượng thấp).
Tránh thumbnail quá gợi cảm (nguy cơ gậy cộng đồng).

**Với xưởng:** thumbnail-prompt tạo ảnh 4K + `thumbnail.jpg` ≤ 2 MB, luật hình của kênh trong `visual.md`. Cách định hướng câu chuyện,
bố cục và màu cho cả kênh: file 03.

### Hình trong video

Có thể là một ảnh render thành video (hiệu ứng) hoặc nhiều footage ghép lại. Kích thước (4K, 1080p…) tùy thể loại; thống nhất
trước, không trộn footage khác kích thước. Footage phải sắc nét, đẹp, hợp thể loại, có quyền dùng (footage không rõ nguồn dễ bị gậy).
Cập nhật kho thường xuyên. **Đặt hình đẹp nhất ở đầu video**: giúp giữ chân và tạo cảm giác mới.

**Với xưởng:** video-generator làm loop từ thumbnail (4K, NVENC). "Đầu video phải đẹp nhất" trùng với luật 15 giây đầu.

## 4. AI trong sản xuất

Tài liệu gốc dùng Midjourney (tạo ảnh từ prompt hoặc ảnh mẫu), Stable Diffusion (ít giới hạn hơn, chất lượng cao, cần máy mạnh, prompt phức tạp),
ChatGPT (viết mô tả, tiêu đề). Xưởng dùng Suno (nhạc), ChatGPT (ảnh), SeedVR2 (upscale). Khai báo AI trong Studio (altered/synthetic = Yes).

## 5. Storytelling để giữ chân người xem

Kể chuyện bằng chữ, hình, video để khơi gợi tưởng tượng và đồng cảm. Giữa rất nhiều kênh nhạc giống nhau, một **chủ đề/câu chuyện
xuyên suốt** là lợi thế để giữ chân và để lại ấn tượng. Chi tiết và phương pháp: file 03.
