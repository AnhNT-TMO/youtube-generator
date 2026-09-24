# <Video title>

> Link: <url> · Kênh: <channel> (<subscribers> subs, lập ≈ <date>) · Đăng: <YYYY-MM-DD> · <duration> · <views> views
> Phân tích ngày <YYYY-MM-DD> bằng youtube-music-analyzer (6 tiêu chí). Nhãn: **[đo]** số đo · **[model]** AudioSet/Whisper · **[suy]** suy luận. Claude không nghe được audio.
> Dữ liệu máy đọc: [reference.yaml](reference.yaml) · Idea: [channel/<name>/ideas/NNN-slug/](../../channel/<name>/ideas/NNN-slug/idea.md)

## 1. Tóm tắt

2-3 gạch: video này là gì, vì sao đáng tham khảo (views, kênh), điều mình lấy làm khung.

## 2. Sáu tiêu chí

| # | Tiêu chí | Tham khảo | Mình (album gần nhất) | Ghi chú |
|---|---|---|---|---|
| 1 | Độ dài video + số bài | | | |
| 2 | Độ dài bài (trung vị, min-max) | | | |
| 3 | Tempo (felt BPM) + nhịp | | prompt / đo | bài lệch họ nhịp |
| 4 | Giọng (nam/nữ, trầm/trung/cao) | | persona | |
| 5 | 15 giây đầu (giọng, lời đầu, âm lượng) | | | gate §3; độ tin |
| 6 | Mật độ lời (từ/phút hát) | | | nguồn: captions / Whisper |

## 3. 15 giây đầu → cách mở Track 01 của mình

Họ mở thế nào (tiêu chí 5) và mình mở thế nào: timeline 0-15 s, lúc giọng và hook vào, 2-3 biến thể → idea `track01`.

## 4. Nền: kênh & đóng gói

Tuổi kênh, single trước hay compilation trước, bài mở có phải single của kênh không, title/thumbnail (nhìn
`thumbnail.jpg`), những gì phải tránh (copy guard).

## 5. Độ tin cậy

Nguồn chia bài và join yếu, số không chắc (tempo_uncertain, `opening.note`), dữ liệu thiếu (captions, qc).
