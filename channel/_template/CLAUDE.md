# <Channel Name>: hướng dẫn kênh

Đọc file này trước khi làm bất cứ việc gì cho kênh. Luật chung ở `CLAUDE.md` gốc; quy trình ở các skill.

| File | Dùng khi | Skill đọc |
|---|---|---|
| `channel.md` | danh tính, hợp đồng kênh, tài nguyên | mọi skill |
| `prompt_suno.md` | tạo bài vào kho | audio-suno-generate |
| `naming.md` | đặt tên bài, chọn đoạn Short | audio-song-naming |
| `album_rules.md` | chọn bài cho album, độ dài, crossfade | pm-production (`album.py`), audio-album-assembly |
| `visual.md` | thumbnail album + ảnh dọc Short | thumbnail-prompt |
| `video.json`, `image_source/` | chuyển động video, logo | video-generator |
| `publish.md` | title, description, tags, Shorts, giờ đăng | upload-youtube-publish, video-shorts |
| `translate.yaml` | dịch sau khi đăng | upload-youtube-translate |

## Âm thanh

<thể loại, các loại bài trong prompt_suno.md, album xếp loại bài thế nào>

## Hình ảnh

<hằng số của mọi ảnh (nhân vật, cảnh, ánh sáng, chữ), chi tiết ở visual.md>

## Trạng thái

Lấy từ `album.py board --channel <ch>` (skill pm-production), không ghi tay ở đây.
