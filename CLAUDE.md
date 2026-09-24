# CLAUDE.md

> **Trạng thái: VẬN HÀNH** (từ 2026-09-23). Giai đoạn phát triển tooling đã xong; việc chính là làm album thật và đăng lên YouTube.
> Không cải tiến skill giữa chừng: chỉ sửa khi lỗi **chặn** hoặc **làm hỏng** lần chạy (sai file, tốn credit, mất lời, số sai);
> lỗi nhỏ ghi lại để sau. Cách dùng từng skill nằm trong `.claude/skills/<skill>/SKILL.md`.
> **Giao cả lô** ("tạo 5 albums"): skill `production-manager` điều phối sub-agent qua mọi bước, tự trả lời thay chủ kênh
> (luật quyết định + luật sửa skill trong SKILL.md §5, §7 của nó), chủ kênh chỉ xem kết quả cuối.

## 1. Project

"Xưởng" làm **album nhạc ~1 giờ (50–90 phút đều được) bằng Suno** rồi đăng lên **YouTube** cho các kênh của chủ repo.
Mỗi kênh là một thư mục `channel/<ch>/` với hướng dẫn riêng; danh sách kênh và cách thêm kênh mới: `channel/README.md`.

**Nguyên tắc cốt lõi:** *lấy cảm hứng, không sao chép.* Album mới có thể cùng vibe, dòng nhạc, tempo với video tham khảo,
nhưng giai điệu, lời, tên bài, hình ảnh và danh tính kênh là của mình. Mục tiêu là **chất riêng của kênh**.

## 2. Skill và kênh

- **Skill = quy trình, dùng chung cho mọi kênh.** `.claude/skills/<skill>/` chỉ nói *làm thế nào* (lệnh, thứ tự, kiểm tra,
  luật chung của Suno/YouTube). Không ghi tên kênh, thể loại, giọng, nhân vật, màu, emoji, câu mẫu hay số đo của một kênh cụ thể.
- **Kênh = nội dung.** Mọi chi tiết *làm gì cho kênh này* nằm trong `channel/<ch>/`:

  | File | Nội dung | Skill đọc |
  |---|---|---|
  | `CLAUDE.md` | chỉ mục, âm thanh + hình ảnh tóm tắt, trạng thái kênh | mọi skill (đọc trước khi làm việc cho kênh) |
  | `channel.md` | danh tính: thể loại, persona, thế giới hình, tài nguyên | mọi skill |
  | `rules.md` | luật nhạc: house Style + Exclude, Voices, mật độ lời, tên bài cần tránh, từ vựng research, nguồn lời (khối YAML máy đọc) | youtube-music-analyzer, album-plan |
  | `visual.md` | luật hình: hằng số, khối CORE ChatGPT, trục biến thể, điều phải kiểm trên ảnh | thumbnail-prompt |
  | `publish.md` | mẫu description, tags mặc định, công thức title, emoji, pinned comment | youtube-publish |
  | `translate.yaml` | ngôn ngữ dịch title, chữ giữ nguyên, glossary | youtube-translate |
  | `video.json`, `image_source/`, `model/`, `voices/` | phong cách video, logo, ảnh nhân vật, Suno Voice | video-generator, thumbnail-prompt, album-plan |
  | `research-queue.txt` | hàng đợi link YouTube chưa analyze | youtube-music-analyzer, production-manager |

- Học được điều gì về một kênh (tên bài trùng bài có thật, lỗi ChatGPT hay gặp, tempo Suno lệch…): ghi vào file của kênh đó,
  không vào skill. Skill chỉ đổi khi *quy trình* đổi.
- Kiểm: `python3 .claude/skills/production-manager/scripts/lint_skills.py` báo mọi chỗ skill/template nhắc tới một kênh cụ thể.
- Kênh mới: chép `channel/_template/`, điền từng file với chủ kênh trước khi làm album đầu tiên.

## 3. Quy trình một album

