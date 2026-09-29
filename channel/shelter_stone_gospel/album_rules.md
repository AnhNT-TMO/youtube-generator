---
length_min: [60, 80]
crossfade_s: 3
pattern: [spoken, sung]
sibling_min_gap: 4
title_song_unique: true
order_must_differ: true
min_new_songs: all
---
# Luật chọn bài cho album: Shelter Stone Gospel

PM chọn bài từ kho `songs/` (bài đã đặt tên) và ghi vào `albums/NNN-slug/album.md` → `tracklist`. Khối front matter ở trên
là luật máy đọc (`pm-production/scripts/album.py check`); phần dưới giải thích.

## Luật (CEO 2026-09-28)

1. **Độ dài master 60–80 phút** (`length_min`). Thiếu thì thêm bài, thừa thì bớt bài; không kéo dài hay cắt bài.
2. **Xen kẽ loại bài** (`pattern`): bài 1 = `spoken` (có lời đọc trước khi hát) → `sung` (vào hát luôn) → `spoken` → `sung` …
   cho đến đủ độ dài.
3. **Nối bằng crossfade nhẹ** (`crossfade_s` giây) giữa hai bài, không cắt intro/outro, không sửa gì trong bài.
   (audio-album-assembly chỉ bỏ phần im lặng tuyệt đối ở hai đầu file và cân loudness.)
4. **Xếp bài theo nội dung, không xếp lung tung** (CEO 2026-09-28): các bài có lời liên quan nhau (cùng nỗi đau, cùng hình ảnh,
   cùng lời xin) đứng gần nhau thành từng cụm; **đầu album là những bài hợp chủ đề album nhất** (title + thumbnail hứa gì thì
   phần đầu trả đúng cái đó), càng về cuối càng rộng dần, để giữ chân người nghe lâu hơn. Vẫn giữ luật xen kẽ (mục 2).

## Mặc định của PM (đổi được, ghi lý do vào album.md)

5. **Bài 1 (title song)** hợp chủ đề album nhất; chưa từng là bài 1 của album nào (`title_song_unique`).
6. **Hai bản v1/v2 của cùng một bài** (`sibling`) được nằm chung album nhưng cách nhau ≥ `sibling_min_gap` vị trí.
7. **Thứ tự không trùng** thứ tự của album nào trước đó (`order_must_differ`).
8. **Bài mới mỗi album** ≥ `min_new_songs` (bài chưa nằm trong album nào; bản v2 của một bài đã dùng cũng tính là đã dùng).
   **CEO 2026-09-29: 3–4 album đầu toàn bài mới** (`all`) để người nghe mới gặp nhạc khác nhau; sau album 004 PM hạ xuống
   (vd. 6) khi kho đủ lớn và bắt đầu đảo bài.
9. Bài dùng cho Short của album (`brief.short.song`) mặc định là bài 1; đoạn cắt lấy từ `short` trong file bài.
