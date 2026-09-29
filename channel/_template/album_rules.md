---
length_min: [60, 80]
crossfade_s: 3
pattern: [<type-a>, <type-b>]
sibling_min_gap: 4
title_song_unique: true
order_must_differ: true
min_new_songs: 0
---
# Luật chọn bài cho album: <Channel Name>

Front matter là luật máy đọc (`pm-production/scripts/album.py check`): độ dài master (phút), crossfade (giây), chuỗi loại bài
lặp lại (bài 1 = loại đầu), khoảng cách tối thiểu giữa 2 clip cùng lượt Suno, bài 1 chưa từng mở album nào, thứ tự không trùng
album cũ, số bài chưa từng dùng tối thiểu.

<giải thích thêm luật riêng của kênh>
