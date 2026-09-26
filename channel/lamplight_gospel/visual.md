# Hình ảnh: Lamplight Gospel

Luật hình riêng của kênh. Skill `thumbnail-prompt` là quy trình (viết prompt, sinh ảnh ChatGPT, chọn, fit 4K, check);
file này là **nội dung**: thế giới hình của kênh, hằng số, khối CORE, các trục biến thể, những gì phải kiểm trên ảnh.
`thumb.py check` đọc khối ``` dưới *Prompt ảnh mặc định (ChatGPT)* (giữ nguyên tên mục).

## Thế giới hình của kênh

- Ánh sáng (đèn dầu, tông vàng ấm) đến với một người đàn ông nghèo, mệt mỏi, đã có tuổi, ở một nơi đơn sơ: khuôn mặt hằn nếp,
  mệt, được ánh sáng nâng lên.
- **Hai hằng số mặc định:** ngọn đèn hổ phách (điểm sáng nhất khung hình, ánh sáng của nó chạm tới ông) và khuôn mặt ca sĩ
  (`model/`). Mọi trục khác chọn theo vibe bài ở *Biến thể hình ảnh*. Một version experiment được đổi cả hai (vd. tĩnh vật
  không người); ranh giới thật ở `channel.md` → *Hợp đồng kênh*.
- Quần áo luôn nghèo, cũ, sờn hoặc vá, thuộc một trong năm loại trang phục; không bao giờ tuxedo, vest hay nơ
  (quần áo trong ảnh `model/` chỉ để cố định khuôn mặt), không gì trông giàu có.
- `biblical`: cả cảnh thuộc thời đó (đá, cây ô liu, đèn dầu đất nung) và ông **không bao giờ là Chúa Giêsu**.
- Tư thế: chọn file `model/` gần góc muốn nhất (`model/README.md`); ông nhìn hoặc quay về phía chữ hay ánh sáng, không nhìn ra
  ngoài khung. Mặt luôn nhận ra được ở mọi khung hình (không bóng đen toàn phần, không quay lưng).
- Bố cục: theo *Bố cục khung hình* ngay dưới (chữ to, người gần, cảnh ít).
- **Vật kể chuyện:** khi tên bài hay lời cầu xin nêu một vật, một màu hay một nơi (tấm biển đỏ, cánh cổng, chiếc ghế trống),
  vật đó nằm sát ông, trong phần cảnh ít ỏi của khung, nhận ra được ở bản thu nhỏ, không phải chi tiết nhỏ ở mép khung. Vật mang màu
  (biển đỏ, kính màu) thì dùng luôn làm ánh sáng nhấn `accent`: câu chuyện tự cho tương phản màu.

## Bố cục khung hình (ảnh ngang album + single)

CEO 2026-09-26: người nghe dòng nhạc này phần lớn trên 65 tuổi (báo cáo bên thứ ba) và xem trên điện thoại, nơi chữ và người
trong thumbnail rất nhỏ. Vì vậy **chữ to, người gần, cảnh ít**:

Tỉ lệ đo trên các video gospel blues đang thắng trong ngách (R&D `research/trends/lamplight_gospel/thumbs/2026-09-26-layout.md`:
chữ 40 %, tiêu đề 32 %, dòng lớn nhất 17 % chiều cao, người 40 %, mặt 40 % chiều cao, cảnh 15 %). Bố cục này là chuẩn vào sân
(hit và flop cùng template đo gần như nhau); lượt bấm do câu chữ và chủ đề quyết định.

| Phần | Chiếm | Cách đặt |
|---|---|---|
| **Chữ** (tiêu đề + dòng "Lamplight Gospel" + dòng thời lượng) | **~2/5 khung** | một cột bên trái (mặc định) hoặc bên phải; riêng khối tiêu đề **~1/3 khung, tối đa 45 %**; dòng chữ lớn nhất cao **15–18 % chiều cao khung**, nét đậm, 3–4 dòng, ~5 chữ |
| **Nhân vật** | **~2/5 khung** | phía đối diện chữ, từ ngực trở lên (`close` / `medium`), mặt cao **35–40 % chiều cao khung**, nhìn hoặc quay về phía chữ hay ngọn đèn |
| **Cảnh** | **~1/5 khung, chạy ra sau chữ** | một dấu hiệu nơi chốn hoặc vật kể chuyện nhận ra được sát nhân vật (lan can hiên, ghế trống, khung cửa sổ); cảnh kéo dài ra sau cột chữ |

- **Chữ đè lên cảnh** (như các kênh gospel blues đang thắng, không nền đen trơn): phần cảnh nằm sau chữ là vùng **tối vừa, ít chi
  tiết** (hậu cảnh xóa phông, trời đêm, tường trong bóng, sương); chữ được có bóng tối mềm quanh nét để tách nền. **Không đặt sau
  chữ:** nguồn sáng hay vùng ánh vàng chói (chữ vàng trên nền vàng là lỗi R&D thấy ở flop), mặt người, đường sọc (lan can, rào,
  mái), tán lá, chỗ chuyển sáng/tối gắt.
- **Đèn** ở sát ông (trong tay, trên bàn ngay cạnh, treo cạnh đầu) để quầng sáng rơi lên mặt; không đặt trong cột chữ hay ngay sau chữ.
- **Chữ trái, người phải** (mặc định): mặt nằm trong khoảng 50–82 % chiều ngang (tránh logo góc trên phải); áo, thân dưới được
  vào góc dưới phải miễn tối và trơn. **Chữ phải, người trái:** cột chữ không vượt 84 % chiều ngang và tránh cả hai góc phải.
- **Chữ phải ngắn để to được:** dòng dài nhất ≤ ~13 ký tự; lời cầu xin album ≤ ~32 ký tự cả câu, không quá 8 chữ (xem *Chữ chính
  trên ảnh*). Tên bài single dài hơn thì chia 3–4 dòng, vẫn giữ cỡ chữ.
- **Kiểu chữ nào cũng ở bản nét đậm:** nét mảnh (serif tương phản cao, chữ viết tay mảnh) mất khi thu nhỏ; ba hit dùng script/serif
  mảnh có chữ nhỏ nhất nhóm (11–13 %).
- **Không chữ phụ nào nhỏ hơn dòng thời lượng:** không câu Kinh Thánh, hàng icon, câu trích, tracklist chữ nhỏ trên ảnh.
- **Không dùng** cho ảnh ngang: `wide`, `lamp-front`, `hands` (người nhỏ hoặc mặt mờ, trái tỉ lệ 2/5); chỉ khi một experiment
  khai báo trong `direction.md`. Ảnh dọc Shorts không có chữ nên theo mục *Ảnh dọc Shorts*.
- Ví dụ chọn theo bài: "Hold my trembling hands" → `close`, hai tay ông khum quanh ngọn đèn ngay dưới mặt; "Morning Is Coming" → tia sáng đầu tiên
  trên chân trời sau lưng ông, đèn vẫn sáng. Bài kết bình yên → `close` + `dawn` + `sepia`; một đêm tuyệt vọng → `close` +
  `single` + `mono`; bài đường xa, chờ đợi → `traveler` + `rain`; bài kể lại một cảnh Kinh Thánh → `biblical` với đèn dầu đất nung;
  cao trào có choir → `sunday` (áo choir cũ) trong nhà thờ gỗ nhỏ.

## Kiểm trên từng bản nháp (Claude nhìn ảnh)

- Chữ chính (album: lời cầu xin; single: tên bài, xem *Chữ chính trên ảnh*), dòng "Lamplight Gospel" và (ảnh album) dòng thời lượng đúng từng chữ; ảnh single không có dòng thời lượng.
- Mặt giống `model/`: ông già ~75 tuổi, tóc xoăn + râu đầy bạc trắng, mặt hằn nếp sâu, không trẻ lại, không giống người nổi tiếng nào. Năm ngón tay.
- Không có gì quan trọng trong các góc bị phủ; đèn là điểm sáng nhất; vẫn đọc được ở cỡ điện thoại (xem bản thu nhỏ **240 px
  ngang**, cỡ video gợi ý trên điện thoại: chữ tiêu đề tách hẳn khỏi nền và đọc được ngay, mặt ông nhận ra được). Sau chữ có
  nguồn sáng, mặt, đường sọc, tán lá hay chi tiết rối thì bản nháp không đạt.
- **Tỉ lệ** (*Bố cục khung hình*): chữ ~2/5 khung (tiêu đề ~1/3, tối đa 45 %), dòng lớn nhất cao 15–18 % chiều cao khung; nhân
  vật ~2/5, mặt 35–40 % chiều cao; cảnh ~1/5. Dòng lớn nhất dưới ~13 % chiều cao, mặt dưới ~30 % chiều cao, hoặc có chữ phụ nhỏ
  hơn dòng thời lượng thì vẽ lại.
- **Góp ý của công cụ chấm thumbnail (vidIQ…)** chỉ là gợi ý chung cho mọi ngách; thước đo thật là CTR và view (`results.md`).
  Nhận: chủ thể to hơn/gần hơn, tương phản màu có sẵn trong câu chuyện, nền gọn sau chữ. Bỏ: mũi tên, biểu tượng hay màu cảnh
  báo, emoji trên ảnh, làm ảnh nhạt hay mờ đi (ngược thế giới đèn dầu tương phản mạnh, và kiểu clickbait không hợp người nghe
  gospel lớn tuổi). Không làm lại ảnh đã chọn chỉ vì điểm thấp; bài học đưa vào ảnh sau.
- Sửa lỗi hay gặp: `.claude/skills/thumbnail-prompt/references/chatgpt.md` (chữ nhỏ sửa thành "Lamplight Gospel").
- Title ở dưới-trái: ChatGPT đặt dòng "Lamplight Gospel" ở y ≈ 0.86–0.89 (6/6 bản, đo 2026-09-24), trong vùng thanh spectrum; ghi rõ trong Composition "the Lamplight Gospel line no lower than 78 % of the height" (ảnh album có dòng thời lượng: "the Lamplight Gospel line no lower than 72 % and the duration line no lower than 80 % of the height").
- `lantern.center`: điểm sáng đầu của `thumb.py check` hay rơi vào ống khói thủy tinh (cao hơn ~2 %) hoặc bóng phản chiếu dưới đèn trên mặt quầy/bàn bóng; đo trên ngọn lửa.

## Prompt ảnh mặc định (ChatGPT)

Khối **CORE**: dán nguyên văn ở đầu mọi prompt tạo thumbnail (album, idea, bài đăng riêng); `thumb.py check` bắt đủ từng dòng.
Chỉ giữ những gì **không bao giờ đổi**: ngọn đèn vàng là điểm sáng nhất, khuôn mặt nhân vật, quần áo nghèo cũ, hệ hệ chữ (dòng "Lamplight Gospel"), vùng trống
cho lớp phủ video (logo 232px góc trên phải, nhóm like/subscribe 448×80 góc dưới phải, sóng nhạc giữa đáy). Mọi thứ khác (khung
hình, ánh sáng, màu, thời tiết, bối cảnh, trang phục cụ thể) viết trong khối **THIS IMAGE**, chọn từ mục *Biến thể hình ảnh* bên
dưới. Đính kèm 1–2 ảnh nhân vật trong `model/`. Mỗi lần gửi xin 3 ảnh riêng, 2K (ChatGPT Images 2.0).

```
Create ONE image for the YouTube channel "Lamplight Gospel" (soulful gospel blues music): the scene described below, as one complete standalone wide 16:9 landscape frame at 2K resolution (2560x1440 pixels). One single picture: no collage, grid, split screen or side-by-side panels.
PHOTO: a cinematic, photorealistic photograph with rich film-like contrast and real, humble textures (old wood, worn fabric, stone, chipped enamel): the light of God reaching a poor, weary man in a humble place. Not glossy, not luxurious, not fantasy, not a painting or 3D render.
THE LAMP: a warm amber flame (the lamp described below) is always the brightest point of the frame, and its light always reaches the singer. Everything else stays darker than the flame.
THE SINGER: the man in the attached reference image is the channel's singer and must be the same person: an original elderly Black man in his mid-70s, deeply weathered dark-brown skin with deep lines on the forehead, around the eyes and down the cheeks, a long gentle sorrowful face, heavy-lidded kind tired eyes, thick curly silver-white hair receding at the temples, a full soft silver-white beard and moustache, lean and slightly stooped, large work-worn hands. Keep his face, hair, beard and skin tone recognisably the same as the reference. Only his pose, clothing and lighting change as described below. His face is always recognisable (never hidden or fully in silhouette). Natural, work-worn hands with five fingers.
CLOTHING: the cardigan and shirt in the reference image only fix his face; dress him as described below. He is a poor, humble man: his clothes are always plain, old and visibly worn or mended, never new, smart, rich or glamorous. The exact outfit is described below.
LETTERING: the title exactly as written below, spelled letter for letter, in the title style described below, 3 to 4 lines (a call like "LORD," may stand on its own line), VERY LARGE and bold for elderly viewers on a small phone screen: the title block covers about a third of the frame (never more than 45%), its largest line about 15-18% of the frame height, heavy strokes (no thin hairlines), in warm light tones (ivory, cream or gold) with a soft dark shadow around the letters so they separate clearly from the picture. Only when THIS IMAGE gives a "Message line": that text exactly as written, one line directly under the title, in the same colour and style as the title, about a third of its letter height. Under them a thin gold horizontal rule broken in the middle by the words "Lamplight Gospel" in a smaller italic serif; this small line never changes style. Only when THIS IMAGE gives a "Duration line": directly under the "Lamplight Gospel" line, that text exactly as written, centred under the rule, in letter-spaced warm gold capitals of a clean bold serif, about a third of the title's letter height, with "1 HOUR" in bold, one line only. No other text (no scripture, quotes, icons or song lists), no watermark, no logo, no border.
LAYOUT: all lettering about two fifths of the frame in one column on one side; the singer about two fifths on the other side (from the chest up, close to the camera, his face about 35-40% of the frame height); the scene about one fifth, one recognisable sign of the place right beside him, and the scene continues behind the lettering. The part of the scene behind the lettering is moderately dark and calm (softly blurred background, night sky, a wall in shadow or mist): no light source, no bright golden glow, no face, no railings, fence lines or leaves behind the letters. The lamp sits right beside him, never inside or behind the lettering column.
FREE AREAS: a logo and a subscribe button are placed over the image later. Keep the top-right corner (right 16% of the width, top 26% of the height) and the bottom-right corner (right 28%, bottom 14%) dark and simple, and keep faces and lettering (including the "Lamplight Gospel" line and the duration line) out of the bottom 15% of the frame.
AVOID: tuxedo, bow tie, necktie, pocket square, a smart or matching suit, polished formal wear, jewelry or anything that looks rich or glamorous, fedora or any hat, a microphone or guitar as the main subject, a halo, a crown of thorns or any suggestion that he is Jesus, a bright blue daytime or heavenly sky, neon, glitter, cartoon look, distorted hands, extra people unless asked, any resemblance to a real celebrity.
```

## Ảnh dọc Shorts

Mỗi Short có **ảnh dọc 9:16 mới** (CEO 2026-09-25), không crop từ ảnh album/single. Ảnh là nền của video Short (video-generator
thêm ánh đèn, bụi, spectrum, lời bài, câu hook) và là khung đầu người xem thấy khi lướt.

- Cùng thế giới hình, hai hằng số, quần áo và AVOID như ảnh ngang. Cảnh lấy từ **chính đoạn lời của Short** (điệp khúc), khác
  cảnh của ảnh album và ảnh single cùng bài (bối cảnh hoặc tư thế khác), giữ chữ ký album (`signature`) ở màu/ánh sáng.
- **Kiểu ảnh theo trend:** trước khi viết prompt, đọc sheet Shorts mới nhất của R&D (`research/trends/<ch>/shorts/*-sheet.jpg` +
  bảng `.md`, lệnh `trend.py shorts`). Gọi tên 2–3 mẫu của các Short được xem nhiều nhất (khung hình, bối cảnh, chủ thể, màu,
  ánh sáng) và chọn `framing`/bối cảnh/`light` gần với mẫu đang thắng trong khả năng của thế giới kênh. Ghi mẫu đã theo dưới
  *Ý tưởng* của `thumbnail-prompt.md`. Lấy cảm hứng, không sao chép: không người thật, không chữ, không bố cục y hệt một Short cụ thể.
- **Không chữ trên ảnh:** hook, lời bài, CTA do video chồng lên (đúng chính tả, đúng giờ).
- **Bố cục điện thoại** (khớp lớp chữ của `video.json` → `short`): mặt và đèn ở nửa trên, từ 20 % đến 52 % chiều cao (đỉnh đầu
  không cao hơn ~18 %: ChatGPT hay vẽ đầu cao hơn mốc xin vài %, nên prompt xin 20 %; cận cảnh thì lệch tới ~8 %, xin ~28 %); 18 % trên cùng tối, đơn giản (logo
  nhỏ góc trên trái, câu hook ở ~6–15 % trong 3 s đầu); từ 56 % trở xuống yên, tối hơn (sàn, bàn, vạt áo, bóng tối): không mặt, không
  tay, không điểm sáng, vì lời bài ở ~63 %, spectrum ở ~72 %, title/nút của YouTube ở 25 % đáy và 12 % mép phải.
- Kiểm bản nháp như ảnh ngang (mặt giống `model/`, năm ngón tay, đèn sáng nhất) + không có chữ nào + `thumb.py check` báo các
  vùng dọc không rối; xem bản thu nhỏ 360 px chiều cao: mặt vẫn nhận ra.

## Prompt ảnh dọc Shorts (ChatGPT)

Khối **CORE dọc**: dán nguyên văn ở đầu mọi prompt ảnh Short; `thumb.py check` bắt đủ từng dòng (thư mục `shorts/`). Sau đó
khối THIS IMAGE như ảnh ngang nhưng không có Title/Title style/Duration line.

```
Create ONE image for the YouTube channel "Lamplight Gospel" (soulful gospel blues music): the scene described below, as one complete standalone tall vertical 9:16 portrait frame made for a phone screen (1440x2560 pixels). One single picture: no collage, grid, split screen or side-by-side panels.
PHOTO: a cinematic, photorealistic photograph with rich film-like contrast and real, humble textures (old wood, worn fabric, stone, chipped enamel): the light of God reaching a poor, weary man in a humble place. Not glossy, not luxurious, not fantasy, not a painting or 3D render.
THE LAMP: a warm amber flame (the lamp described below) is always the brightest point of the frame, and its light always reaches the singer. Everything else stays darker than the flame.
THE SINGER: the man in the attached reference image is the channel's singer and must be the same person: an original elderly Black man in his mid-70s, deeply weathered dark-brown skin with deep lines on the forehead, around the eyes and down the cheeks, a long gentle sorrowful face, heavy-lidded kind tired eyes, thick curly silver-white hair receding at the temples, a full soft silver-white beard and moustache, lean and slightly stooped, large work-worn hands. Keep his face, hair, beard and skin tone recognisably the same as the reference. Only his pose, clothing and lighting change as described below. His face is always recognisable (never hidden or fully in silhouette). Natural, work-worn hands with five fingers.
CLOTHING: the cardigan and shirt in the reference image only fix his face; dress him as described below. He is a poor, humble man: his clothes are always plain, old and visibly worn or mended, never new, smart, rich or glamorous. The exact outfit is described below.
NO TEXT: no lettering, title, words, numbers, watermark, logo or border anywhere in the image; text is added later.
PHONE LAYOUT: his face and the lamp sit in the upper half of the frame, between 20% and 52% of the height from the top (the top of his head no higher than 20%). The top 18% of the frame is plain dark background (wall, ceiling, night sky). Everything below 56% of the height is calm and darker (floor, table, coat, shadow) with no face, no hands, no bright light and no busy detail. Keep the right 12% of the width dark and simple.
AVOID: tuxedo, bow tie, necktie, pocket square, a smart or matching suit, polished formal wear, jewelry or anything that looks rich or glamorous, fedora or any hat, a microphone or guitar as the main subject, a halo, a crown of thorns or any suggestion that he is Jesus, a bright blue daytime or heavenly sky, neon, glitter, cartoon look, distorted hands, extra people unless asked, any resemblance to a real celebrity.
```

## Chữ chính trên ảnh (`title_text`)

CEO 2026-09-25:

- **Album (và idea sẽ thành album):** chữ chính là **một lời cầu xin**, dạng `<GỌI>, <LỜI CẦU XIN>` (GỌI = LORD · GOD · JESUS ·
  FATHER), viết hoa, **không phải tên bài**; tên bài 1 vẫn là title YouTube của video. PM viết và chọn, ghi trong
  `brief.decisions.thumbnail_concept`.
- **Câu này là lý do người ta bấm** (CEO 2026-09-25): nó phải khắc họa **linh hồn của album** và chạm vào tâm hồn người nhìn
  ngay khi lướt qua. Một câu đúng khi:
  1. Nói ra **nỗi đau, nỗi sợ hay khát khao sâu nhất của câu chuyện album** (điều nằm dưới mọi bài), không phải một lời cầu
     chung chung hay tên thể loại. Vd. người già sợ căn nhà im tiếng khi mình đi → `LORD, DON'T LET THIS HOUSE GO QUIET`.
  2. Người xem đọc thấy **"đó là mình"**: ngôi thứ nhất, lời họ muốn nói mà chưa nói được (cha mẹ có con ở xa, người góa, người kiệt sức).
  3. **Cụ thể**, có một hình ảnh hay một điều đang bị đe dọa (căn nhà, các con, một đêm), không dùng chữ nhà thờ trừu tượng
     ("sing over", "abide", "anointing").
  4. Còn **treo một nỗi lo chưa được giải**: người xem bấm để nghe câu trả lời (album).
  5. **Đọc được trong 1 giây ở cỡ điện thoại, bởi người trên 65 tuổi:** chữ thường ngày, ≤ 5 chữ sau lời gọi, ≤ ~32 ký tự cả câu,
     dòng dài nhất ≤ ~13 ký tự, để chữ in to được (*Bố cục khung hình*).
  6. **Mới:** không trùng title/chữ ngách (`research/trends/<ch>/snapshots/`) và web; không lặp chữ của title YouTube.
- Cách làm: đọc câu chuyện album, lời bài 1, hook, câu nặng nhất trong album → viết 5–8 câu ứng viên → chấm từng câu theo 6 điều
  trên → chọn câu mạnh nhất, ghi lý do trong ledger. Kho `experiments/phrases.yaml` chỉ là nguồn cảm hứng + sổ đã dùng (không
  lặp trong 14 ngày), **không giới hạn**: câu mới viết thẳng rồi thêm vào kho.
- **Single:** chữ chính là **tên bài** (nguyên văn như track), không có dòng thời lượng.
  - **Dòng thông điệp** (version `single-message-line`, xem `production/<ch>/direction.md`): khi tên bài là một ẩn dụ không tự nói
    ra nỗi lòng hay lời hứa (vd. "Red As A Barroom Sign"), thêm một dòng 2–4 chữ viết hoa dưới tên bài, lấy từ lời bài: lời hứa
    hay câu trả lời mà bài đem lại (vd. `WASHED CLEAN`), không lặp chữ của title YouTube. Ghi trong THIS IMAGE nguyên văn
    `Message line: "<CHỮ>"` và trong front matter `message_line`. Tên bài đã tự nói điều đó (vd. "Stay With Me, Lord") thì không thêm.
- **Short:** ảnh không có chữ (video chồng hook + CTA).

## Dòng thời lượng (chỉ ảnh album)

Chủ kênh 2026-09-25: ảnh **album** (và idea sẽ thành album) có thêm một dòng ngay dưới dòng "Lamplight Gospel" để người xem
nhận ra ngay đây là album dài 1 giờ, không phải bài lẻ, và có một lời hứa khiến họ muốn bấm (CTR). Áp dụng cho mọi thumbnail
album mới; ảnh album đã có giữ nguyên. **Single không bao giờ có dòng này** (đó là chỗ phân biệt).

- Dạng: `1 HOUR OF <X>` · `1 HOUR WITH <X>` · `1 HOUR IN <X>`, viết hoa, tiếng Anh, ≤ 28 ký tự cả dòng. Chữ "1 HOUR" luôn
  đứng đầu và in đậm; kiểu chữ cố định mọi album (khối CORE) để thành dấu nhận diện.
- Chọn `<X>` theo **vibe của chính ảnh thumbnail** (ánh sáng, bối cảnh, tư thế, cảm giác người xem nhận ngay), không theo tên
  bài và không lặp chữ của lời cầu xin phía trên: người xem đọc được lời hứa trong ảnh trước khi đọc title. Một lời hứa cụ thể, cho người đang mệt/cần an ủi, hơn là một
  chữ chung chung.
- Gợi ý theo ảnh (tự viết thêm được, giữ dạng trên):

  | Ảnh cho thấy | Dòng |
  |---|---|
  | đêm tĩnh, một ngọn đèn, cầu nguyện một mình | `1 HOUR WITH GOD` · `1 HOUR OF PRAYER` · `1 HOUR OF LISTENING TO GOD` |
  | sương, ánh sáng mềm, ngồi nghỉ | `1 HOUR OF PEACE` · `1 HOUR OF STILLNESS` · `1 HOUR OF REST` |
  | bình minh, ánh sáng mới | `1 HOUR OF HOPE` · `1 HOUR OF NEW MERCY` |
  | hai tay khum quanh đèn, bữa ăn đơn sơ, gia đình | `1 HOUR OF THANKSGIVING` · `1 HOUR OF GRATITUDE` |
  | mưa, bão, đường xa | `1 HOUR OF COMFORT` · `1 HOUR OF STRENGTH` |
  | nhà thờ gỗ, choir, ngợi khen | `1 HOUR OF PRAISE` · `1 HOUR IN HIS PRESENCE` |

- Chỉ viết "1 HOUR" khi album đủ ≥ 60 phút (plan `validate` ước lượng; album-assembly kiểm master). Ghi vào front matter
  `duration_line:` và dòng `Duration line: "<…>"` của THIS IMAGE; `thumb.py check` so hai chỗ.
- Dòng này làm khối chữ cao thêm: đặt title cao hơn một chút để dòng thời lượng vẫn ở trên 15 % đáy (xem *Kiểm trên từng bản nháp*).

## Biến thể hình ảnh (chọn theo vibe bài)

Chủ thể cố định chỉ có **ngọn đèn vàng** và **khuôn mặt nhân vật**. Mọi trục dưới đây được đổi, và agent **chọn theo vibe của bài**
(lời, `imagery`, `emotion`, `energy`, `arc_role`), không chọn ngẫu nhiên hay bằng tool (chủ kênh 2026-09-24). Nhiều tổ hợp tự nó
làm ảnh ít trùng; không cần xem lại mọi ảnh cũ. Câu tiếng Anh trong `backtick` là mẫu để dán vào dòng tương ứng của THIS IMAGE
(sửa chi tiết cho hợp cảnh).

**Chữ ký album.** Ảnh album chọn **kiểu chữ title** + 2–3 trục làm chữ ký theo vibe cả album (vd. `letterpress` + mưa + màu teal), ghi ở `signature:` trong
front matter. Các single của album đó giữ chữ ký và đổi các trục còn lại, để người xem nhận ra cùng một "mùa" mà không tưởng là
video album. Album mới chọn chữ ký khác album ngay trước (đọc cột chữ ký trong `thumb.py list`, không cần mở ảnh).

### Trang phục (`wardrobe`)

Luôn nghèo, cũ, sờn hoặc vá. Đổi giữa các ảnh; mỗi loại đổi được màu, lớp áo, chỗ vá.

| Loại | Hợp với bài về | Mẫu (dòng Clothing) |
|---|---|---|
| `work` Lao động cũ | cơm áo, ngày làm việc, gia đình, hóa đơn | `a faded work shirt or flannel with frayed cuffs, a patched old coat or cardigan, work trousers, old suspenders` |
| `farm` Nông dân | ruộng, vườn, mùa màng, mưa nắng, chuồng trại | `faded denim bib overalls patched at one knee over a worn long-sleeve thermal undershirt with the sleeves pushed up, dusty work boots` |
| `traveler` Người lữ hành | đường xa, chờ đợi, trở về, mưa, tuyết, gió | `a long threadbare wool overcoat with the collar turned up, a frayed knit scarf, old wool trousers, scuffed boots` |
| `sunday` Đồ đi lễ của người nghèo | nhà thờ gỗ nhỏ, ngợi khen, choir, lời chứng | `his one old Sunday jacket, secondhand and a size too big, shiny at the elbows and mended at a pocket, over a clean but yellowed white shirt buttoned to the collar, no tie` · hoặc `a faded, much-mended old choir robe of a small country church` |
| `biblical` Vải thô thời Kinh Thánh | bài kể lại chính cảnh Kinh Thánh (manna trong sa mạc, bình bột của bà góa, người chăn chiên, đường Emmaus) | `a long tunic of undyed, coarse homespun linen, a heavy brown wool mantle draped over one shoulder, a rope belt, worn leather sandals` |

`biblical`: cả cảnh theo thời đó (nhà đá, cây ô liu, đồi sa mạc, đèn dầu bằng đất nung `a small clay oil lamp`), không đồ
hiện đại. Ông là người hành hương / chăn chiên / người thường của thời ấy, **không bao giờ là Chúa Giêsu** (không hào quang, không
mão gai, không áo trắng phát sáng; AVOID đã chặn).

### Chữ title (`lettering`)

Chọn theo vibe **album** và giữ cho cả album cùng các single của nó (là một phần của chữ ký album; chủ kênh 2026-09-24).
Chỉ chữ title đổi kiểu. Dòng nhỏ "Lamplight Gospel" và vạch vàng luôn giữ nguyên để nhận diện kênh. Kiểu nào cũng ở bản
**nét đậm** và đọc rõ trên điện thoại ở bản 240 px (*Bố cục khung hình*). Màu chữ theo `palette` (vd. `cold` → trắng ngà, `sepia` → kem).

| Kiểu | Hợp với album về | Mẫu (dòng Title style) |
|---|---|---|
| `serif` Serif thanh lịch | cầu nguyện, đêm dài, an ủi, trang nghiêm | `a bold, heavy serif with thick strokes, elegant but sturdy, ivory to warm gold` |
| `brush` Chữ viết tay bút lông | lời tâm tình, gia đình, biết ơn, bài mộc và gần gũi | `warm hand-lettered brush script with thick, bold strokes, like ink written by hand, ivory to soft gold, every letter clearly legible at small size` |
| `letterpress` Chữ gỗ in mòn kiểu áp phích nhà thờ quê | blues, lao động, nông trại, energy cao, lời chứng mạnh | `a bold, weathered slab-serif like old letterpress wood type on a country church poster, cream with worn edges` |
| `bible` Chữ hoa khắc kiểu trang Kinh Thánh cổ | kể chuyện Kinh Thánh, di sản, thế hệ, trang trọng | `bold classic Roman capitals with heavy strokes like the title page of an old family Bible, warm gold` |
| `glow` Chữ mảnh phát sáng như ánh đèn | hy vọng, bình minh, phục hồi, bài kết êm | `a graceful serif with sturdy, medium-heavy strokes that glows softly from within like lamplight, warm amber halo, crisp edges, clearly legible at small size` |

### Khung hình (`framing`)

Mặt vẫn tránh các góc bị phủ và 15 % đáy. Ảnh ngang chỉ dùng `close`, `medium`, `rim` (*Bố cục khung hình*); `wide`, `hands`,
`lamp-front` chỉ khi experiment khai báo.

| Giá trị | Mẫu (dòng Look) |
|---|---|
| `medium` trung cảnh | `a medium close shot from the chest up, close to the camera, he fills about two fifths of the frame, his face large` |
| `close` cận mặt | `a close-up: his face and shoulders fill about two fifths of the frame on one side, the background dissolves into soft blurred bokeh` |
| `rim` ngược sáng | `he is lit from behind and one side by the lamp, a warm rim of light around his head and shoulders, face in three-quarter profile` |

### Ánh sáng (`light`)

| Giá trị | Mẫu (dòng Look) |
|---|---|
| `single` một ngọn đèn giữa đêm | `one single lamp in near-total darkness, deep black shadows, strong chiaroscuro, no other light` |
| `moon` đèn + trăng | `cool blue moonlight on the edges of everything, warm lamplight on his face` |
| `mist` sương thành vệt sáng | `thick mist: the lamplight becomes a visible golden beam with floating dust` |
| `rain` mưa | `rain falling, drops catching the lamplight as bokeh, wet surfaces reflecting the flame` |
| `snow` tuyết | `snow falling, frost on every edge, his breath visible, warm light against the cold` |
| `dawn` trước bình minh | `the faint first light of dawn low on the horizon, still much dimmer than the lamp, no visible sun, no gold or orange sky` |
| `sunrise` nắng sớm | `soft early sunrise, the sun itself hidden behind the house or trees, warm gold haze near the horizon; the upper sky is the dimmest part of the frame and the lamp stays clearly the brightest point` |
| `fireflies` đom đóm | `a few fireflies glowing in the dark around him` |
| `fire` thêm ánh lửa | `a second, dimmer glow from a stove or fire in the background` |
| `accent` màu nhấn của câu chuyện (đổi vật + màu theo bài) | `a red glow from the painted glass sign above him (lit from inside, not neon tubes) washes one side of his face and coat, clearly dimmer than the flame; the other side is warm lamplight, a bold contrast between the two colours` |

### Màu (`palette`)

| Giá trị | Mẫu (dòng Look) |
|---|---|
| `blue` xanh đen + hổ phách (mặc định) | `deep blue-black shadows and warm amber light` |
| `teal` | `deep teal shadows and warm amber light` |
| `sepia` | `warm sepia-brown shadows, almost monochrome, amber highlights` |
| `cold` | `cold steel-blue and snow-white tones against the amber flame` |
| `dusk` | `deep violet dusk tones against amber` |
| `mono` | `nearly black and white, the flame and its glow are the only colour` |

### Các trục còn lại (viết tự do theo bài)

- **Vai trò của đèn:** cầm giơ cao · trên bàn · treo trên xà/đinh · dưới sàn · bậu cửa sổ · phản chiếu (vũng nước, kính, mặt sông) ·
  đốm nhỏ ở xa, ông đi về phía nó · hàng đèn dọc lối đi · hai tay che gió cho ngọn lửa · đang thắp đèn.
- **Thời tiết, mùa:** đêm quang sao · mưa · tuyết · sương · gió bão · chạng vạng · trước bình minh · thu lá rụng · hè oi.
- **Bối cảnh:** nhà (bếp, hiên, gác xép) · chỗ làm (chuồng trại, xưởng, đường ray, ruộng) · đường (đường đất, trạm xe buýt, sân ga) ·
  nhà thờ gỗ nhỏ · sông, đồi, rừng thông · thời Kinh Thánh (chỉ với `biblical`).
- **Góc máy:** ngang mắt · thấp nhìn lên · cao nhìn xuống · tele nén hậu cảnh · nhìn từ ngoài qua khung cửa.
- **Bên đặt chữ:** cột trái (mặc định) · cột phải (*Bố cục khung hình*; dòng "Lamplight Gospel" vẫn phải cao hơn 85 % chiều cao).
