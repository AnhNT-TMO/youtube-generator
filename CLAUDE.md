# CLAUDE.md

## 0. Công ty

Project là một công ty sản xuất nhạc cho các kênh YouTube. Mục tiêu: nhiều người nghe thật, bền lâu, cải tiến liên tục; mọi việc
cân giá trị với công sức. Chuỗi chỉ huy: **CEO → PM → các nhóm** (skill + sub-agent).

| Vai | Là ai | Làm gì |
|---|---|---|
| **CEO** | chủ repo | cùng PM bàn chủ đề + lên album; duyệt các việc "trình CEO"; tự upload YouTube, đăng nhập Suno/ChatGPT, `auth` YouTube |
| **PM** | skill `pm-production` | nguồn sự thật duy nhất của sản xuất; thảo luận với CEO, chọn bài, viết brief, giao việc cho sub-agent, **duyệt chất lượng đầu ra**, đọc kết quả |
| **R&D** | nhóm `rnd-` | dùng YouTube Data API tìm và hiểu kênh/video; giữ kho câu title/thumbnail (`research/phrase-bank/`); đưa số liệu, không quyết |
| **Audio** | nhóm `audio-` | tạo bài vào kho bằng Suno, đặt tên bài + chọn đoạn Short, ghép album |
| **Video** | nhóm `video-` | thumbnail album + ảnh dọc Short, video loop + video đầy đủ, Short, đóng gói S3 |
| **Upload** | nhóm `upload-` | title, description, tags, chapters (`youtube.md`); dịch title + description sau khi đăng |

- **CEO và PM lên kế hoạch album trực tiếp** (không còn idea/plan): chủ đề, câu chuyện, lời cầu xin trên title/thumbnail, bài nào.
  PM ghi quyết định vào `albums/NNN-slug/album.md` (brief + tracklist); nhân viên làm đúng brief, sáng tạo trong phần brief để ngỏ.
  Brief thiếu, mâu thuẫn hoặc không làm được → dừng và hỏi PM (`BLOCKED`), không tự quyết, không hỏi CEO.
- **PM giao việc bằng sub-agent** và duyệt từng đầu ra theo brief trước khi coi là xong (ảnh đúng concept, title đúng hướng,
  master đúng độ dài, Short đúng đoạn). Sai thì trả lại chính worker đó kèm việc cần sửa.
- **CEO chỉ hỏi PM.** Session nào CEO hỏi về sản xuất thì trả lời với vai PM, từ hồ sơ của PM (`album.md`, ledger `production/`,
  `results.md`, `album.py board`).
- Mọi chỗ SKILL.md ghi "hỏi người dùng / chủ kênh" nghĩa là hỏi PM, trừ việc chỉ CEO làm được. CEO chạy thẳng một skill thì CEO đóng vai PM.
- **Trình CEO:** mở kênh mới, đổi prompt Suno của kênh, đổi hợp đồng kênh, đổi ngân sách hoặc gói Suno, đổi quy trình/skill ngoài lỗi chặn.

**CEO đánh giá PM bằng hai thứ**, mọi báo cáo của PM trả lời hai thứ này trước:
1. Video có bám trend / brief CEO không.
2. View có cải thiện không: video mới so với trung vị các video cùng loại của kênh ở cùng tuổi (48 giờ, 7 ngày).

**Vòng trách nhiệm:** CEO + PM chọn chủ đề (R&D đưa số liệu) → PM viết brief + chọn bài → các nhóm làm → PM duyệt → CEO đăng
→ PM đọc kết quả 48 giờ / 7 ngày (`results.md`) → video dưới kỳ vọng thì phân tích theo trục (chủ đề/thời điểm, title +
thumbnail/CTR, 30 giây đầu/retention, nhạc/thời lượng xem, phát hành/Short) → đổi một trục cho video sau → báo CEO.

- **Đánh giá từng trục:** mỗi video ghi chủ đề, câu title/thumbnail (id trong kho câu), biến thể ảnh + video; không đổi hai trục
  cùng lúc; so bằng trung vị nhiều video, vì một video nổ hay chìm phần lớn là may rủi.
- **Cải tiến liên tục:** sau mỗi lô PM spawn một agent review quy trình và trình CEO **chỉ những thay đổi đáng làm** (≤ 5 mục, mỗi
  mục giá trị kỳ vọng, công sức, rủi ro). Trong lúc chạy chỉ sửa skill khi lỗi **chặn** hoặc **làm hỏng** lần chạy.
