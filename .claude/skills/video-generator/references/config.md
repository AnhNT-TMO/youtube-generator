# Tham số config của video-generator

Config là JSON, chỉ ghi **những gì khác lớp dưới**. Mặc định đầy đủ và chú thích
từng tham số nằm trong `DEFAULTS` ở [scripts/config.py](../scripts/config.py). Chia việc giữa các lớp:

- **Mặc định của tool:** bố cục chung (logo trên phải, subscribe dưới phải, lịch hiện,
  sóng nhạc, intro, loop 5 phút). Muốn đổi cho mọi channel thì sửa ở đây.
- **`channel/<tên>/video.json`:** phong cách channel, ví dụ [lamplight_gospel](../../../../channel/lamplight_gospel/video.json).
  [`example_snow.json`](example_snow.json) là ví dụ phong cách khác (ánh sáng lạnh, tuyết trắng rơi chéo, sóng nhạc trắng).
- **`<idea/album>/video.json`:** phần phụ thuộc ảnh, ví dụ [album 001](../../../../channel/lamplight_gospel/albums/001-when-the-night-is-long/video.json).

`particles` gộp theo vị trí: `"particles": [{"lanes": [0.3, 1.02]}]` chỉ chỉnh lớp
hạt đầu tiên của channel. Thêm phần tử để thêm lớp; `"enabled": false` để bỏ một lớp.

Màu viết `[R, G, B]` 0–255. Vị trí là tỉ lệ khung hình (0 = trái/trên, 1 = phải/dưới);
tham số có đuôi `_px` tính bằng pixel.

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
| `from` | Hướng bay tới, 8 hướng: `top`, `top-right`, `right`, `bottom-right`, `bottom`, `bottom-left`, `left`, `top-left` |
| `count` | Số hạt |
| `shape` | `dot` (chấm mềm) hoặc `flake` (bông tuyết 6 cánh, rõ khi bán kính ≥ 4px) |
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

## `subscribe`

`every_seconds`: khoảng cách giữa hai lần hiện. Ghi một số (vd. `40`) để cách đều,
hoặc `[30, 45]` (mặc định) để mỗi khoảng là một số ngẫu nhiên trong 30–45 giây, cố
định theo `seed` để người xem không đoán được nhịp. Tổng các khoảng vừa khít 5 phút
nên lịch vẫn liền mạch khi loop được nhân bản. `first_at` (mặc định 20) là lần hiện
đầu tiên, để không che 10–15 giây mở đầu (CLAUDE.md mục 3). Muốn tự đặt mốc thì
dùng `at_seconds`, vd. `[20, 170]`. `make_loop.py` in ra lịch thực tế khi chạy.
Còn có `show_seconds` (mỗi lần hiện bao lâu, mặc định 11), `height_px`, `corner`,
`margin_px`, `label`, `label_done`.

## `intro`: intro logo ở đầu video

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

⚠️ Theo CLAUDE.md mục 3, 10–15 giây đầu quyết định người xem có ở lại không. Intro
dời khoảnh khắc thấy ảnh thật đi khoảng 3 giây (nhạc thì không bị dời). Nên so
retention tại 0:15 / 0:30 giữa video có và không có intro.

Nếu ghép `--no-bars` (nối không nén lại), intro phải được nén bằng cùng bộ nén với
loop. `make_loop.py` làm việc đó tự động vì render cả hai trong cùng một lệnh.

## `bars`: dải sóng nhạc (dùng ở `extend.py`)

`center`, `span`, `height_px`, `baseline_px`, `bands`, `bar_width`, `color_tip`, `color_base`,
`opacity`, `glow_px`, `glow_color`, `glow_strength`, `scrim` (bóng tối dưới dải),
`attack`/`release` (tốc độ vọt lên/rơi xuống).

## Chung

`loop_seconds` (300), `fps` (30), `encode` (`encoder`, `crf`, `preset`, `grain`, `gop_seconds`,
`nvenc_preset`, `nvenc_cq`, `vt_bitrate`).
`loop_seconds` nên chia hết cho `gop_seconds` để `extend.py` cắt đoạn đúng keyframe.

