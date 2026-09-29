# Tham số config của video-generator

Config là JSON, chỉ ghi **những gì khác lớp dưới**. Mặc định đầy đủ và chú thích
từng tham số nằm trong `DEFAULTS` ở [scripts/config.py](../scripts/config.py). Chia việc giữa các lớp:

- **Mặc định của tool:** bố cục chung (logo trên phải, subscribe dưới phải, lịch hiện,
  sóng nhạc, intro, loop 5 phút). Muốn đổi cho mọi channel thì sửa ở đây.
- **`channel/<tên>/video.json`:** phong cách channel, ví dụ `channel/<tên>/video.json` của một kênh đang chạy.
  [`example_snow.json`](example_snow.json) là ví dụ phong cách khác (ánh sáng lạnh, tuyết trắng rơi chéo, sóng nhạc trắng).
- **`<album>/video.json`, `<album>/short/video.json`:** phần phụ thuộc ảnh, ví dụ `channel/<tên>/albums/<NNN-slug>/video.json`.

`particles` gộp theo vị trí: `"particles": [{"lanes": [0.3, 1.02]}]` chỉ chỉnh lớp
hạt đầu tiên của channel. Thêm phần tử để thêm lớp; `"enabled": false` để bỏ một lớp.

Màu viết `[R, G, B]` 0–255. Vị trí là tỉ lệ khung hình (0 = trái/trên, 1 = phải/dưới);
tham số có đuôi `_px` tính bằng pixel **của khung 1920×1080**; video ra 3840×2160 (`config.py` `W, H`) và `config.load()`
nhân mọi `_px` với `PX_SCALE` (= 2), nên các `video.json` cũ vẫn đúng tỉ lệ.

## `light`: ánh sáng thở

| Khoá | Ý nghĩa |
|---|---|
| `shapes` | Danh sách vùng sáng: đa giác `[[x,y],...]` và/hoặc elip `{"ellipse":[cx,cy,rx,ry]}`. Tất cả dùng chung một nhịp thở |
| `blur_px` | Độ nhoè mép vùng sáng |
| `color` | Màu ánh sáng (vàng ấm `[255,231,178]`, trắng lạnh `[235,242,255]`...) |
| `floor`, `amount` | Lượng màu lúc tối nhất, và lượng thêm vào lúc sáng nhất (0–1) |
| `base`, `waves` | Nhịp thở = `base + Σ amp·sin(2πt/period + phase)`. Thêm/bớt sóng tuỳ ý |
| `enabled` | `false` để tắt |

## `lantern`: lửa rung (tuỳ chọn)

Cho ảnh có đèn, nến, lửa: `center`, `radius`, `color`, `strength`, `waves` (nhịp nhanh).

## `particles`: bụi / tuyết, nhiều lớp

`particles` là **danh sách**, mỗi phần tử là một lớp riêng. Ví dụ: một lớp hạt nhỏ
ở xa và một lớp bông tuyết to ở gần.

| Khoá | Ý nghĩa |
|---|---|
| `from` | Hướng bay tới, 8 hướng: `top`, `top-right`, `right`, `bottom-right`, `bottom`, `bottom-left`, `left`, `top-left`; `none` = đứng yên tại chỗ (sao lấp lánh; `lanes` giới hạn chiều cao) |
| `count` | Số hạt |
| `shape` | `dot` (chấm mềm), `flake` (bông tuyết 6 cánh, rõ khi bán kính ≥ 4px), `star` (sao 4 tia, dùng với `twinkle_depth` 1 để ẩn hiện), `bokeh` (đĩa mềm to, mờ) |
| `color`, `intensity`, `far_intensity` | Màu, độ sáng hạt gần nhất, và độ sáng hạt xa nhất (tỉ lệ so với hạt gần) |
| `size_px`, `size_curve` | Khoảng bán kính xa → gần; `size_curve` > 1 thì đa số hạt nhỏ |
| `cross_seconds`, `speed_jitter` | Thời gian bay qua màn hình (trên→dưới hoặc trái→phải); độ chênh tốc độ giữa các hạt |
| `parallax` | 0–1: hạt gần bay nhanh hơn hạt xa, tạo chiều sâu |
| `sway_px`, `sway_seconds` | Độ lắc ngang và chu kỳ lắc |
| `twinkle_seconds`, `twinkle_depth` | Chu kỳ lung linh; 0 = sáng đều, 1 = tắt hẳn rồi sáng lại |
| `lanes`, `lane_share` | Chỉ cho hướng thẳng: dồn phần lớn hạt vào một dải, vd. `[0.30, 1.02]` |
| `seed` | Đổi để có bố cục hạt khác |

