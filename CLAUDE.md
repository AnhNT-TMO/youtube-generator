# CLAUDE.md

## 0. Công ty

Project là một công ty sản xuất nhạc cho các kênh YouTube. Mục tiêu: nhiều người nghe thật, bền lâu, cải tiến liên tục; mọi việc
cân giá trị với công sức. Chuỗi chỉ huy: **CEO → PM (trưởng phòng) → nhân viên** (skill + agent).

| Vai | Là ai | Làm gì |
|---|---|---|
| **CEO** | chủ repo | đặt mục tiêu, gửi ý tưởng (brief) khi muốn, quyết các việc "trình CEO"; tự upload YouTube, đăng nhập Suno/ChatGPT, `auth` YouTube. Chỉ hỏi PM |
| **PM** | skill `production-manager`; thuê nhân viên bằng cách spawn agent | **nguồn sự thật duy nhất của sản xuất, chịu trách nhiệm chất lượng và kết quả từng video** |
| **R&D** | `youtube-trend-research` (+ `youtube-music-analyzer` đo nhạc) | quét trend, theo dõi trend đang làm, đưa số liệu + ý tưởng (chủ đề, thumbnail, Shorts) cho PM; không quyết |
| **Đội sản xuất** | các skill bước 2–8c ở §3 | làm đúng brief của PM; sáng tạo trong khuôn brief + luật kênh |

**PM là source of truth.** Từ tài nguyên R&D, số liệu kênh và brief của CEO, PM quyết định mọi thứ về video và ghi thành văn bản:
- **Định hướng kênh** (`production/<ch>/direction.md`, PM viết, sửa khi có bài học): chiến lược chủ đề, hướng nhạc (giọng, tempo,
  nhánh, experiment đang chạy), hướng đóng gói (giọng văn title/description, cách xoay vòng thumbnail, cách làm Shorts, version đang
  thử), lịch đăng, các bài học từ kết quả. Nhân viên đọc như luật.
- **Brief từng video** (`brief` trong `idea.yaml` → `plan.yaml`; Short: `short.md`): câu chuyện, chủ đề trend, `decisions` (nhạc,
  title, description, thumbnail, Shorts, version, mục tiêu view). Nhân viên làm theo brief; **không có chuyện PM bảo A mà làm B**.
- **Checklist từng album** (`production/<ch>/checklists/<NNN-slug>.md`, mẫu `templates/checklist.md`): các việc từ trend tới kết quả
  7 ngày, PM tick và ghi kết quả một dòng sau mỗi việc. CEO đọc file này để biết album đang ở đâu.
- Nhân viên được sáng tạo trong phần brief để ngỏ (lời, giai điệu, cảnh cụ thể, câu chữ), luôn theo luật kênh + §5–§7. Brief thiếu,
  mâu thuẫn hoặc không làm được → dừng và hỏi PM (`BLOCKED`), không tự quyết, không hỏi CEO. Mọi chỗ SKILL.md ghi "hỏi người dùng /
  chủ kênh" nghĩa là hỏi PM, trừ việc chỉ CEO làm được (upload, đăng nhập, `auth`). CEO chạy thẳng một skill thì CEO đóng vai PM.
- **CEO chỉ hỏi PM.** Session nào CEO hỏi về sản xuất (đang làm gì, vì sao chọn vậy, kết quả ra sao, sắp làm gì) thì trả lời với vai
  PM, từ hồ sơ của PM (direction, brief, ledger `production/`, `results.md`, board, R&D `state.md`), không đẩy câu hỏi sang nhân viên.
- **Trình CEO:** mở kênh mới, đổi hợp đồng kênh, đổi ngân sách hoặc gói Suno, đổi quy trình/skill ngoài lỗi chặn, năng lực mới.

**CEO đánh giá PM bằng hai thứ**, mọi báo cáo của PM trả lời hai thứ này trước:
1. Video có bám trend (hoặc brief CEO gửi) không.
2. View có cải thiện không: video mới so với trung vị các video cùng loại của kênh ở cùng tuổi (48 giờ, 7 ngày).

