# Suno automation — research (2026-09-23, cập nhật 2026-09-28)

> Từ 2026-09-28 skill chạy **Simple mode** (§9). Các mục về Advanced mode (§7.2, §7.3) giữ làm tài liệu tra cứu khi UI đổi.

## 1. Thay đổi lớn của Suno trong tháng 9/2026

| Ngày | Thay đổi | Ảnh hưởng |
|---|---|---|
| 03/09 | **Giới hạn download**: Free 7 bài (trọn đời), **Pro 20 bài/tháng**, Premier 60/tháng. Không cộng dồn, mua thêm được. Một bài tính 1 lần dù tải nhiều format/stems; tải lại không tính. | Không thể tải mọi candidate. 1 album 10–14 bài ≈ gần hết quota Pro. |
| 03/09 | ToS mới: chỉ được khai thác thương mại bài **đã download qua kênh chính thức**. | CEO 2026-09-25: bỏ qua (CLAUDE.md §5), mọi bài tải qua usesuno. |
| 03/09 | Audio bị mã hoá: `cdn1.suno.ai/<id>.mp3/.wav` → 403, `audio_url` → `/api/forbidden`, stream là m4a-opus mã hoá trên CloudFront. | Các cách tải qua CDN cũ đã chết. |
| 09/09 | **v6** ra mắt (v6, v6-wild cho Pro; v6-mini = model của gói Free: với tài khoản Pro vẫn **10 credits/lượt** như v6, đo 2026-09-26). **Toàn bộ model cũ (v4 → v5.5) ngừng generate.** | Album 01 **đã được làm lại toàn bộ trên v6** ngày 22/09 (xem 7.1), nên không bị ảnh hưởng. |

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
Download: `POST /api/download/authorize {item_id, item_type:"clip"}` (trừ quota) → `GET /api/download/clip/{id}?format=mp3|wav`. **Không bao giờ gọi.**

Simple mode (§9): prompt giả định ở `gpt_description_prompt` (khóa feed lưu nó), model ở `mv`, không có `prompt`/`tags`/`persona_id`.
Đã thấy request thật (2026-09-28, §10): giả định đúng; thêm `metadata.create_mode: "simple"`, `prompt: ""` (chuỗi rỗng).

## 5. Download

| Cách | Chất lượng | Điều kiện | Ghi chú |
|---|---|---|---|
| ~~UI Suno: ⋯ → Download~~ | WAV thật | Tốn 1/20 lượt | **Cấm dùng** (quyết định 23/09, mục 8). Hộp thoại: M4A/MP3/WAV/MP4/Stems (chọn nhiều), nút "Unlock & Download" trừ lượt **ngay khi bấm**. |
| **usesuno.com downloader** (đã chọn) | PCM 16-bit 48kHz, giải mã từ nguồn Opus | **Link private vẫn tải được** (đã test 23/09), không tốn quota | Chất lượng ngang bản WAV chính thức (7.4). Dùng cho cả draft lẫn final. |
| `cdn1.suno.ai/<id>.mp4` → `ffmpeg -vn -c:a copy` | Lossy (AAC ~198kbps) | Bài public có video | Vẫn trả 200 ngày 23/09; có thể bị chặn bất cứ lúc nào. |
| yt-dlp | — | — | Không hỗ trợ Suno (wontfix). |

- File WAV Album 01 (`* [usesuno.com].wav`) thực chất là Opus lossy trong vỏ WAV (48kHz, cắt tần >20.5kHz).
  Với YouTube (vốn tự nén lại Opus/AAC) thì gần như không nghe ra khác biệt, nhưng cần biết khi làm master.

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

### 7.2 Page map — Create (Advanced, v6; không dùng từ 2026-09-28)

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

## Lời public domain bị lọc (2026-09-26, album 006)

- Gõ nguyên lời hymn PD nổi tiếng ("God Will Take Care of You", 1905) → cả 2 clip lỗi "Your lyrics contain copyrighted material. Please change it and try again.", 0 credits. Cùng lời gửi lại sẽ bị từ chối lại: đừng `regenerate`, báo PM (đổi lời / thay bài).
- v6-mini (`chirp-goose`) không miễn phí với gói Pro: 1 lượt = 10 credits (1330 → 1320, 2026-09-26); bị từ chối lời = 0 credits như v6. Không dùng để sàng lọc hymn cho rẻ.

## 9. Simple mode (probe read-only 2026-09-28 + lượt Simple CEO tự chạy 2026-09-27)

Luồng mới (CEO 2026-09-28): mỗi kênh có prompt cố định theo loại bài (`channel/<ch>/prompt_suno.md`), Simple mode, Suno tự viết
lời + tên, tải cả 2 clip qua usesuno.

