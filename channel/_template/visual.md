# Hình ảnh: <Channel Name>

Luật hình riêng của kênh (skill `thumbnail-prompt` là quy trình). `thumb.py check` đọc khối ``` dưới
*Prompt ảnh mặc định (ChatGPT)* (giữ nguyên tên mục).

## Thế giới hình của kênh

- **Hằng số:** <những gì mọi ảnh đều có>
- <nhân vật, trang phục, bối cảnh, điều cấm>

## Kiểm trên từng bản nháp (Claude nhìn ảnh)

- Title và mọi dòng chữ cố định đúng từng chữ.
- Nhân vật giống `model/`: <đặc điểm khuôn mặt>. Năm ngón tay.
- Không có gì quan trọng trong các góc bị phủ; đọc được ở cỡ điện thoại.

## Prompt ảnh mặc định (ChatGPT)

Khối **CORE**: dán nguyên văn ở đầu mọi prompt; chỉ giữ những gì không bao giờ đổi.

```
Create THREE separate images for the YouTube channel "<Channel Name>" (<genre>): three variations of the scene described below, each a complete standalone wide 16:9 landscape frame at 2K resolution (2560x1440 pixels). Do not combine them into one picture: no collage, grid, split screen or side-by-side panels.
PHOTO: <phong cách ảnh>
THE CHARACTER: <nhân vật trong ảnh tham chiếu đính kèm, những gì giữ nguyên>
LETTERING: <chữ title + dòng cố định>
FREE AREAS: a logo and a subscribe button are placed over the image later. Keep the top-right corner (right 16% of the width, top 26% of the height) and the bottom-right corner (right 28%, bottom 14%) dark and simple, and keep faces and lettering out of the bottom 15% of the frame.
AVOID: <danh sách tránh>
```

## Biến thể hình ảnh (chọn theo vibe bài)

Chọn theo vibe của bài (lời, `imagery`, `emotion`, `energy`, `arc_role`), không ngẫu nhiên. Mỗi trục một bảng `giá trị | mẫu tiếng Anh`.

### Chữ title (`lettering`)

### Khung hình (`framing`)

### Ánh sáng (`light`)

### Màu (`palette`)
