# Đăng YouTube: Shelter Stone Gospel

Luật đóng gói YouTube riêng của kênh (skill `upload-youtube-publish` là quy trình, `video-shorts` cho Short).
`publish.py check` đọc hai khối ``` dưới *Description YouTube mặc định* và *Tags YouTube mặc định* (giữ nguyên tên mục).

## Description YouTube mặc định

Mẫu CEO 2026-09-28, dùng chung cho mọi video album, **nguyên văn**. Mỗi album chỉ điền TRACKLIST (dòng `[` là chỗ điền:
dán khối của `publish.py chapters`). Mẫu không có đoạn ABOUT THIS VIDEO riêng cho từng album.

```
Take a quiet moment with this soulful gospel worship session and allow your heart to rest in God’s presence. These songs are created for prayer, reflection, Scripture reading, morning devotion, evening worship, and the difficult seasons when you need comfort, healing, and renewed faith.

Welcome to Shelter Stone Gospel — a place of peace for anyone seeking strength, grace, hope, and encouragement through deep gospel worship, Christian soul, gospel blues, and prayer-filled music.

This worship session can accompany you while:

• Spending time in prayer or reading the Bible
• Starting your morning with faith and gratitude
• Unwinding and reflecting at the end of the day
• Walking through a difficult or emotional season
• Praying for healing, restoration, or renewed strength
• Looking for peace in moments of worry or uncertainty
• Sitting quietly and resting in God’s presence

Whatever you may be carrying today, may this music remind you that you are never beyond God’s sight. He knows your heart, hears every prayer, and remains faithful even through seasons of waiting.

🙏 If you feel comfortable, share a prayer request, testimony, or a few words of encouragement in the comments.

You can simply write:

“Lord, I place this burden in Your hands.”

Sometimes a simple message of faith can bring hope to someone else who is praying, grieving, waiting, healing, or learning to trust God through a difficult chapter of life.

Subscribe to Shelter Stone Gospel for more soulful gospel worship, Christian soul, gospel blues, peaceful prayer music, midnight worship sessions, healing songs, and music centered on faith in Jesus.

TRACKLIST
[chapters from publish.py chapters, starting at 0:00]

deep gospel worship, soulful gospel music, Christian worship music, gospel prayer music, healing worship, peaceful worship songs, Black gospel worship, gospel soul music, Christian blues, gospel R&B, emotional worship, midnight prayer music, morning worship, evening worship, songs of faith, Jesus worship music, devotional music, music for prayer, worship for healing, Shelter Stone Gospel

#ShelterStoneGospel #GospelMusic #DeepGospelWorship #SoulfulGospel #ChristianMusic #WorshipMusic #BlackGospel #GospelSoul #ChristianBlues #GospelRnB #PrayerMusic #HealingWorship #PeacefulWorship #EmotionalWorship #MidnightPrayer #MorningWorship #EveningWorship #SongsOfFaith #JesusMusic #ChristianSoul
```

## Tags YouTube mặc định

Tags mặc định CEO 2026-09-28 (20 tag, **411/500 ký tự** theo cách YouTube đếm: dấu phẩy + ngoặc kép cho tag có dấu cách).
Mỗi album **thêm tag riêng cho tới sát 500** (còn ~89 ký tự ≈ 4–6 tag): lời cầu xin / chủ đề của album, nỗi đau hoặc
use-case cụ thể, tìm bằng `publish.py tags --expand`; không trùng tag mặc định, không tên kênh khác.

```
deep gospel worship, soulful gospel music, Christian worship music, gospel prayer music, healing worship, peaceful worship songs, Black gospel worship, gospel soul music, Christian blues, gospel R&B, emotional worship, midnight prayer music, morning worship, evening worship, songs of faith, Jesus worship music, devotional music, music for prayer, worship for healing, Shelter Stone Gospel
```

## Title

- Nguồn câu: `album.md` → `brief.title_direction` (PM + CEO chốt), từ kho câu R&D `research/phrase-bank/`. Câu cầu nguyện chung
  / câu trích kinh điển **dùng nguyên văn được** (CEO 2026-09-28), ưu tiên câu vẫn đang lên (`fresh`, vpd_x cao); hoặc chuyển
  thể (đổi Lord ↔ Father/Jesus/God, đổi vài chữ). Không lấy tên/branding kênh khác; không lặp câu của video trước của kênh.
  Ghi id câu gốc vào `brief.phrase_bank`; PM đánh dấu `yt.py bank use` lúc lên album.
- Công thức mặc định (theo ngách, R&D 2026-09-28): `<Addressee>, <lời cầu xin ngôi thứ nhất> 🙏 <Genre phrase> <for …>`,
  ≤ 70 ký tự, một emoji. Genre phrase xoay vòng: *Gospel Blues*, *Soulful Gospel Blues*, *Deep Gospel Blues Worship*…
- Title ≠ chữ trên thumbnail: hai câu bổ sung nhau cùng một nỗi đau/lời xin (chữ ảnh: `visual.md`).

## Shorts

- Title: câu hook của Short (lời bài) + ` 🙏`, **≤ 60 ký tự** (`shorts.py check` cảnh báo khi dài hơn); không cần `#shorts`
  (YouTube tự nhận Short theo khung dọc + ≤ 3 phút), hashtag để trong description.
- Description: 1–2 câu mời nghe trọn album + link album (Related video = album) + 3 hashtag.
- `hook_text`: câu trong đoạn Short, nói thẳng với người xem; `cta_text`: `Full 1-hour album below` (không mũi tên hay ký tự đặc biệt: font video không có, hiện thành ô vuông).

## Pinned comment

Mặc định của PM (CEO đổi được). Không hỏi like/subscribe; tracklist đã có trong description.

```
🙏 What are you carrying today? Write your prayer below: someone who reads it may pray with you.
```

## Giờ đăng

- Mỗi ngày tối đa **1 album + 1 Short** (CEO 2026-09-28: không làm single). Đăng album trước, Short sau (Related video = album).
- Mặc định (theo research giờ đăng cùng ngách 2026-09-25, chờ số liệu kênh): album **06:00 ET**, Short **17:00 ET**.
  Có số liệu: Studio → Audience → *When your viewers are on YouTube*.
- Không đăng 22:00–05:00 ET.
