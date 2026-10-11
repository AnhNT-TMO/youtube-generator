# Tối ưu resource queue (2026-10-04)

Mục tiêu CEO: ít token, chất lượng không đổi, cảnh đa dạng, chạy hiệu quả. File này ghi quyết định + lý do; cách chạy
nằm ở `.claude/skills/pm-production/references/resource-queue.md` và hai skill `video-resource-*`.

## Token đi đâu trước khi sửa

| Chỗ | Vấn đề |
|---|---|
| Generator ảnh + clip (2 agent Sonnet) | chỉ trông một script thuần nhưng mỗi vòng `work` 7 phút lại đọc log, ngữ cảnh cứ dài thêm |
| Reviewer chạy liên tục | một phiên duyệt hàng chục ảnh/clip, mỗi ảnh nằm lại trong ngữ cảnh → mỗi lần xem sau đắt hơn lần trước |
| PM viết prompt clip | PM mở lại từng ảnh đã đạt để viết prompt clip: mỗi ảnh bị xem hai lần (reviewer + PM) |
| PM nạp queue 20 job | 20 ảnh ≈ 30–40 phút việc, PM phải thức dậy nạp lại liên tục |
| PM tự kiểm queue | PM poll board định kỳ dù không có gì cần làm |

## Quyết định

1. **Generator = tiến trình nền, 0 token.** `images.py work` / `videos.py work` chạy 4 giờ một lần (`--seconds 14400`),
   PM chỉ thức khi tiến trình thoát. `work` vẫn tự làm tiếp job dở nên chạy lại an toàn. Agent `resource-generator` chỉ
   còn cho môi trường không chạy nền được (Codex).
2. **Ảnh tự nạp tới 60 job** (`--refill <set> --target 60`, nạp lại khi chờ < 20), lấy xoay vòng qua các đề tài để các
   cảnh liên tiếp khác nhau. Prompt ảnh vốn ghép từ `blocks.json` + `shots.json` nên số job chờ nhiều hơn không làm prompt kém đi.
3. **Reviewer ảnh ghi trường `clip` khi cho đạt** (`resource.json` → `image.card_fields`; queue từ chối ok thiếu trường).
   Reviewer đang xem ảnh rồi, ghi thêm vài trường (shot, deep, window, motion, lock, light, sound) gần như không tốn thêm;
   mỗi ảnh chỉ được xem đúng một lần.
4. **Prompt clip ghép bằng máy** (`videos.py draft`) từ `video_prompt.json` + trường clip. Câu khóa (không zoom, không
   người, không tuyết trong nhà…) là khuôn cố định nên mọi prompt đều có đủ, không phụ thuộc trí nhớ của PM. `forbid` chặn
   chữ cấm (cảnh trong nhà → không có "snow").
5. **Đa dạng chuyển động máy:** `draft` chọn kiểu máy ít dùng nhất trong đề tài (đếm cả queue lẫn clip đã đạt); cảnh
   sâu (`deep`) chỉ slide/arc vì drift forward ở cảnh sâu hay thành zoom (`camera-far`). Trước đây slide chiếm ~75 %.
6. **Reviewer theo lô ≤ 12 job** rồi thoát; lô sau là ngữ cảnh mới. Mỗi lane một reviewer cùng lúc.
7. **Reviewer clip xem ít ảnh hơn:** mặc định `seconds.jpg` + `edges.jpg` + `full8.jpg` (đủ thấy zoom, morph, khựng
   đầu/cuối, chi tiết cuối clip); `full3.5` / `sheet` chỉ mở khi nghi.
8. **PM thức theo `resq.py watch`**, không poll: lệnh chỉ thoát khi có việc của PM (REVIEW ≥ 8 chờ và chưa có reviewer,
   FIX ≥ 5, LOW clip < 10, STUCK, IDLE 4 phút không việc) và in đúng lý do.
9. **ChatGPT lỗi tạm** ("Image generation failed / unavailable") → trả job, không tốn lượt; 3 lần liền → dừng cổng (mã 3)
   thay vì đốt hết 3 lượt của cảnh.

## Giữ nguyên (vì chất lượng)

- Reviewer vẫn là Opus và vẫn tự xem file thật cho mọi verdict; tối đa 3 lượt/cảnh; cắt clip chỉ khi còn ≥ 7 s.
- Prompt sửa (needs_fix) vẫn do PM viết tay theo note + codes, chỉ đổi câu gây lỗi.
- Không tăng số Chrome/tab mỗi cổng; không gửi lại khi không chắc đã gửi.

## Ảnh cũ

