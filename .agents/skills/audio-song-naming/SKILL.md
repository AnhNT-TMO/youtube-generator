---
name: audio-song-naming
description: Give every raw Suno clip in a channel's song pool (channel/<ch>/songs/raw/<id8>.wav + .json + .lyrics.txt, downloaded by audio-suno-generate) an English title taken from its lyrics in the channel's style (channel/<ch>/naming.md) - a generation's 2 clips with the SAME lyrics = ONE song, 2 versions, same title, <title-slug>_v1 / _v2 (v1 = first clip id in songs/manifest.json); with DIFFERENT lyrics = 2 separate songs, own titles, <title-slug> without version - move it into its type folder songs/<type>/ (types from channel/<ch>/prompt_suno.md), write its song card next to it (templates/song.md) and choose its Short segment (a sung chorus / strongest plea, start on the hook, end on a line end) from Whisper word timestamps made in ONE batched job on the GPU server. Runs alongside the Suno lane (only touches clips whose wav is complete, never writes manifest.json). Also drops unusable clips (songs/dropped.json), renames a song later (all its versions, with their album references), writes songs/catalog.md and migrates the old flat layout songs/<slug>.* into the type folders. Use when the PM or the owner says "đặt tên bài", "đặt tên clip", "đổi tên bài", "tên bài từ lời", "chọn đoạn short", "song card", "kho bài", "catalog kho bài", "clip nào chưa tên", "bỏ clip hỏng", "chia kho theo loại", "migrate kho bài", or after Suno clips land in songs/raw/. Does NOT generate music (audio-suno-generate), pick songs for albums (pm-production) or render Shorts (video-shorts).
---

# Song naming

Suno Simple mode tự viết lời; một lượt ra 2 clip, có khi **cùng lời** (một bài, hai bản thu), có khi **khác lời, khác tên**
(hai bài). Script so lời hai clip (`raw/<id8>.lyrics.txt`, chữ đã chuẩn hóa, tỉ lệ giống ≥ 0.8 = cùng lời; `list` và
`candidates` in tỉ lệ):
- **Cùng lời = một bài, 2 bản** (CEO 2026-09-28: không bao giờ mất dấu file nào là cùng một bài): **cùng một tên**, file
  `songs/<type>/<tên-slug>_v1.*` / `_v2.*`, `version` `v1` = clip id đầu tiên của lượt trong `songs/manifest.json` →
  `generations[].clip_ids`, `v2` = clip thứ hai, `sibling` = slug bản kia.
- **Khác lời = 2 bài riêng** (PM 2026-09-28): mỗi bài một tên lấy từ lời của chính nó (không trùng tên bài kia), file
  `songs/<type>/<tên-slug>.*` (không `_vN`), `version` + `sibling` null, `generation` ghi như thường.
- Bản kia **đã bỏ** (`drop`) hoặc lượt chỉ còn một clip dùng được: clip còn lại là bài riêng, như khác lời.

Mỗi clip: một file wav, một song card cạnh nó và một đoạn Short riêng (hai bản thu khác nhau: cùng điệp khúc cũng được). Tên
hiện ở chapters / Short là `title`, không kèm V. Luật đặt tên + luật đoạn Short của kênh: `channel/<ch>/naming.md` (đọc như luật).

**Mỗi loại bài một thư mục** (CEO 2026-09-28: nhìn là biết bài nào có spoken intro): `songs/<type>/`, `<type>` = `type` của
clip (raw json) và phải nằm trong `types` của `channel/<ch>/prompt_suno.md` (vd. `songs/spoken/`, `songs/sung/`). `raw/`,
`manifest.json`, `catalog.md`, `dropped.json`, `.cache/` ở gốc `songs/`. `audio:` của card = `<slug>.wav`, tính từ thư mục của card.
Bố cục cũ (`songs/<slug>.wav` + `.md` nằm thẳng trong `songs/`) vẫn đọc được ở mọi skill; chuyển hẳn bằng `migrate`.

