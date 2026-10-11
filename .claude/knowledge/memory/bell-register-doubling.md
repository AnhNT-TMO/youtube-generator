---
name: bell-register-doubling
description: CEO 2026-10-10 chốt chuẩn phối Christmas piano: giai điệu lên quãng 8 (bell register C5–F6) + nhạc cụ chuông đè quãng 8 trên, không bè dây kéo giữa câu
metadata:
  type: project
---

CEO 2026-10-10 chốt sau thử nghiệm Silent Night (ensemble_arrange.py): giai điệu piano chuyển lên quãng 8 so với sách thánh ca
("trong như chuông" của các kênh YouTube là do quãng, không phải lên 1 cung; key giữ theo allowed_keys), đè quãng 8 trên chỉ bằng
celesta (handchimes bỏ, glockenspiel chỉ đồng âm ở −16 dB, vibraphone VCSL hết tầm ở E6 → đồng âm hoặc quãng 8 dưới). Pattern piano + chuông dùng cho mọi bài, nhưng
phối từng bài theo đặc trưng riêng. Bè viola đối âm kéo giữa câu bị CEO chê "như còi container" → bỏ, dây chỉ nền chord chậm,
lọc 3 kHz. Mức đè −8 dB RMS so với piano (−15 bị lấp, hai biến thể nghe như nhau).

Vibraphone quãng 8 dưới OK cho bài cần ấm. Nền chord chọn theo bài: strings / viola / organ / pad (`--bed`).
Tuning: Piano in 162 cao +11 cents so A440, mẫu glock/celesta lệch tới +30 cents → sampler dùng `~/music-tools/sfz/tune_measured.json`
(measure_tune.py) + `--tune-cents 11`; đè đồng âm lệch >10 cents nghe "vỡ như hai thìa".

**Why:** CEO nghe thấy bản của mình "thấp và không trong" so với kênh tham chiếu; đo trọng tâm phổ 505 → 825 Hz khi lên quãng 8.
**How to apply:** mọi render Christmas piano mới dùng melody +12, double +12 bằng nhạc cụ chuông, không string line; khi
chuyển vào ambient_render.py giữ các rule này. Chi tiết: research/christmas-carols/experiments/piano-arrange/DECISIONS.md.
Liên quan: [[piano162-sfizz-arrangement]], [[christmas-ambient-standard]], [[piano-channel-lead]].
