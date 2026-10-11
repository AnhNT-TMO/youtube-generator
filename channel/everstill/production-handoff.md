# Bàn giao kiến thức sản xuất cho Claude và Codex

Đối chiếu ngày 2026-10-11. Đây là bản đồ đến hồ sơ gốc, không thay trạng thái trong `album.md` và không yêu cầu dựng lại sản phẩm đã xong.

## Album 005: Warm Country Christmas

- Hồ sơ: `channel/everstill/albums/005-warm-country-christmas/album.md`.
- Nhạc cuối cùng là 20 bài từ hai zip Suno của CEO, không phải kế hoạch PD/snowglobe cũ ở đầu brief. Nguồn tái tạo: `audio/order.json`, `audio/tracklist.txt`, `audio/join005.py` trong album. Crossfade 3 s, fade-in 12 s, fade-out 10 s; video 3:00:08. Dòng việc còn lại cũ trong brief đã bị phần cập nhật nhạc/video phía trên thay thế.
- Hình: `montage.json`, `clips.txt`, `timeline.txt`; cast miền quê ấm `nature+home`, seed 3, 150 clip, 8 hero. Thumbnail dùng `christmas-morning-06` đã được chọn; không tự chọn lại.
- Short: `shorts/countdown/cd_spec.json`, `job4k.json`, `youtube.md`. Khi làm Short mới, dùng kit chuẩn đã cải tiến từ 006, không sao chép script riêng cũ của 005.

## Album 006: Bell Piano Christmas

- Hồ sơ: `channel/everstill/albums/006-bell-piano-christmas/album.md`.
- CEO chuyển từ Mureka sang PD tự phối. `loop.json` chỉ còn dùng thứ tự bài/key; trường style/take Mureka cũ không phải nguồn nhạc cuối.
- Chuẩn phối và lịch sử quyết định: `research/christmas-carols/experiments/piano-arrange/PRINCIPLES.md`, `DECISIONS.md`. Tooling: `ensemble_arrange.py`, `render_variants.py`, `measure_tune.py`, `master_album.py` cùng thư mục.
- Spec: `variants_006_first5.json`, `variants_006_rest.json`, `variants_006_sleigh.json`, `variants_006_choir.json`; ghép cuối theo `join_006_album.json`. `join_006_rotation.json` là bản thử một vòng.
- Kho server gốc: `~/youtube-qc/audio/162_bell/`; Mac dùng `audio/162_bell/`. Cần cả mẫu Piano in 162, sfizz, tuning và các nhạc cụ trên server, không chỉ script.
- Bản cuối: 21 bài, 61 lượt, khoảng 181,03 phút. Luân phiên thường/sleigh/choir, lệch pha mỗi vòng; choir MU80 SlowChoir −6 dB, vào từ verse 2, nối âm chung + chồng 0,8 s khi đổi hợp âm. Các thử nghiệm choir SSO/SoftVoice trước đó không phải bản cuối.
- Hình: `montage.json` đã đổi mở đầu theo CEO: frozen-lake-18 → house-lights-08 → christmas-market-02. Giữ silent 4K làm nguồn; thay master bằng mux copy video, không dựng lại hình.
- Short: `shorts/countdown/`, Silent Night `cel_strings`, đoạn 109,16–134,51 s. Số ngày đếm ngược tính lại theo ngày đăng thực tế; không cố định 74 ngày cho Short khác.

## Quy trình dùng lại

1. PM đọc brief và luật kênh; nhạc chọn đúng lane Suno / PD tự phối / Mureka. Không áp luật Mureka cấm choir vào PD tự phối.
2. `video-montage` chọn cast, xếp cảnh, preview và render; chuẩn chung ở `image_source/MONTAGE.md`. Ngoại lệ đã duyệt cho album nằm trong brief. `video-upscale` chuẩn bị clip 1080p; thumbnail qua `thumbnail-prompt`.
3. Countdown dùng `.claude/skills/video-shorts/scripts/countdown/` và `channel/everstill/shorts_kit/README.md`, spec/job mẫu trong `shorts_kit/countdown/`, badge và tiếng chuông ở `branding/badges/`, `branding/sfx/`.
4. Giữ sửa lỗi của 006: chữ tự giãn `line_gap`; glock rải trước rồi chuông mới lắc/reng; mũi tên giữa khung trên y=0,82; sidechain key có `apad` để tiếng không mất ở 7,4 s. Kiểm độ dài tiếng/hình và làm lại thumbnail từ frame 0 khi chữ đổi.
5. Upload theo `publish.md` và skill `upload-youtube-publish`. Với hai album này, hồ sơ chốt gói album riêng; countdown đợi CEO kiểm rồi zip riêng. Không áp mặc định gói lyric Short của `video.py package` vào montage. Sau đăng mới chạy dịch và theo dõi kết quả.

## Đổi assistant hoặc máy

Trên cùng repo, Claude/Codex đọc trực tiếp mọi hồ sơ trên. `.claude/knowledge/memory/` và bản mirror `.agents/knowledge/memory/` giữ memory đã nhập; tra mục liên quan trong `MEMORY.md`.

Đổi máy cần chuyển thêm `research/christmas-carols/`, hai thư mục album, kho audio/scene cần thiết, `pd-evidence/`, `shorts_kit/`, `branding/`, và cấu hình truy cập GPU/browser. Git bỏ qua nhiều thư mục này. Các đường server trong spec phải được kiểm lại trước khi chạy. Giữ thông tin xác thực trong cấu hình máy, không trong tài liệu hay memory.
