# Suno automation — research (2026-09-23)

> Mục tiêu: một skill đọc blueprint album (output của bước phân tích YouTube → `album.md` + `tracks/*.md`),
> gọi Suno để generate, rồi tải bản nháp về `albums/NNN/audio/raw_tracks/` cho session review.
> Mọi điểm đánh dấu **(chưa kiểm chứng)** cần test thực tế trước khi viết skill.

## 1. Thay đổi lớn của Suno trong tháng 9/2026

| Ngày | Thay đổi | Ảnh hưởng |
|---|---|---|
| 03/09 | **Giới hạn download**: Free 7 bài (trọn đời), **Pro 20 bài/tháng**, Premier 60/tháng. Không cộng dồn, mua thêm được. Một bài tính 1 lần dù tải nhiều format/stems; tải lại không tính. | Không thể tải mọi candidate. 1 album 10–14 bài ≈ gần hết quota Pro. |
| 03/09 | ToS mới: chỉ được khai thác thương mại bài **đã download qua kênh chính thức**. | Bài dùng cho YouTube bắt buộc phải tải từ Suno (UI), không qua tool bên thứ ba. |
| 03/09 | Audio bị mã hoá: `cdn1.suno.ai/<id>.mp3/.wav` → 403, `audio_url` → `/api/forbidden`, stream là m4a-opus mã hoá trên CloudFront. | Các cách tải qua CDN cũ đã chết. |
| 09/09 | **v6** ra mắt (v6, v6-wild cho Pro; v6-mini free). **Toàn bộ model cũ (v4 → v5.5) ngừng generate.** | Album 01 **đã được làm lại toàn bộ trên v6** ngày 22/09 (xem 7.1), nên không bị ảnh hưởng. |

Nguồn: help.suno.com/en/articles/13614785, 13926209, 13926081, 13924481 · suno.com/blog/suno-updates-tos · suno.com/terms-september-2026 · suno.com/release-notes

## 2. Các cách điều khiển Suno từ code

| Cách | Đăng nhập | Giữ giọng | WAV | Rủi ro ToS | Bài nằm trong library của mình | Đánh giá |
|---|---|---|---|---|---|---|
| **API chính thức** | — | — | — | — | — | **Không tồn tại.** Suno chỉ đang "explore" partner API (form: sunomusic.typeform.com/apiform). |
| **Chrome DevTools MCP điều khiển suno.com** (đã cài sẵn) | Session thật trong Chrome | Chọn Voice/Persona trên UI | Có (tốn 1 lượt) | Thấp–trung bình | ✅ | **Đề xuất.** Cần sửa selector khi Suno đổi UI. |
| Wrapper dùng cookie (`199-biotechnologies/suno-cli`, fork của `gcui-art/suno-api`) | Cookie `__client` → JWT | `persona_id` | Qua `/api/download/*` | Trung bình–cao (reverse-engineer, giải captcha) | ✅ | Fallback. `gcui-art/suno-api` gốc đã hỏng (422, audio forbidden). v6 chưa kiểm chứng. |
| Reseller API (kie.ai, sunoapi.org, AceDataCloud, RunAPI…) + MCP của họ | API key của họ | Chỉ persona tạo qua họ | Có | Cao | ❌ | **Loại.** Bài không vào library của mình, không dùng được Voice sẵn có, quyền thương mại rất đáng ngờ theo ToS mới. |

MCP servers cho Suno: chủ yếu bọc reseller (AceDataCloud/SunoMCP, CodeKeanu/suno-mcp, runapi-ai/suno-mcp) hoặc Playwright rất mới/ít sao
(sandraschi/suno-mcp, MrDoe/bettersuno-mcp). Không cái nào đủ tin cậy để phụ thuộc → tự dùng Chrome DevTools MCP.

### 2.1 Ghi chú kỹ thuật khi điều khiển UI (từ AndriiShramko/suno-ai-agent-automation-skill, test với v6 ngày 12/09)

