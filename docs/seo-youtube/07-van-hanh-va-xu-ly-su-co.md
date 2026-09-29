# 07. Vận hành kênh và xử lý sự cố

Nguồn: "Quy trình và quy định chạy kênh", sheet "Quy định bắt buộc khi chạy kênh", sheet "Bộ quy trình xử lý các vấn đề kênh"
(out net, tắt/bật kiếm tiền bị từ chối, gậy cộng đồng, gậy bản quyền), FAQ.
Quy trình gốc chia việc cho nhiều phòng (SEO, trợ lý, vận hành, BD); ở đây rút lại cho một chủ kênh, giữ các bước và thời hạn.

## 1. Luật bắt buộc khi chạy kênh

1. **Không kích hoạt Content ID** cho nội dung không có độc quyền.
2. **Không reup** video dưới mọi hình thức.
3. Không dùng tài nguyên không có quyền; đọc kỹ điều khoản từng nguồn; credit đúng cách khi nguồn yêu cầu.
4. **Tuyệt đối không để bị gậy. Nếu bị gậy, không tự ý xóa video bị gậy.**
5. Kênh bị gậy hoặc chết → **báo ngay** (xưởng: chủ kênh ghi vào `channel/<ch>/CLAUDE.md` và dừng đăng trên kênh đó tới khi rõ nguyên nhân).
6. Mô tả video luôn có: giới thiệu kênh, link mạng xã hội/nền tảng khác (nếu có), email liên hệ, credit bắt buộc.
7. Tránh thumbnail quá gợi cảm (gậy cộng đồng).

**Với xưởng:** nhạc, lời, hình đều tự làm, nên rủi ro chính là: claim từ bên thứ ba, *inauthentic content* khi xét YPP, metadata gây hiểu lầm.
Giữ đủ hồ sơ nguồn gốc trong thư mục album (file 01 §6), không xóa kể cả khi album đã đăng lâu.

## 2. Claim

Kiểm ngay ở màn hình **Checks** khi upload (video còn Private) và tab Content → Copyright sau khi đăng.

| Trường hợp | Làm gì |
|---|---|
| **Claim đúng** (mình dùng nội dung của người khác) | gỡ phần đó: cắt đoạn, thay bài, tắt tiếng (Studio Editor) hoặc chấp nhận chia doanh thu. Kênh mới chưa bật kiếm tiền: không để claim tồn tại |
| **Claim láo** (nội dung của mình / trùng không đáng kể / bên claim không có quyền) | **Dispute** trong Studio, nêu lý do + bằng chứng (với xưởng: bài được tạo trên Suno ngày…, clip id, lời tự viết). Bên lớn (hãng đĩa lớn) claim sai → cân nhắc nhờ bên có kinh nghiệm tư vấn |
| Có quyền nhưng vẫn bị claim | nhờ chủ quyền **whitelist kênh** hoặc gỡ claim từng video; hoặc kháng bằng code nếu chủ quyền cấp |

## 3. Tắt kiếm tiền (TKT) / bật kiếm tiền bị từ chối (BKT xịt)

**Thời hạn:** xử lý trong **24–48 h**; thông báo/ghi nhận trong vòng **2 h** kể từ khi phát hiện.

1. **Xác định lý do** từ YouTube Studio (email/thông báo YPP) và hỏi **Creator Support chat** để xác nhận
   (vd. trùng lặp ảnh, nhạc, footage; *reused / inauthentic content*).
2. Ghi lại: kênh, lý do, network (nếu có), ngày.
3. **Tổng hợp bằng chứng kháng** theo đúng lý do bị nêu.
4. **Kháng**, theo thứ tự ưu tiên:
   1. qua network (nếu kênh trong MCN), cách được ưu tiên;
   2. qua Creator Support chat;
   3. qua YouTube Studio (appeal, thường kèm video giải thích);
   4. dịch vụ kháng bên ngoài: ít ưu tiên nhất.