| # | Bước | Nói với Claude | Skill | Kết quả | Chủ kênh quyết định |
|---|---|---|---|---|---|
| 1 | Research | gửi link YouTube (hàng đợi: `channel/<ch>/research-queue.txt`) | youtube-music-analyzer | `research/<slug>/` + `ideas/NNN-slug/idea.yaml` (6 tiêu chí) | giữ persona? tempo |
| 2 | Plan | "lên plan album từ idea NNN" | album-plan | `albums/NNN-slug/`: plan, lời, generation.yaml, selection.yaml | duyệt tracklist + lời + credits (`approve`) |
| 3 | Tạo nhạc | "tạo nhạc" | suno-generate | clip trong `audio/raw_tracks/` + `manifest.json` | — (tự chạy sau approve, §4 Cổng duyệt) |
| 4 | Chọn bản | "verify slot N" | verification-audio | bài được chọn → `audio/tracks/` + front matter | — (tự accept, §4 Cổng duyệt) |
| 5 | Ghép | "ghép album" | album-assembly | `audio/master/<album>.wav` + `assembly.md` | — |
| 6 | Hình | "thumbnail cho …", "render loop" | thumbnail-prompt → video-generator bước 1 | `thumbnail.png` (4K, upscale trên server) + `.jpg`, `video/loop.mp4` | — (tự chọn ảnh, §4 Cổng duyệt) |
| 7 | Video | "ghép video với nhạc" | video-generator bước 2 | video trên GPU server (không tải về Mac) | — |
| 8 | Đăng | "soạn youtube" → "zip lên S3" | youtube-publish → video-generator bước 3 | `youtube.md`; zip (video, thumbnail, youtube.md) lên S3, ghi ở `s3-package.json` | tự upload |
| 8b | Dịch title | "dịch title" (sau upload, có Video URL) | youtube-translate | title các ngôn ngữ trong `translate.yaml` lên YouTube + `title-translations.yaml` | OK trước khi ghi |
| 9 | Học | sau ~7 ngày | — | retention 0:15 / 0:30 / 1:00, CTR vào `youtube.md` | so sánh giữa các album |
| 10 | Catalog | sau khi chốt bài | `album_plan.py catalog` | `library/catalog.md` | — |

- **Thứ tự linh hoạt:** skill chỉ giao tiếp qua file. Có hai nhánh không chờ nhau: **nhạc** (2 → 5) và **hình** (6, làm ở thư mục
  idea hay album đều được); gặp nhau ở bước 7. Có thể làm theo lô (analyze nhiều link, plan vài album, làm ảnh/loop hàng loạt).
- **Chạy cả xưởng:** "tạo N albums" → `production-manager` (lane Suno/ChatGPT 1 luồng, server + plan song song, ledger `production/`, mọi kênh chung một hàng đợi).
- **Xem việc còn lại:** `album_plan.py board --channel <ch>` (mọi idea/album/single và bước tiếp theo).
- **Tiếp tục từ trạng thái hiện có** của album, không làm lại từ đầu.
- **Single** (một bài đăng riêng): `channel/<ch>/singles/NNN-slug/` (`single.md` trỏ về track gốc), audio bằng `assemble.py single`,
  ảnh riêng bằng thumbnail-prompt, youtube-publish chế độ single (không chapters, có lời, link về album).

## 4. Chuẩn bị môi trường (một lần; làm lại khi hỏng)

- **Suno:** Chrome riêng `.claude/skills/suno-generate/scripts/suno-chrome.sh` (cổng 9222, profile `~/.suno-chrome/profile`), đăng nhập
  suno.com + mở tab usesuno.com/tools/downloader. Claude điều khiển qua MCP `suno-chrome` ở **scope local**
  (`claude mcp get suno-chrome`; không để trong `.mcp.json` vì extension VS Code tự từ chối server của project). Thêm server → mở session mới.
- **ChatGPT** (thumbnail tự động): `chatgpt-chrome.sh` (cổng 9223), đăng nhập một lần. Tài khoản dùng chung: xóa thread sau khi lấy ảnh.
- **GPU server** trong LAN (bản sao repo `~/youtube-qc`): analyzer, verify (`verify.py check`),
  ghép album (`assemble.py plan/set/render/single`), render video (`video.py loop/batch/album`), upscale thumbnail 4K
  (`thumb.py fit`, SeedVR2 7B trong `~/thumbnail-prompt`) đều **mặc định chạy trên server**
  (các skill tự gọi qua `remote.sh`); `--local` mới chạy trên Mac. Mac chỉ còn việc nhẹ: điều khiển Chrome (Suno, ChatGPT),
  tải clip, text/yaml, chỉnh ảnh thumbnail, `publish.py`, `verify.py accept`, `assemble.py report/unlock`, `video.py frame`.