- Ô lyrics chỉ nhận text qua synthetic `paste` event; input React cần native value setter.
- Nút Create (`aria-label="Create song"`): `.click()` không ăn, phải gọi React `onClick`.
- Slider chỉ nhận phím mũi tên, ~200ms/bước.
- Tab bị ẩn/background sẽ bỏ qua click → timeout 45s. Giữ tab Suno ở foreground.
- v6 bỏ toggle Instrumental (lyrics rỗng = instrumental). URL có thể mở ở `?mode=SIMPLE` → phải chuyển sang Advanced.
- Xác nhận đã submit thật: network có `POST /api/generate/v2-web/ → 200`. Theo dõi trạng thái: `GET /api/feed/v2?ids=…` (read-only).
- Chuẩn bị WAV có thể mất 2–10+ phút.
- Chrome của MCP dùng profile riêng (persist) → cần đăng nhập Suno 1 lần trong cửa sổ đó (đã kiểm tra 2026-09-23: **chưa đăng nhập**).

### 2.2 Web API nội bộ (tham khảo, không gọi trực tiếp)

Host `studio-api-prod.suno.com`. Generate `POST /api/generate/v2-web/` với `prompt` (lyrics), `tags` (style), `title`, `negative_tags`,
`mv` (`chirp-hawk` = v6, `chirp-hawk-wild` = v6-wild), `persona_id`, `metadata.is_max_mode`, `metadata.control_sliders{weirdness_constraint, style_weight, audio_weight}`.
Download: `POST /api/download/authorize {item_id, item_type:"clip"}` (trừ quota) → `GET /api/download/clip/{id}?format=mp3|wav`.

## 3. Giữ cùng một giọng

- **"Voice (Pro)" trong menu bài hát = "Make Persona" cũ.** Tạo từ bài đã generate → **Style Persona** (không tốn credit).
  Khi Create (Advanced) → nút **Voices** → chọn persona.
- "Voices" kiểu upload giọng thật cần xác minh đọc câu ngẫu nhiên → không dùng cho ca sĩ AI.
- ✅ **Đã kiểm chứng (spike 23/09):** Voice tạo từ bài v6 dùng được với v6, không cần xác minh, không tốn credit (xem 7.1).
- Xếp hạng độ giữ giọng: Persona/Voice > Cover (giữ cả giai điệu, chỉ dùng để "chuyển" bài Album 01 sang v6) > Use as Inspiration (yếu, bổ trợ) > Sample/Mashup (không hợp).
- Persona không phải bản sao 1:1: cùng "nghệ sĩ", không cùng từng khung giọng. Vẫn phải generate nhiều candidate và chọn theo tai.

## 4. MAX Mode

- Trên v6, **Max Mode là toggle chính thức trong Advanced mode**, Suno khuyên dùng cho bài >2 phút, cover, và
  *"keeping vocals and style consistent through the whole track"*.
- ✅ Đã đo (7.1): **Max = 20 credit/lượt, gấp đôi lượt thường (10)**. Nút Create không hiện giá.
- Hack cũ `[Is_MAX_MODE: MAX](MAX) [QUALITY: MAX](MAX) [REALISM: MAX](MAX)` ở đầu Style → không cần nữa.
- Credit Pro: 2.500/tháng, 10 credit = 1 lượt = 2 bài → ~250 lượt (≈125 nếu Max gấp đôi). **Credit không phải nút thắt; download mới là nút thắt.**
- ⇒ Ý tưởng "Max cho Anchor, tắt cho bài sau" vẫn làm được, nhưng vì Max chính là công cụ giữ giọng ổn định và credit dư,
  nên **mặc định bật Max cho mọi bài**, chỉ tắt nếu test thấy tốn gấp đôi mà không khác biệt.

### Thiết lập đề xuất (v6, Advanced)

| | Anchor | Bài sau |
|---|---|---|
| Model | v6 (không dùng v6-wild) | v6 |
| Max Mode | ON | ON (mặc định) |
| Voice / Persona | — (hoặc persona từ Album 01) | Persona của Anchor |
| Variety (mới ở v6, tự viết lại style prompt) | **0 / Off** | **0 / Off** |
| Weirdness | 20–30 | 20–30 |
| Style Influence | 70–80 | 45–55 (để persona dẫn) |
| Audio Influence | — | 60–75 (>80 bắt đầu dính giai điệu bài gốc) |
| Vocal Gender | Male | Male |
| Exclude Styles | female vocals, falsetto, autotune, rap, trap, EDM, modern pop… | giống Anchor |

## 5. Download

