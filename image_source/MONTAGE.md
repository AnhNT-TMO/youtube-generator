# Ghép clip thành video 3 tiếng

Luật để Claude (hoặc script sau này) chọn và xếp clip của `image_source/` thành phần hình cho một video nhạc dài. Người không ngồi
chọn clip: mọi quyết định đọc từ thẻ cảnh (`<id>.json`) và các `montage.json` đã làm.

## 1. Phạm vi

- Video dài bằng master nhạc (album Christmas 120–180 phút); số trong file này tính cho 3 tiếng, video ngắn hơn thì thu nhỏ tỉ lệ.
- Bộ clip thuộc **một kênh**. Mọi video của kênh đó lấy hình từ bộ này (nhạc carol hay Suno đăng xen ngày) tính chung luật
  trùng cast, hero và gia đình cảnh ở §3. Kênh khác không dùng bộ này làm hình chính: kênh bị chấm dứt thì nội dung của nó không
  được đăng lại ở kênh khác cùng chủ (POLICY §8).
- Nguồn: clip có `video.status = ok` ở mọi nhóm **trừ `cozy-loop/`** (bộ riêng: một cảnh suốt video, xem README của nhóm).
- Clip dùng đúng file `<id>.mp4` (đã cắt theo `video.trim`), dài 7–10 s.

## 2. Con số

| Mục | Luật |
|---|---|
| Chuyển cảnh | hòa tan 1 s; mỗi lượt xuất hiện phát clip **một lần** từ đầu tới cuối |
| Một lượt | ≈ độ dài clip − 1 s ≈ 8 s → 3 tiếng ≈ 1.350 lượt |
| Bộ clip của video (*cast*) | **200 clip** (180–220) → mỗi clip ≈ 6–7 lượt |
| Lật ngang | lượt chẵn của một clip phát lật ngang (`flip`) → ≈ 400 hình khác nhau, mỗi hình ≈ 3 lượt |
| Cấm | phát ngược (tuyết bay lên, lửa sai), đổi tốc độ, zoom/crop thêm, chèn chữ |

## 3. Chọn cast

**Gia đình cảnh chủ đạo:** mỗi video có một chủ đề hình người xem nhận ra ngay, khớp thumbnail, không xáo đều cả kho.
- ≥ 50 % cast lấy từ **một gia đình chủ đạo**: một nhóm (`home`, `village`…) hoặc một cặp nhóm kề (cột *Ghép tốt với*) khi
  nhóm lẻ có < 150 clip đạt (vd. `nature` + `travel`, `grand` + `village`).
- Phần còn lại từ nhóm kề + cảnh nối `detail/`.
- Hero và khung thumbnail lấy từ gia đình chủ đạo.
- Hai video liền nhau của kênh (bất kể nguồn nhạc) khác gia đình chủ đạo.

**Mood:** mỗi video một mood; cast chỉ lấy clip qua bộ lọc của mood đó. Mood chỉ được lên lịch khi bộ lọc còn ≥ 300 clip
(để cast thay đổi được giữa các video).

| Mood | Lọc | Ghi chú |
|---|---|---|
| `eve` Đêm Giáng sinh | `time` ∈ night, twilight, evening; `palette` ≠ cool-blue | mood chính, xen trong nhà ↔ ngoài trời |
| `indoor` Trong nhà ấm | `place` = indoor; `time` ∈ night, twilight, evening | cảnh nối là cửa sổ (`snow` = window) và `detail/` |
| `town` Phố và làng đêm | outdoor ≥ 60 % cast; phần còn lại là cửa hàng, quán, sảnh nhìn ra phố | village, travel, magic, grand |
| `winter` Mùa đông trắng xanh | `palette` ∈ cool-blue, white-gold | nature, travel, cảnh cửa sổ |
| `morning` Ngày tuyết | `time` ∈ day, golden | chỉ khi đủ clip; trước đó dùng làm đoạn kết của `eve` |

**Tỉ lệ trong cast:**
- ≥ 10 đề tài, mỗi đề tài ≤ 15 clip.
- `scale`: macro 10–20 %, vista + street ≥ 25 % (trừ mood `indoor`).
- ≥ 10 clip `detail/` hoặc cửa sổ làm cảnh nối.

