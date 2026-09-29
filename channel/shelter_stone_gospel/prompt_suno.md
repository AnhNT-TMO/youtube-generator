---
mode: simple
model: v6
voice:
  name: "Midnight Gospel Soul - Male 04 (314 Hz)"
  id: ecd7feab-681f-4367-86d8-44454fd63f48
clips_per_generation: 2
download: all
types: [spoken, sung]
---
# Prompt Suno: Shelter Stone Gospel

Nguồn: CEO 2026-09-28. Dán **nguyên văn** khối `text` của từng loại vào ô prompt của Suno **Simple mode** (một prompt duy nhất,
Suno tự viết lời và tên), model + Voice ở front matter (Voice của account Suno, cao độ đo ở
`channel/lamplight_gospel/voices/README.md`: Male 01 ~197 Hz, Male 02 263, Male 03 278, Male 04 314). Mỗi lượt Suno ra 2 clip: tải **cả hai** qua usesuno. Cùng lời = 1 bài 2 bản
`<tên>_v1` / `<tên>_v2`; khác lời = 2 bài riêng (skill audio-song-naming quyết theo lời). Lượt cùng lời ~10 credits, khác lời ~20.

Không sửa prompt khi đang chạy. Muốn đổi thì CEO/PM sửa file này, ghi một dòng vào *Lịch sử*.

## spoken

Có lời đọc trước khi hát (spoken intro) và lời đọc cuối bài (spoken outro).

```text
Christian gospel blues with a restrained roots blues-rock edge; dynamic, uncrushed vintage-modern mix; soft gospel piano leads descending-third verses into a two-phrase lift and opening chorus, with sparse slide replies, organic guitar, bass, brushed-to-stick drums, and Hammond organ only in the final third; weathered male bass-baritone with controlled grit, spoken intro and outro, legato sung lines, alternating full-band calls and exposed acapella mature female ensemble answers; relaxed 88 BPM 12/8 shuffle, warm major key, neutral open-fifth ending; long-form six-minute song: three verses, three choruses, a bridge, an instrumental slide-guitar solo and an extended repeated-chorus outro.
```

## sung

Không lời đọc: vào thẳng câu hát đầu tiên, không spoken outro.

```text
Christian gospel blues with a restrained roots blues-rock edge; dynamic, uncrushed vintage-modern mix; soft gospel piano leads descending-third verses into a two-phrase lift and opening chorus, with sparse slide replies, organic guitar, bass, brushed-to-stick drums, and Hammond organ only in the final third; weathered male bass-baritone with controlled grit, legato sung lines, alternating full-band calls and exposed acapella mature female ensemble answers; relaxed 88 BPM 12/8 shuffle, warm major key; no spoken intro or outro, begin directly with the sung verse; neutral open-fifth ending; long-form six-minute song: three verses, three choruses, a bridge, an instrumental slide-guitar solo and an extended repeated-chorus outro.
```

## Lịch sử

- 2026-09-28: CEO gửi 2 prompt `spoken` (555 ký tự) và `sung` (594 ký tự), model "v6-pro".
- 2026-09-28: PM đổi `model: v6-pro` → `v6`: menu Suno chỉ có `v6` (nhãn Pro), `v6-wild`, `v6-mini`; lượt Simple CEO chạy tay 2026-09-27 dùng `v6`. Ô prompt Simple nhận đủ 594 ký tự, Suno lưu nguyên văn.
- 2026-09-28: CEO nghe g001 (không Voice): giọng quá trầm → thử Voice **Male 04 (314 Hz)**, 1 lượt `spoken`. Chưa chốt: CEO nghe rồi quyết.
- 2026-09-28: CEO OK thử bài dài hơn (~6 phút, cách 1): thêm vào cuối prompt `spoken` câu `; long-form six-minute song: three verses, three choruses, a bridge, an instrumental slide-guitar solo and an extended repeated-chorus outro`. Thử 1 lượt; đạt (≥ 5:30) thì áp cho `sung`, không đạt thì bỏ. Bản trước: 556 ký tự (bản CEO gửi 555, thêm dấu chấm cuối khi chạy lượt đầu).
- 2026-09-28: thử g003 (spoken + câu long-form, Male 04) ra 5:59 và 5:39 (trước đó 3:57–4:34), 10 credits → PM áp câu long-form cho `sung` như đã thống nhất với CEO. Cần xem lại độ dài ở vài lượt sau.
