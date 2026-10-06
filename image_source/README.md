# image_source: kho cảnh Giáng sinh (ảnh → video 10 s)

Kho clip 10 giây để ghép video Giáng sinh dài 2–3 tiếng (nhạc PD / không lời làm ở `research/christmas-carols/`).
Mỗi cảnh: **ChatGPT tạo ảnh** từ prompt ghép sẵn → **muse.ai animate** ảnh đó thành clip 10 s → Claude chọn và ghép clip
thành video. Người không ngồi chọn clip: mọi thông tin để chọn nằm trong file.

Đích: **48 đề tài × 20 cảnh = 960 clip** + bộ riêng **cozy-loop 50 cảnh** (video loop 1–2 tiếng cho nhạc không lời).
 
## Cấu trúc

```
image_source/
├── README.md              # file này: cách dùng, luật viết cảnh
├── blocks.json            # các khối câu dùng chung để ghép prompt ảnh + prompt video
└── <nhóm vibe>/           # home, village, nature, magic, grand, travel, detail, cozy-loop
    ├── README.md          # nhóm là gì, bảng màu, ghép với nhóm nào, danh sách đề tài
    └── <đề tài>/
        ├── README.md      # đề tài là gì, vibe, máy quay, ghép cùng
        ├── shots.json     # mặc định của đề tài + danh sách cảnh (git)
        ├── <id>.png       # ảnh ChatGPT (chỉ trên máy)
        ├── <id>.json      # thẻ cảnh: tags, prompt ảnh đã dùng, prompt video, file video (chỉ trên máy)
        └── <id>.mp4       # clip muse.ai 10 s (chỉ trên máy)
```

Git chỉ giữ `README.md`, `blocks.json`, `shots.json`; ảnh, thẻ cảnh, video nằm trên máy (`.gitignore`).

## Làm

Bộ này là một *resource set*: `resource.json` khai báo luật, hai skill dùng chung đọc nó và chạy queue.

| Việc | Skill / lệnh (chạy từ gốc repo) |
|---|---|
| Quy trình, vai, vòng PM | `.claude/skills/pm-production/references/resource-queue.md` |
| Tạo ảnh (ChatGPT) | skill `video-resource-images`: `images.py fill image_source`, `images.py work …` |
| Tạo clip (muse.ai) | skill `video-resource-videos`: `videos.py candidates image_source`, `videos.py add …`, `videos.py work …` |
| Bảng queue, duyệt, làm lại | `pm-production/scripts/resq.py board`, `next-review`, `verdict`, `requeue` |
| Luật prompt + duyệt video | `VIDEO.md` |

Ảnh đạt → `<id>.png` + thẻ `image` / `qc: ok`; clip đạt → `<id>.mp4` + thẻ `video` (`status: ok`, `trim`, `tries`).
Bản thử `<id>.tryN.png|mp4` nằm cạnh đó tới khi job xong (đạt hoặc hỏng) rồi tự xóa: chỉ giữ bản cuối.

## Duyệt ảnh (bắt buộc trước khi sang muse)

Mọi ảnh ChatGPT trả về đều `qc: pending`. Claude mở từng ảnh, so với `subject` của cảnh + README đề tài, rồi `qc ok` hoặc
`qc redo` kèm lý do. Chỉ ảnh `ok` mới được animate và ghép. Thà ít ảnh mà dùng được còn hơn nhiều ảnh rác.

**Loại (`redo`) khi có một trong các lỗi:**

1. Có người, bóng người, tay, hoặc con vật thật (tượng, hình in trên gối thì được).
2. Có chữ, số, logo đọc được, kể cả chữ giả, mặt đồng hồ có số, biển hiệu có chữ.
3. Lỗi vật lý: đồ vật dính/xuyên nhau, đèn hay đồ treo lơ lửng, kiến trúc vô lý (cầu thang, cửa sổ, mái), đồ nội thất méo, lửa
   cháy ngoài lò, tuyết rơi trong nhà, cáp/dây không nối vào đâu.