| Vào (audio-suno-generate ghi, skill này chỉ đọc) | Ra (chỉ skill này ghi) |
|---|---|
| `songs/raw/<id8>.wav` (ghi SAU CÙNG: có wav = clip đã tải xong) | `songs/<type>/<slug>.wav` (chuyển từ raw, không copy; `<slug>` = `<tên-slug>_vN` hoặc `<tên-slug>`) |
| `songs/raw/<id8>.json`: clip_id, generation, type, title (Suno), duration, file_duration, sibling_clip_id… | `songs/<type>/<slug>.md` (mẫu `templates/song.md`, front matter đủ mọi trường) |
| `songs/raw/<id8>.lyrics.txt`: lời đúng như Suno lưu | `songs/.cache/words/<id8>.json` (Whisper), `songs/catalog.md` |
| `songs/manifest.json` → `generations[].clip_ids` (chỉ đọc: bản kia của lượt, thứ tự = v1, v2) | `songs/dropped.json` + `songs/raw/dropped/<id8>.wav` (clip bỏ) |

Không bao giờ ghi `songs/manifest.json`, `raw/*.json`, `raw/*.lyrics.txt`, `raw/gen/`. Một clip "đã tên" khi có
`songs/<type>/*.md` (hoặc `songs/*.md` bố cục cũ) mang `clip_id` của nó; "đã bỏ" khi có trong `songs/dropped.json` (chỉ
songs.py ghi file này).

## Cài một lần

```bash
SK=.claude/skills/audio-song-naming; PY=$SK/.venv/bin/python; S=$SK/scripts/songs.py   # gốc repo, zsh: mỗi biến một từ
python3.12 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt       # Mac: chỉ pyyaml
cp $SK/remote.env.example $SK/remote.env    # điền QC_REMOTE (cùng server + ~/youtube-qc với audio-album-assembly)
bash $SK/scripts/remote.sh setup            # server: venv openai-whisper 20250625 + torch cu128, kiểm CUDA
```

Server: venv `~/youtube-qc/.claude/skills/audio-song-naming/.venv` (torch 2.11.0+cu128, whisper 20250625, model `turbo` =
large-v3-turbo ở `~/.cache/whisper/`); `remote.sh setup` chạy lại chỉ kiểm, không cài lại. Venv hỏng thì xóa thư mục đó rồi
`setup` (uv cài mới, torch cu128).

## Lệnh

```bash
$PY $S list       --channel <ch>                         # clip thô: tỉ lệ lời giống bản kia → v1/v2 hay bài riêng, trạng thái + bài đã tên + clip bỏ
$PY $S words      --channel <ch> [--clip ID8 …] [--force] # Whisper mọi clip chưa tên chưa có cache: 1 job GPU (~30 s / 4 clip gồm upload)
$PY $S candidates <id8>                                  # lời đánh số (t0/t1, đọc/hát) + bảng đoạn Short, mỗi đoạn một khóa L12-L19
$PY $S name       <id8> --title "<Title>" --short L12-L19 [--hook "<dòng>"] [--why "<…>"]
$PY $S drop       <id8> --reason "<vì sao>"                # clip hỏng / không dùng: wav → raw/dropped/, ghi songs/dropped.json
$PY $S drop       <id8> --undo                           # lấy lại clip đã bỏ
$PY $S rename     <slug> --title "<New Title>" [--update-albums]   # slug của bản nào cũng được: đổi mọi bản cùng lời
$PY $S catalog    --channel <ch>                         # → songs/catalog.md (mỗi type một bảng, các bản đứng cạnh nhau)
$PY $S migrate    --channel <ch> [--yes]                 # bố cục cũ → songs/<type>/: in mọi thay đổi; --yes mới làm
```

`candidates` / `name` / `drop` / `rename` tự tìm kênh; id8 có ở hai kênh thì thêm `--channel`. `words` không bao giờ chạy trên Mac:
server không lên được thì dừng, báo PM (CLAUDE.md §5).

## Quy trình cho từng clip

