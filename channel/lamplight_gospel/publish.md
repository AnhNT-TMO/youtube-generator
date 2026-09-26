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
<Hook line> <1 emoji> <Short genre tail>
```

- **Hook line** (CEO 2026-09-26): câu làm người nghe 50–70 tuổi sùng đạo muốn bấm: lời cầu trực tiếp với Chúa ngôi thứ nhất
  ("Lord, …", "Father, …") hoặc câu gọi đúng người nghe và nỗi lòng của họ ("For Every Parent Who …"). Lấy từ câu chuyện album,
  không bắt buộc là tên bài 1. Nối tiếp chữ trên thumbnail, không lặp lại nó.
- **Không "| Full Album"**, không "Playlist", không số giờ (thời lượng đã nằm trên thumbnail).
- **≤ 70 ký tự** (`publish.py check` chặn). Đuôi thể loại ngắn: "Gospel Blues", "Soulful Gospel Blues", "A Father's Gospel Blues Prayer"…
- Ví dụ: `Lord, I Can't Be There, But You Can 🙏 A Father's Gospel Blues Prayer` (68 ký tự).
- Genre phrase: "Slow Gospel Blues", "Soulful Gospel Blues", "Southern Gospel Soul"… (theo Style của album). Use-case: late-night
  prayer, sleep, a heavy heart, quiet time with God…
- Emoji trong thế giới kênh: 🕯️ đèn, 🙏 cầu nguyện.

**Single:**

```
<Song Title> <1 emoji> <Genre phrase> for <Use-case> [| Lamplight Gospel]
```

- **≤ 70 ký tự**. `| Lamplight Gospel` chỉ thêm khi còn chỗ (tên kênh đã hiện dưới title); thường phải bỏ.
- Ví dụ: `Enough For Today 🙏 Gospel Blues Prayer of Thanks for a Hard Season` (66),
  `Stay With Me, Lord 🙏 Slow Gospel Blues Prayer for a Restless Night` (66).

## ABOUT THIS VIDEO

- Không lặp những gì mẫu description đã nói: quiet nights, praying through a difficult night, comfort, hope.
- Câu âm thanh (3): cùng một ca sĩ + nhạc cụ chính (Hammond, piano, guitar blues sạch) + một hình ảnh căn phòng, vd. "one intimate
  service in a small church after midnight".
- Câu hành trình (1), ví dụ: "a one-hour journey through one long night of the soul, told in ten original songs".
- Không thêm dòng Kinh Thánh, danh sách use-case, dòng AI, dòng bản quyền.

## Tags: các nhóm

Nhóm là để không bỏ sót; tag cụ thể phải lấy từ cụm người ta gõ thật (`publish.py tags --expand` / `tags <album>`, SKILL.md → Tags).
Cột ví dụ chỉ minh họa nhóm, không chép tag.

| Nhóm | Ví dụ |
|---|---|
| album / title track name | <title track> |
| use-cases (2–3) | late night prayer music, gospel music for sleep, prayer music for anxiety |
| album theme (1–2) | night worship songs, gospel songs of hope |
| subgenre | southern gospel soul |
| lead instrument | hammond organ gospel |
| format (1–2) | christian blues playlist, slow gospel full album |

Single: song title, hook phrase (nếu khác), album title, 2–3 use-cases, 1–2 themes của bài, subgenre, lead instrument, format
("gospel blues song", "christian soul single").

**Mốc Google Trends:** `spiritual blues` = 4.7 (thang so sánh của `publish.py tags --trends`).

**Bẫy ý định đã thấy** (autocomplete kéo sang khán giả khác, không dùng): "deep gospel" → R&B; "male gospel vocals" → ca sĩ
châu Phi; "redemption songs" → Bob Marley; "evening prayer" → phụng vụ. Cụm của kênh tham khảo, không dùng: "gospel blues room",
"christian soul blues". Title quá dài: rút "Slow Gospel Blues" → "Gospel Blues" trước khi cắt phần khác.

## Pinned comment

Emoji của kênh: 🕯️ đèn · 🙏 cầu nguyện · 🎶 nhạc · ✨ điểm nhấn · 🔥 cao trào · 🌅 hy vọng/bình minh · 🌙 đêm/nghỉ · 💛 ấm áp · ✝️ đức tin.
Emoji điểm nhấn chọn theo `imagery` của bài.

**Album:**

```
🕯️ Welcome to Lamplight Gospel. Thank you for spending this night with us. 🕯️

🙏 Which song spoke to your heart tonight? Tell us in the comments. We read every one.

🎶 TRACKLIST 🎶
1️⃣ 0:00 <Title Track>
...
🔟 <m:ss> <Last Song>

✨ Don't miss
🔥 <m:ss> <Peak Song> · <one short line on why>
🌅 <m:ss> <Turning-point Song> · <one short line>
🌙 <m:ss> <Last Song> · <one short line>