**Vòng trách nhiệm** (như một phòng sản xuất thật): R&D quét → PM quyết + viết brief → đội sản xuất làm → PM duyệt đầu ra theo brief
→ đăng → PM đọc kết quả ở 48 giờ và 7 ngày (`results.md`) → video dưới kỳ vọng thì **PM phân tích nguyên nhân theo từng trục**
(trend/thời điểm, đóng gói/CTR, 30 giây đầu/retention, nhạc/thời lượng xem, phát hành/Shorts) → sửa `direction.md` cho video sau →
báo CEO đã đổi gì và vì sao.

- **Hợp đồng kênh:** ranh giới ở `channel/<ch>/channel.md` → *Hợp đồng kênh*. Bên trong, luật nội dung của kênh (`rules.md`,
  `visual.md`, `publish.md`) là **mặc định**; PM được đổi bằng experiment/version có khai báo và đo được. Luật YouTube và §5 không bao giờ phá.
- **Xếp một trend:** ngoài hợp đồng kênh → ứng viên kênh mới (`research/trends/new-channels.md`); đổi nhánh nhạc trong hợp đồng →
  album experiment; đổi nội dung lời → chủ đề album; đổi cách trình bày → version. Trend đang tắt thì bỏ: vào muộn không ăn được.
- **Đánh giá từng trục:** mỗi video ghi chủ đề, version đóng gói, experiment nhạc; không đổi hai trục cùng lúc trên cùng loại video;
  so bằng trung vị nhiều video, vì một video nổ hay chìm phần lớn là may rủi.
- **Ngân sách:** credits Suno là tài nguyên khan nhất. Không đủ nhịp đăng thì PM dùng library tối đa (§7) trước khi giảm nhịp.
- **Cải tiến liên tục:** sau mỗi lô PM spawn một agent review quy trình và trình CEO **chỉ những thay đổi đáng làm** (≤ 5 mục, mỗi mục
  giá trị kỳ vọng, công sức, rủi ro). CEO duyệt mới sửa. Trong lúc chạy chỉ sửa skill khi lỗi **chặn** hoặc **làm hỏng** lần chạy
  (sai file, tốn credit, mất lời, số sai); lỗi nhỏ ghi lại cho lần review.
- **Báo cáo cho CEO:** ngắn, tiếng Việt: hai tiêu chí ở trên, đã làm gì, quyết định PM đã đưa ra, bài học, việc cần CEO.

## 1. Project

"Xưởng" làm **album nhạc 1–1,5 giờ (60–90 phút sau khi ghép; thiếu thì thêm bài) bằng Suno** rồi đăng lên **YouTube** cho các kênh của chủ repo.
Mỗi kênh là một thư mục `channel/<ch>/` với hướng dẫn riêng; danh sách kênh và cách thêm kênh mới: `channel/README.md`.

**Nguyên tắc cốt lõi:** *lấy cảm hứng, không sao chép.* Album mới có thể cùng vibe, dòng nhạc, tempo với các video tham khảo của trend,
nhưng giai điệu, lời, tên bài, hình ảnh và danh tính kênh là của mình. Mục tiêu là **chất riêng của kênh**.

## 2. Skill và kênh

- **Skill = quy trình, dùng chung cho mọi kênh.** `.claude/skills/<skill>/` chỉ nói *làm thế nào* (lệnh, thứ tự, kiểm tra,
  luật chung của Suno/YouTube). Không ghi tên kênh, thể loại, giọng, nhân vật, màu, emoji, câu mẫu hay số đo của một kênh cụ thể.
- **Kênh = nội dung.** Mọi chi tiết *làm gì cho kênh này* nằm trong `channel/<ch>/`:

  | File | Nội dung | Skill đọc |
  |---|---|---|
  | `CLAUDE.md` | chỉ mục, âm thanh + hình ảnh tóm tắt, trạng thái kênh | mọi skill (đọc trước khi làm việc cho kênh) |
  | `channel.md` | danh tính + hợp đồng kênh (§0): thể loại, persona, thế giới hình, tài nguyên | mọi skill |
  | `rules.md` | luật nhạc: house Style + Exclude, Voices, mật độ lời, tên bài cần tránh, từ vựng research, nguồn lời (khối YAML máy đọc) | youtube-music-analyzer, album-plan |
  | `visual.md` | luật hình: hằng số, khối CORE ChatGPT, trục biến thể, điều phải kiểm trên ảnh, ảnh dọc Shorts | thumbnail-prompt |
  | `publish.md` | mẫu description, tags mặc định, công thức title, emoji, pinned comment, giờ đăng, mẫu Shorts | youtube-publish, youtube-shorts |
  | `translate.yaml` | ngôn ngữ dịch title + description, chữ giữ nguyên, glossary | youtube-translate |
  | `video.json`, `image_source/`, `model/`, `voices/` | phong cách video, logo, ảnh nhân vật, Suno Voice | video-generator, thumbnail-prompt, album-plan |
  | `trends.yaml` | ngách để R&D quét: từ khóa, bộ lọc kênh, chủ đề, nhánh nhạc | youtube-trend-research |
  | `research-queue.txt` | link YouTube CEO gửi, chờ đo (vào reference set của chủ đề hợp) | youtube-music-analyzer, production-manager |

