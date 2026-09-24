# Lamplight Gospel

- **Trạng thái:** đang chạy album đầu tiên (chưa upload)
- **Thể loại:** Christian Gospel Blues / Southern Gospel Soul
- **Vocal persona:** giọng nam baritone ấm, hơi khàn (xem Album 001)
- **Hình ảnh:** ánh sáng (đèn dầu, tông vàng ấm) đến với người nghèo, già, khốn khổ: ca sĩ luôn mặc đồ nghèo, cũ, sờn (5 loại trang phục ở *Biến thể hình ảnh*), không tuxedo/vest sang (chủ kênh 2026-09-23/24), bối cảnh đơn sơ; chỉ ngọn đèn vàng và khuôn mặt là cố định, còn lại đổi theo vibe bài; logo tròn "LAMPLIGHT / GOSPEL" có ngọn lửa
- **Chưa chốt:** tagline, brand voice cho title/description, band profile chính thức

## Description YouTube mặc định

Dùng nguyên văn cho mọi video. Mỗi video chỉ viết phần **ABOUT THIS VIDEO** (3–5 câu riêng về album đó), rồi thêm khối **TRACKLIST**
(chapters, bắt buộc để YouTube tạo chapters) ngay sau nó.

```
Welcome to Lamplight Gospel — soulful gospel blues for wounded hearts.

Here you’ll find deep, emotional Gospel music inspired by faith, prayer, pain, healing, redemption, and hope. These songs are made for quiet nights, difficult seasons, broken hearts, and the moments when you need to remember that God is still near.

Lamplight Gospel blends soulful Gospel, Christian soul, Gospel blues, and slow worship with heartfelt male vocals and honest storytelling about loss, struggle, forgiveness, restoration, and faith.

🎵 ABOUT THIS VIDEO
[Write 3–5 sentences here about the specific song or collection before publishing.]

TRACKLIST
[chapters, bắt đầu bằng 0:00]

Whether you are praying through a difficult night, carrying a heavy heart, searching for peace, or simply spending quiet time with God, I hope this music brings comfort to your soul.

May these songs remind you:
You are not alone.
There is hope after pain.
There is peace in His presence.
And even in the darkest night, the light still shines.

Subscribe to Lamplight Gospel for more soulful Gospel blues, Christian soul, healing music, prayer songs, and worship for the weary heart.

#LamplightGospel #SoulfulGospel #GospelBlues #ChristianSoul #HealingGospel
```

## Tags YouTube mặc định

Dùng cho mọi video. Mỗi video thêm ~10 tags theo chủ đề riêng của album (không trùng các tag dưới đây), tổng ô Tags ≤ 500 ký tự (YouTube tính thêm 2 ký tự cho mỗi tag có dấu cách).

```
Lamplight Gospel, soulful gospel, gospel blues, Christian soul, slow gospel, healing gospel, emotional gospel, gospel soul, worship blues, spiritual blues, male gospel vocals, Christian inspirational music
```

## Prompt ảnh mặc định (ChatGPT)

Khối **CORE**: dán nguyên văn ở đầu mọi prompt tạo thumbnail (album, idea, bài đăng riêng); `thumb.py check` bắt đủ từng dòng.
Chỉ giữ những gì **không bao giờ đổi**: ngọn đèn vàng là điểm sáng nhất, khuôn mặt nhân vật, quần áo nghèo cũ, hệ hệ chữ (dòng "Lamplight Gospel"), vùng trống
cho lớp phủ video (logo 232px góc trên phải, nhóm like/subscribe 448×80 góc dưới phải, sóng nhạc giữa đáy). Mọi thứ khác (khung
hình, ánh sáng, màu, thời tiết, bối cảnh, trang phục cụ thể) viết trong khối **THIS IMAGE**, chọn từ mục *Biến thể hình ảnh* bên
dưới. Đính kèm 1–2 ảnh nhân vật trong `model/`. Mỗi lần gửi xin 3 ảnh riêng, 2K (ChatGPT Images 2.0).

```
Create THREE separate images for the YouTube channel "Lamplight Gospel" (soulful gospel blues music): three variations of the scene described below, each a complete standalone wide 16:9 landscape frame at 2K resolution (2560x1440 pixels). Do not combine them into one picture: no collage, grid, split screen or side-by-side panels. The three variations may differ slightly in camera distance and expression; everything else follows the description.
PHOTO: a cinematic, photorealistic photograph with rich film-like contrast and real, humble textures (old wood, worn fabric, stone, chipped enamel): the light of God reaching a poor, weary man in a humble place. Not glossy, not luxurious, not fantasy, not a painting or 3D render.
THE LAMP: a warm amber flame (the lamp described below) is always the brightest point of the frame, and its light always reaches the singer. Everything else stays darker than the flame.
THE SINGER: the man in the attached reference image is the channel's singer and must be the same person: a Black man in his 50s to early 60s, bald head, full dark beard graying at the chin, warm brown skin, broad build. Keep his face, head shape, beard and skin tone recognisably the same as the reference, but let hard years show: weathered skin, tired eyes, a few deeper lines. Only his pose, clothing and lighting change as described below. His face is always recognisable (never hidden or fully in silhouette). Natural, work-worn hands with five fingers.
CLOTHING: ignore the tuxedo in the reference image. He is a poor, humble man: his clothes are always plain, old and visibly worn or mended, never new, smart, rich or glamorous. The exact outfit is described below.
LETTERING: the title exactly as written below, spelled letter for letter, in the title style described below, at most 2 lines, large, clean and easy to read on a phone, in warm light tones (ivory, cream or gold) that stand out from the background. Under it a thin gold horizontal rule broken in the middle by the words "Lamplight Gospel" in a smaller italic serif; this small line never changes style. No other text, no watermark, no logo, no border.
FREE AREAS: a logo and a subscribe button are placed over the image later. Keep the top-right corner (right 16% of the width, top 26% of the height) and the bottom-right corner (right 28%, bottom 14%) dark and simple, and keep faces and lettering (including the "Lamplight Gospel" line) out of the bottom 15% of the frame.
AVOID: tuxedo, bow tie, necktie, pocket square, a smart or matching suit, polished formal wear, jewelry or anything that looks rich or glamorous, fedora or any hat, elderly silver-haired bluesman, a microphone or guitar as the main subject, a halo, a crown of thorns or any suggestion that he is Jesus, a bright blue daytime or heavenly sky, neon, glitter, cartoon look, distorted hands, extra people unless asked, any resemblance to a real celebrity.
```

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
Chỉ chữ title đổi kiểu. Dòng nhỏ "Lamplight Gospel" và vạch vàng luôn giữ nguyên để nhận diện kênh. Kiểu nào cũng phải
đọc rõ trên điện thoại. Màu chữ theo `palette` (vd. `cold` → trắng ngà, `sepia` → kem).

