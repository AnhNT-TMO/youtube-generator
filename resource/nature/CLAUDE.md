# Everstill nature resource

## Mục tiêu

Bộ này là kho cảnh thiên nhiên quanh năm cho Everstill: núi, hồ, thác, sông và cao nguyên. Cảm giác chính là rộng, sâu, hùng vĩ và yên tĩnh; không phải rừng xanh mùa xuân và không phải phong cảnh fantasy.

- Mục tiêu phase 1: **320 ảnh đạt → clip**, 4 category × 80 (CEO 2026-10-09).
- Đích cuối (CEO 2026-10-09): mỗi album 1 tiếng ghép 80–100 clip, **thứ tự xáo được**, nối crossfade như slide; một clip chạy nhiều lần trong album và lật ngang để thành bản khác. Chuẩn clip (CEO 2026-10-09): **đẹp và giống thật**; chỉ loại AI look (vật hiện ra/biến mất, biến dạng) và nhảy/cắt hình. Mọi chuyển động tự nhiên đều được, frame đầu không cần giống frame cuối.
- Bộ này không theo luật clip của Christmas; chỉ lấy những gì hợp mục tiêu trên.
- Resource native được tạo và duyệt trước; upscale là bước riêng trên GPU server.
- Ưu tiên 2K (2560×1440) cho cast được chọn. 4K chỉ thử trên clip hero sau khi benchmark, không mặc định upscale cả kho.

## Cấu trúc

Mỗi category có ba lớp khoảng cách. Tên folder dùng ASCII để script queue và montage đọc ổn định.

```text
nature/
  mountain-valleys/{wide,mid,close}/
  alpine-lakes/{wide,mid,close}/
  waterfalls-rivers/{wide,mid,close}/
  highland-wilderness/{wide,mid,close}/
```

- `wide`: đặt địa điểm, thấy được quy mô và hướng đi của cảnh.
- `mid`: theo dõi một đối tượng chính như sông, đường núi, bờ hồ, tán cây.
- `close`: chất liệu và chuyển động nhỏ như nước, đá, cỏ, sương; dùng làm cầu nối, không dùng dày đặc.
- Chỉ tiêu mỗi category (CEO 2026-10-09): 27 `wide`, 27 `mid`, 26 `close` = 80. 26 cảnh cùng góc phải khác nhau thật, không phải 26 biến thể của một khuôn hình.
- `close` là cận cảnh phong cảnh (vật chính cách máy 1–5 m, 35–85mm, vẫn thấy một lát hậu cảnh), không phải macro.

## Đa dạng trong một đề tài

Mỗi `shots.json` (một category × một góc) phải trải đều trên các trục sau; mỗi shot ghi `tags.comp`, `tags.anchor`,
`tags.season` và câu `composition` riêng (không dựa vào composition mặc định).

| Trục | Luật |
|---|---|
| `comp` (kiểu bố cục) | wide: `across` ≤5, `overlook` ≤5, `low-foreground` ≤5, `tele-layers` ≤4, `big-sky` ≤4, `natural-frame` ≤4, `axis` ≤3 · mid: `side-anchor` ≤5, `diagonal` ≤5, `look-down` ≤4, `look-up` ≤4, `past-foreground` ≤4, `tele-isolate` ≤5, `reflection` ≤3 · close: `texture-field` ≤5, `hero-object` ≤5, `water-detail` ≤5, `top-down` ≤4, `edge-line` ≤4, `backlit` ≤4; dùng ít nhất tất cả trừ một kiểu |
| `anchor` (vật mắt dừng lại) | mỗi giá trị ≤ 6 shot; với `waterfalls-rivers` anchor là dạng nước (plunge, cascade, rapids, pool, braided, gorge…) |
| `season` | ≥ 3 mùa, không mùa nào > 50 %; `highland-wilderness` không thành rừng xanh mùa xuân |
| `look` | mỗi look 3–6 shot |
| ống kính | ≥ 4 tiêu cự khác nhau mỗi góc |
| motif qua 3 góc | một motif dễ nhận trên thumbnail (biển mây, cây đứng một mình, đảo đá, phản chiếu đối xứng…) ≤ 5 shot wide + mid mỗi category; close có motif đó ở hậu cảnh mờ thì không tính |
| trùng | không hai shot cùng (`comp`, `anchor`, `look`); subject không chỉ khác nhau ở tên loài cây hay màu đá |