- Học được điều gì về một kênh (tên bài trùng bài có thật, lỗi ChatGPT hay gặp, tempo Suno lệch…): ghi vào file của kênh đó,
  không vào skill. Skill chỉ đổi khi *quy trình* đổi.
- Kiểm: `python3 .claude/skills/production-manager/scripts/lint_skills.py` báo mọi chỗ skill/template nhắc tới một kênh cụ thể.
- Kênh mới (CEO duyệt, §0): chép `channel/_template/`, điền từng file với CEO trước khi làm album đầu tiên.

## 3. Quy trình một album

| # | Bước | Nói với Claude | Skill | Kết quả | Ai quyết (§0) |
|---|---|---|---|---|---|
| 1 | Research trend (R&D, §0) | PM đặt; hoặc gửi link YouTube (hàng đợi: `channel/<ch>/research-queue.txt`) | R&D; đo nhạc 3–5 video nổi bật bằng youtube-music-analyzer | báo cáo trend `research/trends/` + `ideas/NNN-slug/idea.yaml` | PM: chủ đề, version (§0) |
| 2 | Plan | "lên plan album từ idea NNN" | album-plan | `albums/NNN-slug/`: plan, lời, generation.yaml, selection.yaml | duyệt tracklist + lời + credits (`approve`) |
| 3 | Tạo nhạc | "tạo nhạc" | suno-generate | clip trong `audio/raw_tracks/` + `manifest.json` | — (tự chạy sau approve, §5 Cổng duyệt) |
| 4 | Chọn bản | "verify slot N" | verification-audio | bài được chọn → `audio/tracks/` + front matter | — (tự accept, §5 Cổng duyệt) |
| 5 | Ghép | "ghép album" | album-assembly | `audio/master/<album>.wav` + `assembly.md` | — |
| 6 | Hình | "thumbnail cho …", "render loop" | thumbnail-prompt → video-generator bước 1 | `thumbnail.png` (4K, upscale trên server) + `.jpg`, `video/loop.mp4` | — (tự chọn ảnh, §5 Cổng duyệt) |
| 7 | Video | "ghép video với nhạc" | video-generator bước 2 | video trên GPU server (không tải về Mac) | — |
| 8 | Đăng | "soạn youtube" → "zip lên S3" | youtube-publish → video-generator bước 3 | `youtube.md`; zip (video, thumbnail, youtube.md) lên S3, ghi ở `s3-package.json` | tự upload |
| 8b | Dịch title + description | "dịch title" (sau upload, có Video URL) | youtube-translate | title + description các ngôn ngữ trong `translate.yaml` lên YouTube + `title-translations.yaml` | — (tự ghi, `--yes`) |
| 8c | Shorts | "làm shorts cho album NNN" | youtube-shorts (ảnh dọc: thumbnail-prompt; video: video-generator `short`) | `shorts/NNN-slug/`: ảnh dọc 9:16, video 1080×1920 ≤ 3 phút, `youtube.md`; zip lên S3 cạnh album | tự upload + gắn Related video |
| 9 | Học | sau ~7 ngày | — | retention 0:15 / 0:30 / 1:00, CTR vào `youtube.md` | so sánh giữa các album |
| 10 | Catalog | sau khi chốt bài | `album_plan.py catalog` | `library/catalog.md` | — |

