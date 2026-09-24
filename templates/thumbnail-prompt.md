---
kind: <single | album | idea>
source: <file bài gốc (single) / idea.yaml packaging.thumbnail_brief (idea) / album.md (album)>
title_text: "<chữ trên ảnh, nguyên văn>"
setting: <vd. night forest clearing / wooden chapel / cabin porch / country road / riverside>
time: <night | moonlit night | pre-dawn | first light | dusk>
pose: model/<NN-...>.png   # ảnh tham chiếu đính kèm (tư thế gần nhất)
wardrobe: <work | farm | traveler | sunday | biblical>: <chi tiết, vd. faded flannel, patched brown cardigan>
framing: <wide | medium | close | hands | lamp-front | rim>
light: <single | moon | mist | rain | snow | dawn | fireflies | fire>   # 1–2 giá trị
palette: <blue | teal | sepia | cold | dusk | mono>
lettering: <serif | brush | letterpress | bible | glow>   # theo album; single chép của album
signature: <chỉ ảnh album: 2–3 trục làm chữ ký album, vd. "light rain + palette teal + tele"; single: chép chữ ký của album>
layout: <vd. text left-top, singer centre-right>
hero_object: <vd. brass oil lantern, bottom-left>
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
<khối CORE "Prompt ảnh mặc định (ChatGPT)" trong channel.md, nguyên văn>
THIS IMAGE: "<title>"
Title text: "<title_text>"
Title style: <mẫu lettering trong channel.md, theo album>
Look: <mẫu framing + light + palette trong channel.md "Biến thể hình ảnh", sửa cho hợp cảnh>
Scene: <bối cảnh, thời điểm, thời tiết, 1–2 chi tiết lấy từ bài>
The singer: <tư thế theo ảnh tham chiếu, biểu cảm, tay>
Clothing: <mẫu wardrobe trong channel.md, đổi màu/chỗ vá cho ảnh này>
Light: <đèn gì, ở đâu (vai trò của đèn), ánh sáng rơi vào đâu>
Composition: <chữ ở đâu, người ở đâu, vật chính ở đâu>
```

## Sửa tiếp (dán trong cùng chat khi cần)

- Chữ sai: `Edit this image. Keep everything else exactly the same. Only fix the title so it reads exactly: "<title_text>" and the small line reads exactly: "Lamplight Gospel".`
- Mặt lệch: `Edit this image. Keep the scene, pose, clothes and light exactly the same. Make his face match the attached reference exactly.`
- Góc phủ rối: `Edit this image. Keep everything else the same. Make the top-right and bottom-right corners darker and emptier.`

## Các lượt thử

| # | File | Vấn đề | Sửa |
|---|---|---|---|