- **Cấu hình máy** (không vào git): mỗi skill dùng server có `.claude/skills/<skill>/remote.env`, chép từ `remote.env.example`
  cạnh nó rồi điền host `user@ip`, SSH key, thư mục trên server. Tiền tố biến theo skill: `QC_` (verification-audio, album-assembly),
  `YTA_` (youtube-music-analyzer), `VG_` (video-generator, thêm S3 bucket/region/prefix/AWS profile), `TP_` (thumbnail-prompt).
- Gói **Suno Pro**: 2.500 credits/tháng; Style ≤ 1000 ký tự; không có Suno Studio.

## 5. Luật bắt buộc

- **Credits:** bài 1 = **2 lượt Max** (4 clip), mỗi bài khác = **1 lượt thường**; ≈ 130 credits/album 10 bài, trần **250** (đủ cho album 14–15 bài).
  Lượt thêm theo **Cổng duyệt** bên dưới. Làm được nhiều album quan trọng hơn vắt bản hay nhất cho từng bài.
- **Cổng duyệt** (chủ kênh 2026-09-24; nguồn chuẩn, các skill và agent manager theo đây khi SKILL.md nói "hỏi người dùng"):
  - *Hỏi chủ kênh:* duyệt plan (`approve`) · lượt thêm khi còn chọn được bản ít lỗi nhất, hoặc sẽ vượt `budget_max_credits` ·
    chạy việc nặng trên Mac (`--local`) · upload YouTube (chủ kênh tự làm) · `auth` YouTube hết hạn · đăng nhập Suno/ChatGPT.
  - *Tự làm, không hỏi:* mọi lượt đã plan của album đã approve · accept bản verify chọn (`--why "auto-accept …"`) ·
    REGENERATE → dùng `best_available` (`--why`); chỉ tạo lại 1 lượt khi **mọi** clip hỏng thật và còn trong trần · ghép album
    (không chờ ai nghe preview) · chọn ảnh thumbnail trong các bản ChatGPT (theo các bước kiểm của thumbnail-prompt;
    sau này agent manager chọn) · dịch title (`--yes`).
  - *Dừng hẳn, báo chủ kênh:* `quota` báo lượt tải chính thức tăng · Suno nhận khác spec (exit 2) · server không kết nối được.
- **Tải nhạc chỉ qua usesuno.com**, cả bản nháp lẫn bản chốt. Không bao giờ bấm Download / "Unlock & Download" của Suno
  (mất lượt tải chính thức 20/tháng); `suno_gen.py quota` dừng cả phiên nếu lượt tải chính thức tăng. Chủ kênh đã chấp nhận rủi ro
  điều khoản thương mại của Suno (chỉ bài tải chính thức mới được dùng thương mại): nhắc một lần lúc đăng, không hỏi lại.
- **Không hỏi chủ kênh nghe để chấm nhạc.** Claude không nghe được; chọn bằng số đo (verification-audio: không hỏng, đủ lời,
  tempo sát prompt, vào lời sớm). Chủ kênh chỉ quyết định: credits, duyệt, chọn. Bài hay hay dở do **retention thật** sau khi đăng.