- **Thứ tự linh hoạt:** skill chỉ giao tiếp qua file. Có hai nhánh không chờ nhau: **nhạc** (2 → 5) và **hình** (6, làm ở thư mục
  idea hay album đều được); gặp nhau ở bước 7. Có thể làm theo lô (analyze nhiều link, plan vài album, làm ảnh/loop hàng loạt).
- **Chạy cả xưởng:** "tạo N albums" → `production-manager` (lane Suno/ChatGPT 1 luồng, server + plan song song, ledger `production/`, mọi kênh chung một hàng đợi).
- **Xem việc còn lại:** `album_plan.py board --channel <ch>` (mọi idea/album/single và bước tiếp theo).
- **Tiếp tục từ trạng thái hiện có** của album, không làm lại từ đầu.
- **Gói đăng mỗi album, trần mỗi ngày** (CEO 2026-09-25): **1 album + 1 single + 1 Short**, đăng cùng một ngày; mỗi ngày tối đa
  1 album, 1 single, 1 Short, để đánh giá dần và không bị xem là spam. Single = bài điểm nhấn (slot 4/7; album không có điểm
  nhấn → bài đạt số đo verify tốt nhất ngoài bài 1): tên mới, không tranh tìm kiếm với album. Short = điệp khúc bài 1 → Related
  video là album. Thứ tự đăng: album → single → Short (video đích phải có trước). Giờ đăng: `channel/<ch>/publish.md`.
  Single/Short dự phòng (làm từ trước) chỉ đăng vào ngày không có album mới, vẫn trong trần mỗi ngày.
- **Short** (video dọc ≤ 3 phút cắt từ một bài): `channel/<ch>/shorts/NNN-slug/` (`short.md` trỏ về track gốc + video đích),
  ảnh dọc **mới** bằng thumbnail-prompt (kiểu ảnh theo Shorts đang được xem nhiều trong ngách: `trend.py shorts`), video riêng
  bằng `video.py short`. Luật chính sách + cách làm: `docs/seo-youtube/09-shorts.md`.
- **Single** (một bài đăng riêng): `channel/<ch>/singles/NNN-slug/` (`single.md` trỏ về track gốc), audio bằng `assemble.py single`,
  ảnh riêng bằng thumbnail-prompt, youtube-publish chế độ single (không chapters, có lời, link về album).

## 4. Chuẩn bị môi trường (một lần; làm lại khi hỏng)

- **Suno:** Chrome riêng `.claude/skills/suno-generate/scripts/suno-chrome.sh` (cổng 9222, profile `~/.suno-chrome/profile`), đăng nhập
  suno.com + mở tab usesuno.com/tools/downloader. Claude điều khiển qua MCP `suno-chrome` ở **scope local**
  (`claude mcp get suno-chrome`; không để trong `.mcp.json` vì extension VS Code tự từ chối server của project). Thêm server → mở session mới.
- **ChatGPT** (thumbnail tự động): `chatgpt-chrome.sh` (cổng 9223), đăng nhập một lần. Tài khoản dùng chung: xóa thread sau khi lấy ảnh.
- **GPU server** trong LAN (bản sao repo `~/youtube-qc`): analyzer, verify (`verify.py check`),
  ghép album (`assemble.py plan/set/render/single`), render video (`video.py loop/batch/album/short`), upscale thumbnail 4K
  (`thumb.py fit`, SeedVR2 7B trong `~/thumbnail-prompt`) đều **mặc định chạy trên server**
  (các skill tự gọi qua `remote.sh`); `--local` mới chạy trên Mac. Mac chỉ còn việc nhẹ: điều khiển Chrome (Suno, ChatGPT),
  tải clip, text/yaml, chỉnh ảnh thumbnail, `publish.py`, `verify.py accept`, `assemble.py report/unlock`, `video.py frame`.
- **Cấu hình máy** (không vào git): mỗi skill dùng server có `.claude/skills/<skill>/remote.env`, chép từ `remote.env.example`
  cạnh nó rồi điền host `user@ip`, SSH key, thư mục trên server. Tiền tố biến theo skill: `QC_` (verification-audio, album-assembly),
  `YTA_` (youtube-music-analyzer), `VG_` (video-generator, thêm S3 bucket/region/prefix/AWS profile), `TP_` (thumbnail-prompt).
