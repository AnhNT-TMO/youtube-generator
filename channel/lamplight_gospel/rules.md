# Luật làm nhạc: Lamplight Gospel

**Nguồn chuẩn duy nhất** khi plan, viết lời và generate cho kênh này (skill album-plan đọc file này; `album_plan.py validate`
đọc khối YAML ở cuối). Chỉ ghi **quyết định**, không ghi phương án; mỗi luật một dòng kèm nguồn + ngày.
Không có file luật Suno chung nào khác: cách Suno đọc Style/tag/lời cho thể loại này nằm ở §5–§9. Channel khác có rules.md riêng.

**Cách bổ sung:** sau mỗi lần chủ kênh nghe, mỗi lần verification-audio đo, mỗi album có retention, hoặc khi Claude thấy lỗi
lặp lại → thêm một dòng vào đúng mục (và vào khối YAML nếu máy kiểm được), ghi nguồn. Luật không còn đúng thì xóa, không để hai bản.

## 1. House sound = MẶC ĐỊNH, không phải khuôn

- Style mặc định = khối nghệ sĩ của Album 001 (`wtnl-v1`), bỏ câu "No …" (v6 bỏ qua phủ định trong Style), đưa các mục
  cần tránh sang Exclude. *Nguồn: chủ kênh chọn 2026-09-23; 10 bài Album 001 đã chốt và đăng.*
- Style một album = `<genre_lead>, <cụm mood của album>. <vocal_line của Voice đã chọn> <band_block> Slow <meter> groove, {bpm} BPM.`
  Album chỉ đổi cụm mood, meter, tempo và (theo Voice) câu giọng. Exclude = `house_style.exclude`.
  Câu giọng của Male 02–04 = đúng câu Style đã tạo ra clip gốc gần cao độ đo được (voice lab 2026-09-23) [try: đo lại ở album đầu dùng Voice đó].
- **Album được khác mặc định** (giọng cao vút, tempo lạ, energy đột biến, ban nhạc khác…) để thử phản ứng người nghe, nhưng
  phải **khai báo** trong `plan.yaml → experiment` (trục nào khác, khác thế nào, lấy từ đặc điểm nào của video tham khảo,
  xem gì trong retention). Không khai báo mà Style/Exclude khác mặc định = lỗi `house_style`.
  *Nguồn: chủ kênh 2026-09-23: "muốn thử nhiều cách … xem phản ứng người nghe thế nào, họ thích cái gì".*
- Giọng có sẵn (Suno Voice, cao độ đo được): `voices/README.md` (Male 01 ~197 Hz = mặc định; Male 02/03/04 = 263/278/314 Hz).
  Voice chọn theo f0 của video tham khảo (§1b), không cần khai báo experiment. *Nguồn: voice lab 2026-09-23.*
- Video tham khảo có đặc điểm khác hẳn house sound (giọng cao, tempo nhanh, lời dày…) → đề xuất làm experiment (open question
  kèm khuyến nghị), không tự ép về mặc định. *Nguồn: như trên.*
- **Trong một album** vẫn một nghệ sĩ, một Style, một dải tempo (nhanh nhất / chậm nhất ≤ 20 %). **Giữa các album** tempo,
  energy, concept nên khác nhau: xem `album_plan.py themes --channel lamplight_gospel` trước khi chọn. *Nguồn: chủ kênh 2026-09-23.*

## 1b. Bám video tham khảo ~50 % + bài điểm nhấn

- **Tempo = tempo cảm nhận của video tham khảo** (`reference.yaml criteria.tempo.felt_bpm_median`), lệch ≤ `reference_follow.tempo_max_dev_pct`.
  Không nhích về phía Album 001. **Giọng:** chọn Voice (bảng `voices` dưới) có f0 gần f0 của video tham khảo (lệch ≤ `voice_f0_max_dev_pct`).
  **Mật độ lời** ≈ của video tham khảo (lệch ≤ `words_per_min_max_dev_pct`), vẫn dưới trần §2.
  Muốn khác → khai báo `experiment` (album) hoặc `waivers`. *Nguồn: chủ kênh 2026-09-23 ("khoảng 50 % là video tham khảo về tempo, giọng + lời").*