## `logo`

`path` (tương đối từ gốc repo, channel đặt thành `channel/<tên>/image_source/logo.png`), `width_px`, `corner` (`tl`/`tr`/`bl`/`br`), `margin_px`, `opacity`, `shadow`.
Logo được nung sẵn vào ảnh nền nên không tốn thời gian render.

## `badge`: ảnh nhỏ thứ hai (tuỳ chọn)

Một ảnh tĩnh nhỏ khác logo, vd. huy hiệu thể loại ở góc dưới trái trong thanh chữ đáy. Cùng khoá và cách đặt như `logo`:
`enabled` (mặc định `false`), `path` (tương đối từ gốc repo; đặt trong `channel/<tên>/image_source/`, vì chỉ thư mục đó được
đồng bộ lên server), `width_px` (150), `corner` (`bl`), `margin_px` (30), `opacity`, `shadow` (mặc định không có; vd.
`{"radius": 18, "spread": 0.42}`). Khi bật: nung vào ảnh nền (chế độ thường), nằm trên lớp phủ khóa màn hình cùng logo
(cinema), và `thumb_logo.py` in cả logo + badge lên `thumbnail.jpg` ở đúng chỗ đó. Shorts luôn tắt badge.
Kênh cho ChatGPT vẽ huy hiệu thẳng vào ảnh (`visual.md` của kênh) thì đặt `badge.enabled: false`: huy hiệu đã có trong ảnh nền
video lẫn `thumbnail.jpg`, code không in thêm lần nữa.

## `subscribe`

`every_seconds`: khoảng cách giữa hai lần hiện. Ghi một số (vd. `40`) để cách đều,
hoặc `[30, 45]` (mặc định) để mỗi khoảng là một số ngẫu nhiên trong 30–45 giây, cố
định theo `seed` để người xem không đoán được nhịp. Tổng các khoảng vừa khít 5 phút
nên lịch vẫn liền mạch khi loop được nhân bản. `first_at` (mặc định 20) là lần hiện
đầu tiên, để không che 10–15 giây mở đầu (CLAUDE.md). Muốn tự đặt mốc thì
dùng `at_seconds`, vd. `[20, 170]`. `make_loop.py` in ra lịch thực tế khi chạy.
Còn có `show_seconds` (mỗi lần hiện bao lâu, mặc định 11), `height_px`, `corner`,
`margin_px`, `label`, `label_done`.

## `intro`: intro logo ở đầu video

`flame` (true): đốm lửa sáng lên trên logo (logo có ngọn lửa); logo khác thì `false`. Intro ngắn: `seconds` 3.5 + `fade_in_seconds` 0.5 + `crossfade_seconds` 1.0 + `shine_at` 0.7; nền mờ nhẹ `bg_blur_px` ~9, `bg_dim` ~0.7.

Đầu mỗi video: logo hiện dần và phóng nhẹ ra giữa màn hình, trên nền là chính ảnh
làm mờ và tối đi (bụi vẫn bay). Quầng sáng vàng thở sau logo, ngọn lửa sáng lên,
một vệt sáng quét qua. Sau đó logo mờ dần trong khi ảnh thật hiện lên. Khung cuối
của intro chảy thẳng vào khung đầu của loop. Nhạc vẫn bắt đầu từ giây 0, và dải
sóng hiện dần cùng ảnh.

`make_loop.py` render intro thành `<loop>_intro.mp4`; `extend.py` tự lấy file đó.
Chỉnh intro mà không cần render lại loop: `scripts/make_loop.py ... --intro-only` (xem internals.md).
Tắt: `"intro": {"enabled": false}` hoặc `extend.py --no-intro`.

