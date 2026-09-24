# Đăng YouTube: Lamplight Gospel

Luật đóng gói YouTube riêng của kênh. Skill `youtube-publish` là quy trình (đo chapters, kiểm độ dài, các màn hình Studio);
file này là **nội dung** của kênh: mẫu description, tags mặc định, công thức title, emoji, mẫu pinned comment.
`publish.py check` đọc hai khối ``` dưới *Description YouTube mặc định* và *Tags YouTube mặc định* (giữ nguyên tên mục).

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

## Title

**Album:**

```
<Title Track> <1 emoji> <Genre phrase> for <Use-case> & <Feeling> | Full Album
```

- Album 001: `When The Night Is Long 🕯️ Slow Gospel Blues for Late-Night Prayer & Peace | Full Album` (86 ký tự).
- Genre phrase: "Slow Gospel Blues", "Soulful Gospel Blues", "Southern Gospel Soul"… (theo Style của album). Use-case: late-night
  prayer, sleep, a heavy heart, quiet time with God…
- Emoji trong thế giới kênh: 🕯️ đèn, 🙏 cầu nguyện.

**Single:**

```
<Song Title> <1 emoji> <Genre phrase> for <Use-case> | Lamplight Gospel
```

- Ví dụ: `Stay With Me, Lord 🙏 Slow Gospel Blues Prayer for a Restless Night | Lamplight Gospel`.

## ABOUT THIS VIDEO

- Không lặp những gì mẫu description đã nói: quiet nights, praying through a difficult night, comfort, hope.
- Câu âm thanh (3): cùng một ca sĩ + nhạc cụ chính (Hammond, piano, guitar blues sạch) + một hình ảnh căn phòng, vd. "one intimate
  service in a small church after midnight".
- Câu hành trình (1), ví dụ: "a 50-minute journey through one long night of the soul, told in ten original songs".
- Không thêm dòng Kinh Thánh, danh sách use-case, dòng AI, dòng bản quyền.

## Tags: các nhóm (ví dụ Album 001)

| Nhóm | Album 001 |
|---|---|
| album / title track name | when the night is long |
| use-cases (2–3) | late night prayer music, gospel music for sleep, prayer music for anxiety |
| album theme (1–2) | night worship songs, gospel songs of hope |
| subgenre | southern gospel soul |
| lead instrument | hammond organ gospel |
| format (1–2) | christian blues playlist, slow gospel full album |

Single: song title, hook phrase (nếu khác), album title, 2–3 use-cases, 1–2 themes của bài, subgenre, lead instrument, format
("gospel blues song", "christian soul single"). Album 001: 22 tags, 464/500.

## Pinned comment

Emoji của kênh: 🕯️ đèn · 🙏 cầu nguyện · 🎶 nhạc · ✨ điểm nhấn · 🔥 cao trào · 🌅 hy vọng/bình minh · 🌙 đêm/nghỉ · 💛 ấm áp · ✝️ đức tin.
Emoji điểm nhấn chọn theo `imagery` của bài.

**Album:**

```
🕯️ Welcome to Lamplight Gospel. Thank you for spending this night with us. 🕯️

🙏 Which song spoke to your heart tonight? Tell us in the comments. We read every one.

🎶 TRACKLIST 🎶
1️⃣ 0:00 When The Night Is Long
...
🔟 45:14 Stay With Me, Lord

✨ Don't miss
🔥 29:43 You Never Let Me Go · the peak of the night
🌅 35:22 Morning Is Coming · when the light returns
🌙 45:14 Stay With Me, Lord · the last prayer before rest

💛 If this music brought you peace:
👍 Like · 🔔 Subscribe · 🔁 Share it with someone carrying a heavy heart tonight

✝️ You are not alone. Even in the darkest night, the light still shines.
```

- Dòng kết lấy từ đoạn "May these songs remind you" của mẫu description.
- Chỉ hứa điều có thật ("We read every one", không "we pray for each of you" nếu chủ kênh không làm).

**Single:** lời chào có tên bài (`🕯️ Thank you for spending these minutes with "<Song Title>". 🕯️`) → một câu hỏi gắn với hook →
trích câu hook → `🎧 The full album "<Album Title>" (<n> songs · <length>): <album_video_url>` → CTA → dòng kết. Mẫu đầy đủ:
`templates/youtube-single.md`.

## Ghi chú kênh

- Title trùng với kênh tham khảo: Album 001 "You Never Let Me Go" cũng là tên bài anchor của stillworship → báo chủ kênh.
- Playlists trong Studio: `Lamplight Gospel · Full Albums` (album) và `Lamplight Gospel · Songs` (single).
