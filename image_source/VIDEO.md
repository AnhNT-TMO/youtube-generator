# image_source: luật clip muse.ai (prompt + duyệt)

Prompt clip mới do `videos.py draft` ghép từ `video_prompt.json` (các câu bắt buộc dưới đây) + trường `clip` trong thẻ
cảnh; trường `clip` do reviewer ảnh ghi lúc cho ảnh đạt (mục *Trường clip*), nên không ai phải mở lại ảnh để viết prompt.
PM chỉ tự viết prompt sửa và cảnh đặc biệt theo mục *Prompt*; reviewer duyệt theo mục *Duyệt*.
Quy trình queue: `.claude/skills/pm-production/references/resource-queue.md`.

## muse.ai đo được

- 1 lượt = 1 clip 10 s, 24 fps, H.264 + AAC. Ảnh 16:9 → 1248×704. Không chọn được độ dài / độ phân giải.
- Khung 0 là ảnh gốc, ~0,5 s sau nhảy sang góc khác và lệch sáng → mọi clip cắt đầu ≥ 1 s.
- Muse đi xa gấp ~2 lần số ghi trong prompt: "a tenth" ra ~20–27 % (làm lại), "a twentieth" ra ~6–10 % (đạt).
- Câu đã thử cho từng vật chuyển động: `blocks.json` → `video.motion` và bảng *Vật chuyển động* trong `README.md`.

## Trường clip (reviewer ảnh ghi khi ok)

`resq.py verdict images <job> … ok --note "…" --card '{"clip": {…}}'`; các trường và nghĩa: `video_prompt.json` → `fields`.
Viết đúng những gì **thấy trong ảnh**: `motion` chỉ nêu thứ có thật (lửa đang cháy, nến, cốc có hơi, đèn cây…), `lock`
liệt kê vật chính dễ bị méo/mọc thêm, `window` tả cảnh ngoài kính không chữ gốc *snow*, `deep` = true cho cảnh sâu/toàn cảnh
rộng. `draft` tự chọn kiểu máy (cân bằng theo đề tài và cả bộ) và từ chối prompt trong nhà có chữ *snow*.

Ví dụ: `{"clip": {"shot": "Medium", "deep": false, "window": "dark pine trees and a lit village at night", "snowfall": false,
"motion": ["The wood fire in the stone fireplace burns with gentle dancing flames and glowing embers.", "A very faint, thin
wisp of steam curls up slowly just above the coffee cup on the low table.", "The warm white fairy lights on the Christmas tree
stay switched on the whole time and shimmer gently, all in the same warm white color as in the first frame."], "lock": "stone
fireplace, Christmas tree, sofa, low table, coffee cup and window frames", "light": "room", "sound": "a soft crackling fire and
a quiet cozy room tone"}}`

## Prompt

Mục tiêu: clip 10 s làm nền video Giáng sinh dài; máy quay chậm, nhẹ nhưng thấy được; cảnh sống bằng những thứ có sẵn
trong ảnh. Mỗi ảnh tự chọn hiệu ứng hợp với nó; các clip đa dạng (kiểu máy, thứ chuyển động). Tiếng Anh, một đoạn, theo thứ tự:

1. **Máy quay** (bắt buộc): `<Wide/Medium/Close> shot; the camera makes one slow, gentle, steady <move> that keeps going
   for the whole clip but covers only a very short distance, about a thirtieth of the frame width in total; it never travels down
   the aisle, path or room, so the last frame shows almost the same view as the first frame, every object still in frame.`
   - Đích: cả clip máy đi ~5–12 % bề ngang khung. Không bao giờ viết `locked tripod` / `camera stays still` / `clearly visible`.
   - `<move>` đổi luân phiên: `drift forward`, `drift back`, `slide to the left` / `slide to the right`, `rise`, `arc`.
   - Toàn cảnh ngoài trời rộng (hồ, núi, rừng, phố mái nhà) và cảnh sâu (lối đi, hành lang, đường hầm đèn, lối giữa nhà
     nguyện, dãy kệ): `slide` ngắn hoặc `arc`; không `drift forward`, không `toward <vật ở xa>`.
   - `drift back` và `rise` đi gấp 2–3 lần: ưu tiên `slide` / `arc`. Mái kính / trần nhiều đèn: không `rise`.
   - Phòng rộng chụp chéo (giường màn, bàn tiệc dài): `arc` nhỏ.
   - **Lần làm lại vì đi quá xa lần hai:** `<Wide/Medium> shot; the camera is almost still, with only a tiny, barely noticeable
     arc to the <left/right> over the whole clip: it moves less than a tenth of the way and never <travels toward X>, so the last
     frame shows the same view as the first frame, with <vật chính> all in frame.`
   - Tàu, cáp treo: `stands still on its track and keeps its exact length, shape and position`.
2. **Thứ chuyển động có trong ảnh** (2–4 câu, nói rõ vị trí): lửa, nến, khói cốc, đèn cây, hơi nước, mặt nước gợn, khói
   ống khói, cực quang, đèn cabin / toa tàu, lá cờ.
3. **Tuyết:**
   - Cảnh trong nhà: không chữ nào gốc *snow* (snow, snowy, snowflakes, winter wonderland…), kể cả khi tả cảnh ngoài cửa.
   - Cảnh trong nhà có cửa sổ: ba câu nguyên văn ngay sau câu máy quay: `The view through the windows stays frozen like a
     still photograph of <cảnh ngoài, không chữ snow>, with nothing moving outside.` · `The air inside the room is perfectly
     clean, clear and still: no particles, flakes, dust or sparkles float or fall anywhere inside the room.` · `Only the flames
     and the lights inside the room move.`
   - Cảnh ngoài trời có tuyết trong ảnh: `Light snowflakes drift down slowly through the cold air.`