174 ảnh đạt trước khi có trường clip được ghi bổ sung bằng agent `resource-reviewer` theo lô ~30
(`videos.py candidates image_source --missing-clip --json --limit 30` → `videos.py clip`). Tốn một lần xem mỗi ảnh,
bằng đúng chi phí cũ của PM khi viết prompt clip, nhưng làm một lần và dùng lại cho mọi lượt draft/làm lại.

## Theo dõi sau lô này

- Tỉ lệ đạt ngay lượt 1 của clip với prompt `draft` so với prompt PM viết tay (trước: zoom `camera-far` và `morph` là lỗi chính).
- Phân bố kiểu máy trong clip đạt (`videos.py draft --dry-run` in số đếm).
- Nếu reviewer lô 12 vẫn nặng → giảm còn 8; nếu ảnh 60 chờ làm ChatGPT hết lượt giữa chừng → hạ target.

## Chỉnh khuôn theo lỗi (2026-10-04)

- Clip: `camera-far` là lỗi số một (4/10) → khuôn máy giảm từ ~1/20 xuống ~1/30 bề ngang khung.
- Ảnh cozy: `motion-missing` 3 lần (thiếu khói cốc / tuyết rơi) → `shots.json` của đề tài ghi rõ "clearly visible" cho
  khói và bông tuyết, để lượt 1 đạt nhiều hơn thay vì tốn lượt làm lại.
- Lô review clip thứ hai (12 job): cả 6 redo đều `camera-far`. `drift forward` trong phòng rộng thành zoom 1,5–2,5×,
  arc đôi khi đi 18–25 %; slide 1/20–1/30 đạt (4–10 %); 1/50 thì quá đứng (`camera-still`). → bỏ `drift forward` khỏi
  khuôn; câu máy thêm "same height, fixed lens, never moves closer, never zooms"; câu cửa thành "every door stays exactly
  as open or closed as in the first frame" (ảnh có cửa mở). `videos.py redraft` đổi luôn 36 job đang chờ theo khuôn mới
  để không đốt lượt vào khuôn cũ.
- Công cụ: `cdp.py` thêm hạn 150 s cho mỗi lệnh Chrome (một cổng ảnh từng treo 13 phút không lỗi).
- Chi phí ghi trường clip cho ảnh cũ: ~3,5k token/ảnh (Opus, 173 ảnh, một lần).
- Lô 3 (14 clip, mọi prompt có "fixed lens, never moves closer"): trung vị máy đi ~17 %. Phòng ấm cỡ vừa (cozy, bedroom,
  bàn tiệc) đạt 4–8 %; macro cận và hội trường rộng (ballroom, hotel lobby) hầu như luôn bị muse đẩy vào 15–26 %. Kết
  luận: cách viết prompt không quyết định nhiều; loại cảnh quyết định. → `videos.py draft` giữ lại (không thêm job) các đề
  tài đã duyệt ≥ 4 lượt mà tỉ lệ đạt < 20 % (`--hold-min`, `--hold-below`); hiện giữ ornaments-macro 0/6, ballroom 1/9.
  Ảnh của các đề tài này vẫn dùng làm ảnh tĩnh; clip chỉ thử lại khi có cách khác (vd. hậu kỳ chuyển động trên server).
  Đang thử câu "slider rail, cùng khoảng cách với vật chính" cho các lượt sửa của các đề tài này.
- Ứng viên tiết kiệm lớn (chưa làm, trình CEO): đo tự động mức máy đi trong `videos.py check` để loại `camera-far` trước
  khi reviewer Opus xem (~60 % số redo, ~10k token/lượt duyệt).
- Lô 4 (12 clip): arc thành đẩy vào/phóng ~1,5× ở 6/8 job lượt 1; slide ở lượt 2 đạt 4/5. → khuôn chỉ còn slide
  trái/phải (đa dạng chuyển động giảm, nhưng đổi lượt đạt; cảnh vẫn đa dạng nhờ ảnh). `redraft` đổi 11 job đang chờ.
  Lượt sửa `camera-far` dùng khoảng ~1/40 + câu "short slider rail, same distance from the main subject".
- Lô 5 (16 clip): câu "slider rail" không hơn arc/slide (7 job có rail: 3 đạt, 4 đi 15–55 %); ba job hết lượt đều thuộc
  đề tài đã bị giữ (ornaments-macro, ballroom) → luật giữ đề tài là cách đúng, không cố sửa prompt cho các cảnh này.
- Reviewer hai lô liền vượt 12 (14–16 job) → `resq.py next-review --batch 12` chặn ở queue, đếm theo tên reviewer;
  PM đặt tên mới mỗi lượt spawn (`<lane>-r<HHMM>`).
