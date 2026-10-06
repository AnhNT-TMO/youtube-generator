# Đăng YouTube: Everstill

Luật đóng gói YouTube riêng của kênh (skill `upload-youtube-publish` là quy trình). `publish.py check` đọc hai khối ``` dưới
*Description YouTube mặc định* và *Tags YouTube mặc định* (giữ nguyên tên mục).

**Chapters:** none

Dòng nhạc Christmas của kênh không có tracklist tên bài (CEO 2026-10-05): description không có dòng `TRACKLIST`, không
timestamp; pinned comment cũng không timestamp. Studio: bỏ tick *Automatic chapters*.

## Description YouTube mặc định

Mẫu CEO 2026-10-05, dùng nguyên văn cho mọi album; không có chỗ điền.

```
🎄 Relaxing Christmas Instrumental Music & Cozy Winter Ambience | Everstill ❄️🔥

Welcome to Everstill — Where Time Becomes Sound. 🎧

I’m Tian, a developer and the person behind Everstill. Instrumental music has always been part of my everyday life — while coding, working, studying, resting, or simply slowing down at the end of the day.

For this Christmas collection, I wanted to create that feeling I love most about the season: warm lights glowing against a cold winter evening, snow falling outside, a peaceful room, and gentle music filling the silence. 🎄✨

Each piece is shaped by experimenting with melodies, piano, strings, guitar, soft orchestration, and atmosphere until everything feels calm, warm, and timeless.

I hope this music can become a small part of your Christmas — whether you're studying late at night, working quietly, reading beside the window, decorating your home, spending time with family, or simply enjoying a peaceful moment alone. ❤️

🎧 Perfect for:

✔️ Studying, coding, working, and staying focused  
✔️ Relaxing after a long day  
✔️ Reading, journaling, or enjoying a quiet cup of coffee  
✔️ Creating a warm Christmas atmosphere at home  
✔️ Sleeping or winding down in the evening  
✔️ Peaceful winter mornings and snowy nights  
✔️ Background music for Christmas gatherings and family time

🔥 Put on your headphones, lower the lights, and let the music stay with you for a while.

If Everstill brings you even a little more peace, focus, warmth, or happiness, then creating it was worth it to me.

Thank you for listening and for spending part of your time here. 🌿

🎶 Welcome to Everstill.  
⏳ Where Time Becomes Sound.

If you enjoy the music, please leave a like, share the video, or subscribe. Every listen helps me keep creating new music and peaceful places for you to return to. ❤️

#christmasmusic, #christmasambience, #relaxingchristmasmusic, #instrumentalmusic, #christmasmusic2026, #cozychristmas, #winterambience, #studymusic, #relaxingmusic, #piano, #pianomusic, #calmpianomusic, #softpiano, #soothingpianomusic, #musicforsleep, #musicforstudying, #peacefulmusic, #everstill
```

## Tags YouTube mặc định

```
Everstill, christmas music, christmas instrumental music, relaxing christmas music, cozy christmas music, christmas piano music, christmas ambience
```

## Title

**Album:** `<Khung cảnh của album> <1 emoji> <Vibe> <Christmas genre phrase có người gõ> [for <Use-case / cảm giác>]`

- **Không ghi độ dài** (không "3 Hours") (CEO 2026-10-05).
- **Vibe của album đứng ngay trước genre phrase** (CEO 2026-10-05), vd. album vui tươi yêu đời → `Cheerful` / `Happy` /
  `Joyful`; chọn chữ vibe đi với genre phrase mà người ta có gõ (`publish.py tags --expand "<vibe> christmas music"`).
- Mỗi album một khung cảnh / cảm giác khác (theo thumbnail + video: đêm Giáng Sinh trong nhà, tuyết ngoài cửa sổ, lò sưởi…)
  và một genre phrase khác (chọn từ `publish.py tags --expand`), để các video không na ná nhau.
- Emoji dùng được: 🎄 ❄️ 🔥 ✨ (một cái trong title). Không ghi "No Ads" (không hứa điều kênh không kiểm soát).
- Tên kênh không vào title (đã có ở dòng đầu description).

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
