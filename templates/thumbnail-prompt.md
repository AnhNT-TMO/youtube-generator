---
kind: <single | album | idea | short>
source: <file bài gốc (single) / idea.yaml packaging.thumbnail_brief (idea) / album.md (album)>
title_text: "<chữ trên ảnh, nguyên văn>"
setting: <bối cảnh, theo channel/<ch>/visual.md>
time: <thời điểm>
pose: model/<NN-...>.png   # ảnh tham chiếu đính kèm (tư thế gần nhất)
wardrobe: <giá trị trục wardrobe trong visual.md>: <chi tiết>
framing: <giá trị trục framing trong visual.md>
light: <giá trị trục light trong visual.md>   # 1–2 giá trị
palette: <giá trị trục palette trong visual.md>
lettering: <kiểu chữ trong visual.md>   # theo album; single chép của album
duration_line: "<chỉ album/idea, khi visual.md có mục Dòng thời lượng: vd. 1 HOUR OF PEACE; single: bỏ trống>"
signature: <chỉ ảnh album: 2–3 trục làm chữ ký album, vd. "light rain + palette teal + tele"; single: chép chữ ký của album>
layout: <vd. text left-top, character centre-right>
hero_object: <vật chính và vị trí>
status: draft             # draft → generated → chosen (existing = ảnh làm trước skill, không có prompt)
chosen:                   # thumbnail-drafts/NN.png khi đã chọn
---

# Thumbnail — <title>

Soạn bằng skill `thumbnail-prompt`. Dán **một lần** khối Prompt vào một chat ChatGPT **mới**, đính kèm ảnh ở mục Đính kèm.
Kiểm tra: `python3 .claude/skills/thumbnail-prompt/scripts/thumb.py check <thư mục>`.

## Ý tưởng

- Từ bài/album: <hình ảnh/cảm xúc cụ thể lấy từ imagery, emotion, hook, lyric_keywords>
- Chọn trục theo vibe bài: <wardrobe / framing / light / palette đã chọn và vì sao hợp bài>
- Chữ ký album: <giữ trục nào của album; single khác ảnh album ở điểm nào>

## Đính kèm

- `channel/<ch>/<pose>` (tư thế)
- `channel/<ch>/model/01-front-eye-contact.png` (giữ mặt, tùy chọn)

## Prompt

```
<khối CORE "Prompt ảnh mặc định (ChatGPT)" trong channel/<ch>/visual.md, nguyên văn>
THIS IMAGE: "<title>"
Title text: "<title_text>"
Title style: <mẫu lettering trong visual.md, theo album>
Duration line: "<duration_line; single hoặc kênh không dùng: xóa dòng này>"
Look: <mẫu các trục trong visual.md "Biến thể hình ảnh", sửa cho hợp cảnh>
Scene: <bối cảnh, thời điểm, thời tiết, 1–2 chi tiết lấy từ bài>
The singer: <nhân vật: tư thế theo ảnh tham chiếu, biểu cảm, tay>
Clothing: <mẫu wardrobe trong visual.md, chỉnh cho ảnh này>
Light: <nguồn sáng chính, ở đâu, ánh sáng rơi vào đâu>
Composition: <chữ ở đâu, người ở đâu, vật chính ở đâu>
```

## Sửa tiếp (dán trong cùng chat khi cần)

- Chữ sai: `Edit this image. Keep everything else exactly the same. Only fix the title so it reads exactly: "<title_text>" and the small line reads exactly: "<dòng cố định trong visual.md>" (album: and the line under it reads exactly: "<duration_line>").`
- Mặt lệch: `Edit this image. Keep the scene, pose, clothes and light exactly the same. Make his face match the attached reference exactly.`
- Góc phủ rối: `Edit this image. Keep everything else the same. Make the top-right and bottom-right corners darker and emptier.`

## Các lượt thử

| # | File | Vấn đề | Sửa |
|---|---|---|---|