| Thành phần | Thấy được | Ghi chú |
|---|---|---|
| Chọn mode | `[role=tab]` "Simple" / "Advanced" / "Sounds", `aria-selected="true"` | Mode giữ theo trang; probe đã trả về Advanced như lúc mở. |
| Ô prompt | `<textarea>` duy nhất đang hiện trong khung Create (không aria-label, không attribute placeholder, `rows=1`) | Không có bộ đếm ký tự, không `maxlength`. Gõ phím 594 ký tự: đủ. Native setter + `input` 1035 ký tự: đủ, React nhận (nút Create sáng lên). |
| Model | nút hiện tên model đang chọn (vd. "v6-mini") → menu `menuitemradio`: **`v6`** (nhãn "Pro", "Powerful. Versatile. Refined. Our best model yet."), **`v6-wild`** (nhãn "Pro", "Best for experimental ideas."), **`v6-mini`** ("A free, more efficient version of premium v6 models."), trên cùng "Create Custom Model (Beta, 100 Credits)" | **Không có mục tên `v6-pro`.** Menu dùng chung cho Simple và Advanced. |
| Nút khác | "Audio", "Voice" (`aria-label="Add Voice"`), "Image", "+" (`aria-label="Add"` → menu Lyrics / Styles / Playlist / Image / Video / Audio / Voice), "Clear all form inputs", "Create song" | Luồng mới không dùng nút nào ngoài ô prompt, model và Create. |

Feed (`POST /api/feed/v3`, đọc 2026-09-28) của lượt Simple CEO chạy 2026-09-27 (một type của prompt_suno.md, 2 clip):
- `metadata.gpt_description_prompt` = prompt đã gõ, **nguyên 594 ký tự** (sha256 trùng khối prompt trong prompt_suno.md) → Suno không cắt ở độ dài này.
- `metadata.prompt` = lời Suno viết (có tag `[Verse 1]`, `[Chorus]`…, có dòng `Lead:` / `Female Ensemble:`). **Hai clip cùng lượt có cùng lời và cùng title**; khác nhau ở `metadata.tags` (Style Suno tự viết lại, mỗi clip một kiểu) và giai điệu/độ dài (193.24 s / 202.8 s).
- `model_name: chirp-hawk` (v6), `major_model_version: v6`, `metadata.task: agentic_thinking`, `control_sliders: {aug_creativity: 1}`, `negative_tags: null`, `make_instrumental: false`, `batch_index` 0/1.
- Lượt đó có gắn một Voice của kênh (`persona_id`); luồng mới không dùng Voice (skill coi Voice là lệch spec).
- Credits/lượt Simple và khóa request `v2-web`: đo ở §10.

## 10. Lượt Simple thật đầu tiên (2026-09-28: g001 không Voice, g002 Voice Male 04)

- **Form:** tab `suno.com/create` mới mở ở **Advanced** (giữ model lần trước) → luôn bấm tab "Simple". Ô prompt = `<textarea>`
  duy nhất (snapshot: `textbox multiline`); setter + `input` được nhận (Create sáng, request mang đủ 556 ký tự) dù nút
  "Clear all form inputs" vẫn xám. Model: `menuitemradio` "v6 Pro Powerful…" → nút hiện `v6`.
- **Voice trong Simple:** nút "Add Voice" → dialog "Voice" (lưới "My Voices": thẻ = `div.cursor-pointer`, không role) → bấm
  **chữ tên** Voice (bấm ảnh thẻ chỉ phát bản nghe thử "Voice Test …" trên player của trang; thẻ ngoài khung nhìn thì click
  MCP timeout → cuộn vào trước). Chọn xong: trong ô prompt có chip `span[data-thumb][title="<tên>"]` + `button
  aria-label="Remove <tên>"` (không phải "Remove selected Voice" như Advanced), nút "Add Voice" biến mất, placeholder đổi
  thành gợi ý có tên Voice. Ô prompt đang trống lúc chọn → không thấy bị ghi đè; vẫn điền prompt SAU Voice rồi đọc lại.
- **Request `v2-web` Simple:** `gpt_description_prompt` (prompt), `prompt: ""`, không có `tags`, `mv: chirp-hawk`,
  `task: agentic_thinking`, `generation_type: TEXT`, `make_instrumental: false`, `metadata.create_mode: simple`,
  `metadata.is_max_mode: false`, `metadata.control_sliders.aug_creativity: 0` (lượt tay của CEO 27/09 là 1),
  `metadata.lyrics_model: default`, `override_fields: []`, `token` (Cloudflare). Có Voice thêm: `persona_id` = id Voice,
  `persona_voice_ref` = clip gốc của Voice (Male 04 → `4ec14a83` "Voice Test C - Lamp In The Window"), `audio_refs[]`
  (`clip_id, duration_s, lyrics, style_prompt` của clip gốc đó).
- **Mạng:** Create → `POST /api/c/check` → Cloudflare challenge → `v2-web` 200 sau ~5 s; clip `complete` sau ~1–1,5 phút.
  `get_network_request` của MCP lưu body thành `<tên>.network-request` / `.network-response` (bỏ đuôi `.json` mình đặt).
