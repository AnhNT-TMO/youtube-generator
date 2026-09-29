# Shelter Stone Gospel: hướng dẫn kênh

Đọc file này trước khi làm bất cứ việc gì cho kênh. Luật chung ở `CLAUDE.md` gốc; quy trình ở các skill.

| File | Dùng khi | Skill đọc |
|---|---|---|
| `channel.md` | danh tính, hợp đồng kênh, tài nguyên | mọi skill |
| `prompt_suno.md` | tạo bài vào kho | audio-suno-generate |
| `naming.md` | đặt tên bài, chọn đoạn Short | audio-song-naming |
| `album_rules.md` | chọn bài cho album, độ dài, crossfade | pm-production (`album.py`), audio-album-assembly |
| `visual.md`, `thumb_pool.json` | thumbnail album + ảnh dọc Short | thumbnail-prompt |
| `video.json`, `image_source/` | chuyển động video, logo, huy hiệu | video-generator |
| `publish.md` | title, description, tags, Shorts, giờ đăng | upload-youtube-publish, video-shorts |
| `translate.yaml` | dịch sau khi đăng | upload-youtube-translate |

## Âm thanh

Christian gospel blues, 12/8 shuffle ~88 BPM, giọng nam bass-baritone phong trần + bè nữ đáp, piano gospel + slide + Hammond.
Hai loại bài: `spoken` (lời đọc trước khi hát và cuối bài) và `sung` (vào hát luôn). Album xen kẽ `spoken → sung → …`,
bài 1 là `spoken`, nối crossfade nhẹ, không cắt sửa.

## Hình ảnh

Ông ca sĩ lớn tuổi (`model/`) hát hết lòng trong nhà nguyện đá, ánh vàng hổ phách, một thánh giá thật, lời cầu xin chữ vàng
rất to, thanh dưới `1 HOUR OF …`. Form cố định theo ảnh mẫu, biến thể theo `thumb_pool.json` (`visual.md`).

## Trạng thái

Lấy từ `album.py board --channel shelter_stone_gospel` (skill pm-production), không ghi tay ở đây.