- **Mỗi album một bài điểm nhấn** (`plan.yaml → highlight`): slot 4 hoặc 7, bài mới, khác thường ở MỘT trục (quãng giọng cao hơn / nâng tông
  chorus cuối, energy vọt, mở a cappella, tempo nhanh hơn rõ, choir dẫn…) nhưng vẫn cùng nghệ sĩ + cùng Voice. Bài này được miễn luật
  bước energy/tempo/intro với bài kề và không tính vào dải tempo của album. Sau khi album xong, bài điểm nhấn **đăng thêm thành single**
  (`singles/NNN-slug`) để đo phản ứng riêng; `youtube.md` ghi mốc thời gian của nó để đọc retention đúng chỗ.
  *Nguồn: chủ kênh 2026-09-23 ("bài 4 hoặc 7 … đăng single luôn để xem phản ứng người nghe").*
- **Thời lượng album 50–90 phút** đều chấp nhận: Suno không ra đúng độ dài từng bài; số bài theo độ dài bài của video tham khảo.
  *Nguồn: chủ kênh 2026-09-23.*
- Kiểm tra: `album_plan.py validate` (`reference_follow`, `voice`, `highlight`).

## 2. Mật độ lời

- Số từ tối đa của một bài = `lyrics.words_per_beat_max` × (bpm/60) × (độ dài − `lyrics.sung_allowance_s`).
  Album 001: Suno hát 320–389 từ/bài, 1.05–1.34 từ mỗi nhịp (trung vị 1.19), phần có giọng = độ dài − ~55 s (intro ~30 s +
  outro ~22 s); cả 10 bài đều được chọn. *Nguồn: số đo `albums/001-…/assembly.yaml` + lyrics, 2026-09-23.*
  Vượt `words_per_beat_max` = lỗi `density`; vượt `words_per_beat_warn` = cảnh báo. Album nhanh hơn thì được nhiều chữ hơn.
- Sau mỗi album: cập nhật hai con số này từ kết quả verification-audio (tỉ lệ dòng Whisper nghe được, giọng vào/ra thật).

## 3. Chữ và tên bài cần tránh

- Title/hook không trùng (kể cả gần trùng) tên bài có thật (`known_titles`) hay tên bài của **mọi** video tham khảo trong kênh
  (copy_guard của mọi album) = lỗi `known_title`; một dòng lời chứa nguyên cụm đó = cảnh báo.
- Trước khi build, tra WebSearch từng title + hook mới (`"<cụm>" song`), ghi kết quả vào `slot.title_check`
  (vd. `"2026-09-23 clear"` hoặc `"2026-09-23 hit: <bài>, đã đổi"`). `validate --final` báo lỗi khi thiếu.
  Tìm thấy bài trùng mới → thêm vào `known_titles`. *Nguồn: đợt kiểm tra 5 album 2026-09-23 tìm ra 15 trường hợp bằng WebSearch.*
- Từ Suno hay tự chèn và từ đọc hai cách (`avoid_words`, `heteronyms`): không dùng trong title/hook/lời. *Nguồn: cộng đồng v6 (Neon, Echo, Silver, Shadow… Suno tự chèn).*

## 4. Trùng ý giữa các album

- Trước khi chọn concept: đọc `album_plan.py themes --channel lamplight_gospel` (concept, title track, Kinh Thánh, hình ảnh,
  bài kết, cách mở bài 1, thumbnail của mọi album) và chọn thứ chưa có. `validate` cảnh báo khi trùng đoạn Kinh Thánh hoặc
  trùng hình ảnh chủ đạo của title track / bài kết với album khác. *Nguồn: đợt kiểm tra 2026-09-23.*
- Plan nhiều album cùng lúc: chạy một lượt đối chiếu chéo trước khi đưa chủ kênh duyệt.

## 5. Viết Style (Suno v6)

