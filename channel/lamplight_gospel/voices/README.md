# Suno Voices của Lamplight Gospel

Voice = persona giọng hát (Suno Pro, loại `vox`), tạo từ một clip đã generate (trang bài → ⋯ → Remix ▸ Voice), không tốn credit.
Tất cả để **riêng tư** (Public tắt). Chọn Voice cho album ở `plan.yaml → identity.voice {name, id}`; Voice khác Male 01 = experiment
trục `voice` (rules.md §1). Cao độ đo bằng cùng phương pháp với video tham khảo (Demucs stem + pYIN, `verification-audio/scripts/qc/vocal.py`).

| Voice | id | Clip gốc | f0 trung vị | p10–p90 | Ghi chú |
|---|---|---|---|---|---|
| Midnight Gospel Soul - Male 01 | `7ebd54d4-454a-4c15-a2e4-973196ae6170` | `3ab17d0d` (WTNL, Album 001) | ~197 Hz (Album 001, 3 bài) | ~100–275 | house default, baritone trầm |
| Midnight Gospel Soul - Male 02 (263 Hz) | `d6d41da0-039d-49a1-85ae-2a781c402bba` | `d2d2d656` (Voice Test C) | 263 Hz | 140–406 | ≈ video tham khảo giọng trung (260–268 Hz) |
| Midnight Gospel Soul - Male 03 (278 Hz) | `36098469-a386-47b8-b301-1e58ec0dd771` | `12a078c3` (Voice Test B) | 278 Hz | 229–394 | thay bản 285 Hz (quá khàn/nhiễu so với tham khảo, đã xoá 2026-09-23) |
| Midnight Gospel Soul - Male 04 (314 Hz) | `ecd7feab-681f-4367-86d8-44454fd63f48` | `4ec14a83` (Voice Test C) | 314 Hz | 233–465 | gần video tham khảo giọng cao (333–354 Hz); AudioSet không bắt được "male singing", có choir/nữ yếu → số đo có thể bị bè choir nâng lên |

Video tham khảo (5 video đầu `research/`): 260, 266, 268, 333, 354 Hz. Chi tiết buổi thử: `notes/voice-lab-2026-09-23.md`.
Audio các clip thử: `audio/` (gitignored).

**Lưu ý khi dùng:** chọn Voice sẽ ghi đè ô Style bằng Style lưu trong Voice → luôn điền Style của album SAU khi chọn Voice.
Style lưu trong Male 02 và Male 04 là câu "high tenor", trong Male 03 là "tenor lead" (chỉ là chữ của clip gốc, không phải số đo).
Khi dùng lần đầu cho album: đo lại f0 + HNR/CPP của các clip ra để biết Voice có giữ cao độ và độ khàn không.

## Độ khàn so với video tham khảo (2026-09-23)

HNR (harmonics-to-noise, dB) và CPP (cepstral peak prominence, dB) trên stem vocal Demucs: thấp hơn = khàn/ráp/nhiều hơi hơn.
Cùng một code cho mọi file (`notes/voice_quality.py`), so tương đối, không phải số lâm sàng. Tham khảo = 19 bài của 5 video (4 bài/video).

| | f0 | HNR (phân vị trong tham khảo) | CPP (phân vị) |
|---|---|---|---|
| Tham khảo: p10 / trung vị / p90 | 248 / 300 / 371 Hz | 5.1 / 5.9 / 7.0 | 17.2 / 19.4 / 22.0 |
| Album 001 (4 bài, Male 01) | 197–264 | 6.3–6.8 (63–79) | 18.7–20.6 (32–58) |
| Male 02 (263 Hz) | 263 | 6.07 (58) | 19.55 (53) |
| Male 03 (278 Hz) | 278 | 6.47 (74) | 18.85 (37) |
| ~~Male 03 cũ (285 Hz)~~ đã xoá | 285 | 4.27 (0) | 16.67 (0) |
| Male 04 (314 Hz) | 314 | 5.85 (47) | 19.43 (53) |