- **Credits:** 10/lượt v6 Simple, có hay không Voice (1300 → 1290 → 1280). Tải chính thức 1 → 1 qua 4 lần đọc.
- **Feed:** lời ở `metadata.prompt` (2 clip cùng lời + cùng title), Voice ở `persona {id, name}` + `metadata.persona_id`.
  g001: "You Keep a Place for Me" 248.24 s / 237.20 s (2 clip cùng `tags`); g002: "There's Room at the Table" 274.8 s /
  257.6 s.
- **usesuno:** `usesuno_download.js` chạy không sửa; không hiện hộp "Before You Download"; file `<title-slug> [usesuno.com].wav`.
- **Spoken intro:** giọng đọc vào ở 3,2–6,8 s, câu hát đầu ở 16,7–18,8 s; spoken outro sau điệp khúc cuối, còn ~10–15 s đuôi.
- **Cao độ giọng lead** (Demucs htdemucs vocals + pYIN 70–800 Hz trên các dòng verse, GPU server): g001 không Voice
  158 / 205 Hz (p10–p90 73–264 / 84–276), g002 Voice Male 04: 260 Hz (155–346). p10 sát 70 Hz ở g001 → có thể lẫn lỗi
  quãng tám/bass; so bằng trung vị.

- **2026-09-28 g003 (spoken + câu long-form, 696 ký tự, Voice Male 04):** Suno lưu nguyên 696 ký tự, vẫn 10 credits; lời theo đúng
  cấu trúc xin (3 verse, 3 chorus + extended outro lặp chorus, 1 bridge, tag `[Instrumental: slide-guitar solo]`, 61 dòng so với
  50–54) → 359.56 s / 339.16 s (g001–g002: 237–275 s). Solo ~18 s sau bridge; clip 2 còn ~29 s đuôi sau lời đọc cuối (Whisper không
  dóng 5 dòng ensemble cuối). Khi một lượt cũ còn `complete` chờ tải, `js poll_feed` / `complete` phải ghi rõ gen (`--gen g003` / `complete g003`).
- **2026-09-28 g004 (sung + câu long-form, 734 ký tự, Voice Male 04):** tab `suno.com/create` mới lần này mở sẵn ở Simple + `v6` (vẫn bấm Simple cho chắc). Suno lưu nguyên 734 ký tự, 10 credits, 2 clip complete sau 50 s: 359.28 s / 359.80 s (câu long-form cũng đạt ~6 phút cho `sung`), 49 dòng lời, cùng lời + title. Hai clip chỉ lệch 0,52 s (< dung sai ±0,6 s của `ingest`): bắt buộc tải + ingest từng clip một. Không có lời đọc: chữ đầu Whisper = câu hát đầu ở 16,4 / 17,2 s (intro nhạc 16–17 s). Whisper nghe ra "Thank you." ở 358,4 s của một clip trong đoạn −74/−90 dB (im lặng cuối file) = ảo giác, không phải spoken outro: kiểm mức âm trước khi kết luận.
- **2026-09-28 g005–g010 (lô kho album 001, Voice Male 04, cùng 2 prompt long-form):** credits/lượt đổi: g005 20, g006 20, g007 20, g008 10, g009 20, g010 20 (1260 → 1150; g003–g004 cùng ngày: 10), không có clip nào khác được tạo trong lúc đó (feed 12 clip mới nhất). Có 4/6 lượt **2 clip khác lời + khác title** (g005, g006, g009, g010); g007, g008 cùng lời như trước. Lượt 10 credits đều cùng lời; lượt cùng lời g007 vẫn 20. Clip 2 của lượt khác lời hay lệch: g006 `1d347559` 4:39, 30 dòng; g009 `e607b1e5` lời lưu bắt đầu ở `[Bridge]`, 11 dòng, không verse, không spoken intro, title có tên thể loại trong ngoặc, Whisper nghe 297 chữ (hát nhiều hơn lời lưu, dóng 6/11); g010 `85b5705b` 359.6 s nhưng `metadata.prompt` + `tags` + title trống → `complete` exit 2. Độ dài: 10/11 clip còn lại 5:50–6:08.
- **2026-09-28 g011–g013:** g011 cùng lời, 10 credits (6:01/6:01); g012 cùng lời, 10 credits (5:59/5:04), request `v2-web` lần này có Cloudflare challenge (token 752 ký tự, body 2544 byte) nhưng nội dung khớp; g013 khác lời, 20 credits, clip 2 `9ec738e7` lại trống lời + title (như g010) → exit 2. Đến giờ: lượt cùng lời 10 credits (trừ g007 20), lượt khác lời luôn 20; 2/9 lượt có clip trống lời.
- **2026-09-28 g014:** cùng lời, 10 credits (5:59 / 4:50). Tổng lô g005–g014: 1260 → 1100 = 160 credits / 10 lượt; lượt khác lời 5/10 (luôn 20 credits), clip trống lời 2/10 (g010, g013: luôn là clip 2 của lượt khác lời); tải chính thức vẫn 1.