Nguồn: (Suno) = tài liệu Suno · (cộng đồng) = báo cáo thử nghiệm v6 tổng hợp 2026-09 · (đo) = đo trong repo này.
- Thứ tự: thể loại → giọng → ban nhạc → production/room → groove + tempo; chữ đầu nặng ký hơn. Tối đa 2 thể loại. (cộng đồng)
- Tempo là con số kèm nhịp (`Slow 6/8 groove, {bpm} BPM`), đúng tempo mục tiêu. Dùng Custom duration. (cộng đồng; CLAUDE.md §4)
- Mỗi ý một chữ (warm/dark/soft trùng nghĩa → giữ một), ~10 mô tả là đủ. Phẩy giữa mô tả, chấm giữa khối; không `; / "`. (cộng đồng)
- Không tên nghệ sĩ (Suno tự thay). **Không viết "No X"** trong Style (v6 bỏ qua phủ định) → cho vào Exclude. (Suno; cộng đồng)
- Chọn Voice sẽ ghi đè ô Style → suno-generate gõ Style sau Voice. Vocal Gender = Male mạnh hơn chữ trong Style. Variety 0 (khác 0 là
  Suno tự viết lại Style). (đo 2026-09-23; Suno)
- Giọng mới (chỉ khi experiment): quãng giọng + 3–4 chất giọng nghe được (`male tenor, bright, slightly raspy`); tránh
  `breathy / whispered / delicate / intimate` (kéo giọng trẻ đi) và > 2 chữ cảm xúc. (cộng đồng)

## 6. Tag trong lời

- Mọi đoạn đều có tag; đoạn không tag bị coi là verse. Tin được: `[Verse N] [Pre-Chorus] [Chorus] [End]`; vừa: `[Bridge] [Break] [Outro]`;
  không tin được: `[Intro]` trơn. (cộng đồng)
- Chỉ dẫn nằm TRONG ngoặc sau dấu hai chấm, 1–3 ý, ≤ 3 nhạc cụ, viết khẳng định: `[Verse 2: bass and brushed drums enter]`,
  không `no guitar`. **Dòng nào ngoài ngoặc Suno đều hát** (bài 01 Album 001 từng để dòng chỉ dẫn trơn). (cộng đồng; đo)
- Đoạn nhạc không lời ghi rõ nhạc cụ (`[Instrumental Break: clean blues guitar, Hammond underneath]`); mỗi đoạn thêm ~20–40 s. (cộng đồng)
- Kết bài: `[Instrumental Outro: <nhạc cụ còn lại>, instrumental only, long sustained final chord]` rồi `[End]`; thiếu `[End]` Suno kéo dài
  hoặc cắt ngang. (cộng đồng)

## 7. 15 giây đầu

- Album 001: không tag nào đưa giọng vào trước giây 16 (kể cả `[Cold Open]`: 28–29 s; tốt nhất `[Short Intro: … one brief piano phrase
  before the vocal]`: 16.6 s). → Mốc giọng ~4–8 s của video đạt ở bước ghép (album-assembly cắt intro theo `vocal_at_s`); không tốn dòng lời
  hay lượt generate để ép bằng tag. Vẫn ghi tag intro ngắn, đúng nhạc cụ mở (định hình âm intro, `intro_type` phải đa dạng). (đo 2026-09-23)
- Cách chưa thử, chỉ làm biến thể bài 1: không tag intro · câu đầu là tiếng ngân `(Mmm, mmm)` · hook là câu hát đầu · `[Intro 2]`.
  verification-audio chọn bản vào lời sớm hơn. Có kết quả → ghi vào đây.
- **Đã đo (album 002 bài 1, v6 + Max + Voice Male 04, 2026-09-23):** `[Short Intro: one held piano chord, lead vocal at once]` + hook là
  câu hát đầu → lời vào giây 6–8 (2/2 clip); verse-cold `[Verse 1: lead vocal at once, …]` không intro → giây 29–34 (2/2 clip).
  → Hook-first là cách mở mặc định cho bài 1.
- **Tempo đo được (cùng lượt):** prompt 43 (6/8) → 52.5–54.8 BPM đo được (+22–28 %, 4/4 clip). Chủ kênh chọn giữ prompt theo plan
  (album đồng đều với bài 1); cập nhật khi có thêm số đo của các bài khác.

## 8. Hình dạng lời