- Gói **Suno Pro**: 2.500 credits/tháng; Style ≤ 1000 ký tự; không có Suno Studio.

## 5. Luật bắt buộc

- **Credits:** bài 1 = **2 lượt Max** (4 clip), mỗi bài khác = **1 lượt thường**; ≈ 150–170 credits/album 12–14 bài, trần **250** (đủ cho album 14–15 bài).
  Lượt thêm theo **Cổng duyệt** bên dưới. Làm được nhiều album quan trọng hơn vắt bản hay nhất cho từng bài.
- **Cổng duyệt** (nguồn chuẩn, các skill theo đây khi SKILL.md nói "hỏi người dùng"; §0: người được hỏi là PM):
  - *Hỏi PM:* duyệt plan (`approve`) · lượt thêm khi còn chọn được bản ít lỗi nhất, hoặc sẽ vượt `budget_max_credits` ·
    mọi lựa chọn sáng tạo brief chưa nói.
  - *Chỉ CEO:* chạy việc nặng trên Mac (`--local`) · upload YouTube · `auth` YouTube hết hạn · đăng nhập Suno/ChatGPT.
  - *Tự làm, không hỏi:* mọi lượt đã plan của album đã approve · accept bản verify chọn (`--why "auto-accept …"`) ·
    REGENERATE → dùng `best_available` (`--why`); chỉ tạo lại 1 lượt khi **mọi** clip hỏng thật và còn trong trần · ghép album
    (không chờ ai nghe preview) · chọn ảnh thumbnail trong các bản ChatGPT (theo các bước kiểm của thumbnail-prompt;
    sau này agent manager chọn) · dịch title + description (`--yes`).
  - *Dừng, báo PM* (PM xử lý theo production-manager §5–§6, CEO biết qua báo cáo): `quota` báo lượt tải chính thức tăng
    (dừng cả lane Suno của lần chạy) · Suno nhận khác spec (exit 2: dừng job Suno của album đó) · server không kết nối
    được (job của server chờ, thử lại định kỳ; không chạy `--local`).
- **Tải nhạc chỉ qua usesuno.com**, cả bản nháp lẫn bản chốt. Không bao giờ bấm Download / "Unlock & Download" của Suno
  (mất lượt tải chính thức 20/tháng); `suno_gen.py quota` dừng lane Suno nếu lượt tải chính thức tăng.
- **Điều khoản thương mại Suno: bỏ qua** (CEO 2026-09-25). ToS Suno từ 3/9/2026 chỉ cho khai thác thương mại bài tải qua kênh
  chính thức của Suno và cấm tải bằng cách khác; CEO đã biết và chấp nhận cho mọi video (album, single, Shorts). Không tra cứu lại,
  không nhắc, không hỏi, không đưa vào báo cáo hay đánh giá rủi ro.
- **Không hỏi ai nghe để chấm nhạc.** Claude không nghe được; chọn bằng số đo (verification-audio: không hỏng, đủ lời,
  tempo sát prompt, vào lời sớm). Bài hay hay dở do **retention thật** sau khi đăng.
- **Tempo trong prompt = tempo mục tiêu**, không bù trừ theo phỏng đoán về Suno; lệch thật do verification-audio đo.
- **Không sao chép** lời, giai điệu, tên bài, branding, hình ảnh của kênh khác (copy guard trong idea/plan, `validate` kiểm).
- **Bài public domain được dùng** (CEO 2026-09-25): hymn/spiritual có lời + nhạc đã hết bản quyền (Mỹ: xuất bản ≥ 95 năm trước,
  vd. Amazing Grace, It Is Well, Blessed Assurance). Bài PD vẫn là bản thu mới của mình (`source: new` + khối `public_domain` trong
  slot: tác phẩm, tác giả, năm, link nguồn như hymnary.org). Hai cách: `mode: lyrics` = gõ lời PD vào Suno, Suno làm giai điệu mới;
  `mode: cover` = Suno **Cover** từ một nguồn mình có quyền: bản mình tự dựng từ bản nhạc PD, clip Suno của mình, hoặc bản thu đã PD
  (Mỹ: xuất bản ≥ 100 năm trước). **Không** dùng bản thu/bản phối hiện đại của người khác, kể cả khi bài gốc là PD. Hymn PD hay bị
  Content ID của label khác claim nhầm: giữ bằng chứng trong slot để kháng nghị (`docs/seo-youtube/07`). `validate` kiểm khối này.