**Hero:** 15 clip đẹp và dễ nhớ nhất của cast (điểm `distinct` cao, §5), lấp đúng 2 phút đầu và cho khung hình thumbnail.
- Chỉ cảnh **trong nhà** (`place` = indoor) của gia đình chủ đạo; **không cận cảnh** (`scale` ≠ macro: không zoom vào ngôi sao,
  quả châu, đèn lồng…); không cảnh ngoài trời.
- Mỗi đề tài ≤ 2 hero; một vật thể nhận diện (§5 `anchors`, vd. piano, lò sưởi) ≤ 2 hero, và hai hero cùng vật thể cách nhau
  ≥ 2 clip.
- Một clip đã làm hero thì không làm hero lại trong 30 ngày; khung hình đã lên thumbnail thì không dùng làm thumbnail nữa.

**Không lặp giữa các video:**
- Cast mới trùng ≤ 50 % với cast của mỗi video trong 7 ngày trước, và ≤ 70 % với bất kỳ video nào cũ hơn.
- Trong số clip qua bộ lọc, ưu tiên clip ít lượt dùng nhất trong 30 ngày.

## 4. Sắp thứ tự

**Khối theo bài nhạc:**
- Mỗi chapter (một bài) = một khối, trong khối là một nhóm (hoặc nhóm kề, cột *Ghép tốt với* trong README nhóm); các folder
  đề tài trong nhóm **thay phiên nhau**, có thể chèn cảnh `detail/`.
- Hai clip cùng folder đề tài không đứng cạnh nhau, nên cách nhau ≥ 2 clip (folder là category: cùng folder = cùng loại phòng/vật).
- Hai khối liền nhau khác đề tài.
- Một đề tài quay lại thì cách ≥ 20 phút.
- Nhạc không có chapter thì chia khối 3–4 phút.
- Trong khối ưu tiên đi toàn → trung → cận (vista/street → room → macro), rồi mở cảnh rộng ở khối sau.

**Nối hai clip liền nhau:**
- Cùng `place`, hoặc nối qua clip `detail/` (macro) hay clip cửa sổ/hiên.
- `time` chỉ dịch một bậc (`day` ↔ `golden` ↔ `twilight` ↔ `evening`/`night`).
- `palette` giống hoặc gần: `warm-gold` ↔ `red-green` ↔ `white-gold`; `cool-blue` chỉ cạnh `white-gold`.
- Không 3 clip liền cùng `camera`.
- Không hai cú trượt ngược chiều liền nhau.
- Hai clip quá giống nhau (`near`, §5) không đứng cạnh nhau.
- Hai clip có chung vật thể nhận diện (`anchors`, §5) không đứng cạnh nhau: `near` so cả khung hình nên không bắt được hai
  phòng khác hẳn nhau cùng có một cây đàn piano.
- Độ sáng đầu/cuối chênh ≤ ngưỡng `luma` (§5).

**Lặp trong video:**
- Một clip quay lại sau ≥ 20 phút.
- Không cặp clip liền nhau nào xuất hiện hai lần.
- Không đoạn 10 phút nào có cùng chuỗi clip với đoạn khác: 3 tiếng là một thứ tự liền, không phải 1 tiếng chép 3 lần.
- Số lượt của các clip trong cast chênh nhau ≤ 1. Riêng clip dễ nhớ (`distinct` cao) tối đa 3 lượt; clip phòng chung chung
  bù số lượt còn thiếu.
- 2 phút đầu là hero; 30 phút đầu không lặp clip nào.

## 5. Chỉ số đo

Đo **một lần cho cả kho** khi session tạo clip xong (≈ 1.000 clip, một job trên GPU server ≈ 10–20 phút), sau đó chỉ đo clip mới.
Kết quả ghi vào thẻ cảnh, mục `measure`:

| Trường | Là gì | Dùng ở |
|---|---|---|
| `luma`, `luma_in`, `luma_out` | độ sáng trung bình, khung đầu, khung cuối | nối hai clip |
| `warmth` | độ ấm màu đo thật (bổ sung `palette`) | nối hai clip, lọc mood |
| `cam` | hướng và tốc độ máy quay: `dx`, `dy`, `zoom` | không trượt ngược chiều |
| `near` | id các clip rất giống (embedding ảnh) | không đứng cạnh nhau, không cùng làm hero |
| `distinct` | 0–1, khác bao nhiêu so với các clip còn lại | hero, trần số lượt |
| `anchors` | vật thể nhận diện: danh từ chính trong `clip.lock` + `subject`, chỉ giữ vật có ở ≤ 15 % clip, bỏ vật chung (khung cửa, cây thông, đèn, bàn…). Tính lúc chọn, không ghi vào thẻ | không cạnh nhau, giãn cách hero |