- Câu ngắn: verse 6–9 âm tiết, chorus ≤ ~11, các câu tương ứng lệch ≤ 2 âm tiết. Verse 8 dòng = 2 khổ 4 dòng, vần ABCB/ABAB, vần gần được. (cộng đồng)
- Chorus giống hệt nhau mọi lần (đổi chữ = đổi giai điệu); chorus cuối chỉ đổi cue trong tag. Hook có thể lặp 2–3 lần. (cộng đồng)
- Verse 2 phải tiến lên (thời gian, mức độ, góc nhìn); bridge 2–4 dòng = một sự thật mới, không diễn lại chorus. (cộng đồng)
- Kết câu bằng danh từ/động từ có trọng âm, không `the / of / and`. Bè `(…)` dùng ít, chủ yếu chorus cuối. Không VIẾT HOA. (cộng đồng)
- Từ đọc hai cách (`heteronyms`): viết lại câu, không đổi chính tả (verify so Whisper với lời gốc). Rút gọn chỉ với đại từ/trợ động từ
  (`I'm, don't, I'll`). Số viết bằng chữ. (cộng đồng; verification-audio)

## 9. Clip hỏng → sửa gì (mỗi lượt đổi MỘT thứ)

| Triệu chứng | Sửa trước tiên |
|---|---|
| Giọng trẻ/nhẹ đi | Style bỏ `intimate/soft`, thêm `weathered, lived-in`; cue `[Verse 1: weathered low baritone]` từng đoạn (experiment) |
| Giọng chung chung | Thay chữ cảm xúc bằng chất giọng nghe được (`raspy chest voice`) |
| Hát vội / bỏ dòng | Lời dày: rút câu, bớt dòng (§2), không phải lỗi slider |
| Trôi sang country | Đưa `Hammond B3`, `gospel` lên sớm hơn trong Style |
| Choir quá lớn | Cue `soft choir` chỉ ở chorus cuối |
| Intro dài | Không tạo lại: bước ghép cắt intro (§7) |

## Khối máy đọc (album_plan.py validate)

