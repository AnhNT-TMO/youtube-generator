# ChatGPT: làm thumbnail

Quy trình người dùng làm trong ChatGPT, và cách sửa các lỗi hay gặp. Viết theo cách Album 001 đã làm
(ảnh 1672×941, nhân vật trong `model/` cũng tạo bằng ChatGPT ngày 2026-09-22).

ChatGPT Images 2.0 (từ 04/2026) tạo được ảnh 2K và nhiều tỉ lệ khung (có 16:9), và tạo nhiều ảnh trong một lượt được. Nhưng trong
app ChatGPT, yêu cầu "nhiều ảnh" đôi khi vẫn trả về một ảnh, một lưới ảnh, hoặc lần lượt từng ảnh. Vì vậy khối channel xin **2 ảnh riêng,
mỗi ảnh 2560×1440**, và cấm ghép (collage/grid/split). Thực tế 2026-09 vẫn ra 1672×941; `fit` cắt 16:9 rồi upscale lên 3840×2160 trên GPU server (SeedVR2 7B).
Nguồn (tra 2026-09-23): https://neurohive.io/en/news/chatgpt-images-2-0-openai-launches-image-generation-model-with-reasoning-2k-resolution-and-multilingual-text/ ,
https://www.glbgpt.com/hub/can-chatgpt-generate-multiple-images-at-once-2025-definitive-guide/

## Mỗi ảnh

1. **Mở chat mới.** Ảnh và yêu cầu của chat cũ ảnh hưởng tới ảnh mới (màu, tư thế, chữ).
2. **Đính kèm** ảnh tư thế trong `channel/<ch>/model/` ghi ở mục *Đính kèm* (PNG nền trong suốt dùng được).
   Nếu mặt hay bị lệch, đính kèm thêm `01-front-eye-contact.png`. Không đính kèm thumbnail cũ, vì ChatGPT sẽ chép bố cục của nó.
3. **Dán nguyên khối Prompt** trong một tin nhắn, không chia nhỏ.
4. **Tải về** bằng nút tải xuống để có bản đủ độ phân giải (không chụp màn hình),
   rồi lưu vào `<dir>/thumbnail-drafts/01.png`, `02.png`… (mỗi lượt 2 ảnh). Gửi đường dẫn cho Claude để kiểm tra.
   Ra 1 ảnh ghép 2 khung: xin lại `Please give me the two images as two separate files, not combined.`
   Chỉ ra 1 ảnh: xin thêm `Now make the second variation as a separate image.`

## Sửa bằng lệnh sửa trong cùng chat

Mỗi lần chỉ sửa một thứ, và luôn nói rõ những gì phải giữ nguyên. Nên sửa theo thứ tự này:

| Lỗi | Câu sửa |
|---|---|
| Chữ sai chính tả hoặc thêm chữ | `Edit this image. Keep everything else exactly the same. Only fix the lettering so the title reads exactly: "<title>" and the small line reads exactly: "Lamplight Gospel". No other text.` |
| Mặt không giống nhân vật | `Edit this image. Keep the scene, pose, clothes and light exactly the same. Make his face match the attached reference exactly: bald head, full dark beard graying at the chin.` (đính kèm lại ảnh model) |
| Tay lỗi | `Edit this image. Keep everything else the same. Fix his hands so they look natural with five fingers each.` |
| Góc logo/subscribe bị rối | `Edit this image. Keep everything else the same. Make the top-right corner and the bottom-right corner darker and emptier.` |
| Chữ hoặc mặt quá sát mép dưới | `Edit this image. Keep everything else the same. Move the title higher, away from the bottom of the frame.` |
| Ảnh không phải 16:9 | Không cần sửa trong ChatGPT: `thumb.py fit` cắt về 16:9 (xem trước ảnh có đủ chỗ ở trên/dưới không) |

Sau khoảng 3 lần sửa mà vẫn lỗi, mở chat mới với prompt đã chỉnh. Mỗi lần sửa ảnh lại bị trôi thêm (mặt, chữ, độ nét).

## Hay gặp

- **Chữ:** ChatGPT viết chữ khá chuẩn nhưng thỉnh thoảng lặp chữ, thiếu chữ hoặc tự thêm dòng phụ. Luôn đọc từng chữ.
- **Tỉ lệ:** nếu ảnh trả về là 3:2 hay vuông, `fit` sẽ cắt bớt trên/dưới hoặc hai bên. Muốn giữ chữ thì chỉnh `--y` hoặc `--x`.
- **Nhân vật bị trẻ đi hoặc gầy đi:** câu "same person as the reference" trong khối channel đã nhắc, nhưng vẫn phải nhìn lại.
- **Đèn không phải điểm sáng nhất** (chùm sáng hoặc chữ vàng sáng hơn): sóng ánh sáng và lửa rung của video-generator sẽ
  đặt sai chỗ. Xem các điểm sáng `check` in ra.
- Không yêu cầu giống người thật hoặc người nổi tiếng. Nhân vật là nhân vật riêng của kênh.