- **Báo cáo cho CEO:** ngắn, tiếng Việt: hai tiêu chí ở trên, đã làm gì, quyết định PM đã đưa ra, bài học, việc cần CEO.

## 1. Project

"Xưởng" làm **album nhạc 60–80 phút** cho các kênh YouTube của chủ repo. Mỗi kênh có **prompt Suno riêng** (một prompt cho mỗi
loại bài); bài được tạo trước thành **kho** (`channel/<ch>/songs/`), mỗi album chọn bài từ kho và dùng lại bài qua nhiều album
(như các kênh lớn cùng ngách). Mỗi lần đăng = **1 album + 1 Short**; không làm single.

**Nguyên tắc cốt lõi:** nhạc là của mình (Suno, prompt của kênh), nhân vật, hình, tên kênh, logo là của mình. Câu title + chữ
thumbnail là lời cầu nguyện phổ biến của ngách, lấy từ kho câu R&D: câu cầu nguyện chung / câu trích kinh điển (như Kinh
Thánh, không thuộc về ai) **được dùng nguyên văn** kể cả khi nhiều kênh đã dùng, nhất là khi câu vẫn đang lên; muốn khác thì
chuyển thể (đổi Lord ↔ Father/Jesus, đổi vài chữ). Không bao giờ lấy tên, logo, branding, hình của kênh khác (CEO 2026-09-28).

## 2. Skill và kênh

- **Tên skill = `<nhóm>-<việc>`** để dễ quản lý: `pm-`, `rnd-`, `audio-`, `video-`, `upload-`.
- **Skill = quy trình, dùng chung cho mọi kênh.** `.claude/skills/<skill>/` chỉ nói *làm thế nào*; không ghi tên kênh, thể loại,
  giọng, nhân vật, màu, câu mẫu hay số đo của một kênh cụ thể. Mỗi skill tự chứa code + venv + cache của nó.
- **Kênh = nội dung.** Mọi chi tiết *làm gì cho kênh này* nằm trong `channel/<ch>/` (danh sách file: `channel/README.md`).
- Học được điều gì về một kênh: ghi vào file của kênh đó, không vào skill. Skill chỉ đổi khi *quy trình* đổi.
- Kiểm: `python3 .claude/skills/pm-production/scripts/lint_skills.py` báo mọi chỗ skill/template nhắc tới một kênh cụ thể.

| Nhóm | Skill | Việc |
|---|---|---|
| PM | `pm-production` | bàn album với CEO, chọn bài (`album.py`), brief, giao việc, duyệt, board, kết quả, lính canh server |
| R&D | `rnd-youtube-api` | hướng dẫn + CLI YouTube Data API: tìm kênh, video tăng nhanh (view/ngày), comment, sheet thumbnail, kho câu |
| Audio | `audio-suno-generate` | Suno Simple mode + prompt của kênh → tải cả 2 clip qua usesuno → `songs/raw/` |
| Audio | `audio-song-naming` | đọc lời → đặt tên → đổi tên file → thẻ bài `songs/<type>/<slug>.md` + đoạn Short |
| Audio | `audio-album-assembly` | nối bài theo tracklist bằng crossfade nhẹ → master + `assembly.json` (chapters) |
| Video | `thumbnail-prompt` (sẽ đổi tên `video-thumbnail`) | ảnh album 4K + ảnh dọc Short (ChatGPT → SeedVR2 4K) |
| Video | `video-generator` (sẽ đổi tên `video-render`) | loop 5 phút / cinema, video đầy đủ trên server, `video.py short`, zip lên S3 |
| Video | `video-shorts` | 1 Short mỗi album từ đoạn `short` của bài → `short.json` → ảnh dọc → render → `youtube.md` |
| Upload | `upload-youtube-publish` | title, description, tags, chapters → `youtube.md`; hướng dẫn Studio |
| Upload | `upload-youtube-translate` | dịch title + description lên YouTube sau khi đăng |

## 3. Quy trình

