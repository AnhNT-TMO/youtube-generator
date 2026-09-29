---
title_words: [5, 9]
title_case: true
title_forbidden: ",."
short_length_s: [30, 60]
short_pre_roll_s: 1
short_max_gap_s: 6
---
# Đặt tên bài + chọn đoạn Short: Shelter Stone Gospel

Skill audio-song-naming đọc file này (front matter = luật máy đọc: số từ, Title Case, ký tự cấm, độ dài đoạn Short). Suno tự viết lời; mình đọc lời rồi đặt tên:
2 clip **cùng lời** = 2 bản của cùng một bài, một tên, file `<tên>_v1` / `<tên>_v2` (CEO 2026-09-28); 2 clip **khác lời** = 2 bài riêng,
mỗi bài một tên từ lời của nó, file `<tên>`. `songs.py candidates` in tỉ lệ giống lời để biết là trường hợp nào. Mỗi bản/bài một đoạn Short.

## Tên bài

Tên bài hiện trong TRACKLIST (chapters) của mọi video và trong Short, nên người xem đọc nó như một chuỗi lời cầu nguyện.
Giọng tên bài = giọng title/thumbnail của ngách mà R&D đã đo: **kho câu** `research/phrase-bank/gospel.yaml` (145 câu của
video tăng view nhanh nhất, tính theo view/ngày, từ 113 kênh cùng ngách) + phân tích `research/phrase-bank/gospel.md` (§3 quy
luật, §4 câu đã bão hoà, §5 20 cặp chuyển thể mẫu). Đọc §3–§4 trước lô đặt tên đầu tiên.

Mẫu CEO đưa (2026-09-28), đúng giọng kênh:

```
Jesus Please Restore What Life Has Broken
When My Strength Ran Out Mercy Kept Me Going
Jesus Im Tired of Fighting This Battle Alone
Jesus Im Leaving Every Burden With You
```

**Nguồn tên:** lấy từ **chính lời bài** (câu hook, câu điệp khúc hoặc ý chính); không bịa ý không có trong lời. Lời gọi
(Jesus / Lord / Father / God) giữ đúng như lời bài gọi.

**Năm dạng tên** (theo `pattern` của kho câu), chọn dạng khớp với câu mạnh nhất của lời:

| Dạng | Khuôn | Ví dụ đúng giọng (không có trong kho) |
|---|---|---|
| plea (xin) | `<Gọi> + động từ xin + nỗi đau cụ thể` | Jesus Please Restore What Life Has Broken |
| cry (than) | `<Gọi> + I'm/I can't + trạng thái` | Jesus Im Tired of Fighting This Battle Alone |
| surrender (phó thác) | `<Gọi> + I'm leaving/I lay + gánh nặng + with You` | Jesus Im Leaving Every Burden With You |
| testimony (làm chứng) | `When + lúc tận cùng + ơn Chúa đã làm gì` | When My Strength Ran Out Mercy Kept Me Going |
| promise (lời hứa) | `You + never/still + điều Chúa giữ` | You Never Let Go When I Fell Apart |

**Luật:**
- Một lời ngôi thứ nhất về **một nỗi đau cụ thể** (kiệt sức, cô đơn, bão tố, gia đình, mẹ đã mất, tiền bạc, bệnh tật, chờ đợi);
  câu cụ thể thắng câu chung (gospel.md §3.2). Có chi tiết cụ thể trong lời (đêm bệnh viện, chiếc ghế trống…) thì đưa vào tên.
- Các từ quá đông trong ngách (heal, faith, peace, rest, mercy, burden, restore, hold me) được dùng nhưng **không làm lõi**
  của tên; lõi là nỗi đau hoặc hành động cụ thể (gospel.md §4).
- Câu cầu nguyện chung / câu trích kinh điển (Kinh Thánh, hymn cổ, câu trong kho) **dùng nguyên văn được** nếu có trong lời
  bài (CEO 2026-09-28). Câu đã bão hoà (gospel.md §4) dùng được nhưng nên ưu tiên câu cụ thể hơn của chính lời bài. Hạn chế đặt
  trùng tên một bài hát nổi tiếng có thật (người tìm bài đó sẽ gặp bài khác).
- 5–9 từ, Title Case (từ nhỏ *of, the, to, a, in, on, for, with, and* viết thường được), tiếng Anh; không dấu phẩy, dấu chấm, emoji.
- Không trùng tên bài nào khác trong kho (`songs/<type>/*.md`), trừ bản kia **cùng lời** của cùng lượt (v1/v2 cùng tên). Xoay vòng cách mở đầu: trong kho, không để quá nửa số bài mở bằng cùng
  một lời gọi (Jesus…), để tracklist một album không đọc như một câu lặp.
- Hai clip cùng lượt **cùng lời** (khác bản thu): **cùng một tên**, khác nhau ở `_v1` / `_v2` (v1 = clip đầu của lượt). Chapters
  hiện tên bài không kèm V. **Khác lời**: bài riêng, tên riêng không trùng, file `<tên>`.

## Đoạn Short

- Một đoạn **hát** (không lấy lời đọc spoken), thường là điệp khúc hoặc câu cầu xin mạnh nhất; 30–60 giây.
- Bắt đầu ngay trên câu hook (≤ 1 s trước chữ đầu), kết ở cuối một câu để lặp lại mượt; không có khoảng nhạc không lời > 6 s.
- `hook`: câu hiện lên đầu Short, lấy từ lời trong đoạn.
- Mỗi bản (v1, v2) có đoạn Short riêng; cùng điệp khúc cũng được (hai bản thu khác nhau, và một album chỉ có một Short).
