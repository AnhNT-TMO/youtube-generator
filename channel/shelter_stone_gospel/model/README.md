# Model: nhân vật chính của Shelter Stone Gospel

Ảnh tham chiếu nhân vật (nền xám studio, PNG 1086×1448) để giữ **cùng một người** trên mọi thumbnail. Nhân vật **gốc, hư cấu**:
không dựa trên và không được giống bất kỳ người thật hay người nổi tiếng nào (CEO chọn 2026-09-28: bản v4).
Trái/phải = **hướng mặt quay về phía nào của khung ảnh** (chữ bên phải → chọn ảnh quay phải, để ông nhìn về phía chữ).

| File | Góc |
|---|---|
| `01-front-eye-contact.png` | Chính diện, nhìn thẳng camera (ảnh gốc, mọi góc khác vẽ từ ảnh này) |
| `02-three-quarter-left-looking-up.png` | Nghiêng 3/4, mặt quay về **bên trái khung**, ngước lên (lật ngang từ 04) |
| `03-profile-left-looking-up.png` | Profile, mặt quay về bên trái khung, ngước lên (lật ngang từ 05) |
| `04-three-quarter-right-looking-up.png` | Nghiêng 3/4, mặt quay về **bên phải khung**, ngước lên, hy vọng |
| `05-profile-right-looking-up.png` | Profile, mặt quay về bên phải khung, ngước lên |
| `06-three-quarter-right-singing-eyes-closed.png` | Nghiêng 3/4 quay phải, nhắm mắt, nhíu mày, nước mắt, đang hát |
| `07-three-quarter-left-singing-eyes-closed.png` | Như 06, quay trái (lật ngang từ 06) |
| `08-front-eyes-closed-hand-on-chest.png` | Chính diện, nhắm mắt cầu nguyện, tay đặt trên ngực |
| `09-slight-right-looking-up-hopeful.png` | Quay nhẹ về phải, ngước lên, cười hy vọng, mắt ướt |

## Mô tả nhân vật (dùng trong prompt tạo ảnh)

> An original Black man about 68 years old, weathered medium-dark brown skin, slightly hollow cheeks, deep lines on the
> forehead, around the eyes and from nose to mouth, short curly salt-and-pepper hair, a full soft grey-white beard and
> moustache, kind dark brown eyes, medium build (neither heavy nor thin), no glasses.

Áo len than + sơ mi trắng trong ảnh model **chỉ để cố định khuôn mặt**; trang phục thumbnail theo `visual.md`.

## Cách tạo lại / thêm góc

ChatGPT (chatgpt-chrome :9223) bằng `thumbnail-prompt/scripts/chatgpt_images.py gen <dir>`, đính kèm `01-front-eye-contact.png`,
mỗi lượt 1 góc, cùng áo, nền, ánh sáng; góc quay trái lật ngang từ góc quay phải để mặt không trôi. Ghi rõ "face turned toward
the RIGHT side of the picture". Prompt các vòng: `research/shelter-stone-character/` (chỉ trên máy). Xóa thread sau mỗi lượt.