- CEO 2026-10-04: không dùng máy đứng yên + thêm chuyển động hậu kỳ (chất lượng kém). Thứ tự: đo khuôn chỉ-slide qua các lô
  duyệt tới; chưa đủ thì làm đo chuyển động tự động trong `videos.py check`, thử trên tập clip đã có số % của reviewer,
  đánh giá xong mới cho chặn queue.
- Lô 6 (12 clip, phần lớn đã là slide): 4 đạt / 8 `camera-far`. Slide không chặn được muse đẩy vào ở cảnh trong nhà
  cận/vừa (attic-loft-10, christmas-morning-06, gingerbread-village-05 đẩy vào 1,4–1,7× hai lượt liền).
- Thử đo chuyển động tự động (chưa bật): ORB + similarity giữa giây 1 và từng giây 2–9 trên `seconds.jpg` (312 px),
  lấy độ dời lớn nhất của 4 góc khung / bề ngang. Tập thử: 88 clip đã có verdict reviewer (36 đạt, 52 `camera-far`).
  Ngưỡng 25 %: 0 clip đạt bị loại nhầm, bắt 33/52 `camera-far`; ngưỡng 28 %: 0 nhầm, bắt 25/52. Clip đạt cao nhất đo
  được 24 % (đạt nhờ cắt đuôi) → biên mỏng, đề xuất bắt đầu ở 28 %. Chờ CEO duyệt trước khi cho chặn queue.
- ChatGPT treo "One last tweak… 99 %" > 8 phút rồi chat không tải được: `wait_image` nâng 480 → 900 s để không bỏ ảnh chậm.
- **Bật cổng đo máy (PM quyết, CEO giao PM tự thử nghiệm):** `video.motion_reject = 0.28`; `videos.py work` đo mọi clip
  sau khi tải (`motion.py`, < 1 s/clip) và cho redo `camera-far` tự động dưới tên `auto-motion`. Mọi clip đều ghi
  `meta.motion` nên sau 1–2 lô so lại với verdict reviewer (clip dưới ngưỡng) rồi quyết hạ xuống 25 %.
- **`videos.py refix`:** lượt sửa của `camera-far` (kèm morph/people/indoor-particles) ghép lại từ khuôn và đảo hướng máy;
  dữ liệu 6 lô cho thấy viết lại câu chữ không làm muse nghe lời hơn, nên PM không tốn token viết tay cho các job này.
- Lô 7: 1/12 đạt (11 `camera-far`). Giả thuyết: câu "fixed lens, never moves closer, never zooms in" (thêm từ lô 3) lại
  gợi muse đẩy vào — trước đó "a twentieth" không có câu này ra 6–10 %. **Thử A/B/C** trên 39 job input (xoay vòng,
  `production/resq/videos/experiments/camera-wording.json`): A = khuôn hiện hành; B = "a twentieth", bỏ câu zoom;
  C = "almost still, tiny … less than a tenth". Đo bằng `meta.motion` (không tốn token reviewer), so trung vị % dời và
  số clip ≤ 12 % / ≥ 28 %; thắng thì đưa vào `video_prompt.json` + `redraft`.
- **CEO 2026-10-04 nới ngưỡng máy sau khi xem clip mẫu 11–40 %:** trượt ≤ 35 %, zoom ≤ 1,2×; vật chính trượt ra mép
  theo hướng máy vẫn đạt. Trọng tâm duyệt chuyển sang **"không lộ AI"**: vật tự mọc/biến mất/đổi hình ngay trong khung
  (bụi cây, đèn, đồ đạc…) là lỗi nặng nhất (`morph`). Đã sửa `VIDEO.md` (mục Duyệt), `resource.json`
  (`motion_reject 0.35`, `zoom_reject 1.2`), cổng đo máy; `resq.py reopen` đưa 2 bản cũ nay đạt ngưỡng về review
  (cable-car-05 34 %, christmas-market-06 17 %). Theo dữ liệu đo, ~2/3 clip từng bị `camera-far` nằm trong ngưỡng mới.
- **Lô 8–9 theo ngưỡng mới:** lô 8 đạt 9/12, lô 9 (2 reviewer) đạt 17/24. Lỗi còn lại chủ yếu là "lộ AI" đúng loại CEO
  muốn bắt: người mọc ra (hotel-lobby-07, cafe-07), cảnh ngoài cửa sổ tự đổi (bedroom-11 mọc nhà thờ, bookshop-04 mọc
  xóm đèn), hạt trắng trong phòng. Sửa khuôn: câu cửa sổ thêm "no new buildings, lights, people or trees appear in the
  window view" (áp cho job ghép mới; job đang chờ giữ nguyên để không phá thí nghiệm A/B/C). `resq.py reprompt` nhận cả
  job ở regen để PM thêm câu sửa theo gợi ý reviewer sau `refix` (cafe-07: phố vắng người).
