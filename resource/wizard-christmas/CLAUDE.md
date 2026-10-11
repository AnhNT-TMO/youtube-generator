# Wizard-school Christmas resource

## Mục tiêu

Kho cảnh Giáng sinh ở một trường phép thuật trong lâu đài cổ, tuyết, nến, lửa, huyền bí và ấm áp, cho các album
Christmas mới của Everstill (CEO 2026-10-09). Ảnh ChatGPT → clip muse.ai 10 s, máy quay chậm như bộ `image_source/`.

- Đích phase 1: **320 clip đạt**, 10–15 video; lặp clip và lật ngang được. Hiệu quả tốt thì scale thêm.
- **Không thương hiệu:** không tên trường, nhà, nhân vật, phim hay sách; không huy hiệu, quốc huy, con vật biểu tượng,
  chữ, logo. Prompt tả chung ("ancient castle school of magic", "the scarlet-and-gold house"). Nhà chỉ nhận ra bằng màu.
- Ghép video: xáo như luật hero của `image_source/MONTAGE.md`, cảnh đẹp nhất lên trước; luật trùng cast riêng làm sau.

## Cấu trúc và số lượng

| Thư mục | Clip | Có học sinh | Cảnh ngày |
|---|---|---|---|
| `castle/great-hall` sảnh tiệc lớn | 40 | 13 | 5 |
| `castle/vista` lâu đài từ xa | 35 | 5 | 12 |
| `common-room/{scarlet,emerald,sapphire,amber}` phòng sinh hoạt 4 nhà | 10 × 4 | 4 × 4 | 1 × 4 |
| `castle/library` thư viện khổng lồ | 30 | 12 | 6 |
| `castle/staircase` cầu thang đá cổ | 20 | 8 | 4 |
| `castle/dormitory` ký túc xá | 25 | 10 | 5 |
| `grounds/keeper-hut` túp lều người giữ khóa | 25 | 8 | 8 |
| `town/wizard-alley` hẻm phố phù thủy | 30 | 12 | 9 |
| `town/wizard-village` làng phù thủy tuyết | 35 | 14 | 12 |
| `grounds/snow-forest` rừng tuyết huyền bí | 25 | 6 | 8 |
| `grounds/viaduct-train` tàu hơi nước đỏ qua cầu đá | 15 | 3 | 7 |
| **Tổng** | **320** | **107** | **80** |

Màu nhà: scarlet = đỏ tươi + vàng kim · emerald = xanh lục + bạc · sapphire = xanh dương + đồng · amber = vàng + đen.

## Luật ảnh

- Ảnh thật kiểu khung phim fantasy live-action, 16:9; không tranh vẽ, không 3D.
- Giờ: 75 % đêm / chạng vạng (`candle-night`, `twilight`, `snowy-night`), 25 % ngày tuyết (`snow-day`, `interior-day`):
  trời xám bạc, tương phản thấp, cửa sổ và đèn vẫn sáng ấm để đứng cạnh cảnh đêm không lệch.
- Phép thuật được dùng: nến bay lơ lửng **đứng yên tại chỗ**, tuyết phép rơi **thưa** từ trần sảnh, đom đóm, nến phép
  trong rừng (không đèn lồng). Không cầu thang di chuyển, chân dung cử động, đũa phép phát sáng. Hiệu ứng nào muse làm
  sai nhiều lần thì bỏ khỏi shot mới.
- Rừng tuyết huyền bí: không đáng sợ, không sinh vật.
- Tàu: một đầu máy hơi nước đỏ cổ kéo toa đỏ, không biển số, không chữ. Trong clip tàu **chạy** chậm đều dọc cầu, khói hơi kéo về sau (CEO 2026-10-10); ảnh để chỗ trống phía trước đầu tàu.

**Học sinh** (`tags.people` = `students`, ~1/3 mỗi nhóm): 1–3 người, cỡ vừa hoặc xa, **chỉ thấy lưng / sau đầu**,
đứng hoặc ngồi yên (nhìn cửa sổ, nhìn lò sưởi, đọc sách). Áo chùng đen trơn, khăn len sọc màu nhà, không huy hiệu, không
đũa. Phòng sinh hoạt của nhà nào thì khăn màu nhà đó; nơi khác trộn màu các nhà.

## Duyệt ảnh

Đạt khi đúng subject, photoreal, 16:9, có thứ chuyển động thật trong ảnh và đẹp. Lỗi:

- `face`: thấy mặt, nghiêng mặt quá nửa, hoặc người quay về phía máy.
- `people`: sai số người, người quá gần (chiếm > 1/3 cao khung), người ở cảnh không có học sinh, người lạ ở xa, tượng/chân dung người.
- `brand`: huy hiệu, quốc huy, con vật biểu tượng trên cờ/khăn/áo, logo, bất cứ chi tiết gọi tên thương hiệu.
- `text`: chữ, số, biển có chữ, gáy sách có chữ đọc được.
- `physics`, `off-brief`, `not-photo`, `format`, `duplicate`, `watermark`, `motion-missing` như các bộ khác.
- Cảnh đẹp còn 1–2 lỗi rất nhỏ ở xa vẫn cho đạt.

Reviewer ghi `clip` khi cho đạt theo `video_prompt.json` → `fields`: `people` tả đúng người trong ảnh (rỗng nếu không có),
`still_air` = true cho cảnh trong nhà không tuyết phép, `indoor_snow` = true khi có tuyết phép.

## Luật clip

CEO 2026-10-10: không đo zoom / độ dời khung nữa; muse làm máy quay cơ bản ổn. Clip chỉ bị loại khi **hỏng**:

- Soi khung mỗi **0,5 s** từ đầu tới cuối, so từng cặp liền nhau: vật hiện ra / biến mất / nhảy chỗ / đổi hình mà khung trước không có
  (kiểu AI) → `morph` hoặc `people`. Vật mới vào từ mép khung do máy di chuyển là bình thường.
- Vật chuyển động **đúng**: lửa, nến, khói, tuyết, nước động tự nhiên; vật phải đứng yên thì đứng yên (nến bay, học sinh);
  tàu chạy dọc cầu, giữ số toa và hình dạng.
- Cắt đầu ≥ 1 s (khung đầu muse nhảy). Còn ≥ 7 s.
- `face-turn`: học sinh quay đầu, nhìn lại, lộ mặt dù chỉ thoáng.
- `people`: người mới xuất hiện / biến mất, người đi lại, tay chân biến dạng.
- `morph`: vật hiện ra / biến mất / biến dạng (nến bay đổi chỗ, toa tàu dài ra, mái nhà chảy, đồ đạc đổi chất liệu).
- `particles`: hạt bay trong nhà không có trong brief, hoặc tuyết phép dày che cảnh.
- `lights` (đèn đổi màu / tắt), `brightness`, `scene-cut`, `camera-still` (máy đứng im hẳn), `watermark`.
- Huy hiệu, cờ hiệu, chữ do muse tự vẽ thêm **được giữ, không phải lỗi** (CEO 2026-10-10: AI sinh, không giống hệt bản gốc;
  ưu tiên tỉ lệ đạt), kể cả chữ trùng đúng tên trong truyện/phim (vd. tên tiệm kẹo). Ảnh ChatGPT vẫn giữ luật không huy hiệu / chữ.
- Không xét máy đi xa, zoom, lùi, hạ thấp hay khung cuối khác khung đầu, miễn là không có vật nhảy / mọc ra kiểu AI.