| Khoá | Ý nghĩa |
|---|---|
| `seconds` | Độ dài intro (mặc định 4) |
| `fade_in_seconds`, `crossfade_seconds` | Thời gian logo hiện ra; thời gian logo mờ đi và ảnh hiện lên |
| `logo_width_px` | Cỡ logo giữa màn hình |
| `bg_blur_px`, `bg_dim` | Nền: độ mờ và độ tối của ảnh phía sau logo |
| `halo_color`, `halo_strength` | Quầng sáng sau logo |
| `shine_at` | Lúc vệt sáng bắt đầu quét qua logo (giây) |

⚠️ Theo CLAUDE.md, 10–15 giây đầu quyết định người xem có ở lại không. Intro
dời khoảnh khắc thấy ảnh thật đi khoảng 3 giây (nhạc thì không bị dời). Nên so
retention tại 0:15 / 0:30 giữa video có và không có intro.

Nếu ghép `--no-bars` (nối không nén lại), intro phải được nén bằng cùng bộ nén với
loop. `make_loop.py` làm việc đó tự động vì render cả hai trong cùng một lệnh.

## `cinema`: camera 2.5D + ánh sáng động (GPU, `cinema.py`)

Bật (`enabled: true`) thì loop không dùng `light` + ảnh cố định nữa mà dựng từng khung trên GPU server: ánh sáng trong không
gian ảnh → camera 2.5D (depth map Depth Anything V2 Small, Apache-2.0, tính một lần và cache `.depth-<hash>.npy` cạnh ảnh) →
vùng khóa màn hình → sương → hạt → lớp tối dưới sóng nhạc + logo → subscribe. Mọi chu kỳ làm tròn để lặp số nguyên lần trong
`loop_seconds` (loop vẫn nối khít). Cần torch + transformers trên server (`requirements-gpu.txt`, `video.py` tự cài).

| Khoá | Ý nghĩa |
|---|---|
| `overscan` | phóng sẵn ảnh để camera không lộ mép (nên ≥ 2·pan·(1+2·parallax)); thiếu thì mép ảnh bị kéo giãn: `video.py qa` đo `edge_smear_px` |
| `parallax`, `focus` | mỗi điểm đi theo camera (pan + zoom) nhân hệ số `1 + 2·parallax·(độ sâu − focus)`; độ sâu 0–1, 1 = gần. Điểm có độ sâu = `focus` đi đúng bằng camera, gần hơn đi nhiều hơn, xa hơn đi ít hơn; `parallax` 0 = phẳng |
| `camera` | `path` (`static`, `push_pull`, `pan_h`, `pan_diag`, `figure8`, `arc`, `drift`), `period` (s), `pan` [x, y] (tỉ lệ khung), `zoom` (biên độ phóng, 0 = không), `zoom_period`, `phase`, `zoom_phase` |
| `text_zones` | các ô [x0, y0, x1, y1] (tỉ lệ) chứa chữ. `text_layer` tắt: depth trong ô làm phẳng nên chữ chỉ trôi nguyên khối, không méo; ánh sáng ×0.15, hạt ×0.25, sương ×0.3 trong ô; riêng đèn `breathing` không né ô chữ (sáng tối cả khung, trừ `static_zones`) |
| `static_zones` | các ô khóa màn hình (thanh chữ dưới đáy…): lấy nguyên ảnh gốc, không camera, không ánh sáng |
| `feather` | độ mềm mép `text_zones` |
| `lights` | danh sách: `breathing` (`amp`, `period`: sáng tối cả khung), `god_rays` (`center`, `angle`°, `spread`°, `length` theo chiều cao, `rays`, `drift_period`), `halo` / `glow` (`center`, `radius` theo chiều cao; `glow` thêm `color2`, `hue_period`), `spotlight` (`center`, `radius`, `path` [ax, ay], `path_period`), `sweep` (`angle`, `width`, `period`, `duty`: một vệt sáng quét qua mỗi chu kỳ). Chung: `strength`, `color`, `period` + `amp` (nhịp thở của đèn) |
| `haze` | sương trôi: `enabled`, `opacity`, `color`, `drift_cycles` (số vòng trôi mỗi loop), `top` (sương dày dần từ độ cao này xuống), `seed` |
| `text_layer` | tách chữ thành lớp riêng: `enabled` (false), `zoom` (biên độ phóng, 0.03), `period` (7 s), `phase`, `keep_above` (1.0; chữ phóng không xuống quá độ cao này, vd. mép trên sóng nhạc); nhận chữ trong `text_zones` bằng `lum_min` (125, độ sáng) + `sat_max` (120; 256 = bỏ điều kiện màu, dùng cho chữ vàng), `halo_px` (11, lấy cả bóng quanh chữ), `feather_px` (4); hai khoá `_px` tính theo 1080p như mọi `_px`. Nền sau chữ được tô lấp, chỉ trong ô chữ; depth trong ô không làm phẳng. Cảnh chạy theo camera còn chữ đứng yên trên màn hình, chỉ phóng nhẹ (tự giảm `zoom` để khung chữ cách mép khung 1 % và nằm trên `keep_above`); mọi đèn kể cả `breathing` nằm dưới lớp chữ, hạt và sương chỉ né đúng con chữ. Không pixel nào trong ô qua ngưỡng thì dừng và báo. Tắt thì chữ đi theo cảnh (depth làm phẳng) |
| `anchors` | (per ảnh) điểm neo tỉ lệ khung, vd. `{"window": [x, y], "cross": [x, y], "head": [x, y]}`; `cinema_pool` gọi bằng `"@window"` |
| `variant` | do `video.py variant` ghi: tên từng trục + seed |