5. Cập nhật kết quả; thất bại → lên phương án khác (sửa kênh theo góp ý của support rồi nộp lại sau thời gian chờ).

Có hai lựa chọn khi bị từ chối: chấp nhận, sửa kênh theo gợi ý của support rồi nộp lại; hoặc kháng bằng bằng chứng. Kết quả tùy từng kênh.

**Bằng chứng xưởng có sẵn cho lý do "nội dung lặp lại / thiếu nguyên bản":** mỗi album có brief + tracklist riêng (`album.md`), thứ tự bài
không trùng album cũ và luật bài mới tối thiểu (`album.py check`, `album_rules.md`), title + thumbnail + biến thể video riêng; quá trình ghi lại theo từng bước.
Nếu bị từ chối vì lý do này, trước khi nộp lại cân nhắc: ẩn/gỡ các video quá giống nhau, tăng khác biệt giữa album (bài mới, bài 1, thứ tự bài, title/thumbnail, hình), thêm nội dung giá trị riêng.

## 4. Gậy cộng đồng

1. **Xác định lý do** từ Studio và từ nội dung bị nêu (audio / footage / thumbnail / metadata). Đúng hay láo? **Không xóa video.**
   Lỡ xóa → nhắn Support xin khôi phục ngay.
2. Ghi lại: kênh, loại gậy (đúng/láo; footage/thumb/audio), network.
3. Xác định tài nguyên gây ra: nhạc (claim đúng khi dùng nhạc chưa whitelist trên live; nhạc có quyền nhưng bị claim láo), hình (ảnh duy nhất của video, footage), hoặc chưa rõ → xét cả hai.
4. Soạn mẫu kháng (nêu nguồn gốc, quyền sử dụng, bằng chứng).
5. **Kháng** qua YouTube Studio hoặc Support chat; theo dõi **2 ngày/lần** tới khi gỡ xong.
6. Đóng case, **ghi bài học** (xưởng: vào file của kênh, vd. `visual.md` → điều phải kiểm; CLAUDE.md §2).

Gậy cộng đồng đầu tiên thường chỉ là cảnh cáo (warning); gậy tiếp theo hạn chế đăng, 3 gậy trong 90 ngày → chấm dứt kênh (kiểm trang chính sách).

## 5. Gậy bản quyền

1. Xác định lý do và **bên đánh gậy** (có bên dùng video để đánh gậy audio → kiểm kỹ). **Không xóa video.**
2. Ghi lại: kênh, loại gậy, network.
3. Rà soát toàn kênh (và các kênh khác cùng dùng tài nguyên đó) để loại rủi ro bị gậy tiếp bởi cùng nội dung.
4. Chọn cách xử lý:
   - **Kháng**: gửi **counter notification** trong Studio nếu chắc mình có quyền (có hệ quả pháp lý, chỉ làm khi chắc); báo cáo tiến độ 2 ngày/lần;
   - **Liên hệ** bên đánh gậy xin **rút lại** (retraction).
5. Đóng case, ghi bài học.

Hậu quả gậy bản quyền: mất khả năng tải lên, mất kiếm tiền; nặng thì mất kênh; nếu kênh trong MCN còn ảnh hưởng tới quan hệ với network và các kênh khác.

## 6. Kênh bị loại khỏi network (out net)

1. Ghi nhận ngay; xóa thông tin network khỏi hồ sơ kênh.
2. Tìm network phù hợp khác và xin gia nhập (hoặc chạy độc lập).
3. Được mời → chấp nhận lời mời trong kênh, cập nhật hồ sơ kênh. Chưa được → tiếp tục tìm.

## 7. Thói quen báo cáo

Tài liệu gốc tổng hợp mọi sự cố vào **thứ 6 hàng tuần**. Với xưởng: mỗi tuần một lần xem Studio (Copyright, Monetization, Community strikes, email YouTube)
cùng lúc với việc đọc kết quả 48 giờ / 7 ngày (file 05 §5), checklist ở file 08 §C.