| Cách | Chất lượng | Điều kiện | Ghi chú |
|---|---|---|---|
| ~~UI Suno: ⋯ → Download~~ | WAV thật | Tốn 1/20 lượt | **Cấm dùng** (quyết định 23/09, mục 8). Hộp thoại: M4A/MP3/WAV/MP4/Stems (chọn nhiều), nút "Unlock & Download" trừ lượt **ngay khi bấm**. |
| **usesuno.com downloader** (đã chọn) | PCM 16-bit 48kHz, giải mã từ nguồn Opus | **Link private vẫn tải được** (đã test 23/09), không tốn quota | Chất lượng ngang bản WAV chính thức (7.4). Dùng cho cả draft lẫn final. |
| `cdn1.suno.ai/<id>.mp4` → `ffmpeg -vn -c:a copy` | Lossy (AAC ~198kbps) | Bài public có video | Vẫn trả 200 ngày 23/09; có thể bị chặn bất cứ lúc nào. |
| yt-dlp | — | — | Không hỗ trợ Suno (wontfix). |

- File WAV Album 01 (`* [usesuno.com].wav`) thực chất là Opus lossy trong vỏ WAV (48kHz, cắt tần >20.5kHz).
  Với YouTube (vốn tự nén lại Opus/AAC) thì gần như không nghe ra khác biệt, nhưng cần biết khi làm master.
- Các cách "tải không tốn quota" (usesuno, mp4 CDN, service worker `/_sw-mango/passthrough`) đi vòng qua giới hạn/bảo vệ nội dung →
  rơi vào vùng ToS cấm ("circumvent content protections", "obtain content through unauthorized means"). Không dùng cho bản final; cân nhắc kỹ nếu dùng cho draft.

## 6. Kiến trúc skill đề xuất (bản nháp)

```
/suno-generate <album-dir> [--tracks 01,03] [--candidates 2]
  1. Đọc album.md (Style prompt, persona, settings) + tracks/NN-*.md (title, lyrics + arrangement tags)
  2. Chrome DevTools MCP → suno.com/create (Advanced, v6) → điền Style/Lyrics/Title/Exclude, chọn Voice, sliders, Max
  3. Create → xác nhận v2-web 200 → poll feed/v2 đến khi "complete" → lấy 2 clip id / lượt
  4. Ghi albums/NNN/audio/raw_tracks/manifest.json: track, clip_id, suno_url, settings, credit, trạng thái
  5. Dán link suno.com/song/<id> (private cũng được) vào usesuno → WAV → albums/NNN/audio/raw_tracks/<slug> <clip-id-8>.wav
     (đọc billing/info trước/sau: download_usage không được đổi; nếu đổi thì dừng ngay)
  6. Session review đọc manifest + audio → chấm → copy bài được chọn từ raw_tracks/ sang audio/tracks/ (không tải lại)
Anchor: chạy trước, chờ duyệt, tạo Voice từ Anchor, rồi mới chạy các bài sau.
```

## 7. Spike (2026-09-23)

| # | Việc | Kết quả |
|---|---|---|
| 1 | Đăng nhập Suno trong suno-chrome | ✅ Đã đăng nhập (`@nguyentienanhxxx`, Pro, kỳ 22/09 → 22/10). |
| 2 | Map UI Create v6 | ✅ Xem 7.2. |
| 3 | Voice (Pro) từ Anchor | ✅ Voice tạo từ một clip v6 của Anchor chọn được với v6, `persona_type: vox`. Voice của từng kênh: `channel/<ch>/voices/README.md`. |
| 4 | Generate test + đo credit | ✅ Không cần tốn credit: suy ra từ lịch sử (7.1). |
| 5 | ~~Tải thử WAV qua UI~~ | ❌ **Bỏ theo quyết định của chủ repo (chỉ dùng usesuno).** ⚠️ Trong spike đã lỡ bấm "Unlock & Download" cho WTNL (`3ab17d0d`) trước khi có quyết định này → **đã trừ 1/20 lượt tháng 9–10**. File vẫn tự tải về `~/Downloads` (`When The Night Is Long.wav` + `.m4a`), dùng để so chất lượng ở 7.4. |

### 7.1 Những gì đọc được từ library (API read-only)

- **Album 001 = 10 clip v6 (`chirp-hawk`) tạo ngày 22/09, đều bật Max Mode.** WTNL có 3 lượt không dùng Voice; từ lúc tạo Voice xong thì 9 bài còn lại dùng Voice đó.
  Duration của 10 file WAV trong `audio/tracks/` khớp với clip được giữ lại (lệch < 0.01s) → đã điền `suno_url` vào `tracks/*.md`.
