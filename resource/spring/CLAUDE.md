# Everstill spring resource

## Mục tiêu

Bộ này là kho cảnh mùa xuân cho Everstill: rừng xanh, suối nhỏ, hoa dại, cây ra chồi và vườn đầu mùa. Cảm giác chính là tươi, mềm, trong và dễ chịu; không phải phong cảnh núi hùng vĩ của bộ nature và không phải vườn hoa rực rỡ giả tạo.

- Mục tiêu phase 1: **300 clip đạt**, chia 4 category, mỗi category khoảng 75 clip.
- Một album 60–80 phút dùng cast khoảng 80–120 clip. Mỗi đoạn liên tục chỉ dùng 30–50 clip rồi đổi family hình ảnh.
- Resource native được tạo và duyệt trước; upscale là bước riêng trên GPU server.
- Ưu tiên 2K (2560×1440) cho cast được chọn. 4K chỉ thử trên clip hero sau khi benchmark, không mặc định upscale cả kho.

## Cấu trúc

Mỗi category có ba lớp khoảng cách. Tên folder dùng ASCII để script queue và montage đọc ổn định.

```text
spring/
  green-woodland/{wide,mid,close}/
  spring-water/{wide,mid,close}/
  wildflower-meadows/{wide,mid,close}/
  orchards-gardens/{wide,mid,close}/
```

- `wide`: đặt không gian và nhận ra thời tiết đầu mùa.
- `mid`: theo dõi đường mòn, bờ suối, cụm hoa, cành cây hoặc tán lá.
- `close`: chồi non, lá non, cành hoa, rêu và giọt nước; dùng làm điểm chạm và cầu nối.
- Chỉ tiêu mỗi category: khoảng 30 `wide`, 30 `mid`, 15 `close` = 75 clip. Có thể lệch vài clip nếu một scale có tỷ lệ redo cao.
- Tổng tỷ lệ gợi ý: 40% wide, 40% mid, 20% close. Close cần có chi tiết nhưng không được làm kho thành bộ ảnh macro.

## Bốn category

### green-woodland

Đường mòn trong rừng lá non, thân cây ấm, rêu, dương xỉ và ánh sáng lọt qua tán. Rừng phải yên và thoáng; tránh rừng quá tối, cây chen chúc hoặc màu xanh phát sáng.

### spring-water

Suối, ao nhỏ, bờ đá, cầu gỗ đơn giản và ánh sáng phản chiếu. Chuyển động ưu tiên là dòng nước chậm, gợn sóng nhẹ và lá rung; giữ mặt nước ổn định, không tạo sóng lớn kiểu fantasy.

### wildflower-meadows

Bãi cỏ, khoảng rừng trống và hoa dại đầu mùa. Hoa phân bố tự nhiên, có khoảng trống và nhiều màu xanh hơn màu hoa. Không dùng một biển hoa dày phủ toàn bộ khung hình.

### orchards-gardens

Vườn cây, hàng cây ra chồi, góc vườn bách thảo, cành cong và luống hoa đầu mùa. Không dùng nhà kính, công viên có biển hiệu, người làm vườn hay vật dụng có chữ.

## Luật hình và clip

- Ảnh 16:9, photorealistic, ánh sáng tự nhiên, không collage, không khung, không text, logo, người, động vật hay xe.
- Không dùng hoa quá to bất thường, cành cây xoắn, lá neon, giọt nước bay vô lý hoặc hạt phấn trông như tuyết.
- Bảng màu: fresh green, moss, pale yellow, white blossom, soft pink. Độ tương phản vừa phải, giữ highlight sạch và nhìn lâu không mỏi mắt.
- Mỗi cảnh phải có ít nhất một chuyển động nhẹ: lá rung, cỏ lung lay, nước chảy, sương mỏng, ánh sáng đi qua tán cây hoặc giọt nước.
- Chuyển động của Muse chậm, liên tục và có điểm neo. Camera không zoom, không bay xuyên tán cây, không cắt cảnh.
- Mỗi category cần có sáng sớm, âm u và golden hour; không để cả kho chỉ có ánh nắng vàng.

