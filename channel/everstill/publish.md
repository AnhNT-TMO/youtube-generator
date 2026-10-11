# Đăng YouTube: Everstill

Luật đóng gói YouTube riêng của kênh (skill `upload-youtube-publish` là quy trình). `publish.py check` đọc hai khối ``` dưới
*Description YouTube mặc định* và *Tags YouTube mặc định* (giữ nguyên tên mục).

**Chapters:** none

Dòng nhạc Christmas của kênh không có tracklist tên bài (CEO 2026-10-05): description không có dòng `TRACKLIST`, không
timestamp; pinned comment cũng không timestamp. Studio: bỏ tick *Automatic chapters*.

**Dịch sau khi đăng (CEO 2026-10-06):** mọi album và Short dịch title + description sang đúng 10 ngôn ngữ thị trường RPM cao
trong `translate.yaml` (de, fr + fr-CA, nl, no, da, sv, fi, ja, ko, it); không thêm ngôn ngữ thị trường view rẻ. Thuật ngữ
dùng lại theo `glossary`, "Everstill" và "Tian" giữ nguyên.

## Description YouTube mặc định

Mẫu CEO 2026-10-06: description nói về video, không kể chuyện kênh. Dòng `[…]` ngay sau dòng 🎄 Everstill là chỗ điền ABOUT THIS VIDEO (3–5 câu riêng cho từng video); mọi dòng còn lại dùng nguyên văn, kể cả đoạn 🙏 tri ân tác giả các bài thánh ca public domain. Upload defaults trong Studio (Settings → Upload defaults → Description) = mẫu này bỏ dòng `[…]` và dòng trống ngay sau nó; khi đăng, dán đoạn ABOUT THIS VIDEO của `youtube.md` vào dưới dòng 🎄 Everstill.

```
🎄 Everstill — relaxing Christmas instrumental music and cozy winter ambience. Soft piano carols with gentle strings, set to slow-moving winter scenes. ❄️🔥

[Write 3–5 sentences here about this video: the scenes you see, the light and mood, the carols you hear, how long it plays.]

🎧 Perfect for:

✔️ Studying, coding, working, and staying focused  
✔️ Relaxing after a long day  
✔️ Reading, journaling, or enjoying a quiet cup of coffee  
✔️ Creating a warm Christmas atmosphere at home  
✔️ Sleeping or winding down in the evening  
✔️ Peaceful winter mornings and snowy nights  
✔️ Background music for Christmas gatherings and family time

🔥 Put on your headphones, lower the lights, and let the music stay with you for a while.

🎹 Every arrangement and recording here was created, arranged and performed by Everstill. Please do not copy, re-upload or cover these recordings in any form.

🙏 With gratitude to the composers and hymn writers, known and unknown, whose Christmas carols have been sung for generations. Every melody here is a public domain carol, arranged for gentle piano by Everstill.

If you enjoy the music, please leave a like, share the video, or subscribe. ❤️

#christmasmusic, #christmasambience, #relaxingchristmasmusic, #instrumentalmusic, #christmasmusic2026, #cozychristmas, #winterambience, #studymusic, #relaxingmusic, #piano, #pianomusic, #calmpianomusic, #softpiano, #soothingpianomusic, #musicforsleep, #musicforstudying, #peacefulmusic, #everstill
```

## Description: dòng chỉ cho nhạc public domain

CEO 2026-10-08: các dòng dưới đây chỉ ghi khi album dùng carol public domain (`album.md` → `music_source: pd`). Album nhạc
gốc (`music_source: suno`) bỏ hẳn các dòng này cùng dòng trống ngay trước; `publish.py check` báo ❌ nếu ghi sai.

**Dòng chủ quyền (CEO 2026-10-11):** album nào dùng giai điệu public domain do mình phối khí và thu (`music_source: pd`) ghi thêm
dòng 🎹 khẳng định bản phối + bản thu là của Everstill và đề nghị không copy / đăng lại / cover, đặt **ngay trước dòng 🙏 tri ân**.
Giai điệu gốc là PD nên dòng này chỉ nói về *bản phối và bản thu*, không nhận quyền với bài hát.

```
🎹 Every arrangement and recording here was created, arranged and performed by Everstill. Please do not copy, re-upload or cover these recordings in any form.

🙏 With gratitude to the composers and hymn writers, known and unknown, whose Christmas carols have been sung for generations. Every melody here is a public domain carol, arranged for gentle piano by Everstill.
```

## Tags YouTube mặc định

```
Everstill, christmas music, christmas instrumental music, relaxing christmas music, cozy christmas music, christmas piano music, christmas ambience
```

## Title

**Album (CEO 2026-10-07):** `<Christmas genre phrase có người gõ> 🎄 <Khung cảnh của album> ❄️ <Christmas genre phrase thứ hai>`,
vd. `Relaxing Christmas Piano 🎄 Cozy Snowy Village ❄️ Christmas Ambience`; ≤ 70 ký tự; mẫu tham khảo chỉ là kiểu, không chép
cụm của người khác. Tên vibe (Snow Globe…) chỉ là tên nội bộ, không làm chủ đề title.

- **Không ghi độ dài** (không "3 Hours") (CEO 2026-10-05).
- **Chữ vibe nằm trong genre phrase** (CEO 2026-10-05), vd. album vui tươi yêu đời → `Cheerful` / `Happy` /
  `Joyful`; chọn chữ vibe đi với genre phrase mà người ta có gõ (`publish.py tags --expand "<vibe> christmas music"`).
- Mỗi album một khung cảnh / cảm giác khác (theo thumbnail + video: đêm Giáng Sinh trong nhà, tuyết ngoài cửa sổ, lò sưởi…)
  và một genre phrase khác (chọn từ `publish.py tags --expand`), để các video không na ná nhau.
- Emoji dùng được: 🎄 ❄️ 🔥 ✨ (hai cái, ngăn ba cụm). Không ghi "No Ads" (không hứa điều kênh không kiểm soát).
- Tên kênh không vào title (đã có trong description).

## Tags: các nhóm

| Nhóm | Ví dụ |
|---|---|
| vibe của album | cheerful christmas music instrumental, happy christmas music instrumental |
| nhạc / hình thức của album | christmas waltz instrumental, christmas piano music instrumental |
| khung cảnh album | christmas eve music, christmas piano fireplace |
| use-cases (2–3) | cozy christmas music for studying, christmas music for studying instrumental |
| nhạc cụ chính | christmas waltz piano, relaxing christmas music piano |
| format | cozy christmas music playlist, christmas eve music playlist |

Bẫy ý định (autocomplete ra thứ khác): tên ca sĩ (frank sinatra, carpenters, laufey, doris day), `karaoke`, `tutorial`,
`easy`, `for kids`, `for classroom`, `jazz` (trừ album jazz), `catholic`, `lofi`, `no ads`.

## Pinned comment

Emoji của kênh: 🎄 ❄️ 🔥 ✨ 🎧 ❤️ 🌿. Không timestamp. Mẫu (đổi câu khung cảnh theo album):

```
🎄 Thank you for being here. Where are you listening from tonight, and what are you doing while the music plays? ❄️
```

## Giờ đăng

<chưa chốt>

## Ghi chú kênh

- Playlists trong Studio: `Everstill · Christmas`.
- Thumbnail (CEO 2026-10-06): mọi thumbnail có logo `branding/logo-clock-piano.png` ở góc phải trên (rộng 15 % ảnh, lề 2,5 %, bóng mờ nhẹ); giữ bản không logo `thumbnail-nologo.png`.