💛 If this music brought you peace:
👍 Like · 🔔 Subscribe · 🔁 Share it with someone carrying a heavy heart tonight

✝️ You are not alone. Even in the darkest night, the light still shines.
```

- Dòng kết lấy từ đoạn "May these songs remind you" của mẫu description.
- Chỉ hứa điều có thật ("We read every one", không "we pray for each of you" nếu chủ kênh không làm).

**Single:** lời chào có tên bài (`🕯️ Thank you for spending these minutes with "<Song Title>". 🕯️`) → một câu hỏi gắn với hook →
trích câu hook → `🎧 The full album "<Album Title>" (<n> songs · <length>): <album_video_url>` → CTA → dòng kết. Mẫu đầy đủ:
`templates/youtube-single.md`.

## Shorts

Skill `youtube-shorts` đọc mục này. Chung mọi Short: tiếng Anh, AI use = Yes, không dành cho trẻ em, Related video = video đích.

**Title** (≤ 60 ký tự để hiện đủ trong feed; `shorts.py check` cảnh báo > 60, chặn > 100):

```
<emotional line from this song's lyrics> | <Song Title> 🕯️
```

- Câu đầu lấy ý từ chính đoạn lời của Short, nói với người đang mệt/cầu nguyện (vd. `When you have nothing left to give Him | …`);
  không lặp title album, không hứa điều video không có. Trục thử (version): kiểu `<Song Title> 🕯️ Full Song ↓`.

**Description:**

```
<one sentence for the listener, from this song's theme>
🎧 <Full album "<Album Title>" (1 hour) | Full song>: <related video URL>
💬 <one call to comment tied to the lyric, e.g. If you are still carrying it tonight, type "Amen".>

#GospelBlues #ChristianMusic #LamplightGospel
```

- 3 hashtag, đúng chủ đề; không thêm dòng AI/Suno.

**Tags:** khối *Tags YouTube mặc định* + tên bài + tên album (≤ 500 ký tự).

**Pinned comment:** `🎧 Full album "<Album Title>" (1 hour): <URL>` (Short → album) · `🎧 Full song "<Song Title>": <URL>` (Short → single),
thêm một câu hỏi gắn với câu hook.

**Chữ trên video** (`short.md`):

- `hook_text` (0–3 s): một câu ≤ 8 từ viết từ lời bài, nói thẳng với người xem (vd. `For the one bringing God the blues tonight`);
  mỗi Short một câu mới, không dùng lại câu cũ.
- `cta_text` (4 s cuối): Short → album `Full 1-hour album below` · Short → single `Full song below` (chỉ xuống link Related video; font video
  không có glyph mũi tên/emoji, chỉ dùng chữ).

## Ghi chú kênh

- Playlists trong Studio: `Lamplight Gospel · Full Albums` (album) và `Lamplight Gospel · Songs` (single).

## Giờ đăng

- Mặc định **06:00–07:00 ET** (Schedule trong Studio): 1–2 giờ trước đỉnh tìm "gospel music" / "gospel songs" trên YouTube ở Mỹ (07–11 h ET).
  Giờ VN: 17:00–18:00 khi Mỹ theo EDT, 18:00–19:00 khi theo EST.
- **Gói một album** (1 album + 1 single + 1 Short, CLAUDE.md §3), cùng một ngày; mỗi ngày tối đa 1 album + 1 single + 1 Short:

  | Giờ ET | Video | Vì sao |
  |---|---|---|
  | 06:00 | album | trước đỉnh tìm kiếm buổi sáng |
  | 12:00 | single bài điểm nhấn | cách album 6 giờ, album đã public để có link |
  | 17:00 | Short (điệp khúc bài 1 → album) | Shorts ăn nhất chiều tối; video đích đã public |

  Khi album đăng thưa hơn mỗi ngày: album ưu tiên sáng Chủ nhật 06:00 ET (Chủ nhật 08–10 h ET là đỉnh tìm kiếm của tuần);
  ngày không có album mới chỉ đăng single/Short dự phòng, vẫn tối đa 1 single + 1 Short.
- Không đăng 22:00–05:00 ET (đáy tìm kiếm).
- Nguồn: `research/golden-hour-gospel-2026-09-25/` (Google Trends 8 tuần theo giờ + giờ đăng của 11 kênh cùng niche).
  Khi kênh có số liệu: thay bằng Studio → Audience → *When your viewers are on YouTube*.

## Thứ tự đăng

- Video phải dựng từ master hiện hành: trước khi zip/upload, so thời lượng video với `assembly.md`.
- Short đăng sau video đích của nó (Short của gói sau album; Short dự phòng trỏ về single thì sau single đó) để gắn được Related video và link.
- Single phải có link album ngay khi public: upload album trước (URL có ngay cả khi đang private/scheduled), điền
  `album_video_url` vào `single.md`, rồi mới soạn/dán description + comment + end screen của single.