```
KHO BÀI (làm trước, theo lô PM đặt; 1 lượt Suno = 1 bài = 2 bản v1/v2 ~6 phút)
  audio-suno-generate (lane suno, 1 luồng)  ──raw/<id8>.wav + lời──▶  audio-song-naming (chạy song song)
                                                                        └─▶ songs/<type>/<tên>_v1|_v2.wav + .md (tên, đoạn Short)
MỖI ALBUM
  CEO + PM: chủ đề, câu title/thumbnail (kho câu R&D), bài 1 ─▶ album.md (brief + tracklist theo album_rules.md)
     └─▶ album.py check → build (tracks/NN-*.md)
            ├─▶ audio-album-assembly (server) → master 60–80 phút + assembly.json
            └─▶ thumbnail-prompt (lane chatgpt) → thumbnail 4K → video-generator loop (server)
                    └───────────┬───────────┘
                                ▼
            upload-youtube-publish → youtube.md ─▶ video-generator album (server): video đầy đủ 4K
            video-shorts (albums/NNN/short/): short.json → ảnh dọc → video.py short → youtube.md
                                ▼
            video.py package <album>: MỘT zip trên S3 = album + short/ + README thứ tự đăng
                                ▼
            CEO tải 1 lần, đăng (album → Short) → upload-youtube-translate → kết quả 48 giờ / 7 ngày (pm-production)
```

- **Thứ tự linh hoạt:** skill chỉ giao tiếp qua file. Kho bài làm độc lập với album; nhạc và hình của một album chạy song song, gặp
  nhau ở video đầy đủ. Tiếp tục từ trạng thái hiện có, không làm lại từ đầu. Xem việc còn lại: `album.py board --channel <ch>`.
- **Mỗi ngày tối đa 1 album + 1 Short** (đăng album trước; Related video của Short = album). Giờ đăng: `channel/<ch>/publish.md`.
- **Album:** master 60–80 phút; loại bài xen kẽ theo `album_rules.md` → `pattern` (ví dụ bài có lời đọc → bài hát thẳng → …);
  nối crossfade nhẹ, không cắt sửa bài. Luật chọn bài của kênh: `channel/<ch>/album_rules.md` (`album.py check` kiểm).
- **Short** là một phần của album, nằm ở `albums/NNN-slug/short/`: đoạn hát trong bài (mặc định bài 1) mà audio-song-naming đã
  chọn; ảnh dọc **mới** (người đứng trong cảnh nhà nguyện cùng vibe album, không micro, không đồ vật: luật ảnh ở `visual.md`); video ≤ 3 phút. Luật: `docs/seo-youtube/09-shorts.md`.

## 4. Chuẩn bị môi trường (một lần; làm lại khi hỏng)

- **Suno:** Chrome riêng `.claude/skills/audio-suno-generate/scripts/suno-chrome.sh` (cổng 9222, profile `~/.suno-chrome/profile`),
  đăng nhập suno.com + mở tab usesuno.com/tools/downloader. Claude điều khiển qua MCP `suno-chrome` ở **scope local**
  (`claude mcp get suno-chrome`; không để trong `.mcp.json` vì extension VS Code tự từ chối server của project).
- **ChatGPT** (thumbnail): `.claude/skills/thumbnail-prompt/scripts/chatgpt-chrome.sh` (cổng 9223), đăng nhập một lần. Tài khoản
  dùng chung: xóa thread sau khi lấy ảnh.
- **GPU server** trong LAN (bản sao repo `~/youtube-qc`): Whisper (đặt tên bài), ghép album, render video, upscale thumbnail 4K đều
  **mặc định chạy trên server** (các skill tự gọi qua runner của mình); `--local` mới chạy trên Mac. Mac chỉ làm việc nhẹ: điều
  khiển Chrome, tải clip, text/yaml, chỉnh ảnh, `video.py frame`.
- **Cấu hình máy** (không vào git): skill dùng server có `remote.env`, chép từ `remote.env.example` cạnh nó. Tiền tố biến: `QC_`
  (audio-song-naming, audio-album-assembly), `VG_` (video-generator, thêm S3), `TP_` (thumbnail-prompt).
- **YouTube Data API:** key ở `~/.config/yt-research/api_key` (R&D); OAuth của kênh cho dịch + analytics (`auth`, CEO làm).
- Gói **Suno Pro**: 2.500 credits/tháng, 20 lượt tải chính thức/tháng (không dùng).

## 5. Luật bắt buộc

- **Credits:** PM đặt lô (loại bài × số lượt; mỗi lượt ra 1 bài 2 bản v1/v2, hoặc 2 bài khác lời). Trước mỗi lượt kiểm credits còn ≥ lượt đó + dự phòng
  100. Lượt nào Suno lỗi thì báo PM, không tự tạo lại quá 1 lần.