- **Credit thực tế:** kỳ này đã dùng 420 = 18 lượt không Max + 12 lượt Max ⇒ **không Max = 10, Max = 20 credit/lượt (gấp đôi)**. Dùng Voice không tốn thêm credit.
  2.500 credit/tháng ≈ **125 lượt Max** (250 bài nháp). Credit vẫn không phải nút thắt.
- Các clip Album 001 hiện đều **private** (`is_public: false`); usesuno vẫn tải được, không cần Publish.
- `billing/info` → `download_usage`: `current_period_downloads_used`, `..._limit` (20), `additional_download_remaining` (7). Dùng để skill **kiểm tra quota không bị tụt** sau mỗi lần chạy.
- `control_sliders.aug_creativity` = slider Variety (0–4). Album 001: 0 cho WTNL/Valley, 1–2 cho các bài sau.
- Mặc định danh sách clip ở Create có "Filters (3)", chỉ hiện 6 bài → skill nên đọc qua `POST /api/feed/v3` (`{"limit":100}`, clip đã trash thì thêm `filters.trashed`, phân trang bằng `cursor`), token lấy từ cookie `__session`.

### 7.2 Page map — Create (Advanced, v6)

| Thành phần | Selector / cách thao tác | Ghi chú |
|---|---|---|
| Model | button "v6" → menu: `v6` / `v6-wild` / `v6-mini` / **Create Custom Model (Beta, 100 credit)** | Custom Model = tạo model từ bài upload, chưa thử. |
| Voice | button "Add Voice" → dialog "Voice" → bấm tên voice | ⚠️ **Chọn Voice sẽ ghi đè Style box bằng style của voice** → luôn điền Style *sau* khi chọn Voice. Có "Remove selected Voice". |
| Lyrics | textbox "Lyrics editor" (tối đa 5000 ký tự) | Để trống = instrumental. |
| Style | textarea (placeholder là gợi ý style, không có label cố định), đếm `N/1000` | |
| More Options | button "More Options" (expandable) | |
| Exclude styles | textbox "Exclude styles" | |
| Vocal Gender | button "Male" / "Female" | Không chọn = để tự do. |
| **Duration** (mới) | "Auto" / "Custom" → slider 10–360s + textbox `m:ss` | Album 001 dài 5–6 phút → nên đặt Custom. |
| Max Mode | button "Off" / "On" | |
| Weirdness, Style Influence | slider 0–100 (mặc định 50) | |
| Audio Influence | slider 0–100 (mặc định 25) | Chỉ hiện khi đã chọn Voice/audio. |
| Variety | slider 0–4 (mặc định 1 = "Normal") | |
| **Personalize** (mới) | "My Taste" / "Off" / "On" | Để Off. |
| Title | textbox "Song Title (Optional)" | |
| Create | `button[aria-label="Create song"]` | **Không hiện số credit** trên nút hay tooltip. |

- Toggle đang bật có class `hxc-btn-variant-standard-legacy`, tắt là `hxc-btn-variant-tertiary-legacy` (không có `aria-pressed`).
- Menu ⋯ của bài: Remix ▸ (**Cover, Extend, Reuse Prompt**, Reverse, Adjust Speed), Edit ▸, Publish, Share ▸, Download *(cấm dùng)*, Manage ▸, Add to Queue/Playlist, Song Radio, Report, Move to Trash.
  Submenu ▸ không mở được bằng hover/phím mũi tên qua MCP; nút "Remix" ở panel phải thì mở được.

### 7.3 Test thực tế (2026-09-23)

**Tải qua usesuno (link private):** `usesuno.com/tools/downloader/` → dán `https://suno.com/song/<id>` → "Find download options"
→ "Audio (Choose format)" → **WAV** → (lần đầu có hộp "Before You Download" → "Continue download") → file về `~/Downloads/<slug> [usesuno.com].wav`.
- Tải lại Track 02 Album 001: **giống từng byte** file đang có (cùng SHA-256). Quota tải không đổi (1 → 1).
- Sau mỗi lần tải có modal "Download complete" chặn thao tác tiếp theo → tải lại trang trước khi làm bài kế.
- 2 clip cùng title thì cùng tên file → phải đổi tên (thêm id clip) ngay sau mỗi lần tải.
- Nút trên trang usesuno render chậm; script phải chờ nút xuất hiện trước khi click.