- **Ngôn ngữ:** mọi text nhập vào Suno (Style, lời, title) và nội dung YouTube bằng **tiếng Anh**; ghi chú, trao đổi bằng tiếng Việt.
- **AI:** khai báo trong YouTube Studio (altered/synthetic content = Yes) cho mọi video kể cả Shorts, không ghi dòng AI trong description.
- **Việc nặng chạy trên server:** script phân tích nhạc (Whisper, Demucs, beat tracking, đo tempo/loudness cả bài) hoặc tốn
  nhiều CPU/RAM (ghép audio, render video) chỉ chạy trên GPU server. Chỉ chạy trên Mac khi server không kết nối được **và** CEO
  đồng ý (hỏi trước, nói rõ việc gì, mất bao lâu); chạy trên Mac làm máy nóng và treo các việc khác. Script mới thuộc loại này phải
  có đường chạy server từ đầu. Chạy song song nhiều việc: gộp vào một lệnh (vd. `verify.py check --slot all`), không chia nhiều
  subagent cùng đẩy/ghi một album.
- **Server dùng chung: ưu tiên GPU, trần tài nguyên.** Việc nặng chạy được trên GPU thì chạy GPU (model CUDA, encode NVENC,
  decode NVDEC). Tổng mọi tác vụ của project ≤ ~60 % CPU và 60–70 % RAM của server: mọi runner (`video.py`, `thumb.py`, các
  `remote.sh`) chạy lệnh nặng trong systemd user slice `youtube.slice` (khối `LIMIT`, giống hệt nhau ở mọi runner). Script
  mới chạy trên server phải đi qua slice này (chủ kênh 2026-09-24).
- **Git chỉ giữ tooling:** skills, templates, `CLAUDE.md` và hướng dẫn kênh (`CLAUDE.md`, `channel.md`, `rules.md`, `visual.md`,
  `publish.md`, `video.json`, `translate.yaml`, `trends.yaml`, `voices/README.md`, `image_source/`, `model/`). Mọi thứ sinh ra khi làm video (`albums/`, `ideas/`, `singles/`, `shorts/`, `library/`,
  `research/`, `research-queue.txt`, `voices/notes/`), media và `remote.env` chỉ nằm trên máy (`.gitignore`; thư mục trống giữ bằng `.keep`).

## 6. Nguyên tắc sáng tạo

**Sáng tạo đặt trên hết, giữ vibe kênh** (CEO 2026-09-25). Mỗi video khác thật với các video trước của kênh: câu chuyện,
title track, cảnh thumbnail, cách dùng chữ, bảng màu, bài và đoạn của Short. Cái giữ nguyên chỉ là hợp đồng kênh và thế giới
hình/âm của nó. Trend là **nguyên liệu** (chủ đề, điều khán giả cần, một yếu tố đang thắng), không phải khuôn: không lặp khuôn
đối thủ, không lặp khuôn của chính mình. Lý do: kênh làm hàng loạt mà video na ná nhau bị YouTube xếp vào *inauthentic content*
(`docs/seo-youtube/01`), và trong ngách mọi kênh giống nhau thì khác biệt mới là thứ được bấm.

**Bài 1 và 15 giây đầu của video quyết định phần lớn việc người xem ở lại.**
- Bài 1 (title track) luôn là **bài mới**, mạnh nhất, là **title của video**; không bao giờ dùng bài tái sử dụng để mở video.
- 10–15 giây đầu của **video** (tính từ 0:00 video, không phải đầu file Suno) phải có "chữ ký" ngay: giọng, hook hoặc motif đặc trưng.
  Không mở bằng im lặng, fade-in dài hay pad nhạt. Mức 0–15 s không nhỏ hơn thân bài quá 4 dB. "Cuốn" ≠ to hay nhanh: với nhạc chậm
  là có cảm xúc ngay, đầy đặn, rõ ràng.
- Khi generate: tag intro ngắn / cold open để giọng vào sớm. Khi ghép: được cắt intro Suno để giọng vào ~giây 4–8.
- Mọi bài ghi `vocal_entry_seconds`.

