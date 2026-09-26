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
Create ONE image for the YouTube channel "<Channel Name>" (<genre>): the scene described below, as one complete standalone wide 16:9 landscape frame at 2K resolution (2560x1440 pixels). One single picture: no collage, grid, split screen or side-by-side panels.
PHOTO: <phong cách ảnh>
THE CHARACTER: <nhân vật trong ảnh tham chiếu đính kèm, những gì giữ nguyên>
LETTERING: <chữ title + dòng cố định>
FREE AREAS: a logo and a subscribe button are placed over the image later. Keep the top-right corner (right 16% of the width, top 26% of the height) and the bottom-right corner (right 28%, bottom 14%) dark and simple, and keep faces and lettering out of the bottom 15% of the frame.
AVOID: <danh sách tránh>
```

## Ảnh dọc Shorts

<mỗi Short một ảnh dọc 9:16 mới (không crop ảnh ngang), không chữ trên ảnh; cảnh lấy từ đoạn lời của Short; kiểu ảnh theo sheet
Shorts của R&D (`trend.py shorts`); bố cục điện thoại khớp `video.json` → `short`: mặt/chủ thể ở ~18–52 % chiều cao, 10 % trên tối,
dưới 56 % yên và tối (lời bài, spectrum, title YouTube), 12 % mép phải đơn giản>

## Prompt ảnh dọc Shorts (ChatGPT)

<khối CORE dọc, dán nguyên văn đầu mọi prompt ảnh Short; `thumb.py check` kiểm từng dòng>

```
<CORE dọc: 3 ảnh riêng, khung dọc 9:16 cho điện thoại; các hằng số của kênh; NO TEXT; PHONE LAYOUT; AVOID>
```

## Chữ chính trên ảnh (`title_text`)

<album: chữ gì là chữ chính (tên bài 1, hay một câu/lời cầu từ kho `experiments/phrases.yaml`) · single: tên bài · Short: không chữ>

## Dòng thời lượng (chỉ ảnh album)

<tùy chọn: một dòng "1 HOUR …" dưới dòng cố định để ảnh album khác ảnh single; kiểu chữ nằm trong CORE, chữ chọn theo vibe ảnh,
ghi ở `duration_line:` + `Duration line: "…"` của THIS IMAGE. Kênh không dùng thì xóa mục này.>

## Biến thể hình ảnh (chọn theo vibe bài)

Chọn theo vibe của bài (lời, `imagery`, `emotion`, `energy`, `arc_role`), không ngẫu nhiên. Mỗi trục một bảng `giá trị | mẫu tiếng Anh`.

### Chữ title (`lettering`)

### Khung hình (`framing`)

### Ánh sáng (`light`)

### Màu (`palette`)