4. **Sự sống (tùy chọn, ~1/3 cảnh ngoài trời):** bò / gà / ngựa / cừu ở trang trại, nai ở rừng, chim nhỏ trên cành, vịt trên
   nước không đóng băng; ít con, đi chậm, trung/hậu cảnh. Không người, không thú trong nhà / nhà nguyện / phố đông.
5. **Khóa cảnh:** `The <kiến trúc/đồ vật chính> keep their exact shape and position; doors stay closed; no new objects, people,
   hands or text appear; no statues, busts, sculptures or figures of people.`
6. **Ánh sáng:** `The <light/room> stays as bright and warm as the first frame throughout, with the same colors.`
7. **Âm thanh:** `Sound: <âm thanh hợp cảnh>.`

Không viết câu phủ định về chuyển động ("snow never falls inside"); chỉ nói điều cần có.

**Prompt sửa (PM):** giữ phần đã đúng, chỉ đổi câu gây lỗi theo note reviewer: đi quá xa → `slide`/`arc` hoặc câu
*almost still*; gần như đứng yên → câu chuẩn với `slide`/`arc`; hạt trong phòng → kiểm lại không còn chữ snow + ba câu
cửa sổ; vật mọc ra / méo → thêm vật đó vào câu khóa cảnh.

## Duyệt

**Ưu tiên số một: clip không được lộ là AI** (CEO 2026-10-04). Soi kỹ từng giây xem có vật nào tự mọc ra, tự biến
mất, đổi hình hay trôi lệch khỏi cảnh ngay trong khung (bụi cây, cây, đèn, đồ đạc, cửa sổ, mái nhà, thú, xe…): đó là
lỗi nặng nhất, kể cả khi máy đạt. Vật ra/vào ở **mép** khung đúng theo hướng máy trượt là bình thường, không phải lỗi.

Chạy `videos.py check <job>` (in sẵn % máy dời và tỉ lệ zoom) rồi xem `seconds.jpg` (vật mọc/mất/méo giữa khung), `edges.jpg` (cắt đầu bao nhiêu) và
`full8.jpg` (hạt trong phòng, chữ, người ở độ phân giải đầy đủ) + số đo độ sáng / cắt cảnh. Chỉ mở thêm `full3.5.jpg` /
`sheet.jpg` khi còn nghi (hạt mờ, vật đổi giữa clip). Mỗi verdict ghi `--codes` theo `resource.json` → `video.codes`.

**Làm lại (`redo`)** khi có:

- Bất kỳ hạt trắng nào bay/rơi trong nhà (phòng, nhà kính, hành lang), kể cả chấm mờ (`indoor-particles`).
- Người, tay, bóng người; tượng/tượng bán thân mọc ở mép (`people`).
- Vật tự mọc ra, tự biến mất hoặc đổi hình ngay trong khung (không phải do máy trượt đưa vào/ra ở mép); vật méo; vật
  chuyển động nhân đôi / chồng nhau (tàu, cáp treo) (`morph`). Note ghi vật gì, ở đâu, giây nào.
- Chữ/số đọc được mọc ra; logo/biểu tượng kiểu watermark đứng yên ở góc màn hình (`text`). Đèn tắt hoặc đổi màu giữa clip (`lights`).
- Tốc độ máy (CEO 2026-10-04): dùng số "máy dời" của `check` (góc khung dịch lớn nhất so với giây 1 / bề ngang).
  < ~2 % → `camera-still`; trượt > 35 % hoặc zoom > 1,2× → `camera-far` (cổng tự động đã loại phần lớn trước khi tới
  reviewer). Trong ngưỡng thì vật chính trượt ra mép hay cảnh mới lộ ở mép theo hướng máy **vẫn đạt**.

**Đẹp hơn hoàn hảo** (CEO 2026-10-04): cảnh đẹp nổi bật mà chỉ có 1–2 sạn nhỏ, xa, khó thấy (vd. người tí hon ở xa
không mọc ra/biến mất rõ, chi tiết nhỏ ở hậu cảnh) → `ok`, note ghi sạn gì, ở đâu, giây nào để lúc ghép tránh cắt cận.
Vẫn `redo` khi lỗi lộ rõ kiểu AI ở vùng người xem nhìn vào (vật/người hiện ra-biến mất rõ, biến hình, hạt trong nhà).

**Cắt rồi đạt** (`verdict … ok --trim-head S --trim-tail S`), chỉ khi phần còn lại ≥ `video.min_seconds_after_trim` giây
(script từ chối nếu ít hơn → chọn `redo`):

- Mọi clip: `--trim-head` ≥ 1.
- Máy vượt ngưỡng chỉ ở mấy giây cuối (Muse hay tăng tốc nửa sau): cắt đuôi nếu vẫn còn đủ độ dài.
- Con vật thêm vào tự hiện ở đầu → cắt tới khi cảnh ổn định.
- `cắt cảnh ở X s` hoặc độ sáng tụt/lên mạnh ở cuối → cắt đuôi trước điểm đó.
- Độ sáng trôi chậm đều (máy lùi khỏi vùng sáng) là bình thường, không cắt.

**Hết 3 lượt mà cảnh trong nhà có cửa sổ vẫn lọt tuyết:** PM `fail` với note `nosnow`; sau này tạo lại ảnh có cửa sổ không
tuyết rồi thêm tuyết GPU chỉ trong ô kính (`video-resource-videos/scripts/window_snow.sh`).
