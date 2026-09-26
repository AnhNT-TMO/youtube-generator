# 04. Thiết lập kênh mới

Nguồn: Module 3 §1 "Cách thiết lập và cài đặt kênh YouTube", quy định kênh mới trong "Quy định chung" và "Hướng dẫn sử dụng tool".
Tên menu Studio có thể đổi theo phiên bản; ý của từng mục vẫn vậy.

Làm song song với phần nội dung của kênh trong repo: `cp -R channel/_template channel/<tên>` rồi điền theo `channel/README.md`.

## 1. Tạo kênh

1. Đăng nhập YouTube bằng tài khoản Google dành cho kênh.
2. Ảnh đại diện → Settings (⚙️) → **Create a channel** → đặt tên (tạo **Brand Account**, để sau này thêm người quản lý mà không chia sẻ mật khẩu).
3. Kiểm thông báo kênh đã được thêm vào tài khoản, rồi tối ưu kênh ngay (dưới đây).

**Tên kênh / handle:** ngắn, dễ nhớ, gợi thể loại, không trùng hoặc gần giống kênh tham khảo (copy guard).

## 2. Ảnh kênh

Studio → Customization → Branding. Dùng kích thước YouTube khuyến nghị để hiển thị đẹp
(bổ sung, kiểm lại trên Help: ảnh đại diện 800×800, hiển thị tròn ~98 px; banner 2560×1440, vùng an toàn chữ/logo ở giữa 1546×423, ≤ 6 MB).
Ảnh đại diện và banner nằm trong cùng câu chuyện hình của kênh (file 03). Ở repo: `channel/<ch>/branding/` (chỉ trên máy).

## 3. Settings: từng mục

| Mục | Chọn | Lý do |
|---|---|---|
| **General** | tiền tệ mặc định **USD** | thống nhất báo cáo doanh thu |
| **Channel → Basic info** | **Keywords** kênh (từ khóa chính của dòng nhạc), **Country** kênh | giúp YouTube hiểu kênh; country ảnh hưởng thị trường mặc định |
| **Channel → Advanced settings** | **"No, set this channel as not made for kids"** | nội dung "made for kids" mất comment, mất quảng cáo cá nhân hóa, mất nhiều tính năng |
| **Channel → Feature eligibility** | **xác minh số điện thoại** (Intermediate features) | bắt buộc để upload video **dài hơn 15 phút**, dùng **thumbnail tùy chỉnh**, livestream. Album 60–90 phút cần mục này. Một số điện thoại chỉ xác minh được số lần giới hạn |
| **Upload defaults → Basic info** | Title: để trống · Description: mẫu của kênh · Visibility: **Private/Unlisted** · Tags: tags mặc định của kênh | xem §4 |
| **Upload defaults → Advanced** | License: **Standard YouTube License** · Category: **Music** · Video language: ngôn ngữ thị trường mục tiêu (xưởng: English) · Caption certification: không chọn · Community contributions: mặc định · Comments: **Hold potentially inappropriate comments for review** | lọc spam, giữ an toàn kênh |
| **Upload defaults → Monetization** (khi đã vào YPP) | bật **mọi loại quảng cáo** (pre-roll, mid-roll, post-roll, skippable, non-skippable) | tối đa doanh thu quảng cáo |
| **Permissions** | chưa cần; thêm người quản lý qua đây (không chia sẻ mật khẩu) | |
| **Community** | Automated filters: **Block links** (giữ comment chứa link để duyệt) · Defaults: giữ tin nhắn chat có khả năng không phù hợp để duyệt | chặn tài khoản ảo spam link, comment xấu |

## 4. Mặc định cho video tải lên

Tài liệu gốc đề xuất description mặc định gồm:

- ~~Tiêu đề lặp lại 3 lần~~ → **không dùng** (nhồi từ khóa; README "Không áp dụng").
- Mô tả kênh 4–5 dòng chứa từ khóa chính.
- Mô tả riêng video chứa từ khóa cần SEO (viết trước khi public).
- Hashtag liên quan từ khóa chính và phụ.
- Link đối tác / hãng nhạc theo quy định dự án (xưởng: không có).
- Email liên hệ.

Tags kênh: 20–25 tag cơ bản, cách nhau bằng dấu phẩy, tổng ≤ 500 ký tự.

**Khác với xưởng:** description mặc định = khối *Description YouTube mặc định* trong `channel/<ch>/publish.md` (giới thiệu kênh + chỗ
cho ABOUT THIS VIDEO + TRACKLIST + lời kết + hashtag), không có dòng AI, không lặp title. Tags mặc định ~12 tag trong `publish.md`
+ 5–12 tag riêng mỗi album đã research (file 06 §5), vì tag ít trọng số và tag bịa làm loãng.
Visibility mặc định Private: điền đủ metadata, kiểm Checks (claim), rồi mới public/schedule.

## 5. Nội dung trang kênh

- **Giới thiệu (About):** kênh là gì, cho ai, giá trị mang lại; chứa từ khóa chính tự nhiên; email liên hệ.
- **Playlists** ngay từ đầu (vd. `<Kênh> · Full Albums`, `<Kênh> · Songs`): giúp SEO playlist và tự phát tiếp (file 06 §1).
- **Trang chủ:** video trailer/featured cho người chưa đăng ký, section theo playlist.

## 6. Luật cho kênh mới (từ tài liệu gốc)

- **Upload video đầu tiên trong vòng 7 ngày** kể từ khi tạo kênh.
- **Không để video nào có claim** trước khi bật kiếm tiền (file 01 §6).
- Nhân viên mới tập trên kênh "ngoài net" 1–2 tháng (làm video, thumbnail, SEO) trước khi được giao kênh quan trọng.
  Với xưởng: kênh mới là nơi thử; khóa `rules.md`, `visual.md`, `publish.md` sau vài album đầu dựa trên retention.
- Mọi thay đổi của kênh (người quản lý, network, dự án) ghi lại ngay (xưởng: `channel/<ch>/CLAUDE.md`).

**Bổ sung (kiểm lại trên trang YPP):** điều kiện YPP đầy đủ thường là 1.000 người đăng ký + 4.000 giờ xem công khai trong 12 tháng
(hoặc 10 triệu view Shorts trong 90 ngày), bật xác minh 2 bước, không có gậy cộng đồng đang hiệu lực, có tài khoản AdSense.