- **Cổng duyệt:**
  - *PM quyết:* lô bài cần tạo, tracklist album, câu title/thumbnail; duyệt đầu ra của worker (tên bài, đoạn Short, ảnh).
  - *Chỉ CEO:* đổi prompt Suno, luật cứng của kênh (`album_rules.md` phần *Luật* của CEO, form ảnh), chạy việc nặng trên Mac (`--local`),
    upload YouTube, `auth` YouTube, đăng nhập Suno/ChatGPT.
  - *Worker tự làm, PM duyệt sau:* mọi lượt Suno trong lô PM đã đặt, tải cả 2 clip, đặt tên + chọn đoạn Short theo
    `naming.md`, ghép album, chọn ảnh trong các bản ChatGPT theo bước kiểm của skill, dịch title + description (`--yes`).
  - *Dừng, báo PM:* lượt tải chính thức của Suno tăng (dừng lane Suno) · Suno nhận khác prompt/model (dừng lane Suno) · server
    không kết nối được (job server chờ, không chạy `--local`).
- **Tải nhạc chỉ qua usesuno.com.** Không bao giờ bấm Download / "Unlock & Download" của Suno (mất lượt tải chính thức).
- **Điều khoản thương mại Suno: bỏ qua** (CEO 2026-09-25). CEO đã biết và chấp nhận cho mọi video. Không tra cứu lại, không nhắc,
  không hỏi, không đưa vào báo cáo hay đánh giá rủi ro.
- **Không hỏi ai nghe để chấm nhạc.** Claude không nghe được; bài hay hay dở do **retention thật** sau khi đăng.
- **Không sao chép** tên kênh, logo, branding, hình của kênh khác. Câu cầu nguyện chung dùng nguyên văn được (§1); hai video của
  mình thì không dùng cùng một câu title/thumbnail.
- **Ngôn ngữ:** mọi text nhập vào Suno và nội dung YouTube bằng **tiếng Anh**; ghi chú, trao đổi bằng tiếng Việt.
- **AI:** khai báo trong YouTube Studio (altered/synthetic content = Yes) cho mọi video kể cả Shorts, không ghi dòng AI trong description.
- **Việc nặng chạy trên server:** Whisper, đo loudness cả bài, ghép audio, render video, upscale chỉ chạy trên GPU server. Chỉ chạy
  trên Mac khi server không kết nối được **và** CEO đồng ý. Script mới thuộc loại này phải có đường chạy server từ đầu. Nhiều việc
  cùng loại: gộp vào một lệnh, không chia nhiều subagent cùng đẩy/ghi một thư mục.
- **Server dùng chung: ưu tiên GPU, trần tài nguyên.** Việc nặng chạy được trên GPU thì chạy GPU (CUDA, NVENC). Tổng mọi tác vụ
  ≤ ~60 % CPU và 60–70 % RAM: mọi runner chạy lệnh nặng trong systemd user slice `youtube.slice` (khối `LIMIT`, giống hệt nhau ở
  mọi runner). **Lính canh** `youtube-guard` (CEO 2026-09-28) chạy kèm mọi job, kill ngay job bất thường; mọi runner tự bật nó.
  Lệnh tạm trên server chạy qua `.claude/skills/pm-production/scripts/server_guard/guard.sh run '<lệnh>'`; job chết bất thường →
  `guard.sh kills` trước khi chạy lại.
- **Git chỉ giữ tooling:** skills, templates, `CLAUDE.md`, hướng dẫn kênh (`CLAUDE.md`, `channel.md`, `prompt_suno.md`, `naming.md`,
  `album_rules.md`, `visual.md`, `publish.md`, `video.json`, `translate.yaml`, `image_source/`, `model/`). Mọi thứ sinh ra khi
  làm video (`songs/`, `albums/` kể cả `short/` bên trong, `research/`, `production/`), media và `remote.env` chỉ nằm trên máy.

## 6. Nguyên tắc sáng tạo

- **Kho bài dùng lại, đóng gói không lặp.** Nhạc là một house sound dùng lại qua nhiều album; mỗi video phải khác thật ở những
  gì người xem thấy trước: lời cầu xin trên title + thumbnail, cảnh/tư thế/trang phục của ảnh, biến thể chuyển động video, bài 1
  và thứ tự bài, đoạn Short. Lý do: nhiều video na ná nhau bị YouTube xếp vào *reused / inauthentic content* (`docs/seo-youtube/01`).