```yaml
house_style:
  version: lg-house-v2
  genre_lead: "Slow Christian gospel blues, Southern gospel soul"
  vocal_line: >-               # câu giọng mặc định (Male 01); album dùng Voice khác lấy voices[].vocal_line
    Warm mature male baritone, deep, soulful, slightly raspy, emotional but restrained, natural gospel phrasing.
  band_block: >-               # ban nhạc + phòng thu: cố định cho mọi album
    Warm Hammond B3 organ, vintage piano, clean expressive blues guitar, round bass, soft live drums, subtle gospel
    choir only at emotional peaks. Warm analog production, dark intimate tone, rich low mids, natural small-church
    ambience. Spacious arrangement, guitar responses between vocal lines.
  exclude: "female vocals, youthful vocals, falsetto, autotune, rap, trap, EDM, modern pop, pop worship, country, blues rock, cinematic orchestra, cinematic choir, modern punchy drums"
  meter_default: "6/8"         # khi plan chưa có sound.tempo.meter
  groove_line: "Slow {meter} groove, {bpm} BPM."   # câu cuối của Style; {meter} từ plan, {bpm} điền lúc generate
research:                      # youtube-music-analyzer: từ vựng của thể loại kênh này
  intro_vocab: [vocal_hum, vocal, choir, hammond, piano, acoustic_guitar, slide_guitar, electric_guitar, full_band, strings]
  genre_words: [gospel, blues, soul, vintage, christian, worship, prayer, prayers, psalm, psalms, praise, hymn, hymns,
                delta, southern, deep, dark, oldies, faith, spiritual, relaxing, sleep, healing, peace, peaceful, "r&b", rnb]
                               # chữ chỉ thể loại trong title video tham khảo: cụm chỉ gồm các chữ này không bị copy guard chặn
sources:                       # nguồn mà lời bài diễn giải (idea slots[].source_ref, plan slot.source_ref)
  kind: scripture              # tên gọi trong báo cáo
  numbered:                    # tham chiếu có số trong title video tham khảo → copy_guard.source_avoid
    pattern: '\b(?:psalms?|ps\.?)\s*(\d{1,3})'
    format: "Psalm {n}"
lyrics:
  words_per_beat_max: 1.35     # Album 001 cao nhất 1.34 (bài 02), vẫn được chọn
  words_per_beat_warn: 1.20    # Album 001 trung vị 1.19
  sung_allowance_s: 55         # intro ~30 s + outro ~22 s (Album 001 đo)
reference_follow:              # §1b; số của video tham khảo đọc từ research/<slug>/reference.yaml (sources.research của plan)
  tempo_max_dev_pct: 5
  voice_f0_max_dev_pct: 15
  words_per_min_max_dev_pct: 20
highlight:
  slots: [4, 7]
  required: true
voices:                        # Suno Voice (riêng tư) + f0 trung vị đo được; chi tiết voices/README.md
  - name: "Midnight Gospel Soul - Male 01"
    id: 7ebd54d4-454a-4c15-a2e4-973196ae6170
    f0_hz: 197
    persona: warm-baritone-v1  # identity.vocal_persona của album dùng Voice này (library chỉ trộn bài cùng persona)
    default: true              # vocal_line = house_style.vocal_line
  - name: "Midnight Gospel Soul - Male 02 (263 Hz)"
    id: d6d41da0-039d-49a1-85ae-2a781c402bba
    f0_hz: 263
    persona: high-baritone-m02-v1
    vocal_line: "Warm mature male high baritone, strong and soulful, raspy, gritty, emotional but restrained, natural gospel phrasing."
  - name: "Midnight Gospel Soul - Male 03 (278 Hz)"
    id: 36098469-a386-47b8-b301-1e58ec0dd771
    f0_hz: 278
    persona: tenor-m03-v1
    vocal_line: "Mature male tenor lead, raspy and gritty, soulful gospel belting, rasp on the long notes, natural gospel phrasing."
  - name: "Midnight Gospel Soul - Male 04 (314 Hz)"
    id: ecd7feab-681f-4367-86d8-44454fd63f48
    f0_hz: 314
    persona: male04-high-tenor-v1
    vocal_line: "Mature male high tenor, raspy soaring gospel voice, gritty high chest belts, rasp on the long notes, natural gospel phrasing."
avoid_words: [neon, echo, ghost, silver, shadow, whisper, crystal, velvet]
heteronyms: [tear, tears, wind, winds, wound, wounds, live, lead, bow, close, content, desert, present, read]
known_titles:                  # bài có thật (title hoặc câu nổi tiếng). Thêm khi tìm thấy; ghi nguồn sau dấu #
  - Amazing Grace
  - I'll Fly Away
  - Peace in the Valley
  - Precious Lord Take My Hand
  - How Great Thou Art
  - It Is Well
  - Blessed Assurance
  - Wade in the Water
  - Swing Low
  - Just a Closer Walk
  - Running Over                          # Seth Sykes, thánh ca thiếu nhi (verify 002)
  - The Rain Came Down and the Floods Came Up   # "The Wise Man Built His House" (verify 002)
  - Tomorrow Belongs to Me                # Cabaret (verify 002)
  - Still Calls Me Son                    # John Waller 2007 (verify 003)
  - You Came Running                      # VOUS Worship "Prodigal Praise" (verify 003)
  - When My Last Song Is Sung             # Merle Haggard 1977 (verify 004)
  - Brand New Man                         # Brooks & Dunn 1991 (verify 004)
  - Mending Fences                        # Restless Heart 1993 (verify 004)
  - Scarlet to Snow                       # Jukebox Saints 2024 (verify 004)
  - He Meant It For My Good               # Dottie Peoples (verify 005)
  - He Turned It Around for My Good       # Testimony Joe (verify 005)
  - I Will Praise Him Again               # CityAlight, Psalm 42 (verify 005)
  - Breathe on These Dry Bones            # Emmaus (verify 005)
  - Fire's Gonna Fall                     # weareworship.com (verify 006)
  - Fire Fall Down                        # Hillsong UNITED (verify 006)
  - Ring of Fire                          # Johnny Cash (verify 006)
  - Bank the Fire                         # Zydeco Flames 2003 (verify 006)
  - The Steadfast Love of the Lord        # thánh ca (verify 006)
  - She Stayed                             # Alexandra Kay 2023 (fix 002)
  - On An Ordinary Tuesday                 # Buddy Jewell 2003 (fix 002)
  - Rain On A Tin Roof                     # Little Big Town 2010 (fix 002)
  - Roof Over My Head                      # Sugar Minott 1992 (fix 002)
  - Let The Creek Rise                     # Evans/Fleck/Douglas 2024 (fix 002)
  - Blessings On Blessings                 # Newsboys 2021 (fix 002)
  - Put Another Chair At The Table         # Mills Brothers 1944 (fix 002)
  - Little Things Mean a Lot               # Kitty Kallen 1954 (fix 002)
  - Letter On The Table                    # Delta Fuse 2021 (fix 002)
  - I'll Leave It In Your Hands            # Saga 2003 (fix 002)
  - My Cup Runneth Over                    # Ed Ames 1967 (fix 002)
  - Take These Blues                       # Rob Garland (fix 004)
  - I Still Hear Mama Praying              # Chester D.T. Baldwin 2000 (fix 004)
  - Is Your All on the Altar               # E. A. Hoffman 1905 (fix 004)
  - Lay It on the Altar                    # Tamela Mann 2009 (fix 004)
  - When Sunday Morning Comes              # Sunday Morning 2016 (fix 004)
  - I Sing the Blues                       # Etta James (fix 004)
  - Porch Swing Angel                      # Muscadine Bloodline 2016 (fix 004)
  - Just You 'n' Me                        # Chicago 1973 (fix 004)
  - White as Wool                          # Daniel Howard 2013 (fix 004)
  - Not a Stain on Me                      # Big Tuck 2004 (fix 004)
  - Church Bells                           # Carrie Underwood 2015 (fix 004)
  - Dashboard Jesus                        # Carly Pearce 2023 (fix 004)
  - Same Old Strings                       # Dan Fowler 2006 (fix 004)
  - Lay My Cards Down                      # Aoife Carton (fix 004)
  - Clean Heart                            # Bryan & Katie Torwalt (fix 004)
  - More Than I Can Carry                  # Tapping the Grey Sky 1998; Benjamin Tod 2019 (fix 005)
  - Why So Downcast Oh My Soul             # Great Songs of Praise 1994 (fix 005)
  - Rock Bottom                            # 11th Hour (fix 005)
  - Scars That Sing                        # ChaptrTwo 2025 (fix 005)
  - I Sing About My Scars                  # Brad Irons 2023 (fix 005)
  - You Healed Every Scar                  # Praise Soundwaves 2025 (fix 005)
  - When My Feet Almost Slipped            # Psalm 73 worship (fix 005)
  - Empty Barn                             # Jeff Corle 2022 (fix 005)
  - Tired of Being Strong                  # nhiều bài 2023-2026 (fix 005)
  - Rattle                                 # Elevation Worship (fix 005)
  - Still Green                            # Ronelle 2022 (fix 006)
  - Hills of Fire                          # Sarah Kinsley 2022 (fix 006)
  - The Hills Are On Fire                  # Shaw & Ashdown 2016 (fix 006)
  - Follow the Fire                        # Academy Worship 2021 (fix 006)
  - A Flickering Wick                      # Bodach 2019 (fix 006)
  - After the Fire                         # Roger Daltrey 1985 (fix 006)
  - Inside the Fire                        # Disturbed 2008 (fix 006)
  - Let The Fire On My Altar Never Burn Out # Pulse Worship 2024 (fix 006)
  - Put More Wood on the Fire              # Eartha Kitt 1953 (fix 006)
  - We Didn't Start the Fire               # Billy Joel 1989 (fix 006)
  - Watching The Road                      # Poppy Prescott 2023 (fix 003)
  - The Whole House Is Singing             # Alasdair Roberts 2003 (fix 003)
  - Leave the Gate Open                    # Tony Kennelly 2020 (fix 003)
  - The Hired Hand                         # Woven Hand (fix 003)
  - Does The Light Still Shine             # Ray Boltz (fix 003)
  - There's Room Enough for Us             # Li'l Abner (fix 003)
  - Come In, Brother                       # Joy Electric (fix 003)
  - Road Back Home                         # Zakk Wylde 1996 (fix 003)
  - Light Your Windows                     # Quicksilver Messenger Service (fix 003)
  - Back The Way I Came                    # 2020 Christian single (fix 003)
  - Turn Your Heart Toward Home            # Steve & Annie Chapman (fix 003)
  - I Will Arise and Go to My Father       # thánh ca (fix 003)
  - Nobody Knows My Name                   # nhiều bài (fix 003)
  - When I Came To Myself                  # Kilo Kish 2025 (main 2026-09-23)
  - I'm Still Yours                        # Kutless (main 2026-09-23)
  - Let It Lie                             # Common; The Bros. Landreth (main 2026-09-23)
  - Turn the Night Around                  # Tommy Rogers 1989 (main 2026-09-23)
```