- `axis` (nhìn dọc thung lũng/sông) và cảnh `deep` khó cho Muse: giữ ít, ghi `deep` trong trường clip.
- Duyệt ảnh: sau lượt đầu mỗi đề tài, PM xem contact sheet các ảnh đạt; cụm ảnh trông như một khuôn → sửa shot, không tạo thêm.

## Bốn category

### mountain-valleys

Dãy núi, thung lũng, đèo cao, sông núi và mây trôi. Cảnh phải có lớp tiền cảnh, trung cảnh và hậu cảnh rõ để tạo cảm giác độ sâu. Tránh địa danh nổi tiếng, kiến trúc lớn và khung cảnh quá siêu thực.

### alpine-lakes

Hồ trên núi, mặt nước phản chiếu, bờ đá, sương và mây thấp. Chuyển động ưu tiên là mặt nước nhẹ, sương trôi và mây chậm; không tạo sóng lớn nếu brief là calm.

### waterfalls-rivers

Thác, suối đá, sông qua khe núi và vực nước. Nước là anchor chuyển động chính; giữ dòng chảy liên tục, không để vật thể biến dạng hoặc nước chảy ngược.

### highland-wilderness

Cao nguyên, đồng cỏ núi, sườn thông xa, đường mòn cao và biển mây. Đây là category để hạ nhịp sau cảnh hùng vĩ; vẫn phải có không gian mở, không trở thành green woodland của bộ spring.

## Luật hình và clip

- Ảnh 16:9, photorealistic, ánh sáng tự nhiên, không collage, không khung, không text, logo, người, động vật hay xe.
- Không dùng landmark có thể nhận ra. Núi và hồ là phong cảnh tổng quát, tưởng tượng được.
- Bảng màu: slate blue, deep green, gray mist, muted gold. Không neon green, không màu fantasy, không HDR quá tay.
- Mỗi cảnh phải có ít nhất một chuyển động tự nhiên: nước, sương, mây, cỏ rung, cây rung hoặc ánh sáng trôi.
- Máy đứng yên (`static camera`); chuyển động đến từ chính cảnh: nước, sương, mây, cỏ, lá. Không zoom, không bay, không cắt cảnh.
- Mỗi category cần có cả sáng sớm, trời âm u và golden hour; không để cả kho chỉ có một giờ trong ngày.

## Duyệt ảnh

Chỉ cho ảnh đạt nếu đúng subject, đúng scale, photorealistic, 16:9 và có motion element thật sự nhìn thấy trong ảnh. Loại ảnh có người, động vật, chữ/logo, collage, sai vật lý, sai palette, watermark rõ, gần trùng ảnh đã đạt hoặc thiếu lớp không gian.

- Reviewer ghi `clip` ngay khi cho đạt: `shot`, `deep`, `motion`, `lock`, `light`, `sound`.
- `motion` chỉ liệt kê vật sẽ chuyển động và đang có trong ảnh: nước, sương, mây, cỏ, lá. Mây/sương chỉ viết "drift slowly sideways"; không viết lift, rise, roll in, clear, break apart (Muse làm mây dâng che núi).
- `lock` chỉ liệt kê địa hình và vật thể cố định: đá, bờ núi, thân cây, đường sông, đường chân trời và bố cục. Không đưa nước, lá, cỏ, mây hoặc sương vào `lock`. Băng, icicle, tuyết phủ là vật cố định: luôn vào `lock` để Muse không làm tan hay mọc thêm.
- Ghi chú các lỗi nhỏ ở góc để montage tránh cắt cận; không tự cho đạt ảnh chỉ vì có thể sửa bằng crop.
- Chất liệu chấm ở cỡ xem toàn khung (bề ngang ~1920): vân lưới/vân đan lặp của ChatGPT chỉ thấy khi phóng 1:1 trên một vùng đá/cỏ nhỏ ở cảnh wide/mid không phải lỗi (đẹp hơn hoàn hảo). Thành `not-photo` khi thấy ở cỡ toàn khung, hoặc ở close khi chất liệu đó là vật chính.
- Mùa trong ảnh phải khớp `tags.season`; ảnh hè mà cây vàng thu là `off-brief` (giữ cân bằng mùa của bộ).