Mẫu đầy đủ cho kênh mới: `references/example_cinema.json`. `video.py qa DIR` (server) đo: `seam_step_ratio` (bước nhảy ở chỗ nối / bước thường, ≤ 2,5),
`text_shape_corr_min` (hình chữ sau khi bù dịch + phóng, ≥ 0,95), `static_zone_diff` (≤ 2), `edge_smear_px` (≤ 2),
`camera_scale_for_text` (≥ 0,8), `luma_step_per_frame` (≤ 3, chống nhấp nháy) → PASS/FAIL, ghi `DIR/video/qa.json`.
`text_layer` tắt: đo hình chữ trên cả ô `text_zones`, `camera_scale_for_text` = phần camera + overscan còn giữ để ô chữ
không ra ngoài khung. `text_layer` bật: đo trên khung bao con chữ, trọng số theo alpha của lớp chữ (nền chạy phía sau
không tính), camera không bị thu nhỏ; `camera_scale_for_text` = phần `zoom` của chữ còn giữ sau khi giới hạn theo mép khung
và `keep_above`. Shorts không dùng cinema (look 9:16 riêng).

`cinema_pool` (trong `channel/<ch>/video.json`, nội dung của kênh): `camera` {tên: khối camera}, `parallax` {tên: số},
`atmosphere` {tên: {`particles`: [...], `haze`: {...}}}, `lighting` {tên: [đèn...]}, `avoid_last` (N). `video.py variant DIR`
chọn một tổ hợp khác mọi tổ hợp đã dùng và khác N video gần nhất của kênh ở ≥ 3/4 trục (nới dần nếu hết), bỏ các bộ đèn cần
điểm neo mà ảnh chưa có, rồi ghi `DIR/video.json` (`cinema.*` + `particles`, seed hạt mới). `--set trục=tên` cố định một trục.

## `bars`: dải sóng nhạc (dùng ở `extend.py`)

`center`, `span`, `height_px`, `baseline_px`, `bands`, `bar_width`, `color_tip`, `color_base`,
`opacity`, `glow_px`, `glow_color`, `glow_strength`, `scrim` (bóng tối dưới dải),
`attack`/`release` (tốc độ vọt lên/rơi xuống).

## Chung

`loop_seconds` (300), `fps` (30), `encode` (`encoder`, `crf`, `preset`, `grain`, `gop_seconds`,
`nvenc_preset`, `nvenc_cq`, `vt_bitrate`).
`loop_seconds` nên chia hết cho `gop_seconds` để `extend.py` cắt đoạn đúng keyframe.