1. **`list`**: chỉ làm clip "sẵn sàng" hoặc "cần words". "đang tải" / "wav vừa ghi" / "chưa có raw json" / "chờ lời bản kia"
   = Suno lane chưa xong, bỏ qua, lát làm. Cột "lời vs bản kia" cho biết clip là bản v1/v2 của một bài hay bài riêng.
2. **`words`** cho cả lô (một lệnh, một job server). Clip mới về thì chạy lại: chỉ clip thiếu cache mới lên server.
3. **`candidates <id8>`**, đọc: lời đánh số, dòng nào đọc (spoken) / hát, `vocal_entry_s`, `sung_entry_s`, tên Suno, bản
   (`v1`/`v2` nếu cùng lời với bản kia, `bài riêng` nếu khác lời / bản kia đã bỏ) và tỉ lệ lời giống bản kia; cùng lời mà bản
   kia đã tên thì dòng `→` in đúng tên phải dùng. Bản kia chưa có lời → `name` từ chối (chờ lane Suno; bản kia hỏng thì `drop`).
   Clip không dùng được (hỏng tiếng, cụt, sai loại, không đoạn hát nào) → `drop <id8> --reason "…"`, không đặt tên.
4. **Chọn tên** theo `naming.md`: tìm dòng cầu xin / lời chứng mạnh nhất trong lời (thường là hook, điệp khúc hoặc câu của bridge),
   chuyển thành một tên đúng giọng kênh (ngôi thứ nhất, nói với Jesus / Lord / Father / God…). Tên phải nói ý CÓ trong lời.
   Cùng lời: một tên cho cả bài, đặt tên bản đầu tiên là đặt tên cho cả hai bản; bản kia đã tên → `name` chỉ nhận **đúng tên
   đó** (khác → từ chối, in tên của bản kia). Khác lời: mỗi bài tên riêng từ lời của nó. Tự kiểm: không trùng một bài hát
   nổi tiếng có thật (Claude biết thì đổi). Tên đã dùng cho bài khác (kể cả bài khác lời cùng lượt), trùng file, sai luật máy đọc của naming.md → `name` từ chối, nói lý do. Trùng nguyên văn title / chữ thumbnail trong `research/phrase-bank/*.yaml` → chỉ cảnh báo kèm id câu:
   được dùng nguyên văn câu cầu nguyện chung / câu kinh điển (CEO 2026-09-28); tên, branding kênh khác thì không bao giờ.
5. **Chọn đoạn Short** trong bảng: ưu tiên đoạn bắt đầu bằng điệp khúc hoặc câu cầu xin mạnh (≤ 1 s trước chữ đầu), `trọn đoạn`
   ✔, `hết đoạn` ✔ (kết cuối đoạn → lặp mượt), `lặng dài nhất` nhỏ, ít dòng "ước lượng giờ" (dòng Whisper không dóng được, giờ
   được chia đều giữa hai dòng bên cạnh). Bảng chỉ có phần hát, 30–60 s, không lặng > 6 s (số của naming.md). Mỗi bản chọn
   khóa của riêng nó (giờ khác nhau giữa hai bản thu); cùng điệp khúc với bản kia được. `--hook`: dòng hiện đầu Short, phải
   nằm trong đoạn (mặc định dòng đầu).
6. **`name --short <khóa>`** (ghi `songs/<type>/<tên-slug>_<bản>.*`, bài riêng `songs/<type>/<tên-slug>.*`): khóa = cột `khóa` của bảng (`L<dòng đầu>-L<dòng cuối>`, số dòng lời đánh số ở trên), không
   phải số thứ hạng `#`: thứ hạng có thể đổi khi bảng xếp lại, khóa thì không. Khóa không còn trong bảng
   (vd. chạy lại `words --force`) → `name` từ chối, không tự đổi đoạn. Kiểm dòng in ra: tên, loại, vào lời / vào hát, đoạn Short.
7. Hết lô: **`catalog`**, báo PM: số bài mới (bài 2 bản / bài riêng), tên, loại, đoạn Short từng bản, clip bỏ + lý do,
   clip còn chờ và vì sao.

