# Luật làm nhạc: <Channel Name>

**Nguồn chuẩn duy nhất** khi plan, viết lời và generate cho kênh này (album-plan đọc file này; `album_plan.py validate` và
youtube-music-analyzer đọc khối YAML ở cuối). Chỉ ghi **quyết định**, mỗi luật một dòng kèm nguồn + ngày.

## 1. House sound = MẶC ĐỊNH, không phải khuôn

- Style một album = `<genre_lead>, <cụm mood của album>. <vocal_line của Voice> <band_block> <groove_line>`.

## 1b. Bám video tham khảo ~50 % + bài điểm nhấn

## 2. Mật độ lời

## 3. Chữ và tên bài cần tránh

## 4. Trùng ý giữa các album

## 5. Viết Style (Suno)

## 6. Tag trong lời

## 7. 15 giây đầu

## 8. Hình dạng lời

## 9. Clip hỏng → sửa gì

## Khối máy đọc (album_plan.py validate)

```yaml
house_style:
  version: <prefix>-house-v1
  genre_lead: "<Genre, subgenre>"
  vocal_line: >-
    <câu giọng mặc định>
  band_block: >-
    <ban nhạc + phòng thu>
  exclude: "<những gì tránh, phân cách bằng dấu phẩy>"
  meter_default: "4/4"
  groove_line: "{meter} groove, {bpm} BPM."
research:
  intro_vocab: [vocal, piano, full_band]
  genre_words: []
sources:
  kind: null
lyrics:
  words_per_beat_max: 1.35
  words_per_beat_warn: 1.20
  sung_allowance_s: 55
reference_follow:
  tempo_max_dev_pct: 5
  voice_f0_max_dev_pct: 15
  words_per_min_max_dev_pct: 20
highlight:
  slots: [4, 7]
  required: true
voices: []
avoid_words: []
heteronyms: []
known_titles: []
```