## Duyệt ảnh

Chỉ cho ảnh đạt nếu đúng subject, đúng scale, photorealistic, 16:9 và có motion element thật sự nhìn thấy trong ảnh. Loại ảnh có người, động vật, chữ/logo, collage, sai vật lý, sai palette, watermark rõ, gần trùng ảnh đã đạt hoặc thiếu lớp không gian.

- Reviewer ghi `clip` ngay khi cho đạt: `shot`, `deep`, `motion`, `lock`, `light`, `sound`.
- `motion` chỉ liệt kê vật sẽ chuyển động và đang có trong ảnh: lá, cỏ, nước, sương, ánh sáng.
- `lock` chỉ liệt kê địa hình và vật thể cố định: thân cây, đá, bờ vườn, thân nước, hàng rào và bố cục. Không đưa lá, hoa, cỏ, nước, mây hoặc sương vào `lock`.
- Ghi chú các lỗi nhỏ ở góc để montage tránh cắt cận; không tự cho đạt ảnh chỉ vì có thể sửa bằng crop.

## Hai lớp prompt

Prompt không viết lại thủ công cho từng job. `blocks.json` giữ các câu dùng chung; `shots.json` chỉ ghi subject, composition, lens, look, tags và `motion_elements` của cảnh.

### Prompt ảnh ChatGPT

Thứ tự ghép cố định: `head` → `subject` → `composition` → `realism` → `look` → `natural light` → `motion_ready` → `clean` → `tail`.

- `subject` chỉ nói một không gian và 3–5 vật chính; không nhắc lại các câu chung trong blocks.
- `composition` phải nói rõ lớp tiền cảnh, trung cảnh, hậu cảnh và hướng nhìn; cảnh `wide` phải cho thấy không gian, `mid` có đường đi/anchor, `close` có một chất liệu chính.
- `motion_elements` là vật đang có thật trong ảnh và sẽ được animate: lá, cỏ, nước, sương, ánh sáng; không yêu cầu Muse tự phát minh hoa hay động vật.
- Dùng lens để tạo đa dạng, nhưng tránh nhiều cảnh `close` bị ép thành macro. Ảnh phải là một phong cảnh 16:9 duy nhất, photorealistic, đúng tỷ lệ vật thể.
- Không dùng prompt phủ định dài dòng. Nếu một ảnh bị watermark, vật thể sai hoặc logo ở góc, sửa bằng một câu khóa cụ thể cho job đó; không thêm câu phủ định đó vào block chung theo phản xạ của một lỗi lẻ.

### Prompt video Muse

`video_prompt.json` tạo prompt theo thứ tự: camera ngắn → motion đã thấy trong ảnh → lock vật thể → khóa exposure/màu → sound. Reviewer ảnh ghi trường `clip` một lần, gồm `shot`, `deep`, `motion`, `lock`, `light`, `sound`.

- Ưu tiên slider trái/phải ngắn, khoảng 1/30 bề ngang khung, cùng độ cao và gần như cùng framing.
- Không dùng drift forward, drone bay vào tán cây, arc dài, zoom hoặc đường dẫn hội tụ sâu; các cảnh sâu và cảnh close dễ bị đẩy vào, mọc thêm lá hoặc morph.
- Mỗi câu motion chỉ nói một vật đang có trong ảnh. Khóa vật thể giữ nguyên hình, vị trí và số lượng; không để Muse tự thêm cây, hoa, chim, người hay vật dụng.
- Giữ ánh sáng và white balance nguyên từ frame đầu đến frame cuối. Một clip chỉ có một loại chuyển động chính và một ambient phụ.
- Prompt mới chỉ được xem là thành công khi clip không có `camera-far`, `camera-still`, `morph`, người/chữ, cắt cảnh hoặc thay đổi ánh sáng đột ngột.

