# cozy-loop: phòng khách lò sưởi đứng yên

Bộ riêng cho video **1–2 tiếng nhạc Giáng sinh không lời**. Không ghép với các nhóm khác: **mỗi video = một cảnh** loop suốt video.

## living-room-fireplace (50 cảnh, `shots.json`)

Mọi ảnh có đủ 4 thứ, thấy rõ, không che nhau: **lò sưởi đang cháy**, **cây thông đèn nhấp nháy**, **cửa kính tuyết rơi bên ngoài**,
**bàn phía trước có cốc cà phê bốc khói + chút đồ ăn Giáng sinh** (`defaults.composition`). 50 cảnh khác nhau ở kiểu phòng
(`tags.style`: cabin gỗ, Victorian, Scandinavian, farmhouse, chalet, cottage, loft…), kiểu lò sưởi, cảnh ngoài cửa sổ, cây thông,
đồ ăn, bảng màu (`tags.palette`) và giờ (`tags.time`: đa số tối, vài cảnh chạng vạng / buổi sáng).

## Video

- `camera: static`: máy quay đứng yên tuyệt đối; chỉ lửa cháy, đèn cây nhấp nháy, khói cà phê, tuyết ngoài cửa chuyển động.
- Clip 10 s không quay về khung đầu được (lửa, khói, tuyết chỉ đi một chiều), nên loop bằng cách hòa tan cuối clip vào đầu clip
  (~1,5 s) rồi lặp tới 1–2 tiếng. Lửa và tuyết che vết nối tốt; kiểm vết nối trước khi lặp cả video.
- Thumbnail = chính ảnh đó (upscale 4K khi dùng).