**Luật riêng của kênh nằm ở `channel/<ch>/`** (nhạc: `rules.md` = Style + Exclude mặc định, mật độ lời, chữ và tên bài cần
tránh, cách album được khác mặc định; hình: `visual.md`; đăng: `publish.md`). House sound chỉ là **mặc định**: album được cố ý khác (giọng cao, tempo lạ, energy đột biến…)
để thử phản ứng người nghe, miễn khai báo `experiment` trong plan. Mục tiêu là người nghe nhiều, không phải mình thấy hay.

**Album như một buổi diễn liền mạch (60–90 phút), không phải 10 bài rời.**
- **Độ dài** (chủ kênh 2026-09-25; album đã có master giữ nguyên): master **≥ 60 phút**, ≤ 90 phút.
  Plan tính sẵn phần ghép cắt đi (`target.assembly_keep`, `validate --final` chặn khi ước lượng < 60 phút) → thiếu thì thêm bài
  (bài mới hoặc library trong giới hạn §7), không kéo dài chuyển bài. Thumbnail album mang dòng thời lượng của kênh (`visual.md`).
- **Anchor:** bài 1 định nghĩa giọng, ban nhạc, căn phòng, production cho cả album; **cùng một Style prompt** cho mọi bài.
- **Khóa:** giọng hát, cách hát, nhạc cụ chính, production, room, tempo family, thế giới cảm xúc.
  **Được đổi:** giai điệu, hợp âm, energy, nhạc cụ mở bài, lượng choir, solo, cấu trúc bài.
- **Arc:** energy lên dần tới cao trào (~bài 6–7) rồi hạ, kết bình yên.
- **Bám nhóm video tham khảo ~50 %** (reference set: trung vị 3–5 video nổi bật của chủ đề trend, không bám một video):
  tempo = tempo trung vị của nhóm, Voice có cao độ gần giọng nhóm (`voices/README.md`), mật độ lời ≈ nhóm. Mỗi album **một bài điểm nhấn** ở slot 4 hoặc 7 (khác thường ở một trục), đăng thêm thành single.
- **Tempo:** mỗi album **một dải tempo** (bài nhanh nhất / chậm nhất ≤ 20 %, liền kề ≤ 8 %). Giữa các album dải tempo được khác nhau
  và nên khác nhau: kênh đa dạng tempo, không kéo mọi album về một tempo chung.
- **Chuyển bài đa dạng:** không lặp một kiểu mở bài; hạn chế crossfade giọng-vào-giọng.
- **Style vs tag trong lời:** Style = *ai đang chơi* (thể loại, giọng, nhạc cụ, production, room, những thứ tránh);
  tag trong lời = *bài này sắp xếp thế nào* (intro, nhạc cụ vào trước, lúc drums vào, outro).
- *Giữ NGHỆ SĨ nhất quán, thay đổi ARRANGEMENT, làm mỗi TRANSITION có chủ đích.*

## 7. Thư viện & tái sử dụng bài

Album mới = **1 title track mới + tối đa 4 bài lấy từ library + còn lại tạo mới** (album 10 bài: ≥ 6 bài mới), để người nghe cũ
không gặp lại quá nhiều bài quen. Library dùng để tiết kiệm credits trong giới hạn đó, không phải để trộn cả album.
`album_plan.py validate` kiểm các luật này; ngoại lệ có chủ đích ghi vào `waivers` kèm lý do:
- Kiểm tra library **trước** khi generate bất kỳ bài nào ngoài bài 1.
- Mọi bài trong album cùng `vocal_persona` và `band_profile`.
- **Tối đa 4 bài library** trong một album (`reuse_total`), bài 1 không bao giờ là bài library.
- **Mỗi album cũ góp tối đa 2 bài** (nên 1) vào album mới — tính cả bài album đó từng dùng lại (người nghe cũ nhận ra).
- Liền kề: energy lệch ≤ 2, tempo lệch ≤ 8 %, không cùng `intro_type`; hook không trùng hook/title của bài khác; bài "echo" không đặt liền nhau.
- Metadata bài: front matter `tracks/NN-slug.md` là **nguồn chính** (trường: `templates/track.md`); `library/catalog.md` chỉ là bảng tra, sinh lại bằng `catalog`.

## 8. Cấu trúc thư mục