- **Giới hạn cổng đo:** cú đẩy máy vào vật gần (staircase-hallway-06) đo chỉ ×1,16 vì điểm khớp nằm nhiều ở nền xa
  (thị sai); reviewer vẫn bắt được bằng mắt. Chưa sửa motion.py; theo dõi nếu lọt nhiều.
- **Chờ ảnh 900 s → 360 s:** đo 48 ảnh đạt: trung vị 81 s, p95 112 s, chỉ 1 ảnh 655 s. Ảnh kẹt ("Thinking" mãi) thì chạy
  lại từ đầu ra trong ~70 s, nên chờ 15 phút mỗi lần kẹt (≈5 lần/giờ lúc ChatGPT chậm) là phí; 360 s đổi 1/48 ảnh
  chậm lấy ~9 phút tiết kiệm mỗi lần kẹt.
- **Người mọc ra ở cảnh ngoài trời** (`people` 13 lần/giờ, lô 13: town-square, christmas-market, cable-car): khuôn thêm
  câu riêng cho cảnh ngoài trời "Every street, square, path, stall and terrace stays completely empty and deserted…"
  (áp cho job ghép mới và job refix ghép lại; job đang chờ giữ nguyên). Theo dõi tỉ lệ `people` ở các lô sau.
- **Đo máy sai khi tuyết rơi dày** (town-square-tree-05: check báo 3,5 %, mắt thấy ~19 %): điểm ORB bám vào bông tuyết.
  Cổng tự động chỉ chặn khi vượt ngưỡng nên sai số này làm lọt chứ không làm hỏng clip tốt; reviewer vẫn xem bằng mắt.
  Nếu cần: lọc điểm khớp nhỏ/sáng hoặc chỉ đo nửa dưới khung. Chưa sửa.
- **Lỗi lặp theo cảnh:** cảnh có hậu cảnh sâu (lối chợ, nhà nguyện có tượng) hay mọc người/tượng ở lượt 3 → bỏ
  (christmas-market-11, candlelit-chapel-08). Nếu cần thêm clip của các cảnh này: làm lại ảnh với hậu cảnh kín.
- **Câu sửa tay của PM hiệu quả (lô 17: 5/5 lượt 2 sạch lỗi cũ):** đồng hồ giữ trống (train-station-04), lửa giữ màu
  cam + bỏ "glowing embers" (reading-nook-07), tàu tắt máy (toy-train-06), bụi cây tối (snowy-forest-06), câu cửa sổ
  cấm vật mới (bedroom-11). Cách: chèn một câu khóa cụ thể ngay trước câu `{lock}` + đổi hướng trượt. Không cứu được:
  cảnh có mặt trời trong khung (luôn thành timelapse hoàng hôn), quả cầu tuyết (nội dung đổi), tàu đồ chơi chạy, lối
  chợ/nhà nguyện sâu (mọc người/tượng) → giữ lại theme hoặc làm lại ảnh.
- **Chữ "snow" trong trường `window` của ảnh trong nhà** vẫn do reviewer ảnh viết (7 thẻ) dù README cấm; `draft` giờ bỏ
  qua thẻ đó và in "PM sửa trường clip" thay vì dừng cả lô; PM đổi "snow-covered/snowy" → "white-…".

- 12:20 — town-square-tree-07 và -08 hỏng sau 3 lượt (mã people) dù đã có câu phố vắng: quảng trường nhìn xuống đường phố xếp chung nhóm ngõ chợ sâu, không làm clip thêm cho kiểu cảnh này. Câu khóa màu đèn cây ("every bulb … warm white, no blue") và câu hơi nước chỉ từ cốc thêm tay cho bedroom-17 / christmas-morning-12; theo dõi lượt sau.
- 12:12 — cổng ảnh 9223 chết lặng từ 09:58 (thread lỗi, kết quả chỉ in khi generator thoát sau 4 giờ) → mất nửa công suất ảnh ~2 giờ. `images.py work` nay ghi `cổng dừng: …` vào work.log ngay khi một cổng dừng; khởi động lại thì 9223 làm tiếp tree-farm-07 bình thường. PM xem board: job ảnh `sent` > 10 phút = cổng chết.
- 12:30 — dừng theo lệnh CEO (tắt máy). Ảnh 151 đạt, clip 178 đạt / 31 hỏng. Khởi động lại: 2 generator + watch như resource-queue.md; job dở (4 clip + 1 ảnh `sent`) tự làm tiếp; cable-car-15 dừng lúc `sending` → stuck → resolve về input; mỗi lane còn 1 needs_fix chờ PM.