- **Tempo trong prompt = tempo mục tiêu**, không bù trừ theo phỏng đoán về Suno; lệch thật do verification-audio đo.
- **Không sao chép** lời, giai điệu, tên bài, branding, hình ảnh của kênh khác (copy guard trong idea/plan, `validate` kiểm).
- **Ngôn ngữ:** mọi text nhập vào Suno (Style, lời, title) và nội dung YouTube bằng **tiếng Anh**; ghi chú, trao đổi bằng tiếng Việt.
- **AI:** khai báo trong YouTube Studio (altered/synthetic content = Yes), không ghi dòng AI trong description.
- **Việc nặng chạy trên server:** script phân tích nhạc (Whisper, Demucs, beat tracking, đo tempo/loudness cả bài) hoặc tốn
  nhiều CPU/RAM (ghép audio, render video) chỉ chạy trên GPU server. Chỉ chạy trên Mac khi server không kết nối được **và** chủ kênh
  đồng ý (hỏi trước, nói rõ việc gì, mất bao lâu); chạy trên Mac làm máy nóng và treo các việc khác. Script mới thuộc loại này phải
  có đường chạy server từ đầu. Chạy song song nhiều việc: gộp vào một lệnh (vd. `verify.py check --slot all`), không chia nhiều
  subagent cùng đẩy/ghi một album.
- **Server dùng chung: ưu tiên GPU, trần tài nguyên.** Việc nặng chạy được trên GPU thì chạy GPU (model CUDA, encode NVENC,
  decode NVDEC). Tổng mọi tác vụ của project ≤ ~60 % CPU và 60–70 % RAM của server: mọi runner (`video.py`, `thumb.py`, các
  `remote.sh`) chạy lệnh nặng trong systemd user slice `youtube.slice` (khối `LIMIT`, giống hệt nhau ở mọi runner). Script
  mới chạy trên server phải đi qua slice này (chủ kênh 2026-09-24).
- **Git chỉ giữ tooling:** skills, templates, `CLAUDE.md` và hướng dẫn kênh (`CLAUDE.md`, `channel.md`, `rules.md`, `visual.md`,
  `publish.md`, `video.json`, `translate.yaml`, `voices/README.md`, `image_source/`, `model/`). Mọi thứ sinh ra khi làm video (`albums/`, `ideas/`, `singles/`, `library/`,
  `research/`, `research-queue.txt`, `voices/notes/`), media và `remote.env` chỉ nằm trên máy (`.gitignore`; thư mục trống giữ bằng `.keep`).

## 6. Nguyên tắc sáng tạo

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

**Album như một buổi diễn liền mạch (50–90 phút), không phải 10 bài rời.**
- **Anchor:** bài 1 định nghĩa giọng, ban nhạc, căn phòng, production cho cả album; **cùng một Style prompt** cho mọi bài.
- **Khóa:** giọng hát, cách hát, nhạc cụ chính, production, room, tempo family, thế giới cảm xúc.
  **Được đổi:** giai điệu, hợp âm, energy, nhạc cụ mở bài, lượng choir, solo, cấu trúc bài.
- **Arc:** energy lên dần tới cao trào (~bài 6–7) rồi hạ, kết bình yên.
- **Bám video tham khảo ~50 %:** tempo = tempo video tham khảo, Voice có cao độ gần giọng video tham khảo (`voices/README.md`),
  mật độ lời ≈ video tham khảo. Mỗi album **một bài điểm nhấn** ở slot 4 hoặc 7 (khác thường ở một trục), đăng thêm thành single.
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
│   ├── translate.yaml             # ngôn ngữ dịch title + chữ giữ nguyên + glossary (skill youtube-translate)
│   ├── voices/README.md           # các Suno Voice của kênh + cao độ đo được (voices/audio/, voices/notes/: chỉ trên máy)
│   ├── video.json, image_source/, model/   # phong cách video, logo, ảnh nhân vật 8 góc
│   │   # ── từ đây: sinh ra khi làm video, chỉ trên máy (git chỉ giữ .keep) ──
│   ├── ideas/NNN-slug/            # idea.yaml (+ idea.md, thumbnail.png, video/loop.mp4)
│   ├── albums/NNN-slug/           # plan.yaml, generation.yaml, selection.yaml, album.md, tracks/NN-slug.md,
│   │                              # assembly.yaml/.md, youtube.md, thumbnail.png, notes/,
│   │                              # video/ + audio/{raw_tracks,tracks,master}/
│   ├── singles/NNN-slug/          # single.md, thumbnail, audio/master/, video/, youtube.md
│   └── library/catalog.md         # sinh bởi album_plan.py catalog
├── research/<slug>/               # analysis.md + reference.yaml (dùng chung, một video tham khảo có thể phục vụ nhiều kênh); chỉ trên máy
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