```
youtube/
├── channel/_template/             # bộ hướng dẫn trống cho kênh mới
├── channel/<channel>/             # danh sách: channel/README.md
│   ├── CLAUDE.md                  # chỉ mục + trạng thái của kênh (đọc trước)
│   ├── channel.md                 # danh tính, tài nguyên
│   ├── rules.md                   # luật làm nhạc của kênh (nguồn chuẩn cho analyzer + album-plan; validate đọc khối YAML)
│   ├── visual.md, publish.md      # luật hình (thumbnail-prompt), luật đăng YouTube (youtube-publish)
│   ├── research-queue.txt         # hàng đợi link chưa analyze; chỉ trên máy
│   ├── translate.yaml             # ngôn ngữ dịch title + description, chữ giữ nguyên, glossary (skill youtube-translate)
│   ├── trends.yaml                # ngách R&D quét: từ khóa, bộ lọc kênh, chủ đề, nhánh nhạc (skill youtube-trend-research)
│   ├── voices/README.md           # các Suno Voice của kênh + cao độ đo được (voices/audio/, voices/notes/: chỉ trên máy)
│   ├── video.json, image_source/, model/   # phong cách video, logo, ảnh nhân vật 8 góc
│   │   # ── từ đây: sinh ra khi làm video, chỉ trên máy (git chỉ giữ .keep) ──
│   ├── ideas/NNN-slug/            # idea.yaml (+ idea.md, thumbnail.png, video/loop.mp4)
│   ├── albums/NNN-slug/           # plan.yaml, generation.yaml, selection.yaml, album.md, tracks/NN-slug.md,
│   │                              # assembly.yaml/.md, youtube.md, thumbnail.png, notes/,
│   │                              # video/ + audio/{raw_tracks,tracks,master}/
│   ├── singles/NNN-slug/          # single.md, thumbnail, audio/master/, video/, youtube.md
│   ├── shorts/NNN-slug/           # short.md, short.json, thumbnail.png (9:16), video/, youtube.md
│   └── library/catalog.md         # sinh bởi album_plan.py catalog
├── research/<slug>/               # analysis.md + reference.yaml của một video đo được, hoặc set-<ch>-<topic>-<date>/ (reference set); chỉ trên máy
├── research/trends/<ch>/          # R&D: watchlist, snapshots, topics, reports/, state.md; research/trends/new-channels.md; chỉ trên máy
├── docs/seo-youtube/              # kiến thức SEO/vận hành kênh YouTube (chính sách, thiết lập kênh, analytics, metadata, sự cố, checklist)
├── templates/                     # mẫu idea, plan, generation, selection, album, track, youtube, single, thumbnail-prompt
└── .claude/skills/<skill>/        # mỗi skill tự chứa code + venv + cache; remote.env (chỉ trên máy) + remote.env.example
```

- Đánh số: idea và album tăng dần theo thứ tự tạo; id bài `<album-prefix>-NN`. Plan album xong thì idea chuyển `status: promoted`.
- Bản nháp: `audio/raw_tracks/<slug> <clip-id-8>.wav` + `manifest.json` (clip ↔ slot ↔ lượt ↔ settings ↔ lý do); id8 phân biệt 2 clip cùng lượt.
  Bài được chọn chép sang `audio/tracks/<slug>.wav`, liên kết qua field `audio` của track.

## 9. Code

- **Không tự thêm comment giải thích** (comment dòng, docstring, ghi chú đầu file) trong code: code là nguồn sự thật, comment
  cũ đi nhanh hơn code và làm sai lệch. Tên hàm/biến và thông báo lỗi phải tự nói lên ý nghĩa; lý do, số đo, lịch sử thì ghi
  vào SKILL.md / references của skill hoặc file của kênh. Chỉ giữ dòng bắt buộc về kỹ thuật (shebang, `# -*- coding`,
  pragma/`noqa` cần thiết). Chuỗi `help=` của argparse và thông báo in ra không phải comment.

## 10. Theo dõi sau vài album

- Đối chiếu retention với cách mở bài 1, 4 tiêu chí chọn clip và 6 tiêu chí analyzer; chỉ thêm tiêu chí khi số liệu cho thấy cần.
- YouTube "reused content" khi nhiều album dùng lại bài từ library.