## 2026-10-04 14:55 — reviewer song song đè file tạm
- images-r1440 và videos-r1440 cùng ghi `nx.sh` trong scratchpad chung → một lần claim nhầm job lane kia (front-porch-08). Sửa agent reviewer (Claude + Codex): file tạm chỉ trong thư mục con mang tên reviewer.
- muse 2 lần hỏi lại "Want me to retry?" (lỗi đọc đường dẫn ảnh) → job stuck sau 15 phút, PM trả về input. Nếu lặp thêm: generator tự trả lời thử lại.
- draft báo 3 thẻ trong nhà có "snow" trong `window` → sửa tay trường clip (staircase-hallway-08, gingerbread-village-09, bookshop-10).

## 2026-10-04 15:25 — ảnh ngoài trời "tuyết rơi" mà không có tuyết rơi
- Đo thẻ đã duyệt: cảnh outdoor `tags.snow=falling` chỉ 79/123 (64 %) có `clip.snowfall=true`. Nghi câu chung của khối `lights` ("the air itself is perfectly clear… no specks") triệt luôn tuyết.
- Thử: `blocks.json` thêm `lights_snowing` (bỏ câu không khí sạch, trừ bông tuyết) + `snowing` (tuyết đang rơi rõ khắp khung); `images.py` dùng khi `snow=falling` và `place=outdoor`. Reprompt 19 job outdoor đang chờ. Đo lại tỉ lệ snowfall sau ~20 ảnh; nếu tuyết ra dạng hạt lấp lánh/AI thì bỏ.
- Hai reviewer cùng lane chạy song song vẫn đè file tạm của nhau (định nghĩa agent mới chưa nạp trong phiên) → mỗi lane chỉ một reviewer một lúc.
- christmas-market-10: subject "castle hill" mâu thuẫn câu cấm "no castle on a hill"; ảnh đạt, lâu đài chung chung.

## 2026-10-04 16:40 — kết quả khuôn tuyết rơi ngoài trời
- 13/13 ảnh outdoor dùng khối `snowing` có `snowfall=true` (trước 64 %), cả 13 đạt duyệt, không reviewer nào báo hạt lấp lánh/AI. Giữ khối này.
- Prompt spawn reviewer phải ghi đường dẫn tuyệt đối cho thư mục tạm (đường tương đối làm reviewer tạo `scratchpad/` trong repo).

## 2026-10-04 14:40 — generator chạy code cũ sau khi sửa khuôn
- `images.py work` nạp code + blocks lúc khởi động → job nạp thêm sau khi sửa khuôn vẫn dùng prompt cũ (house-lights-12, front-porch-12 ra không tuyết rơi). Luật: sửa `images.py`/`blocks.json` → khởi động lại generator khi mọi cổng ở `sent` (không `sending`), rồi reprompt job input lệch khuôn (31 job).
- Dừng tiến trình đúng lúc đã tải ảnh, đã xóa chat, chưa submit → cổng báo "không mở được chat" và chết. Kiểm `show` thấy output có trên đĩa → PM `submit` tay rồi khởi động lại generator.
- reading-nook-08 hết 3 lượt (morph lan can) → failed.

