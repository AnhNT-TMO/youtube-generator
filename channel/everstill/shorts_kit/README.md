# Short đếm ngược Everstill: chuẩn kênh

Quy trình chung: skill `video-shorts` → *Short đếm ngược*. File này giữ những gì riêng của Everstill. Bản chuẩn đầu tiên là
Short của album 006, CEO duyệt ngày 2026-10-11.

## Bộ dùng chung

| Cái gì | Ở đâu |
|---|---|
| Spec chữ + badge + chuông (sửa số ngày, tên cảnh) | `shorts_kit/countdown/cd_spec.json` |
| Job render mẫu (cắt cảnh, nhạc, overlay, âm thanh chuông) | `shorts_kit/countdown/job4k.json` |
| Badge dùng lại: SUBSCRIBE (bản đủ, bản tách nền + quả chuông), FULL 3-HOUR ALBUM | `branding/badges/` |
| Âm thanh chuông Subscribe | `branding/sfx/` (chép vào `sfx/` của Short) |
| Font, logo | `shorts_kit/fonts/`, `shorts_kit/logo/` |

Badge mới làm thêm (ví dụ "FULL 2-HOUR ALBUM") thì để ở `branding/badges/` cùng kiểu dáng, không làm riêng trong thư mục album.

## Chữ

- Số ngày (Instrument Serif Italic vàng + vệt sáng), "days until Christmas", tên cảnh 2 dòng (Dancing Script Bold).
- Hai dòng không được chạm nhau: `line_gap` 12 px ở 1080 (24 px ở 4K). `cd_text.py` tự đẩy dòng dưới xuống và in
  `'<chữ>' chạm dòng trên → xuống Npx`.
- Frame 0 là thumbnail, nên sửa chữ xong thì làm lại `thumbnail.png` / `.jpg` từ frame 0.

## Badge SUBSCRIBE + chuông

- Badge hiện từ 2,0 s đến 5,9 s. Mũi tên ở giữa (x 0,5), ngay dưới badge, đầu mũi tên không thấp hơn y 0,82, vì từ 0,82 trở
  xuống là hàng tên kênh và nút Subscribe của YouTube. Bố cục giống end card.
- Thứ tự tiếng, không chồng nhau (CEO 2026-10-11):
  1. Badge hiện lên cùng **một lượt glockenspiel rải G–C–E–G–C–E** (`sweep_glock_tail.wav`, −5 dB, vào trước tiếng chuông
     đầu 0,88 s, đuôi mờ từ 0,6 s). Lúc này quả chuông trên badge đứng yên.
  2. Glock đã tắt bớt thì chuông mới lắc và **reng** (lượt lắc bắt đầu 0,95 s sau khi badge hiện). Tiếng là chuông cầm tay
     thật `bell_hb1.wav` / `bell_hb2.wav` luân phiên, mỗi lượt lắc 4 tiếng, mỗi tiếng nhỏ dần 3,5 dB.
  3. Lắc lần hai 2,45 s sau khi badge hiện, chỉ có chuông cầm tay, xong trước khi badge tắt.
- Cả lớp chuông đi qua reverb phòng lớn 2,2 s (`ir_hall.wav`, wet −8 dB). Nhạc tự lùi khoảng 3 dB khi chuông kêu.
- Không dùng: chuông gió vuốt (CEO thấy lố), handchime VCSL (gần như sóng sin, nghe như tiếng bíp).
- Nguồn: VCSL "Hand Bells, Nepalese" và VSCO-2-CE Glockenspiel, đều CC0.
- Nốt glock ở giọng Đô. Nhạc của Short ở giọng khác thì làm lại lượt rải theo giọng đó.

## End card

- Logo + badge FULL 3-HOUR ALBUM + mũi tên ngắn nhún nhảy, 4,4 s cuối.
- Không kéo mũi tên xuống tận ô Related video: mũi tên sẽ cắt qua giao diện YouTube, mà vị trí ô đó lại khác nhau theo máy.

## Kiểm trước khi gửi CEO

- Độ dài tiếng = độ dài hình (`ffprobe`). Từng có lỗi tiếng tắt ở 7,4 s.
- Loudness khoảng −14 LUFS, đỉnh ≤ −1,3 dBFS.
- Soi frame: chữ không chạm nhau, chuông đứng yên khi glock vang và lắc khi reng, mũi tên ở trên y 0,82.
- CEO xem Short trước khi lên Drive. Album lên Drive trước, Short zip riêng sau khi CEO duyệt.