## Hai lớp prompt

Prompt không viết lại thủ công cho từng job. `blocks.json` giữ các câu dùng chung; `shots.json` chỉ ghi subject, composition, lens, look, tags và `motion_elements` của cảnh.

### Prompt ảnh ChatGPT

Thứ tự ghép cố định (lớp không gian nằm trong `composition` của từng shot, `motion_ready` chỉ nêu vật chuyển động): `head` → `subject` → `composition` → `realism` → `look` → `natural light` → `motion_ready` → `clean` → `tail`.

- `subject` chỉ nói một địa điểm và 3–5 vật chính; không nhắc lại các câu chung trong blocks.
- `composition` phải nói rõ lớp tiền cảnh, trung cảnh, hậu cảnh và hướng nhìn; cảnh `wide` phải có quy mô, cảnh `mid` có anchor, cảnh `close` có một chất liệu chính.
- `motion_elements` là vật đang có thật trong ảnh và sẽ được animate: mặt nước, sương, mây, cỏ, lá; không yêu cầu Muse tự phát minh vật mới.
- Dùng lens để tạo đa dạng, nhưng tránh nhiều cảnh `close` bị ép thành macro. Ảnh phải là một phong cảnh 16:9 duy nhất, photorealistic, đúng tỷ lệ vật thể.
- Không dùng prompt phủ định dài dòng. Nếu một ảnh bị watermark, vật thể sai hoặc logo ở góc, sửa bằng một câu khóa cụ thể cho job đó; không thêm câu phủ định đó vào block chung theo phản xạ của một lỗi lẻ.

### Prompt video Muse

`video_prompt.json` tạo prompt theo thứ tự: camera ngắn → motion đã thấy trong ảnh → lock vật thể → khóa exposure/màu → sound. Reviewer ảnh ghi trường `clip` một lần, gồm `shot`, `deep`, `motion`, `lock`, `light`, `sound`.

- Máy quay (CEO 2026-10-09): mid/wide máy chạy rất nhẹ: câu *almost still* với một `slide`/`arc` trái/phải "less than a tenth of the way" (câu "about a thirtieth" làm Muse bay quá xa: 31/42 lượt `camera-far`); không drift forward, drone, rise, zoom. Cổng: máy dời < ~2 % = `camera-still` (chỉ với prompt máy chạy), > 35 % hoặc zoom > 1,2× = `camera-far`; trong ngưỡng thì cảnh mới lộ ở mép theo hướng máy vẫn đạt. `camera-far` với câu *almost still* → làm lại `static camera` và thêm chuyển động máy lúc ghép. Close: `static camera` (Muse bay 40–137 % ở close với mọi câu đi); clip static (close, mid/wide rơi về static, bản `.static.mp4` dự phòng) được thêm chuyển động máy lúc ghép (trượt/zoom chậm trên server).
- Giống thật: không vật nào (đá, cây, đỉnh núi, cành, người) xuất hiện, biến mất, mọc hay đổi hình; địa hình không đổi. Frame đầu không cần giống frame cuối.
- Mây, sương, nắng được thay đổi tự nhiên: trôi, dày, mỏng, dâng, tan, bóng mây lướt qua đều đạt nếu tốc độ như quay thật. `morph` khi mây/sương chạy nhanh kiểu timelapse, mọc ra từ hư không ở giữa trời, hoặc tan đi để lộ đỉnh núi/cây không có trong ảnh. `brightness` chỉ khi ánh sáng nháy/nhấp nháy hoặc nhảy giờ trong ngày kiểu timelapse (golden → chạng vạng trong 10 s).
- Kỹ thuật prompt (giảm AI look, không phải luật duyệt): cảnh có nước/cỏ/lá chuyển động thì prompt không nhắc tới trời, mây, sương ở bất kỳ câu nào (kể cả câu cấm: nhắc tới là Muse làm chúng động), close thêm "Everything else in the frame is perfectly still, like a photograph." sau câu motion; mid/wide máy chạy được nhắc mây/sương trôi chậm. Cảnh mà mây/sương là chuyển động duy nhất thì giữ câu mây trôi ngang. Ảnh wide nhiều trời (≥ 1/3 khung, mây tích, biển mây) là loại clip hay hỏng nhất.
- Chuyển động trong cảnh phải thấy rõ trong 10 s (`motion-missing` nếu không); một chuyển động chính, một ambient phụ.
- Mỗi câu motion chỉ nói một vật đang có trong ảnh; khóa vật thể giữ nguyên hình, vị trí, số lượng.
- Cắt đầu/đuôi chỉ khi có lỗi thật (khựng, nháy, nhảy hình, vật lạ ở 1–2 s đầu hoặc cuối); không cắt mặc định 1 s; giữ đoạn ≥ 7 s.
- Clip đạt khi đẹp, giống thật và không có `morph` (theo nghĩa trên), `scene-cut`, `motion-missing`, `brightness` (nháy/timelapse), người/chữ, `camera-far`, `camera-still` (prompt máy chạy).