| Kiểu | Hợp với album về | Mẫu (dòng Title style) |
|---|---|---|
| `serif` Serif thanh lịch (kiểu album 001–002) | cầu nguyện, đêm dài, an ủi, trang nghiêm | `an elegant high-contrast serif, ivory to warm gold` |
| `brush` Chữ viết tay bút lông | lời tâm tình, gia đình, biết ơn, bài mộc và gần gũi | `warm hand-lettered brush script, like ink written by hand, ivory to soft gold, every letter clearly legible` |
| `letterpress` Chữ gỗ in mòn kiểu áp phích nhà thờ quê | blues, lao động, nông trại, energy cao, lời chứng mạnh | `a bold, weathered slab-serif like old letterpress wood type on a country church poster, cream with worn edges` |
| `bible` Chữ hoa khắc kiểu trang Kinh Thánh cổ | kể chuyện Kinh Thánh, di sản, thế hệ, trang trọng | `classic engraved Roman capitals like the title page of an old family Bible, slightly letter-spaced, warm gold` |
| `glow` Chữ mảnh phát sáng như ánh đèn | hy vọng, bình minh, phục hồi, bài kết êm | `a thin, graceful serif that glows softly from within like lamplight, warm amber halo, crisp edges` |

### Khung hình (`framing`)

Mặt vẫn tránh các góc bị phủ và 15 % đáy.

| Giá trị | Mẫu (dòng Look) |
|---|---|
| `wide` toàn cảnh | `a wide shot: he is small, about a sixth of the frame height, and the place and the darkness around the lamp tell the story` |
| `medium` trung cảnh | `a medium shot from the waist up, he fills about a third of the frame` |
| `close` cận mặt | `a close-up: his face and shoulders fill about half of the frame on one side, the background dissolves into soft blurred bokeh` |
| `hands` cận tay + đèn | `a close-up of his work-worn hands around the lamp in sharp focus, his face softly out of focus just behind, still recognisable` |
| `lamp-front` đèn tiền cảnh | `the lamp in the foreground in sharp focus, he stands a few steps behind it, softer but recognisable` |
| `rim` ngược sáng | `he is lit from behind and one side by the lamp, a warm rim of light around his head and shoulders, face in three-quarter profile` |

### Ánh sáng (`light`)

| Giá trị | Mẫu (dòng Look) |
|---|---|
| `single` một ngọn đèn giữa đêm | `one single lamp in near-total darkness, deep black shadows, strong chiaroscuro, no other light` |
| `moon` đèn + trăng | `cool blue moonlight on the edges of everything, warm lamplight on his face` |
| `mist` sương thành vệt sáng | `thick mist: the lamplight becomes a visible golden beam with floating dust` |
| `rain` mưa | `rain falling, drops catching the lamplight as bokeh, wet surfaces reflecting the flame` |
| `snow` tuyết | `snow falling, frost on every edge, his breath visible, warm light against the cold` |
| `dawn` trước bình minh | `the faint first light of dawn low on the horizon, still much dimmer than the lamp` |
| `fireflies` đom đóm | `a few fireflies glowing in the dark around him` |
| `fire` thêm ánh lửa | `a second, dimmer glow from a stove or fire in the background` |

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
- **Bố cục chữ:** trái trên · phải giữa · giữa trên · trái dưới (dòng "Lamplight Gospel" vẫn phải cao hơn 85 % chiều cao).

## Tài nguyên

| Đường dẫn | Nội dung |
|---|---|
| `image_source/logo.png` | Logo kênh 1024px nền trong suốt. Sinh lại: `.claude/skills/video-generator/.venv/bin/python .claude/skills/video-generator/scripts/make_logo.py --channel lamplight_gospel` |
| `video.json` | Phong cách video của kênh: bụi, ánh sáng, màu sóng nhạc, logo (xem skill `video-generator`, `references/config.md`) |
| `ideas/` | Idea album: ảnh + video loop 5 phút làm sẵn trước khi có nhạc |
| `albums/` | Album đang/đã làm |
| `singles/` | Bài nổi trội đăng riêng (trỏ về bài gốc trong album, có ảnh + video + youtube.md riêng), mẫu `templates/single.md` |
| `model/` | Ảnh tham chiếu nhân vật (8 góc, nền trong suốt), đính kèm khi tạo ảnh bằng ChatGPT |
| `library/catalog.md` | Thư viện bài hát của kênh (cùng persona) để tái sử dụng |