## 2026-10-04 16:15 — watermark lần 3
- Ảnh ra dấu mờ kiểu watermark/icon ở góc: front-porch-11, light-festival-12 (redo), reading-nook-13 (đạt, cắt mép). Thêm câu "no watermark, logo, icon or mark in any corner" vào `image.tail` của bộ; reprompt 52 job input; khởi động lại generator (2 cổng đang `sent`, chưa có file).
- bedroom-19 failed sau 3 lượt indoor-particles → note `nosnow`.
- tree-farm-07, ski-village-07: lượt 2 lặp đúng lỗi lượt 1 dù đã có câu khóa (chữ thương hiệu máy kéo; đường trượt/núi biến đổi) → PM fail sớm, không phí lượt 3. Luật: lỗi lặp nguyên dạng sau câu khóa = muse không nghe, fail.
- 2026-10-04 15:30 · ornaments-macro-16 vẫn ra dấu viền xám góc trên phải dù prompt đã có câu cấm watermark chung (giống cafe-15). Sửa từng job bằng câu "4 góc chỉ có bokeh/nền, không viền/biểu tượng". Theo dõi: nếu câu cấm chung không giảm tỉ lệ `format`, thử bỏ nó (có thể đang mồi ý).
- 2026-10-04 15:45 · PM quyết: chân dung sơn dầu treo tường lộ ra trong clip (staircase-hallway-08) vẫn đạt nếu tranh đứng yên, không cử động/biến dạng; chỉ redo khi mặt trong tranh động hoặc méo.
- 2026-10-04 15:50 · Thử nghiệm cửa sổ: muse hay đổi cảnh ngoài kính (mọc nhà/núi/cột đèn, ô kính nở rộng). Mốc trước: 23/520 lượt duyệt bị redo `morph` vì cửa sổ (~4,4 %). Đổi câu window trong video_prompt.json: cảnh ngoài "soft, slightly out-of-focus" + "every window pane keeps exactly the same size and shape". Áp cho job draft từ giờ (47 job input cũ giữ prompt cũ = nhóm đối chứng). Đánh giá sau ~60 lượt duyệt mới.
- 2026-10-04 16:03 · Cổng 9225 dừng (BLOCKED UNAVAILABLE: ChatGPT trả rỗng 3 lần liền ở hotel-lobby-16, 15:52). Restart generator lúc 9223 đang 'sent' → 9225 chạy lại bình thường. Nếu lặp lại thường xuyên: cho generator tự thử lại cổng sau ~10 phút thay vì dừng hẳn.
- 2026-10-04 16:15 · Bỏ câu watermark chung khỏi `image.tail`: tỉ lệ redo vì watermark trước câu ~1,4 % (5/317 lượt duyệt), sau câu ~3,7 % (4/108, thêm gingerbread-15, ice-rink-16 sau đó) → câu không giúp, có thể mồi ý. Reprompt 58 job input bỏ câu; restart generator (2 cổng `sent`). Lỗi watermark lẻ: sửa từng job bằng câu "4 góc chỉ có cảnh". Đánh giá lại sau ~100 lượt duyệt.
- 2026-10-04 16:35 · Watermark tiếp: countryside-day-15 (prompt còn câu cũ, job nhận trước khi reprompt), mountain-cabin-15 (prompt đã bỏ câu). Câu sửa từng job dạng khẳng định "4 góc chỉ có cảnh" đã cứu 4/4 lượt lại (cafe-15, ornaments-macro-16, gingerbread-15, ice-rink-16) — nhưng redo vốn ít lặp nên chưa kết luận. Dấu luôn ở góc phải dưới.
- 2026-10-04 16:53 · Tên reviewer phải chưa từng dùng trong ngày: queue tính lô theo tên, tên trùng (images-r1700a) trả BATCH_DONE ngay. Đặt tên theo giờ thật + hậu tố chữ (vd. images-r1653x).

## 2026-10-04 17:40 — 9225 timeout
Cổng 9225 dừng 16:13 (WebSocketTimeoutException), mất ~1,5 giờ một cổng ảnh vì không có báo động. Khởi động lại generator khi cả hai cổng ở pha sent. Bài học: mỗi lần watch báo sự kiện, xem board có job working nào > 15 phút không.

## 2026-10-04 17:55 — Cả 2 tab ChatGPT treo
Renderer của cả hai tab ChatGPT (9223, 9225) chạy 100% CPU sau ~29 giờ mở liền; JS không trả lời, nên generator ảnh dừng (WebSocketTimeout); 9225 đã dừng từ 16:13. CEO cho phép PM tự reload tab ChatGPT khi treo. Bài học: khi watch báo sự kiện, xem job working > 15 phút; reload tab ChatGPT định kỳ ~12 giờ.

## 2026-10-04 18:30 — ChatGPT chậm, chờ ảnh 360 → 600 s
Hôm nay 9 lần "360 s chưa có ảnh → stuck". 2 lần PM reconcile thì ảnh đều đã có trong chat (ornaments-macro-19, snow-globes-17), nghĩa là ChatGPT chỉ chậm. Nâng wait_image lên 600 s để bớt stuck và bớt phải dừng generator. Cách gỡ stuck: dừng generator lúc mọi cổng ở pha sent, chạy images.py reconcile, rồi chạy lại. Chat không tồn tại (mở chat thì bị đưa về trang chủ) nghĩa là không có ảnh; khi đó đánh dấu stuck rồi resolve về regen. Cũng hôm nay, cả 2 tab ChatGPT treo sau ~29 giờ; CEO cho PM tự reload.

## 2026-10-04 19:58 — 9223 treo lại sau ~2 giờ
- Renderer 9223 lại lên ~80 % CPU chỉ ~2 giờ sau lần reload trước → kill + navigate. Không phải chỉ do tab mở lâu; theo dõi thêm, nếu lặp lại < 3 giờ thì reload định kỳ mỗi ~2 giờ lúc cả hai cổng ở `sent`.
- candlelit-chapel-20 (9225, 600 s không ảnh): reconcile NotSent dù tab bình thường → resolve regen.
- Lô video r1945a: 6/12 đạt; 3 lỗi people/morph đều ở cảnh có điểm tụ xa + slide dài → để ý trong lô sau trước khi đổi khuôn.