## Bài học từ kho Christmas

- Block prompt và trường shot cố định giúp generator và reviewer làm việc ổn định hơn prompt viết tay.
- Reviewer ảnh phải ghi trường `clip` ngay khi cho đạt; không để PM mở lại 300 ảnh để viết prompt Muse.
- Loại cảnh quan trọng hơn việc thêm nhiều câu khóa: đường hội tụ dài, cảnh macro và phòng quá rộng có tỷ lệ lỗi cao. Với bộ này, giữ wide có lớp cảnh rõ và close vừa phải.
- Motion tự động chỉ là cổng lọc; reviewer vẫn phải xem morph, vật tự nhiên biến dạng và vật thể tự mọc ra. Ngưỡng đo không thay thế mắt người.
- Khi một category có tỷ lệ đạt thấp sau ít nhất 4 lượt, tạm giữ category đó thay vì đốt thêm credit. Lỗi lặp y nguyên sau câu khóa thì fail sớm.
- Sửa `blocks.json` hoặc `video_prompt.json` phải restart generator sau khi các cổng đang ở pha an toàn, rồi redraft queue còn chờ; không để job mới dùng khuôn cũ.

## Chiến lược ghép video

Không lặp máy móc một mẫu `wide → mid → close` cho từng clip. Một `nhịp nhỏ` gồm khoảng 10–19 placement; ghép 3–5 nhịp nhỏ thành một block hình 4–8 phút. Thời lượng tính từ clip thực tế sau trim và dissolve, không tính bằng số file.

1. **Mở không gian:** 2–3 clip `wide` của rừng, đồng cỏ, vườn hoặc mặt nước.
2. **Theo đường đi:** 4–8 clip `mid`, giữ cùng hướng sáng và cùng nhiệt độ màu.
3. **Chạm chi tiết:** 1–2 clip `close` của chồi, lá, hoa, rêu hoặc giọt nước.
4. **Trở lại nhịp:** 2–3 clip `mid` rồi `wide`, để người xem thở ra trước khi đổi category.

Tỷ lệ toàn khối khoảng 30–40% wide, 40–50% mid, 15–20% close. Close không quá hai clip liên tiếp. Không bắt buộc khối nào cũng có đủ cả ba lớp nếu âm thanh đang cần tĩnh; khi đó dùng mid làm cầu nối thay vì chèn close cho đủ công thức.

- Trong một khối, giữ cùng category hoặc category kề nhau: woodland → spring-water, meadow → orchard.
- Dùng `close` làm bridge khi chất liệu giống nhau: giọt nước sang lá non, rêu sang thảm cỏ, hoa sang cành vườn.
- Palette và thời điểm chỉ dịch một bậc; tránh cắt từ âm u xanh sang nắng vàng gắt.
- Có thể giữ cùng anchor hoặc hướng camera để tạo continuity, nhưng không đặt hai cảnh gần như trùng bố cục liên tiếp.
- Khoảng lặp tối thiểu tính theo một vòng cast thực tế: ưu tiên lặp lại sau khi đã dùng hết 70–80% cast của album; không lặp nguyên một chuỗi 5 clip.
- Cast 80–120 clip unique mỗi album để 30–50 clip chỉ là một nhịp nhỏ, không phải toàn bộ 60–80 phút. Nếu album cần nhiều hơn 120 clip, tăng cast trước khi giảm khoảng lặp.

## Kiểm tra trước khi dùng

Bộ phải giữ được nhận diện mùa xuân ngay cả khi không có hoa: lá non, màu xanh mới, ánh sáng đầu mùa và nước trong. Không dùng lại cùng clip với bộ nature nếu việc đó làm mờ ranh giới mùa. Hai album liên tiếp nên đổi family chủ đạo và đổi palette phụ.