## Bài học từ kho Christmas

- Block prompt và trường shot cố định giúp generator và reviewer làm việc ổn định hơn prompt viết tay.
- Reviewer ảnh phải ghi trường `clip` ngay khi cho đạt; không để PM mở lại 300 ảnh để viết prompt Muse.
- Loại cảnh quan trọng hơn việc thêm nhiều câu khóa: đường hội tụ dài, cảnh macro và phòng quá rộng có tỷ lệ lỗi cao. Với bộ này, giữ wide có lớp cảnh rõ và close vừa phải.
- Motion tự động chỉ là cổng lọc; reviewer vẫn phải xem morph, vật tự nhiên biến dạng và vật thể tự mọc ra. Ngưỡng đo không thay thế mắt người.
- Khi một category có tỷ lệ đạt thấp sau ít nhất 4 lượt, tạm giữ category đó thay vì đốt thêm credit. Lỗi lặp y nguyên sau câu khóa thì fail sớm.
- Sửa `blocks.json` hoặc `video_prompt.json` phải restart generator sau khi các cổng đang ở pha an toàn, rồi redraft queue còn chờ; không để job mới dùng khuôn cũ.

## Chiến lược ghép video

Album 1 tiếng = 80–100 clip của kho, xáo thứ tự, mỗi album một cách xáo; clip dùng lại qua nhiều album là bình thường.

- Xáo có ràng buộc nhẹ, không theo công thức `wide → mid → close`: tỷ lệ khoảng 35 % wide, 45 % mid, 20 % close; close không quá hai clip liền nhau.
- Hai clip liền nhau khác shot id và khác (`comp`, `anchor`); clip cùng anchor cách nhau ≥ 5 clip.
- Ánh sáng chỉ dịch một bậc giữa hai clip liền nhau (sáng sớm ↔ golden ↔ âm u ↔ ngày); không đặt golden cạnh âm u xám.
- Một clip được dùng nhiều lần trong album (cách nhau xa) và lật ngang để thành bản khác; không chạy ngược thời gian cảnh có nước chảy/thác (nhìn giả).
- Album chọn một category chủ đạo + một phụ; hai album liên tiếp khác thứ tự xáo và khác clip mở đầu.
- Muse cho clip 10 s; album nối crossfade, không cần clip loop liền mạch.
- Clip static (prompt `static camera`) được thêm chuyển động máy trên GPU server, **sau** upscale 1080p (upscale ra khung dư ~10 % để crop không phóng): close = push-in zoom 1,00 → 1,08 giữ tâm (thật nhất, nét nhất); mid/wide static = luân phiên trượt ngang ~7 % (crop 90 %) và chéo + zoom ×1,04. Dùng đường đi gần tuyến tính để máy không khựng ở đoạn crossfade.

## Kiểm tra trước khi dùng

Bộ cần có đủ category để mỗi album chọn một family chủ đạo và một family phụ. Hai album liên tiếp không dùng cùng family chủ đạo. Nếu một category có tỷ lệ redo cao vì nước, sương hoặc camera, giữ lại prompt tốt và giảm số lượt tạo lại trước khi mở rộng kho.