Không chọn được (lời lạ, Whisper dóng < 50 % dòng, không đoạn nào vừa luật) → không đoán: báo PM clip đó + lý do.

## Chạy song song với Suno lane

- Suno lane ghi `raw/<id8>.json` + `.lyrics.txt` trước, `.wav` sau cùng; skill này chỉ nhận clip khi wav có header RIFF đủ
  (kích thước file = header), đã đứng yên ≥ 5 s, dài khớp `file_duration` của raw json (±1.5 s). File đang tải bị bỏ qua.
- Hai worker không đụng file của nhau: Suno lane chỉ ghi trong `raw/` + manifest; skill này chỉ **chuyển** `raw/<id8>.wav`
  (sang `songs/<type>/` hoặc `raw/dropped/`) và ghi `songs/<type>/*.md`, `.cache/`, `catalog.md`, `dropped.json`.
- Chạy `list` → `words` → đặt tên nhiều lần trong ngày tùy clip về; `words` không làm lại clip đã có cache.

## Quy tắc máy (script tự làm)

- **Whisper**: `openai-whisper` model `turbo`, trên bản mix 16 kHz (không tách giọng), `word_timestamps`, không điều kiện câu
  trước, `hallucination_silence_threshold=2`.
- **Dóng lời**: từng dòng lời (bỏ dòng trong ngoặc tròn, bỏ đoạn [Instrumental]/[Break]/[Solo]/[Interlude]) tìm trong 80 token
  Whisper kế tiếp, lấy vị trí **sớm nhất** khớp ≥ 0.8 (không thì khớp tốt nhất ≥ 0.55): điệp khúc lặp lại không nhảy cóc.
- **Đọc / hát**: đoạn có tag chứa spoken / narration / recitation… luôn là đọc. Bài `type: spoken`: [Intro] có lời (hoặc lời
  không tag ở đầu) trước đoạn hát đầu tiên cũng là đọc. `vocal_entry_s` = dòng đầu (đọc hay hát), `sung_entry_s` = dòng hát đầu.
  Bài spoken mà lời không có tag nào → cảnh báo, `sung_entry_s` = dòng đầu.
- **Điểm đoạn Short**: điệp khúc +2, trọn đoạn bắt đầu +1, kết cuối đoạn +1, lặng sau dòng cuối (≤ 2 s) +0–1, độ tin Whisper
  trung bình +0–1, mỗi dòng ước lượng −0.2, lần lặp sau của cùng điệp khúc −0.1.
- **Cùng bài hay bài riêng**: bản kia = các clip id khác của lượt trong `songs/manifest.json` `generations[].clip_ids`, trừ
  clip trong `songs/dropped.json`. Lời so bằng `raw/<id8>.lyrics.txt` (bài đã tên mà thiếu file này: khối Lyrics của card), bỏ
  dòng tag `[…]`, chữ thường, chỉ chữ cái; tỉ lệ SequenceMatcher (lấy lớn hơn của hai chiều) ≥ 0.8 = cùng lời.
- **Bản**: cùng lời → `version` = vị trí clip id trong `generations[].clip_ids` (`v1`, `v2`), slug = `slugify(title)` +
  `_v1`/`_v2`; không bản kia cùng lời → `version` null, slug = `slugify(title)`. Clip chưa có trong manifest, hoặc bản kia chưa
  có lời → `name` từ chối (lane Suno chưa ghi xong), không đoán.
- **Song card**: front matter theo `templates/song.md` (thứ tự khóa của mẫu), `short` tính bằng giây trong file bài;
  `sibling` = slug bản kia cùng lời, ghi hai chiều khi bản thứ hai được đặt tên; bài riêng: `sibling` null.
- **Tên không trùng** trong cả kho (mọi `songs/<type>/` + `songs/` bố cục cũ: slug, title, file `.wav`/`.md`): một title chỉ
  dùng cho các bản cùng lời của **một** lượt (hai bài khác lời cùng lượt: hai tên khác nhau).
