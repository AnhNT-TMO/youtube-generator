# video-generator: cách hoạt động bên trong

Viết lại từ `~/Desktop/lamblight_channel/tools/` (tool cũ dựng từng khung cho cả album, ~20 phút). Bản này render **một loop 5 phút nối khít** rồi nhân bản.

## Cách hoạt động

```
ảnh + preset ──make_loop.py──▶ loop.mp4 (5 phút, chỉ hình, nối khít)
                           └──▶ loop_intro.mp4 (4 giây intro logo)
                                 │
loop + intro + nhạc ──extend.py──▶ video full: intro → nhân bản loop, + dải sóng nhạc + audio
```

- **Nối khít:** mọi chuyển động tính theo pha vòng lặp và lặp **số nguyên lần
  trong 5 phút**. Chu kỳ khai báo trong config được làm tròn cho khớp, vd. nhịp
  sáng 7.3s → 300/41 = 7.317s. Hạt bay cũng đi hết màn hình một số nguyên lần.
  Kết quả: khung ở giây 300 **trùng từng pixel** với khung ở giây 0 (đã kiểm tra
  với cả 8 hướng bay và popup subscribe vắt qua điểm nối).
- **Dải sóng nhạc** phụ thuộc vào nhạc thật nên không nằm trong loop. `extend.py`
  vẽ nó lên trên loop khi ghép. Python chỉ tạo mặt nạ xám của các thanh (~1ms/khung),
  còn màu, quầng sáng và việc chồng lớp do ffmpeg làm.

## Lệnh cấp thấp

`video.py` gọi các lệnh dưới. Dùng trực tiếp khi cần kiểm soát từng bước
(`SK=.claude/skills/video-generator`, `PY=$SK/.venv/bin/python`, các `--preset` xếp lớp theo thứ tự, lớp sau thắng):

```
P="--preset channel/<ch>/video.json --preset <thư mục>/video.json"
$PY $SK/scripts/make_loop.py ANH.png frame.png $P --frame 30
$PY $SK/scripts/make_loop.py ANH.png loop.mp4 $P --seam-check --jobs 4     # + loop_intro.mp4
$PY $SK/scripts/make_loop.py ANH.png loop.mp4 $P --intro-only
$PY $SK/scripts/extend.py loop.mp4 ALBUM.wav thu.mp4 $P --start 600 --seconds 30   # xem thử
$PY $SK/scripts/extend.py loop.mp4 ALBUM.wav OUT.mp4 $P                   # cả album
$PY $SK/scripts/extend.py loop.mp4 ALBUM.wav OUT.mp4 $P --no-bars         # không sóng nhạc
```

- **Logo:** mỗi channel có `image_source/logo.png` (vuông, nền trong suốt). Logo tròn có
  thể vẽ bằng code: `$PY $SK/scripts/make_logo.py --title <TRÊN> --sub <DƯỚI> --out channel/<ch>/image_source/logo.png`
  (lệnh cụ thể của kênh ghi trong `channel.md` → *Tài nguyên*).
- **`--no-bars`:** nếu định ghép không có sóng nhạc, render loop với `make_loop.py ... --no-bars`,
  vì lớp bóng tối mờ dưới sóng nhạc được nung sẵn vào loop.

## Thời gian đo thực tế (album 50:16)

| Bước | MacBook Pro M2 | Server |
|---|---|---|
| `make_loop.py` 5 phút (9.000 khung) | ~100 s | **13–17 s** (`--jobs 16`) |
| `extend.py` có dải sóng, x264 | ~11 phút (`--jobs 4`) | **~2 phút** (`--jobs 16`) |
| `extend.py` có dải sóng, NVENC | — | **~1.5 phút** (`--jobs 12`), file lớn hơn ~50% |
| `extend.py --no-bars` | ~1 phút | ~1 phút (thời gian nén audio WAV → AAC) |
| Trọn gói `video.py album` (upload WAV 870MB lần đầu + tải về ~900MB) | — | **3–4 phút** |
| Tool cũ, dựng cả 90.000 khung | ~20 phút (máy 2 nhân) | |

Có dải sóng thì vẫn phải nén lại toàn bộ độ dài một lần. Đó là giới hạn của
H.264, không phải của Python. Album được cắt tại keyframe (keyframe được ép đúng
mỗi 10s) thành `--jobs` đoạn nén song song trong các process riêng, rồi nối lại
không nén. Audio WAV được nén sang AAC song song với phần hình.

Bộ nén (`--encoder`, hoặc `encode.encoder` trong preset):
- `nvenc`: **mặc định trên server** (`VG_ENCODER` trong `remote.env`). GPU NVIDIA; 16 phiên 4K song song chạy được.
  Kèm NVDEC: `extend.py` giải mã loop bằng `-hwaccel cuda`. Đo 2026-09-24, loop 5 phút 4K: x264 247 s và ~100 GB RAM
  (32 encode × ~120 luồng), NVENC 52 s, CPU/RAM gần như rảnh. File to hơn x264 một chút.