**Tạo bài qua suno-chrome (1 lượt thường):** Voice của kênh, Style của album đầu tiên, Max Off, Male, Duration Auto, Variety 1.
- Credits 2.220 → **2.210 (đúng 10)**. Ra 2 clip: `78999681…` (3:05) và `90ea9304…` (3:16), title "Leave The Light On".
- Luồng mạng: `POST /api/c/check` → (Cloudflare challenge chạy ngầm, không cần làm gì) → `POST /api/generate/v2-web/ → 200` → poll `feed/v3` đến `status: complete` (~1–2 phút).
- **Lyrics editor là Lexical (contenteditable):** synthetic paste và `execCommand('insertText')` đều không giữ xuống dòng.
  Cách chạy được: click vào editor → `Meta+A`, `Backspace` → gõ phím thật (`type_text`). Xuống dòng giữ đúng; chỉ mất 1 dòng trống.
- Title và Exclude: `fill` bình thường. Nút Create: click chuột thật (MCP `click`) là chạy.
- ⚠️ **Variety = 1 ("Normal") làm Suno viết lại Style của cả 2 clip** (vd. "user's own recorded male baritone…"). Muốn giữ đúng Style prompt thì đặt **Variety = 0**.

### 7.4 Chất lượng: usesuno vs Download chính thức (WTNL)

| So sánh (đã căn thời gian) | Lệch thời gian | Chênh gain | Sai khác còn lại |
|---|---|---|---|
| WAV chính thức vs M4A chính thức (Opus 136kbps) | 0 | 0 dB | −38 dB |
| WAV chính thức vs WAV usesuno | 312 mẫu (6.5ms) | usesuno to hơn ~1.6 dB | −37 dB |

- Cả 3 file đều cắt tần ở ~20 kHz. Bản usesuno khác bản WAV chính thức chỉ ở mức sai số giải mã Opus, **không có khác biệt nghe được**.
- Bản usesuno to hơn ~1.5 dB, peak −0.3 dBFS (bản chính thức: −3.1 dBFS). Khi master nên hạ gain một chút để không clip.

### 7.5 Đã gói thành skill (2026-09-23)

1. ✅ Skill `suno-generate` (`../SKILL.md`): `scripts/suno_gen.py` + `scripts/js/*.js` (các đoạn JS lấy từ spike ở trên).
2. ✅ Input = `<album>/generation.yaml` (mẫu `templates/generation.yaml`), tổng hợp từ `idea.yaml` + research này.
3. ⏳ Chưa chạy thật lần nào qua skill: lần đầu cần kiểm lại `read_form.js` bằng screenshot, và ghi lại tên các trường
   slider/duration trong body `POST /api/generate/v2-web/` (§2.2 mới là suy đoán) để `check-request` kiểm được hết.

## 8. Quyết định & câu hỏi mở

- **Đã chốt (2026-09-23):** tải nhạc bằng **usesuno.com** (chất lượng Opus lossy là đủ, Album 01 nghe ổn).
  usesuno tải được cả link **private** (trang của họ ghi "public only" nhưng test thực tế 23/09 vẫn được).
- **Chrome cho Suno (đã chốt 2026-09-23):** Chrome do plugin DevTools MCP tự mở bị Google chặn đăng nhập ("This browser may not be secure"),
  và không đọc được cookie tạo từ Chrome thường (Puppeteer chạy `--use-mock-keychain`). Suno không có login email; login bằng phone
  sẽ tạo tài khoản mới. ⇒ Dùng **Chrome riêng** mở bằng [suno-chrome.sh](../scripts/suno-chrome.sh) (profile `~/.suno-chrome/profile`, cổng 9222)
  + MCP server `suno-chrome` (scope local: `claude mcp add suno-chrome -s local -- npx chrome-devtools-mcp@1.9.0 --browser-url=http://127.0.0.1:9222`; không để trong `.mcp.json` vì extension VS Code tự từ chối server của project) gắn vào qua `--browser-url`. Đăng nhập Google 1 lần trong Chrome đó.
- **Đã chốt (2026-09-23): KHÔNG bao giờ bấm Download / "Unlock & Download" của Suno**, kể cả cho bài final. Mọi lượt tải đều qua usesuno.
  Skill không được có bước nào chạm vào hộp Download hay `/api/download/*`.
- Có nâng lên Premier (60 lượt/tháng) hay mua thêm lượt tải khi làm >1 album/tháng?
- Format đầu ra của skill phân tích YouTube (session khác) → cần chốt schema blueprint làm input.
