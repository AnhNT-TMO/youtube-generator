# Model: nhân vật chính của Lamplight Gospel

Ảnh tham chiếu nhân vật (nền xám studio, PNG 1086×1448) để giữ **cùng một người** trên mọi thumbnail.
Trái/phải = **hướng mặt quay về phía nào của khung ảnh** (chữ bên phải → chọn ảnh quay phải, để ông nhìn về phía chữ). Nhân vật **gốc, hư cấu**: không dựa trên và không được giống bất kỳ người thật hay
người nổi tiếng nào (CEO 2026-09-25: đổi từ nhân vật 50 tuổi sang ông già 70–80 tuổi).

| File | Góc |
|---|---|
| `01-front-eye-contact.png` | Chính diện, nhìn thẳng camera (ảnh gốc, mọi góc khác vẽ từ ảnh này) |
| `02-three-quarter-left-looking-up.png` | Nghiêng 3/4, mặt quay về **bên trái khung**, ngước nhìn lên (lật ngang từ bản gốc) |
| `03-profile-left-looking-up.png` | Profile, mặt quay về bên trái khung, ngước lên |
| `04-three-quarter-right-looking-up.png` | Nghiêng 3/4, mặt quay về **bên phải khung**, ngước nhìn lên |
| `05-profile-right.png` | Profile, mặt quay về bên phải khung, nhìn thẳng |
| `06-back.png` | Sau lưng, cúi nhẹ đầu |
| `07-front-hands-in-pockets.png` | Chính diện từ gối trở lên, tay đút túi quần, cười nhẹ |
| `08-slight-right-looking-up-smile.png` | Quay nhẹ về bên phải khung, ngước lên, cười hy vọng |
| `09-three-quarter-right-singing.png` | Nghiêng 3/4, mặt quay về bên phải khung, ngước lên, miệng hé như đang hát |

## Mô tả nhân vật (dùng trong prompt tạo ảnh)

> An original elderly Black man in his mid-70s, deeply weathered dark-brown skin with deep lines on the forehead, around the
> eyes and down the cheeks, a long gentle sorrowful face, heavy-lidded kind tired eyes, thick curly silver-white hair receding
> at the temples, a full soft silver-white beard and moustache, lean and slightly stooped, large work-worn hands.

Trong ảnh model ông mặc sơ mi cotton cũ không cổ + áo len nâu vá khuỷu tay: **chỉ để cố định khuôn mặt**. Trên thumbnail ông
mặc theo 5 loại trang phục ở `visual.md` → *Biến thể hình ảnh* (luôn nghèo, cũ, sờn hoặc vá).

## Cách tạo lại / thêm góc

ChatGPT (chatgpt-chrome :9223) bằng `thumbnail-prompt/scripts/chatgpt_images.py gen <dir>` với `thumbnail-prompt.md` tự viết:
vòng 1 = chân dung chính diện (không đính kèm); các vòng sau đính kèm `01-front-eye-contact.png` (+ một ảnh nghiêng) và xin
tối đa 4 góc mỗi lượt, cùng nền, cùng quần áo, cùng ánh sáng. ChatGPT hay nhầm hướng "left/right": ghi rõ "face turned toward
the RIGHT side of the picture". Prompt các vòng: `research/character-v2/` (chỉ trên máy). Xóa thread sau mỗi lượt.

`archive-v1/`: nhân vật cũ (ông 50 tuổi đầu trọc), dùng cho album 001–003 và các single/Short đã đăng.