## 2026-10-04 21:00 — dừng ca (CEO)
- Dừng 2 generator lúc 21:00. 9225 chạm QUOTA lúc 20:57 (giới hạn tạo ảnh của tài khoản). 2 ảnh dở trên 9223 lấy về bằng reconcile trước khi dọn chat.
- Còn lại cho ca sau: ảnh review 48 (chưa duyệt); video review 17, needs_fix 6, working 4 (tự làm tiếp khi chạy lại).
- Dọn chat ChatGPT (tài khoản dùng chung): chỉ xoá chat có tin nhắn đầu = prompt mẫu của mình; API đọc chat bị 429 nếu gọi nhanh → đọc cách 3 s.

## 2026-10-04 21:40 — CEO: đẹp hơn hoàn hảo
- Không thêm luật né khung nhìn xa (phố, hành lang, cửa kính); giữ sáng tạo.
- Cảnh rất đẹp được giữ 1–2 sạn nhỏ (vd. người tí hon ở xa, khó thấy) → đạt kèm note. Vẫn redo lỗi AI lộ rõ (hiện ra/biến mất rõ, biến hình).
- Ca sau: cập nhật chuẩn reviewer theo hướng này; soi lại các clip đã fail vì `people` để vớt cảnh đẹp.

## 2026-10-05 08:08 — thử 3 tab muse mỗi cổng (CEO)
- CEO: hôm nay chỉ làm clip để đuổi kịp ảnh (563 ảnh đạt / 392 clip đạt); lane ảnh nghỉ.
- Mở thêm 1 tab muse.ai ở 9224 và 9226 → 6 slot (script đã coi mỗi tab là một slot, không sửa code).
- Đo: clip nộp/giờ so với ca 2 tab, tỉ lệ "Delivery not confirmed"/quá hạn có tăng không.
- VIDEO.md thêm mục "Đẹp hơn hoàn hảo" cho reviewer.
- 08:40 — sunroom-16: muse đóng logo kiểu watermark đứng yên ở góc trên phải (mã text); lượt 2 thêm câu cấm logo/watermark; VIDEO.md thêm dòng này vào mục text.
- 08:35 — sunroom-16 fail: watermark nằm sẵn trong ảnh nguồn (chìm trong cành cây), muse làm rõ lên; ghi vào danh sách tạo lại ảnh khi lane ảnh chạy lại.
- 09:04 — đo 3 tab/cổng (6 slot, 55 phút): 125 clip nộp ≈ 136/giờ, so với ca 4 slot hôm qua 08–11h 256 clip/2,94 h ≈ 87/giờ (×1,56). Thời gian một clip không đổi (trung vị 1,8 vs 1,7 phút, p75 3,0 vs 2,7) → muse chạy song song thật; trả queue 1 lần. Lên 4 tab/cổng (8 slot), restart generator (job sent được nhận lại). Reviewer thành nút cổ chai: chạy 3 reviewer song song.
- Kho cảnh có trường clip còn 137 (+49 job input) → với tốc độ này hết sau ~2 giờ; 48 ảnh chờ review sẽ thêm cảnh.
- 09:04–09:50 — 4 tab/cổng HỎNG: 39 phút chỉ 3 clip, 85 'Delivery not confirmed' + 8 quá hạn (generator tự gửi lại → mỗi lần một side chat mới). muse nhận tin nhưng không trả lời, cả tab cũ. Nghi muse giới hạn ~6 việc song song/tài khoản rồi nghẽn vì hàng trăm yêu cầu dồn. 09:44 quay về 6 tab bằng --page-id; muse vẫn im → 09:52 dừng generator chờ muse xả hàng.
- 10:05–10:14 — chạy lại 6 tab: muse vẫn không trả lời, generator gửi lại mỗi ~70 s (Delivery not confirmed). Dừng hẳn, chờ CEO kiểm tài khoản muse. Bài học: generator không có phanh khi muse im: nhiều 'Delivery not confirmed' liên tiếp phải tự dừng thay vì gửi lại.
- 10:20 — phanh mới chạy đúng (dừng sau 6 lần). Muse báo 'Message failed to send' + 'Couldn't load this activity feed', danh sách side chat không tải: lỗi phía muse/tài khoản, không phải do số tab. Chờ CEO kiểm.
- 2026-10-05 10:42 muse hồi lại sau ~1 giờ nghẽn (3 tab/cổng, giữ proxy): 9226 trả 3 clip ngay lượt thử 2; 2 job quá 15 phút lúc nghẽn → regen. Proxy không phải nguyên nhân (sáng nay cùng proxy vẫn ~136 clip/h); nguyên nhân là tab thứ 4.
- 2026-10-05 11:40–12:10 — buổi trưa, 3 tab/cổng, giữ proxy: muse vẫn yếu, 10 clip trong 12 phút sau lần chạy lại 11:58 (~50/h, sáng ~136/h), nhiều 'Delivery not confirmed'; phanh dừng 1 lần lúc 11:43. Thử tắt proxy ở 9226 bị chặn quyền, CEO hoãn.
- 2026-10-05 11:58–12:41 — vẫn yếu: 15 clip / 43 phút (~21/h tính cả 15 phút phanh 12:17–12:32), 6 timeout, 8 undelivered. Cùng cấu hình sáng (~136/h) → muse/tài khoản đang bị bóp sau đợt 4 tab, chưa hồi.
- 2026-10-05 12:40–12:59 — muse gần như ngừng: 0 clip, 6 tab đều quá hạn. PM tạm nghỉ generator 45 phút (13:00→13:45) để tài khoản hồi, rồi chạy lại cùng cấu hình.
- 2026-10-05 13:04–13:07 — CEO cho tắt proxy (giữ cookie): 9226 không proxy trả clip mới sau ~1,5 phút, 9224 còn proxy cùng lúc toàn 'Delivery not confirmed' → proxy là nút nghẽn buổi trưa. 13:09 chuyển cả 2 cổng sang không proxy (IP VN thật), muse vẫn đăng nhập.
- 2026-10-05 13:15 — PM bỏ chữ snow khỏi trường clip 'window' của 28 thẻ cảnh trong nhà (draft từ chối) → snowy/snow = white/white frost.
- 2026-10-05 13:25 — reviewer: máy tiến sâu vào cảnh (snowy-forest-16 bay qua cổng) mà số đo chỉ 4% / ×1.05 → cổng tự động bỏ sót kiểu drift-forward sâu; reviewer vẫn bắt bằng mắt. Ứng viên cải tiến đo sau lô.
- 2026-10-05 13:09–13:39 — cả 2 cổng không proxy: 68 clip / 30 phút (~136/h, bằng sáng). 9226: 54, 9224: 14 (tab 899940CD chậm, 3 quá hạn) — theo dõi tiếp.
- 2026-10-05 15:32–16:05 · Bỏ giữ ballroom + snow-globes (CEO duyệt), chạy 23 cảnh với khuôn prompt hiện tại (slide, fixed lens, cổng đo tự động, refix): đạt 20/23 (ballroom 9/10, snow-globes 11/13); lượt 1 đạt 14/23. Hỏng: ballroom-20 đẩy vào 3 lượt; snow-globes-09 tàu trong cầu đổi hình; snow-globes-15 ghế cáp treo mô hình mọc người 2 lượt. Tỉ lệ thấp cũ (2/12, 1/6) là của khuôn arc/drift cũ → luật giữ đề tài cần tính lại theo khuôn hiện tại, không cộng dồn lượt cũ.