- `x264`: file nhỏ nhất ở cùng chất lượng, mặc định khi render trên Mac (`--local`). Mỗi encode chỉ được một phần số
  nhân (`encode.share_threads`), vì x264 tự mở ~120 luồng cho một encode 4K.
- Khung hình vẫn ghép trên CPU: `effects_gpu.py` (torch CUDA, cho ra đúng từng pixel) chậm hơn khi 16 tiến trình chia một
  GPU (103–110 s so với 52 s); bật thử bằng `VG_GPU=1`.
- Mọi lệnh render/đóng gói trên server chạy trong systemd user slice `youtube.slice` (CLAUDE.md): tổng mọi skill
  ≤ 60 % CPU, RAM 60 % (MemoryHigh) / 70 % (MemoryMax).
- `videotoolbox`: chip nén của Mac, ít tốn CPU nhưng không nhanh hơn x264 đáng kể.

## Cinema (`cinema.py`)

Mỗi khung dựng trên GPU (torch): ánh sáng trong không gian ảnh → `grid_sample` theo depth map (Depth Anything V2 Small,
cache `.depth-<hash>.npy` cạnh ảnh trên server) → vùng khóa màn hình → sương → hạt (lớp riêng, giảm trong vùng chữ) → lớp phủ
(logo, badge, lớp tối sóng nhạc) → subscribe. Đo 2026-09-28: loop 5 phút 4K 139 s (8 phần chung GPU, 28 GB VRAM, CPU gần rảnh);
nhiều chuyển động nên NVENC cq 24 ≈ 23 Mbps (1 giờ ≈ 10 GB). `qa` so hình chữ bằng tương quan sau khi dò dịch + tỉ lệ
(0,93–1,07), vì zoom làm chữ to/nhỏ đều mà không méo.

## Ghi chú

- **Audio:** nên đưa WAV vào. `extend.py` nén một lần sang AAC 320k. Nếu đưa
  `.m4a` AAC thì audio được ghép thẳng, không nén lại.
- **Keyframe:** loop có keyframe mỗi 10 giây. Ở mỗi keyframe (kể cả điểm nối),
  x264 làm ảnh đổi rất nhẹ (~1.5/255). Điểm nối không lộ hơn bất kỳ keyframe nào khác.
- **Bẫy bóng đổ quanh logo** (từ tool cũ): bóng phải được làm mờ *sau khi* chèn
  lề rộng quanh sprite, nếu không sẽ hiện một khung chữ nhật mờ. `brand.drop_shadow`
  đã xử lý việc này.
- **Preview `--no-bars --start`** bị làm tròn về keyframe gần nhất (không nén lại
  thì không cắt giữa GOP được).

## Đóng gói (`video.py package <album>`)

Một zip cho mỗi album (CEO 2026-09-28): album + Short của nó, để CEO tải một lần.

- Mac: `package.py stage` dựng từng phần vào thư mục tạm (`<album>/` và `<album>/short/`: youtube.md, `upload/*.txt`,
  `thumbnail.jpg`, `thumbnail_full.*`, `meta.json`), ghi `build.json` (tên, kênh, các phần: video trên server, tên file
  trong zip, khung mong đợi, thư mục audio để so độ dài, cảnh báo check `--force`; các dòng *Giờ đăng* / *Thứ tự đăng* của
  `channel/<ch>/publish.md`, bỏ dòng còn `<…>`), rsync sang `in/<album job>/pkg/`.
- Server: `pkg_server.py build <pkg>/build.json` hard-link hai video vào (`<album>.mp4`, `short/<album>-short.mp4`),
  ffprobe, `manifest.json` + `README.txt` ở gốc gói, zip (stored, zip64) vào `out/<album job>/`, in một dòng JSON
  (size, sha256, parts, files, entries, warnings, readme). `--dry-run` in cây file + README rồi xoá zip, không upload.
- Không đóng gói Short riêng: `package <album>/short` từ chối; `album` chỉ tự đóng gói khi Short đã render + có youtube.md.
- `s3-package.json` (một file ở thư mục album): mỗi lần upload một bản ghi `s3`, `size`, `sha256`, `parts.{album,short}`
  (dir, title, video probe, thumbnail, youtube), `checks` (`pass` / `fail, packaged with --force` / `not included (--no-short)`).

## Server (mặc định; `--local` = render trên Mac)

Host, key, số job, thư mục trạng thái nằm trong `../remote.env` (`VG_REMOTE`, `VG_KEY`, `VG_JOBS`, `VG_DIR`; biến môi trường cùng tên sẽ ghi đè). Trên server: `~/$VG_DIR/scripts` (bản sao scripts), `.venv/`, `repo/channel/<tên>/image_source/`, `in/<job>/`, `out/<job>/`, trong đó `<job>` là đường dẫn thư mục album (hoặc `albums/<album>/short`) viết liền, vd. `<kênh>__albums__<album>__short`. Nhạc đã upload được giữ lại, lần sau không upload lại. Ổ /home trên server đã đầy ~83%, nên thỉnh thoảng xoá `out/*/video.mp4` cũ.