Ngưỡng đã chốt từ phân bố đo thật (550 clip, 2026-10-04): `near` ≥ 0,85 là trùng (không cùng cast/hero), ≥ 0,80 không đứng
cạnh nhau; độ sáng đầu/cuối chênh ≤ 0,08; `distinct` ≥ 0,85 là clip dễ nhớ (tối đa 3 lượt). Cast nhỏ (150 clip ≈ chu kỳ 19 phút):
khoảng lặp tối thiểu = min(20 phút, 0,75 × chu kỳ).

## 6. Kiểm trước khi đăng

Đặt thumbnail + title + 3 khung hình (0:30, giữa video, cuối) của video mới cạnh 3 video gần nhất của kênh. Trông như cùng
khuôn thì đổi gia đình chủ đạo hoặc mood rồi ghép lại (POLICY §1.2: *"channels where content feels interchangeable from video
to video are not allowed to monetize"*; spam policy cấm AI làm hàng loạt video giống nhau, POLICY §6).

## 7. Đầu ra

`montage.json` trong thư mục album:
- `mood`, `cast` (id), `hero` (id);
- `sequence`: mỗi lượt `{clip, flip, start_s}`;
- `checks`: kết quả từng luật ở §3–§4.

Số lượt dùng và lịch sử hero của mỗi clip tính lại từ các `montage.json` đã làm; không giữ sổ riêng.

## 8. Nguồn của các con số

| Luật | Nguồn |
|---|---|
| Video 3 tiếng | R&D 2026-10-04 §3: 3 h là nhóm đông nhất của ngách (265 video mùa 2025, 116 hiện tại); không độ dài nào thắng trong cùng kênh |
| Gia đình cảnh chủ đạo, khớp thumbnail | POLICY §1.2 (interchangeable) + R&D §4, §8: 11/16 hit mùa 2025 là một cảnh nội thất ấm (suy từ thumbnail); A/B ở vài video đầu |
| Hai kênh không dùng chung bộ clip | POLICY §8 (circumvention) |
| Kiểm 4 video liền nhau | POLICY, việc cần làm số 1 |
| 200 clip, lật lượt chẵn, cách ≥ 20 phút, trùng ≤ 50 %, 12 hero, 2 phút hero | **xưởng tự đặt** từ phép tính kho clip; API không đo được lặp cảnh trong video người khác. Kiểm bằng retention thật sau khi đăng |

Báo cáo: `research/youtube-policy/POLICY-2026-10.md`, `research/niche-instrumental-ai/REPORT.md` (R&D, chỉ trên máy).

## Bản cuối 4K + intro kênh

`montage.py render <tên> --channel <ch> --audio <master.wav>`: lấy clip 1080p ở `~/video_sources/<library>/` (library = `"library"` trong `resource.json` của bộ). Unit `montage-render` **chờ tới khi đủ mọi clip của cast** (kiểm mỗi 5 phút, upscale tầng 1 làm cast trước rồi nhường GPU cho render, CEO 2026-10-06); `--wait-clips 0` = thiếu thì thoát (ghi
`*.missing.txt`). Đủ thì ghép ở 1080p → Lanczos `scale_cuda` lên 3840×2160 → HEVC NVENC cq 24 (`<tên>-2160p-silent.mp4`); có `--audio` thì ghép master thành AAC 320k → `<tên>-2160p.mp4`; để trên
server (`~/video-montage/out/<tên>/`). Intro mở video (CEO 2026-10-04, dùng cho mọi album dài): đọc
`channel/<ch>/intro.json` (logo tròn, tên kênh, tagline, font trong `video-montage/fonts/`); ~4,8 s trên clip 1: nền mờ tối +
bụi vàng → vòng vàng quét như kim đồng hồ làm lộ logo → sao 4 cánh ở 12 giờ → tên kênh hiện từng chữ + đường kẻ vàng +
tagline → vệt sáng lướt chữ → tan ra cảnh. Thông số ở `scripts/intro_server.py` (`T`, `L`).