4. Thiếu thứ chuyển động của cảnh (`motion_elements`); với cozy-loop: thiếu hoặc che mất một trong bốn thứ (lửa, cây đèn, khói cốc,
   tuyết ngoài cửa).
5. Sai brief: không đúng `subject` (thiếu vật chính, sai nơi chốn), sai ánh sáng của đề tài (`look`: tối, đục, cháy sáng), lệch hẳn
   bảng màu của nhóm, không có không khí Giáng sinh.
6. Không giống ảnh chụp thật: kiểu tranh vẽ, 3D rẻ tiền, nhựa bóng, màu gắt quá mức, mờ, nhiễu.
7. Collage, lưới, khung chia, viền, watermark; cỡ < 1600 px hoặc không phải 16:9 (worker ghi `warnings` vào job).
8. Gần trùng một ảnh đã `ok` trong cùng đề tài (cùng bố cục + cùng vật chính); nhất là khi nhiều ảnh cùng một chat.

**Chấp nhận:** lỗi nhỏ ở góc/mép mà khi xem video không ai để ý (một quả châu lệch, vân gỗ lặp), miễn vật chính và vùng
chuyển động sạch. Ghi lỗi nhỏ vào `--note` để lúc ghép tránh cắt cận vùng đó.

**Khi cho đạt:** ghi luôn trường `clip` cho bước video (`--card '{"clip": {…}}'`, mục *Trường clip* trong `VIDEO.md`); queue
từ chối `ok` thiếu trường này. Ảnh chỉ được xem một lần: prompt clip ghép từ trường này, không ai mở lại ảnh.

Bước video (muse.ai): luật viết prompt và duyệt clip ở `VIDEO.md`.

## Prompt

Prompt = các khối trong `blocks.json` + trường của cảnh (trường cảnh ghi đè `defaults` của đề tài):

- **Ảnh:** `head` + `subject` + `composition` + `realism` (ống kính `lens`) + `look` + `lights` + `motion_ready` (`motion_elements`) + `clean` + `tail`.
- **Video (cảnh có `motion`, cách mới, đã thử):** `motion_frame.static` (`place_name`) + mỗi vật trong `motion` theo thứ tự
  (`blocks.json` → `video.motion`, chỗ `{where}` lấy từ `motion_where` của cảnh, không có thì mặc định của vật) +
  `motion_frame.hold` + `motion_frame.exposure` + `motion_frame.sound[sound]`. Không có `head`: lời dặn image-to-video nằm
  trong tin nhắn gửi Muse (skill `video-resource-videos`).
- **Video (cảnh chưa chuyển, cách cũ, chưa thử đạt):** `head` (`seconds`) + `camera` (`focus`) + `out_and_back` (trừ `static`) +
  `ambient` + `anchored`/`static_only` + `lights_motion` + `snow` (chỉ `tags.snow` = `falling`) + `tail`.
- `look`: `interior-bright`, `interior-evening`, `twilight`, `night-lights`, `winter-day`, `golden`.
- `camera`: `static`, `push-in`, `pull-out`, `slide`, `arc`, `crane-up`, `drone`, `tilt-up`. **Out-and-back**: đi nửa đầu, quay về
  nửa sau, khung cuối = khung đầu, nên một clip phát 2 lần liền nhau không thấy vết nối.

### Vật chuyển động (`video.motion`): câu nào dùng, câu nào tránh

Mỗi vật một câu đã thử trên muse, đo bằng `muse_qc.py` (skill). Cảnh có vật nào thì thêm key đó vào `motion`.
Vật mới: thử ≥ 2 lượt cùng prompt, đạt cả 2 mới thêm vào `blocks.json`.

| Key | Dùng | Tránh (đã hỏng) |
|---|---|---|
| `fire` | lửa "burns with gentle dancing flames and glowing embers" | — |
| `candles` | "The small candle flames {where} flicker softly", kể chỗ có nến | không kể nến → nến gần như đứng yên |
| `mug-steam` | "a very faint, thin wisp … just above the {mug}" | "thin wisp rises and drifts away" → cột khói to trôi qua cây |
| `tree-lights` | "stay switched on the whole time and shimmer gently, all in the same warm white color as in the first frame" | "each bulb fading in and out / brightening and dimming" → đèn tắt dần hoặc đổi xanh đỏ |
| `window-view` | "The view through the windows stays the same {where} as in the first frame, with no new buildings or objects appearing" | thiếu câu này → đôi khi mọc nhà mới ngoài cửa |

