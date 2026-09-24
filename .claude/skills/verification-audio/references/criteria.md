# Chọn clip Suno bằng 4 tiêu chí (v2, 2026-09-23)

> Thay cho bản verify đầy đủ v1 (20 check, điểm có trọng số, baseline theo Anchor), đã xóa ngày 2026-09-23.
> Cách dùng: [../SKILL.md](../SKILL.md).

## Vì sao chỉ 4 tiêu chí

- Budget chỉ đủ 1 lượt (2 clip) mỗi bài, title track 2 lượt (4 clip). Việc cần làm là **chọn bản dùng được hơn**, không phải chấm nhạc.
- 2 clip của cùng một lượt dùng chung Style, Voice, lời, nên thể loại, giọng và production hiếm khi khác nhau. Cái hay khác nhau là:
  bản bị cắt/ngắn, bản hát thiếu hoặc sai lời, tempo (cặp clip cùng lượt của Album 001: 63.2 và 54.9 BPM, prompt 70), bản có intro dài hơn.
- Bài hay hay dở do **người nghe thật** quyết (retention 0:15 / 0:30 / 1:00 sau khi đăng, ghi trong `youtube.md`), không phải tool.
  Chỉ thêm tiêu chí khi dữ liệu người nghe cho thấy cần.

## Tiêu chí

| # | Tiêu chí | Đo | Ngưỡng |
|---|---|---|---|
| 1 | Không hỏng | ffmpeg (`qc/basic.py`) | hỏng khi: độ dài ngoài `rules.duration_range` · 1 giây cuối còn to hơn −6 dB so với trung vị bài (bị cắt ngang; Album 001: −17 đến −26 dB) · khoảng lặng < −50 dB dài ≥ 2 s giữa bài |
| 2 | Hát đủ lời | Whisper large-v3-turbo trên **bản mix** (không tách stem), khớp mờ từng dòng lời (≥ 0.6), dòng lặp tính một lần | hỏng khi nghe ra < 60 % số dòng |
| 3 | Tempo sát prompt | autocorrelation onset trên **bản mix**, mức nhịp gần BPM prompt nhất (`qc/tempo.felt`); BPM prompt = manifest `settings.bpm` → track md `target_bpm` → selection.yaml `tempo.target_bpm` | không loại, chỉ xếp hạng (xem dưới) |
| 4 | Vào lời sớm | giây sớm nhất một dòng lời được nghe ra (chữ Whisper nhầm trên intro không lời không khớp dòng nào nên không tính) | không có ngưỡng, chỉ để phân xử |

**Quyết định:** bỏ clip hỏng → giữ các clip có % lời kém bản tốt nhất ≤ 10 điểm → giữ các clip có độ lệch tempo so với prompt
hơn bản sát nhất ≤ 3 điểm % → bản vào lời sớm nhất thắng.
Không còn clip nào → REGENERATE. Gợi ý ghi `[cả N clip]` khi mọi clip cùng lỗi (do prompt/lời), `[1/N clip]` khi lỗi ngẫu nhiên.

Tempo không dùng để loại: Suno hay ra chậm hơn prompt (Album 001: prompt 70 → 57–67). Nếu loại bản lệch > 8 % thì 7/10 bài
Album 001 phải tạo lại, tốn credits mà cùng prompt vẫn ra như vậy. Tempo xếp trước giây vào lời vì intro còn cắt được lúc ghép,
tempo thì không.

## Kiểm tra (2026-09-23)

- Whisper trên bản mix, 2 bài Album 001: nghe ra 100 % dòng lời; giây vào lời 36.4 s (wtnl-01) và 27.6 s (mercy-met-me-there),
  khớp với số đo trên stem vocal của v1 (vocal vào 28–37 s). ~30–80 s/clip trên Mac M2; nay chạy trên server GPU (vài giây/clip).
- Mac (mlx-whisper) và server (openai-whisper, CUDA) đôi khi lệch giây vào lời. Album 002, 7 clip, so với năng lượng stem vocal
  (qc/vocal): server khớp (35.6 / 34.2 s, 30.8 / 32.0 s, 31.3 / 32.5 s), Mac từng ra 7.7 s ở clip vào lời thật ~34 s → dùng số server.
  Whisper trên **stem vocal** thử rồi bỏ: stem gần im ở intro nên Whisper bịa chữ ở giây 0–7 (sai hơn bản mix).
- Album thử 3 clip (bản gốc wtnl-01 · cùng bài bị cắt ở 4:50 · bài khác = sai lời): chọn bản gốc; bản bị cắt → "bị cắt ngang ở cuối";
  bản sai lời → 11 % dòng lời. Chỉ đưa 2 bản hỏng → REGENERATE, gợi ý đúng từng lỗi.
- Tempo trên bản mix, 10 bài Album 001: khớp cách đo có tách stem drums (Demucs) trong 0.3 %, ~1 s/bài.
- Bản gốc wtnl-01 (67.2, −4 %) so với cùng bài kéo chậm 12 % và bỏ intro (59.1, −16 %, vào lời giây 19 so với 36): chọn bản gốc.

## Không đo nữa (và ai lo thay)

| Bỏ | Lý do | Ai lo |
|---|---|---|
| Giọng giống Anchor (ECAPA), âm vực | 2 clip cùng Voice hiếm khi lệch giọng; người nghe sẽ phát hiện | người nghe / retention |
| Thể loại (CLAP), production, Audiobox | cùng Style prompt | người nghe |
| Key, kiểu intro, nối với bài trước | việc của lúc ghép | album-assembly |
| Gate Track 01 (mức 15 s đầu, hook) | intro được cắt khi ghép; tiêu chí 3 đã ưu tiên bản vào lời sớm | album-assembly (`vocal_at`), retention |