- **Drop**: chỉ clip thô chưa tên, bắt buộc `--reason`; wav đang ghi (< 5 s) → từ chối; không có wav thì chỉ ghi
  `dropped.json`. Clip có trong manifest mà chưa từng tải về (Suno trả clip rỗng, lane Suno bỏ qua) cũng drop được:
  ghi `downloaded: false`, bản kia của lượt thành bài riêng. Sau khi bỏ, bản kia đã tên `_vN` mà không còn bản cùng lời → script in lệnh `rename` về tên không `_vN`.
- **Luật máy đọc của naming.md** (front matter, tùy chọn; không có thì chỉ kiểm trùng): `title_words: [min, max]`,
  `title_case: true` (mọi từ viết hoa chữ đầu; a, an, and, as, at, but, by, for, from, in, into, nor, of, on, or, over,
  the, to, up, with viết thường được, trừ từ đầu), `title_forbidden: ",."`, `short_length_s: [30, 60]` (mặc định 30–60),
  `short_pre_roll_s: 1`, `short_max_gap_s: 6`.

## Sửa sau

- Đổi đoạn Short / hook: chạy lại `name <id8>` với **đúng tên cũ** và khóa mới (ghi đè song card, không chuyển file).
- Đổi tên: `rename <slug> --title …` (slug của bản nào cũng được) đổi **cả bài**: mọi bản cùng lời của lượt → `<tên-slug>_v1`
  / `_v2` (wav + card viết lại từ mẫu, giữ lời + đoạn Short, ghi `version`, nối `sibling`); bài riêng chỉ đổi chính nó →
  `<tên-slug>` (`version` + `sibling` null; card khác trỏ `sibling` vào nó thì bỏ trống), tại chỗ trong thư mục type. Card sai
  bố cục (`list` / `catalog` cảnh báo "sai bố cục": cùng lời mà thiếu `_vN`/`version`, hoặc khác lời / bản kia bỏ mà còn `_vN`)
  sửa bằng lệnh này, giữ tên cũ được (`--title` = tên cũ). Bản đang nằm trong album
  (tracks/*.md, album.md `tracklist` + `brief.short.song`, assembly.json) → từ chối, trừ khi `--update-albums` (sửa luôn
  các file đó, cả tên file `tracks/NN-<slug>.md`, rồi chạy `assemble.py report` của album; youtube.md phải soạn lại). Album
  đã đăng YouTube: đừng đổi tên bài của nó.
  Short của album (`albums/*/short/short.md`, cả `shorts/*/short.md` bố cục cũ) có `song` / `track` / `clip_id` là của bản
  cũ: skill này không sửa file Short, chỉ in lệnh đồng bộ lại cho từng Short
  (`python3 .claude/skills/video-shorts/scripts/shorts.py spec channel/<ch>/albums/NNN-slug/short`, video-shorts tìm lại bài
  theo `clip_id`).

## Chuyển kho sang thư mục theo loại (`migrate`)

`migrate --channel <ch>` (mặc định chỉ in, exit 1 nếu có ❌): mỗi song card `songs/<slug>.md` bố cục cũ + wav của nó →
`songs/<type>/` theo `type` của card, rồi sửa mọi đường dẫn trỏ vào chỗ cũ: `albums/*/tracks/*.md` `audio`,
`albums/*/assembly.json` `tracks[].audio`, `albums/*/short/short.md` `track`, `albums/*/short/short.json` `audio` + `track`
(và `shorts/*/` bố cục cũ; `album.md` chỉ ghi slug: không đổi). Xem danh sách in ra, rồi `--yes` (chuyển, sửa, ghi lại `catalog.md`). Chạy lại được:
lần sau chỉ sửa đường dẫn còn sót. ❌ = type không có trong `prompt_suno.md`, hoặc bài có ở cả hai chỗ: sửa tay rồi chạy lại.
**Không chạy khi một worker khác đang `name` trên kênh đó** (PM chạy sau lô đặt tên). Audio không đổi nên không phải ghép
hay render lại; lần ghép sau audio-album-assembly đẩy file bài theo đường mới lên server (bản cũ trên server không dùng nữa).