- **Bài 1 và 15 giây đầu quyết định phần lớn việc người xem ở lại.** Bài 1 là bài hợp chủ đề album nhất và chưa từng mở album nào;
  video vào giọng ngay (lời đọc hoặc câu hát), không mở bằng im lặng hay fade dài.
- **Title + thumbnail là một lời cầu xin ngôi thứ nhất** về một nỗi đau cụ thể; hai câu bổ sung nhau, không trùng nhau (`publish.md`, `visual.md`).
- Trend là **nguyên liệu** (chủ đề, điều người xem cần), không phải khuôn; khác biệt mới là thứ được bấm.

## 7. Kho bài

- **Hai clip của một lượt Suno:** cùng lời = **một bài, 2 bản `v1` / `v2`** cùng tên (`<tên>_v1` / `<tên>_v2`, v1 = clip đầu của lượt;
  CEO 2026-09-28: không bao giờ mất dấu hai bản của cùng một bài); khác lời (hoặc một clip hỏng, bị bỏ) = **2 bài riêng**, mỗi bài tên
  riêng, file `<tên>` không `_vN`. Chapters hiện tên bài, không kèm V. Clip hỏng: `songs.py drop` (ghi `songs/dropped.json`).
  Bài nằm theo loại: `songs/<type>/` (mỗi `type` của `prompt_suno.md` một thư mục, vd. `songs/spoken/`, `songs/sung/`). Thẻ bài
  `songs/<type>/<slug>.md` là **nguồn chính** về bài/bản đó (tên, loại, version, lời, thời gian vào giọng, đoạn Short); do audio-song-naming ghi.
- `songs/manifest.json` là sổ của lane Suno (lượt, clip, credits, lượt tải); chỉ audio-suno-generate ghi. Nhờ tách hai người ghi,
  lane Suno và lane đặt tên chạy song song.
- Bài nằm trong album nào: `album.py pool` tính từ các `albums/*/album.md`. Dùng lại bài qua nhiều album là bình thường; giới hạn
  (bài mới tối thiểu, khoảng cách sibling, thứ tự không trùng) nằm ở `album_rules.md` của kênh.

## 8. Cấu trúc thư mục

```
youtube/
├── channel/_template/             # bộ hướng dẫn trống cho kênh mới
├── channel/<channel>/             # hướng dẫn kênh (git) + dữ liệu (chỉ trên máy); danh sách: channel/README.md
│   ├── songs/                     # kho: raw/<id8>.* (chưa tên), <type>/<slug>.wav + .md, manifest.json, catalog.md
│   └── albums/NNN-slug/           # album.md, tracks/, assembly.json/.md, audio/master/, thumbnail*, video/, youtube.md, s3-package.json
│       └── short/                 # Short của album: short.md, short.json, thumbnail.png (9:16), video/, youtube.md
├── research/                      # R&D: dữ liệu API (yt/), kho câu phrase-bank/; chỉ trên máy
├── production/                    # PM: ledger run-<date>.md, <ch>/direction.md, checklists/, results.md; chỉ trên máy
├── docs/seo-youtube/              # kiến thức SEO/vận hành kênh YouTube
├── templates/                     # mẫu album, song, track, checklist, short, youtube, thumbnail-prompt
└── .claude/skills/<nhóm>-<việc>/  # mỗi skill tự chứa code + venv + cache; remote.env (chỉ trên máy)
```

- Đánh số: album tăng dần theo thứ tự tạo (`album.py new`). Short là một phần của album (CEO 2026-09-28): `albums/NNN-slug/short/`, `shorts.py new <album>`.

## 9. Code

- **Không tự thêm comment giải thích** (comment dòng, docstring, ghi chú đầu file) trong code: code là nguồn sự thật, comment
  cũ đi nhanh hơn code. Tên hàm/biến và thông báo lỗi phải tự nói lên ý nghĩa; lý do, số đo, lịch sử thì ghi vào SKILL.md /
  references của skill hoặc file của kênh. Chỉ giữ dòng bắt buộc về kỹ thuật (shebang, pragma/`noqa`). Chuỗi `help=` của
  argparse và thông báo in ra không phải comment.

## 10. Theo dõi sau vài album

- Retention 0:15 / 0:30 / 1:00 theo loại bài mở album và theo câu title/thumbnail; chỉ thêm luật khi số liệu cho thấy cần.
- YouTube *reused content*: theo dõi Studio (monetization, cảnh báo) khi kho bài được dùng lại nhiều.