- **Tuyết ngoài cửa sổ: không viết chữ nào về tuyết** (`snow`, `snowflakes`, `falling snow`). Ảnh có tuyết ngoài kính thì muse
  tự cho tuyết đó rơi, chỉ sau kính. Nhắc tới tuyết dưới mọi dạng (phủ định "never inside", tả "behind the glass, far away")
  → tuyết rơi cả trong phòng. Muốn cảnh ngoài cửa đứng yên hẳn thì prompt cũng không đủ (muse vẫn cho tuyết rơi):
  dùng `window_snow.py --freeze-window` (skill).
- Tuyết rơi ngoài trời trong cảnh ngoài trời (`tags.snow = falling`): chưa thử.
- Độ sáng khác nhau giữa các lượt cùng prompt; câu `exposure` không bảo đảm. Chọn lượt bằng số đo, không bằng prompt.
- Chỉ nói điều cần có; câu phủ định chỉ dùng cho vật không liên quan tới chuyển động ("no new buildings").

### Viết một cảnh (`subject`)

- Một câu cụ thể tiếng Anh: nơi chốn + 3–5 vật chính + nhìn ra đâu + nguồn sáng. Không viết lại những gì `blocks.json` đã nói.
- Phải có **thứ chuyển động được**: đèn, tuyết, lửa, nến, hơi nước, mặt nước, khói. Cảnh không có gì động = clip chết.
  Thứ động nên có sẵn key trong `video.motion`; chưa có thì thêm key theo luật ở mục trên.
- Không người, không con vật (video AI làm méo), không chữ đọc được, không thương hiệu, không địa danh thật nổi tiếng.
- 20 cảnh trong một đề tài phải khác nhau thật: kiểu nơi chốn, góc (~8 toàn, ~8 trung, ~4 cận), màu trong bảng màu của nhóm, vật chính.

## Thẻ cảnh (tags) để ghép

| Tag | Giá trị |
|---|---|
| `place` | `indoor`, `outdoor` |
| `time` | `day`, `golden`, `evening`, `twilight`, `night` |
| `palette` | `warm-gold`, `red-green`, `white-gold`, `cool-blue` |
| `scale` | `macro`, `room`, `street`, `vista` |
| `snow` | `falling` (tuyết rơi trong khung), `window` (tuyết ngoài cửa sổ), `lying` (tuyết nằm), `none` |
| `energy` | `still`, `calm`, `lively` |

Tag mặc định ở `defaults.tags` của đề tài, cảnh ghi đè khi khác (vd. một cảnh ban ngày trong đề tài ban đêm).

## Ghép video (Claude chọn)

Luật chọn cast, xếp thứ tự, lặp và lật clip cho video nhạc dài: [MONTAGE.md](MONTAGE.md).

## Nhóm và đề tài

| Nhóm | Là gì | Đề tài |
|---|---|---|
| [home](home/README.md) | Các phòng trong nhà, vàng ấm | 13 |
| [village](village/README.md) | Phố, chợ, cửa hàng lúc chạng vạng/đêm | 10 |
| [nature](nature/README.md) | Rừng, hồ, núi, vườn, trang trại tuyết | 8 |
| [magic](magic/README.md) | Xưởng Santa, Bắc Cực, mô hình, lễ hội ánh sáng | 6 |
| [grand](grand/README.md) | Sảnh khách sạn, phòng khiêu vũ, nhà nguyện, trang viên | 5 |
| [travel](travel/README.md) | Cáp treo, tàu hơi nước, làng trượt tuyết, cảng | 4 |
| [detail](detail/README.md) | Cận cảnh: cầu nối giữa các đề tài | 2 |
| [cozy-loop](cozy-loop/README.md) | Phòng khách lò sưởi đứng yên, loop 1–2 tiếng | 1 (50 cảnh) |