## 2026-10-06 — CEO: xong hết ảnh + clip trong sáng
- Lane ảnh: 616 đạt, 0 tồn. Vẽ lại 7 cảnh nhóm 3 (thêm câu cấm watermark/logo góc khung) và 10 cảnh còn thiếu; countryside-day-20 vá watermark bằng PIL.
- Lane clip: 775 đạt, 30 bỏ, 0 tồn. Làm lại các cảnh fail có giá trị bằng cách lưu job cũ vào archive/ + xóa video.status ở thẻ + draft lại.
- Câu máy: "almost still" không ổn định (muse vẫn đẩy vào ×1.24–1.45 hoặc đứng im); câu pull-back lúc đầu đạt 2/2 rồi lùi quá 4/6 (×0.47–0.78) → bỏ. Dùng slide ngắn + "same distance, never closer, never back, never zooms, framing never tighter or wider"; lặp lỗi thì đảo hướng + câu khóa cỡ vật.
- Cổng đo tự động bỏ sót máy tiến thẳng tâm, lùi xa và xoay (steam-train-12, christmas-market-10, ballroom-08, cafe-06, ornaments-macro-05); reviewer bắt bằng mắt (cỡ vật chính đầu/cuối). Ứng viên cải tiến: đo tỉ lệ cỡ vật/scale thay vì chỉ dời khung.
- Fail sớm khi một lỗi lặp lần 3 (tính cả khuôn cũ). Lỗi muse không sửa được bằng prompt: người ở phố/quầy nhìn sâu (cafe, christmas-market, ice-rink), hạt tuyết trong tiệm có cửa mở ra phố (bookshop), chữ trên máy kéo/cabin, trời đổi hoàng hôn hồng (ski-village) → cần đổi ảnh nguồn, không sửa prompt tiếp.
