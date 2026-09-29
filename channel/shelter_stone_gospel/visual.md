# Hình ảnh: Shelter Stone Gospel

Luật hình riêng của kênh (nháp 2026-09-28, CEO duyệt dần). Skill `thumbnail-prompt` là quy trình; file này là nội dung.
`thumb.py check` đọc khối ``` dưới *Prompt ảnh mặc định (ChatGPT)* (giữ nguyên tên mục).

## Thế giới hình của kênh

- Một người đàn ông đã có tuổi, mệt, đang hát lời cầu nguyện của mình trong một **nhà nguyện đá** cũ, tối: tường đá thô, vòm
  đá, cửa sổ kính màu, ánh sáng vàng hổ phách ấm rọi qua cửa sổ tràn khắp khung, bóng tối nâu sẫm ấm (CEO 2026-09-28: theo thị hiếu ngách 65+, khung
  hình và cảnh nghiêng hẳn về tông vàng; không dùng bóng xanh lạnh). Đá = nơi che chở (tên kênh); ánh sáng = lời đáp.
- **Hằng số** (CEO 2026-09-28): khuôn mặt ca sĩ (`model/`), nhà nguyện đá + **một thánh giá thật** (gỗ thô hoặc đá chạm, gắn
  trên tường hoặc trong khung cửa sổ, được ánh cửa sổ chạm vào), bảng màu thumbnail vàng hổ phách + nâu sẫm + chữ vàng kim (avatar/banner giữ tông đá của thương hiệu).
  Chỗ đặt, chất liệu, cỡ thánh giá và dáng cửa sổ đổi theo từng ảnh. Người xem sùng đạo 65+: thánh giá cho biết ngay đây là nhạc thờ phượng.
- Ông **hát bằng cả tâm hồn, nhiệt huyết** (CEO 2026-09-28): miệng mở to gào hát, đầu hơi ngửa, gân cổ nổi, một tay giơ lòng bàn tay
  lên trời hoặc nắm chặt trên ngực; hoặc nhắm mắt ngước lên, nhíu mày, nước mắt, tay đặt trên ngực hoặc giơ lòng bàn tay; micro
  chrome cổ trên chân đứng trước miệng. Mặt luôn nhận ra được, nhìn hoặc quay về phía chữ.
- Trang phục: vest/áo khoác nhà thờ trơn, tông trầm (than, xanh đêm, nâu đỏ sẫm, xanh rêu, nâu lạc đà), sơ mi tối; đổi màu mỗi
  video. Không gấm vàng, không lấp lánh.
- **Không dùng** (tổ hợp riêng của kênh khác; chữ vàng và tông vàng là chuẩn chung của ngách nên được dùng): chữ vàng vát cạnh 3D
  rắc kim tuyến, thánh giá vàng phát sáng lơ lửng giữa khung, bokeh vàng dày, hội
  chúng giơ tay phía sau, logo vẽ trong ảnh, vest gấm/brocade. Thánh giá không nằm sau cột chữ. Không giống người thật hay người nổi tiếng.

## Ảnh mẫu (form cố định) + biến thể

- **Ảnh mẫu:** `branding/master/thumbnail.jpg` (CEO 2026-09-28, chỉ trên máy). Mọi thumbnail giữ đúng **form** của ảnh này: nhân vật to
  (~1/2 khung, mặt ~45 % chiều cao), lời cầu xin rất to bằng chữ vàng nổi khối, thanh dưới viền vàng với huy hiệu GOSPEL BLUES bên trái và
  dòng `1 HOUR OF …` to căn giữa, logo nhỏ ở góc trên, tông vàng hổ phách, một thánh giá thật trong cảnh. Duyệt bản nháp = đặt cạnh ảnh mẫu.
- **Micro:** chỉ một loại, đúng chiếc trong ảnh mẫu (`branding/ref/microphone-ref.png`, đính kèm mọi lượt). **Chữ vàng:** đính kèm
  `branding/ref/gold-lettering-ref.png` (chỉ lấy chất liệu).
- **Biến thể mỗi video:** `thumb_pool.json` (5 trục: bố cục, kiểu chữ vàng, tư thế, trang phục, cảnh; 3.600 tổ hợp).
  `python3 .claude/skills/thumbnail-prompt/scripts/thumb.py variant <dir> --title "<lời cầu xin>"` chọn một tổ hợp khác các video gần đây
  và in các dòng dán vào THIS IMAGE. Bố cục `center_low` (chữ vắt ngang nửa dưới, trước ngực nhân vật) chỉ khi lời cầu xin ≤ 26 ký tự;
  `between_hands` (chữ giữa mặt và bàn tay giơ lên) đi kèm tư thế giơ tay sang bên.
- Bố cục chữ trái: `<dir>/video.json` đặt `logo.corner "tl"`, `subscribe.corner "bl"`; chữ phải hoặc giữa: `tr` / `br`. Badge luôn do
  ChatGPT vẽ ở đầu trái thanh (kênh tắt `badge` trong `video.json`); trong video cinema, ô badge phải nằm trong `static_zones`
  (vd. `[0.0, 0.74, 0.17, 1.0]`) để badge không bị camera kéo lệch khỏi thanh.

## Bố cục khung hình (ảnh ngang video 1 giờ)

Mỗi video của kênh dài **1 giờ** (CEO 2026-09-28; Mercy Harbor làm 2 giờ, mình không theo điểm này).

Người nghe phần lớn trên 65 tuổi, xem trên điện thoại (CEO 2026-09-28): chữ rất to, tương phản mạnh, người gần, cảnh ít.

| Phần | Chiếm | Cách đặt |
|---|---|---|
| **Nhân vật** | **~1/2 khung**, một bên (mặc định trái), to và gần như chuẩn ngách (CEO 2026-09-28) | cắt ở ngực/eo, mặt cao ~45 % chiều cao khung, quay về phía chữ; **tư thế đổi mỗi video** (giơ một tay lòng bàn tay lên trời · chắp hai tay trước ngực · tay đặt trên ngực · hai tay nắm micro · dang hai tay · tay chạm trán), ghi `pose` trong `thumbnail-prompt.md` và không lặp tư thế của 2 video trước |
| **Chữ chính** | ~1/2 khung, bên kia | lời cầu xin 3–4 dòng, dòng lớn nhất 15–18 % chiều cao, nét đậm |
| **Thanh dưới** | toàn chiều ngang, **~14 % đáy** | nền tối trong suốt viền hổ phách mảnh; đầu trái: **huy hiệu "GOSPEL BLUES"** (cao ~17 % khung, nhô lên khỏi mép thanh một chút), **ChatGPT vẽ vào ảnh** theo ảnh đính kèm `image_source/badge.png` để cùng chất vàng, ánh sáng với thanh chữ (CEO 2026-09-28; không dán bằng code nữa); chữ `1 HOUR OF …` **to (~55 % chiều cao thanh), căn giữa** trong khoảng 16–94 % chiều ngang; nút subscribe hiện đè đầu phải thanh vài giây mỗi lần |
| **Góc logo + subscribe** | luôn ở **phía bên chữ** (CEO 2026-09-28) | chữ phải → logo avatar nhỏ góc trên phải, subscribe góc dưới phải; người phải, chữ trái → cả hai sang trái. Góc logo (12 % ngang × 20 % dọc) tối, trống; cột chữ không vào góc này |

- **Chữ đặt cao** (CEO 2026-09-28): đỉnh cột chữ ngang đỉnh thánh giá (~10–14 % chiều cao), **đáy ≤ 65 %**; xa sóng nhạc (~82–85 %)
  và thanh tiến trình của YouTube ở đáy khung.
- **Lề cho chuyển động video:** cột chữ cách mép trái/phải ≥ 7 % và mép trên ≥ 6 % chiều khung; sát hơn thì video phải thu nhỏ
  chuyển động camera để chữ không ra khỏi khung (`cinema` tự thu, in cảnh báo).
- Sau chữ là tường đá trong bóng tối hoặc bóng tối xóa phông: không nguồn sáng, không mặt, không chi tiết rối.
- Chữ chính: **vàng ròng bóng loáng, nổi bật hẳn** (CEO 2026-09-28, mẫu chất liệu `branding/ref/gold-lettering-ref.png` chỉ để lấy màu/độ bóng):
  serif in hoa nét rất dày, mặt chữ vàng rực, ánh sáng trắng-vàng lóa trên mép trên, rãnh vát đồng-nâu sẫm, cạnh vát 3D sắc, viền tối
  mảnh, bóng đổ sâu, vài điểm lóe sáng nhỏ; gọi (LORD, · JESUS, · GOD, · FATHER,) đứng riêng một dòng.
- Thanh dưới: `1 HOUR OF <X>` (+ lời hứa ngắn) chữ sans hẹp in hoa màu kem, chữ khóa màu vàng kim; ≤ 32 ký tự (chỉ ~70 % thanh).
- Lớp phủ video: logo (`image_source/logo.png`) + subscribe đứng yên trên góc phía bên chữ; ảnh nguồn của video **không** có logo,
  ảnh JPG upload làm thumbnail YouTube được dán logo bằng code đúng chỗ đó (`video-generator/scripts/thumb_logo.py <dir>`). Chữ trái thì `<dir>/video.json` đặt
  `logo.corner: "tl"`, `subscribe.corner: "bl"` (mặc định kênh `tr` / `br`). Sóng nhạc: thấp, sát mép trên thanh dưới, dưới cột chữ. Trong video chữ là một lớp riêng: đứng yên trên màn hình, phóng nhẹ
  3 % mỗi 7 s, còn cảnh (người, nhà nguyện) chuyển động theo camera.

## Chữ chính trên ảnh (`title_text`)

Lời cầu xin `<GỌI>, <LỜI CẦU XIN>`, không phải title YouTube; 6 phép thử giống Lamplight: nói nỗi đau sâu nhất, "đó là mình",
cụ thể, còn treo nỗi lo, đọc được trong 1 giây (≤ 5 chữ sau lời gọi, ≤ ~32 ký tự, dòng ≤ ~13 ký tự). Nguồn câu: kho câu R&D
`research/phrase-bank/` qua `album.md` → `brief.thumbnail_text` (câu cầu nguyện chung dùng nguyên văn được, CEO 2026-09-28; không
tên/branding kênh khác; không lặp chữ ảnh của video trước của kênh).

## Kiểm trên từng bản nháp (Claude nhìn ảnh)

- Góc logo trống; trong thanh chỉ có dòng `1 HOUR OF …` và badge GOSPEL BLUES ở đầu trái, đúng badge đính kèm (chữ đọc được,
  cùng chất vàng với thanh), không logo nào khác. ChatGPT hay vẽ badge to hơn yêu cầu (~20 % chiều cao thay vì 17 %): chấp nhận
  khi không đè chữ của thanh.
- Chữ đúng từng chữ; mặt giống `model/` (~68 tuổi, má hơi hõm, nếp nhăn sâu, tóc xoăn ngắn muối tiêu, râu xám-bạc dày), năm
  ngón tay; xem bản thu nhỏ 240 px: chữ đọc được ngay, mặt nhận ra.
- Không có dấu hiệu "Không dùng" ở trên.

## Prompt ảnh mặc định (ChatGPT)

```
Create ONE image for the YouTube channel "Shelter Stone Gospel" (soul gospel prayer worship): the scene described below, as one complete standalone wide 16:9 landscape frame at 2K resolution (2560x1440 pixels). One single picture: no collage, grid, split screen or side-by-side panels.
PHOTO: a cinematic, photorealistic photograph with deep contrast inside an old, dim stone chapel: rough weathered stone walls and arches, a stained-glass window letting in rich warm golden-amber light with soft visible light rays that fill the frame, and one real cross (rough wood or carved stone) on the wall or in the window, touched by that light. The whole picture leans warm gold and amber; shadows are deep warm brown, never cool blue. Not glossy, not fantasy, not a painting or 3D render.
MICROPHONE AND CROSS: always the same microphone as the attached microphone reference (a classic vintage chrome microphone with a rounded capsule, horizontal grille slots and a chrome swivel mount on a stand), in front of him, never a modern handheld or any other microphone; every cross is a plain cross with no figure on it.
THE SINGER: big and close to the camera like the niche's leading thumbnails (about half of the frame, his face about 45% of the frame height), singing with his whole soul, passionate and full of fervor. The man in the attached reference image is the channel's singer and must be the same person: an original Black man about 68 years old, weathered medium-dark brown skin, slightly hollow cheeks, deep lines on the forehead, around the eyes and from nose to mouth, short curly salt-and-pepper hair, a full soft grey-white beard and moustache, medium build. Keep his face, hair, beard and skin tone recognisably the same as the reference. Only his pose, expression, clothing and lighting change as described below. His face is always recognisable. Natural hands with five fingers.
LETTERING: the title exactly as written below, spelled letter for letter, in powerful, extra-bold heavy serif capitals with very thick strokes that look cast in solid gold with crisp 3D bevels, a thin dark outline and a deep dark drop shadow, punctuation exactly and only where written (no extra apostrophes, commas or marks), in the finish given by the "Lettering finish" line below (the attached gold lettering sample shows the level of shine and depth; take only its material, never its words or layout), 3 to 4 lines (the call like "LORD," on its own line), VERY LARGE for elderly viewers on a small phone screen: the title block covers about half of the frame, placed exactly as the "Layout" line below says, its largest line about 15-18% of the frame height, at least 7% away from the left and right edges and never lower than 80% of the frame height. At the bottom, a full-width dark translucent bar about 14% of the frame height with a thin warm gold line on its top edge; in the bar the "Bar line" given below exactly as written, in large condensed bold sans-serif capitals about 55% of the bar's height, warm cream with the key words in gold, centered between 16% and 94% of the frame width. At the LEFT end of the bar, the attached round "GOSPEL BLUES" badge, reproduced faithfully (same emblem, same words, same shape), about 17% of the frame height, its bottom resting in the bar and its top rising slightly above the bar's gold line, lit and finished in the same warm gold as the bar text so it belongs to the same design. No other text, no watermark, no logo, no border.
FREE AREAS: a small channel logo and a subscribe button are placed over the image later on the lettering side. Keep the top corner on the lettering side (outer 12% of the width, top 20% of the height) dark, plain and empty; the lettering never enters it.
AVOID: glitter or sparkle texture on the letters, cool blue or teal color casts, any logo, emblem or circle other than the attached badge at the left end of the bar, a glowing golden cross floating in the air, dense golden bokeh, a cross behind the lettering, a crowd or congregation behind him, gold brocade or glitter clothing, a halo, neon, cartoon look, distorted hands, extra people, any resemblance to a real person or celebrity.
```

## Ảnh dọc Shorts

(nháp PM 2026-09-28, chờ CEO duyệt; CEO 2026-09-28: không micro, không đạo cụ, đứng thẳng chính diện nhìn người xem)

Mỗi Short có **ảnh dọc 9:16 mới**, không cắt từ ảnh album. Ảnh là nền video Short (video-generator vẽ câu hook, lời bài,
spectrum, CTA, logo) và là khung đầu người xem thấy khi lướt.

- **Chỉ ông ca sĩ đứng trong nhà nguyện đá:** cùng người trong `model/` (ảnh tham chiếu chính `model/01-front-eye-contact.png`),
  **đứng thẳng, chính diện, mắt mở nhìn thẳng người xem**; không nhắm mắt, không nghiêng 3/4, không profile. Khung 3/4 người
  (từ đùi/gối trở lên) hoặc cả người, mặt đầy cảm xúc như ảnh album (hát hết lòng, nước mắt).
- **Tư thế đổi mỗi Short** (không lặp Short trước): hai tay giơ cao, dang rộng hai tay, hai bàn tay mở trước ngực, tay đặt trên
  tim… Một lựa chọn CEO thích: **thánh giá thật phía trên ông rực sáng, ánh sáng đổ xuống từ trên cao** như Chúa giáng thế.
  **Không micro, không đạo cụ** (không bàn, ghế, nến, đèn, sách, đồ vật): chỉ người, nhà nguyện đá, ánh cửa sổ kính màu và một
  thánh giá thật. Trang phục như ảnh ngang.
- **Cùng vibe với ảnh album của Short đó:** ánh vàng hổ phách qua cửa sổ kính màu, thánh giá thật, bóng tối nâu ấm, và giữ không khí
  riêng của ảnh album (vd. cửa sổ mưa bão với khe sáng vàng). Khác ảnh album ở tư thế và khung dọc; cảm xúc lấy từ lời của đoạn Short
  (`short.json` → `captions`).
- **Kiểu ảnh theo Shorts đang lên của ngách:** trước khi viết prompt, làm sheet Shorts (skill rnd-youtube-api:
  `yt.py fast --file research/phrase-bank/gospel.yaml --kind short --name <tên>` rồi `yt.py sheet --from <json> --vertical --top 12`
  → `research/yt/sheets/<ngày>-<tên>.jpg`), đọc sheet, gọi tên 2–3 mẫu của các Short nhiều view/ngày nhất (khung, cử chỉ, màu,
  ánh sáng) và ghi dưới *Ý tưởng*. Lấy cảm hứng, không sao chép: không người thật, không chữ, không bố cục y hệt một Short.
- **Không chữ trên ảnh**, không logo, không huy hiệu: video vẽ hết.
- **Bố cục điện thoại** (khớp lớp chữ Short của video-generator: logo góc trên trái ~2–8 %, câu hook ~13 % trong 3 s đầu,
  CTA ~55 % 4 s cuối, lời bài ~63 %, spectrum ~70–75 %; giao diện YouTube che ~10 % trên, ~25 % dưới, ~12 % mép phải,
  `docs/seo-youtube/09-shorts.md` §1): mặt ở nửa trên, từ 20 % đến 52 % chiều cao (đỉnh đầu không cao hơn 20 %); 18 % trên cùng
  là vòm/tường đá tối, trơn; tay chỉ ở trên 52 % (trên ngực, giơ lên); từ 56 % trở xuống yên và tối hơn (vạt áo, quần, sàn đá,
  bóng tối ấm): không mặt, không tay, không điểm sáng, không chi tiết rối; 12 % mép phải tối, đơn giản. Thánh giá và cửa sổ nằm
  trong khoảng 18–55 % (ưu tiên đỉnh thánh giá ≥ 18 %).
- **Ngoại lệ bố cục (PM 2026-09-28, sau Short 001):** tư thế "ánh sáng từ trên thánh giá" được để một chùm sáng mềm đi xuống từ
  mép trên (câu hook vẫn đọc được nhờ viền + bóng chữ của video); tay giơ được chạm gần mép trái/phải khi ở trên dải lời bài
  (trên 56 %). ChatGPT hay vẽ thánh giá cao hơn mốc xin (Short 001: xin 20 %, ra ~8 %) và tay dang rộng hơn mốc xin.
- Kiểm bản nháp như ảnh ngang (mặt giống `model/`, năm ngón tay, không dấu hiệu "Không dùng") + không có chữ, không micro, không
  đồ vật + `thumb.py check` báo các vùng dọc không rối; xem bản thu nhỏ 360 px chiều cao: mặt vẫn nhận ra.

## Prompt ảnh dọc Shorts (ChatGPT)

(nháp PM 2026-09-28, chờ CEO duyệt)

Khối **CORE dọc**: dán nguyên văn ở đầu mọi prompt ảnh Short; `thumb.py check` bắt đủ từng dòng (thư mục Short). Sau đó
khối THIS IMAGE như ảnh ngang nhưng không có Title / Bar line / Layout chữ.

```
Create ONE image for the YouTube channel "Shelter Stone Gospel" (soul gospel prayer worship): the scene described below, as one complete standalone tall vertical 9:16 portrait frame made for a phone screen (1440x2560 pixels). One single picture: no collage, grid, split screen or side-by-side panels.
PHOTO: a cinematic, photorealistic photograph with deep contrast inside an old, dim stone chapel: rough weathered stone walls and arches, a stained-glass window letting in rich warm golden-amber light with soft visible light rays, and one real cross (rough wood or carved stone) on the wall or in the window, touched by that light. The whole picture leans warm gold and amber; shadows are deep warm brown, never cool blue. Not glossy, not fantasy, not a painting or 3D render.
ONLY THE SINGER: the singer stands alone and upright in the chapel, facing the camera straight on (frontal view), seen as a three-quarter figure (from the thighs up) or a full figure. There is NO microphone and NO props: no microphone stand, table, chair, candle, lamp, book, bench or any other object; only the man, the stone chapel, its stained-glass window light and the one cross, a plain cross with no figure on it.
THE SINGER: the man in the attached reference image is the channel's singer and must be the same person: an original Black man about 68 years old, weathered medium-dark brown skin, slightly hollow cheeks, deep lines on the forehead, around the eyes and from nose to mouth, short curly salt-and-pepper hair, a full soft grey-white beard and moustache, medium build. Keep his face, hair, beard and skin tone recognisably the same as the reference. Only his pose, expression, clothing and lighting change as described below. He looks straight into the camera with his eyes open, making direct eye contact with the viewer (never eyes closed, never in profile or three-quarter view), and sings his prayer with his whole soul, full of emotion; his face is always recognisable and lit by the warm light, never hidden or in silhouette. Natural hands with five fingers.
CLOTHING: the sweater and shirt in the reference image only fix his face; dress him as described below, always in a plain, dark-toned church suit, never gold brocade, glitter or anything flashy.
NO TEXT: no lettering, title, words, numbers, watermark, logo, badge or border anywhere in the image; all text is added later by the video.
PHONE LAYOUT: his face sits in the upper half of the frame, between 20% and 52% of the height from the top (the top of his head no higher than 20%), and his hands stay above 52% of the height. The top 18% of the frame is dark stone wall or vault with no detail and no light source inside the frame (when a soft beam of light comes down from above, only its faint soft rays may pass through this area); the top of the cross is preferably at or below 18% of the height. Everything below 56% of the height is calm and darker (his suit, the stone floor, warm shadow) with no face, no hands, no bright light and no busy detail. Keep the right 12% of the width dark and simple; only raised hands above 56% of the height may reach toward the left and right edges.
AVOID: any text or logo, a microphone or any prop or object, closed eyes, a profile or three-quarter view, glitter or sparkle, cool blue or teal color casts, a glowing golden cross floating in the air, dense golden bokeh, a crowd or congregation behind him, gold brocade or glitter clothing, a halo, neon, cartoon look, distorted hands, extra people, any resemblance to a real person or celebrity.
```
