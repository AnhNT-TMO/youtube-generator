# Checklist album <NNN-slug> · <Album title>

<!-- `album.py new` tạo file này ở production/<ch>/checklists/<NNN-slug>.md. PM tick [x] + ghi kết quả 1 dòng sau mỗi việc;
     việc không làm: [-] + lý do. Chi tiết nằm ở file được trỏ tới, không chép vào đây. -->

**Brief:** <một câu> · **Chủ đề:** <topic> · **Nguồn:** CEO | R&D · **Kho câu:** <id → câu của mình> · **Mục tiêu:** 48 h <n> · 7 d <n>

## Chuẩn bị
- [ ] 1. Kho bài đủ (`album.py pool`: đủ mỗi loại cho 60–80 phút, bài 1 có đoạn short) — <spoken / sung, bài mới>
- [ ] 2. album.md: brief + tracklist (PM + CEO) — <chủ đề, bài 1, bài cho Short, câu title / thumbnail>
- [ ] 3. `album.py check` + `build` — <số bài, phút ước lượng, waiver nếu có>

## Sản xuất
- [ ] 4. Master (audio-album-assembly) — <thời lượng, cảnh báo>
- [ ] 5. Thumbnail 4K + jpg (thumbnail-prompt) — <chữ trên ảnh, bản chọn, số vòng vẽ>
- [ ] 6. Loop (video.py loop / qa) — <variant, qa>
- [ ] 7. youtube.md (upload-youtube-publish, `publish.py check`) — <title>
- [ ] 8. Video full (video.py album) — <độ dài = master>
- [ ] 9. Short (video-shorts: short.json, ảnh dọc, video, youtube.md) — <albums/NNN-slug/short, bài>
- [ ] 9b. Một zip S3 cho album + Short (video.py package <album>) — <S3 URI, checks>

## Đăng + kết quả
- [ ] 10. CEO upload cùng ngày (album → Short) — <ngày, Video URL đã điền, Related video>
- [ ] 11. Dịch title + description (upload-youtube-translate) — <ngôn ngữ>
- [ ] 12. Kết quả 48 h — <view, x so với trung vị, ret 30 s>
- [ ] 13. Kết quả 7 ngày + bài học — <kết luận, điều PM đổi trong direction.md>

## Vướng / quyết định của PM
- <ngày · việc · đã quyết gì · vì sao>
