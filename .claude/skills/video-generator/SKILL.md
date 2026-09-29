---
name: video-generator
description: Turn a channel's still thumbnail into its YouTube video, in three steps - (1) add the channel's effects to the image to make a seamless 5-minute loop video (breathing light, drifting dust/snow, channel logo top-right, like/subscribe clicks bottom-right, 4 s logo intro; or, for a channel with `cinema` on, a 2.5D moving picture: depth-map camera moves, window rays / halos / glow / sweeps, stars, dust, embers, bokeh, mist, one combination per video picked by `video.py variant` and checked by `video.py qa`), no music needed; (2) once the album audio has been mixed (by another skill), repeat that loop to the audio's exact length and add the audio-reactive spectrum bars, the full video staying on the GPU server; (3) pack the album video and its Short into ONE zip on the server (each with its thumbnails - YouTube JPG + full-resolution original -, youtube.md and paste-ready fields, the Short in `short/`, a README with the upload order) and upload it to S3 through presigned requests signed on this Mac ("zip lên S3", "đóng gói upload", "package"). Use when the user wants a loop/video made or re-rendered for an album or its Short, wants loops batch-rendered for many albums, wants to tune how the effects sit on an image ("chỉnh ánh sáng", "bụi bay hướng nào", "logo", "subscribe", "intro"), sets up the video look of a new channel, or says "tạo video 5 phút", "render loop", "ghép video với nhạc", "thêm sóng nhạc".
---

# Video generator

Three steps, run on an **album folder** `channel/<name>/albums/NNN-slug/` (older `ideas/` and `singles/` folders still
work); the album's Short lives in its `short/` subfolder (*Short* below):

| Step | Input | Command | Output |
|---|---|---|---|
| 1. Image → 5-min video | `<dir>/thumbnail.png` + channel look | `video.py loop <dir>` | `<dir>/video/`: `loop.mp4` (seamless 5 min), `loop_intro.mp4` (4 s logo intro), `loop_seam.mp4` (check clip) |
| 2. Loop → full video | step 1's loop + the **mixed album audio** | `video.py album <dir> <audio>` | full video **on the server** (intro, loop repeated to the audio's length, spectrum bars, audio); `<dir>/video/` gets only `video.mp4.json` (ffprobe), `check_5s.png`, `check_mid.png`, `remote.json` |
| 3. Package → S3 | step 2's video + `<dir>/youtube.md` + thumbnail, and the Short's render + `short/youtube.md` | `video.py package <album>` (run by step 2 itself only when the Short is ready too) | **one zip per album** holding the album and its Short (`short/`): `s3://$VG_S3_BUCKET/$VG_S3_PREFIX<channel>/albums/<album>/<album>-<time>.zip` (`remote.env`; an old `singles/` folder: `single-<slug>-<time>.zip` in the album named by `album:` in its `single.md`), recorded in `<album>/s3-package.json` |

Step 1 needs no music, so loops can be made for many albums ahead of time (`video.py batch`), before their master
is mixed. Step 2 runs whenever the album's master exists.
Step 2 does not mix music; it takes the finished album audio from the mixing skill as-is.

```bash
SK=.claude/skills/video-generator
V="python3 $SK/scripts/video.py"      # run from the repo root; creates $SK/.venv on first use
```

Needs python3 and ffmpeg/ffprobe. `loop` / `batch` / `album` / `short` render on the GPU server in `$SK/remote.env` by default
(3840×2160, encoded with NVENC on the server GPU, inside the capped `youtube.slice` (CLAUDE.md); a 5-min loop ~1 min,
a Short ~1–2 min, a 50-min album ~10 min including transfers). `--local` renders on this Mac
(~2 min / ~12 min, heats the Mac and stalls other work): only when the server is unreachable **and the user said yes**
(CLAUDE.md). `frame` (one still) always runs here.

## Where the settings live

| Layer | File | Holds |
|---|---|---|
| tool defaults | `$SK/scripts/config.py` `DEFAULTS` | layout shared by every channel: logo top-right, like/subscribe bottom-right every 30–45 s, 4 s logo intro, spectrum row, 5-min loop |
| channel | `channel/<name>/video.json` + `channel/<name>/image_source/logo.png` | the channel's look: particle kind/colour/direction, light colour, bar colours |
| album / Short | `<dir>/video.json` (optional) | what depends on this one image: light shaft shape, lamp flicker position, dust lanes |

Change a setting at the lowest layer it belongs to. Do not copy channel settings into an
album's `video.json`: `particles` merges by position, so `[{"lanes": [0.3, 1.02]}]` is enough.
Every key is documented in `$SK/references/config.md`. How it works, timings, encoders and
low-level commands are in `$SK/references/internals.md`.

## Step 1 — thumbnail → 5-minute loop

1. **Check inputs.** `<dir>` is inside `channel/<name>/` and holds `thumbnail.png` (16:9, 3840×2160: the
   `thumbnail-prompt` skill's `fit` upscales ChatGPT's image to 4K on the server and keeps it on this Mac; whose `thumb.py check` also prints the warm bright
   spots, a starting point for `lantern.center`). The channel has `video.json` and `image_source/logo.png`. For a new
   channel, follow `channel/README.md`. `$SK/references/example_snow.json` shows a different
   look (cool light, white snow from a corner, white bars).
2. **Tune on stills.** `$V frame <dir> --at 30`, then Read `<dir>/video/frame_30s.png`. Look
   at where the photo's own light comes from and whether it shows a lamp, candle or fire, then
   write `<dir>/video.json` (`light.shapes`, `lantern`, particle `lanes`). Check again, e.g.
   `--at 25` so the like/subscribe group is on screen. If the logo corner (top-right) or the
   subscribe corner (bottom-right) covers something important, tell the user; the layout is
   shared across the channel and should not move per image.
3. **Render.** `$V loop <dir>`. For every album (and old idea / single folder) that has a thumbnail but no loop yet:
   `$V batch channel/<name>`.
4. **Verify.** Read frames from `loop_intro.mp4` (≈0.5 s, 1.6 s, 3.3 s) and from `loop_seam.mp4`
   around 4 s, where the loop joins. Report anything odd. Never claim to have watched a video.

## Cinema channels (2.5D camera, lights, varied per video)

A channel whose `video.json` has `cinema.enabled` gets a moving picture instead of a still with breathing light: a slow 2.5D
camera over a depth map, image-anchored lights (window rays, halo, glow, spotlight, sweep), stars / dust / embers / bokeh /
mist, all seamless in the 5-min loop. Keys: `references/config.md` → `cinema`. Per image, before `loop`:

1. `$V frame <dir> --at 0` (cinema stills render on the server) and look: write `<dir>/video.json` → `cinema.anchors`
   (with `text_layer` on, `cinema.text_zones` = one tight box per line of lettering, a little larger than the glyphs, keeping
   bright scene parts such as a lit wall or a microphone out of the boxes; `qa` then checks the layer)
   (`window`, `cross`, `head`… as fractions of the frame, only those the image really has).
2. `$V variant <dir>` picks this video's camera × parallax × atmosphere × lighting from the channel's `cinema_pool`, unlike
   the channel's earlier videos (`--set lighting=…` when the brief asks for one; `--dry-run` to see it first).
3. `$V qa <dir>` (server, ~1 min): PASS = seamless join, lettering only moves/scales as a whole, bar still, no smeared
   edge, camera not shrunk for the lettering, no flicker. FAIL names the check; fix the image's zones/anchors or the pool.
   `$V frame <dir> --at 12` to look: light where the image's own light is. `$V loop <dir> --seconds 30` renders a short preview (`video/loop_preview.mp4`);
   then `$V loop <dir>` (8 parts share the GPU: 5-min 4K loop ≈ 140 s; `--intro-only` re-renders just the intro).
   A new cinema channel starts from `references/example_cinema.json`.
4. The video's logo is an overlay, so `thumbnail.png` (the video's source) has none; the YouTube upload
   `thumbnail.jpg` gets the same logo at the same place: `$SK/.venv/bin/python $SK/scripts/thumb_logo.py <dir>`
   (also the `badge`, a second small static image, when the channel's `video.json` enables it).

## Step 2 — loop → full-length video with spectrum bars

1. **Input audio** is the mixed album file from the `audio-album-assembly` skill (WAV preferred;
   AAC `.m4a` is muxed without re-encoding): `channel/<name>/albums/<album>/audio/master/<album>.wav`. An old album
   made from an idea (`plan.yaml sources.idea`) with no `thumbnail.png` / `video.json` / `video/loop.mp4` of its own
   still uses the idea's.
2. **Render.** `$V album <dir> <audio>`. It re-renders the loop on the server (cheap),
   puts the intro first, repeats the loop to the audio's length and draws the bars from the
   audio. The full video **stays on the server** (`~/video-generator/out/<job>/video.mp4`); it is not downloaded
   to this Mac (`--download` fetches it anyway, e.g. to watch it locally). Then step 3 runs by itself only when
   `<dir>/youtube.md` exists **and** the Short is ready (rendered on the server + `short/youtube.md`); otherwise it
   prints the exact `video.py package <album>` to run once the Short is done (`--no-package` never packages).
3. **Verify.** Read `<dir>/video/video.mp4.json` (ffprobe of the server file): the duration matches the audio, with
   video and audio streams present, and the resolution is 3840×2160 (the renderer's frame, `config.py` `W, H`). Read
   `<dir>/video/check_5s.png` (bars fading in) and `check_mid.png` (mid-album).

## Short (vertical, for the video-shorts skill)

`video.py short <short>` renders a Short from the album's `channel/<ch>/albums/NNN-slug/short/` (an old
`channel/<ch>/shorts/NNN-slug/` is still a Short): its 9:16 `thumbnail.png` (thumbnail-prompt) and `short.json`
(video-shorts `shorts.py new` / `spec`: audio file, in/out, lyric lines with times, hook, CTA). On the server
(`scripts/short.py`, `VG_FRAME=1080x1920`, inside `youtube.slice`): a seamless loop exactly as long as the clip (so the
Short replays without a jump), the clip cut + faded + loudness-normalised to −14 LUFS, spectrum bars, then the text layers
(hook 0–3 s, one lyric line at a time, CTA in the last 4 s) → `video.mp4` 1080×1920 on the server; back to `<short>/video/`:
`video.mp4.json`, `check_hook.png`, `check_mid.png`, `check_cta.png`, `overlays.json` (each text block's top/bottom).
Layout (logo top-left, no subscribe, no intro, bars above the bottom 25 %, text fonts/colours/positions) comes from
`config.py` `DEFAULTS["short"]`, overridden by the channel's `video.json` → `short` and the Short's own `video.json`
(image-specific light, lantern, lanes; tune with `video.py frame <short> --at 5`, which renders a 1080×1920 still).
`short` only renders: the Short is never packaged alone, it ships inside its album's zip (`video.py package <album>`;
`package <album>/short` refuses and names that command; an old `shorts/NNN-slug`: `shorts.py migrate` first).
`--local` / `--download` keep the Short as `<short>/video/<album>-short.mp4`.

## Step 3 — package for YouTube → S3 (one zip per album: album + Short)

`$V package <album>` (again any time, e.g. after editing a youtube.md; each run uploads a new timestamped zip).
Needs step 2's video on the server + `<album>/youtube.md` (`upload-youtube-publish`), and the Short: `short/` rendered
on the server (`video.py short`) + `short/youtube.md` (video-shorts). Chapters come from the album's `assembly.json`
(`publish.py chapters <album>`), written for the same master the video plays from 0:00.

1. **Gate.** Short missing (no `short/`, no 9:16 image, no render, no `youtube.md`) → stop, naming what is missing;
   `--no-short` zips the album alone and the README says so. Then `publish.py check <album>` and
   `shorts.py check <album>/short` both run; any ❌ stops the zip (`--force` packs anyway, the README and the record say so).
2. **Here:** stages each part: `youtube.md`; `upload/title.txt`, `description.txt`, `tags.txt`, `pinned_comment.txt`
   (the ``` blocks of youtube.md, paste-ready); `thumbnail.jpg` = the largest JPEG YouTube accepts (≤ 2 MB, same size as
   the source when possible; also saved next to its youtube.md unless an up-to-date one is there); `thumbnail_full.<ext>` =
   the original at full resolution. The album thumbnail is the one the video was made from (4K from thumbnail-prompt
   `fit`; `--thumbnail FILE` for another), the Short's is its 9:16 `thumbnail.png`.
3. **Server:** hard-links both videos in, writes `manifest.json` (ffprobe of each video, size + sha256 of every file,
   warnings) and `README.txt` (upload order: album first, then the Short with Related video = the album, AI disclosure =
   Yes on both, the channel's `publish.md` → *Giờ đăng* / *Thứ tự đăng* lines; what each file is; the Studio steps of
   each part), zips it all (stored, zip64). Warns when a video or thumbnail is not full size, or the album video length
   ≠ the mixed audio.

   ```
   <album>/README.txt · manifest.json
   <album>/<album>.mp4 · thumbnail.jpg · thumbnail_full.png · youtube.md · upload/{title,description,tags,pinned_comment}.txt
   <album>/short/<album>-short.mp4 · thumbnail.jpg · thumbnail_full.png · youtube.md · upload/*.txt
   ```
4. **`--dry-run`:** stops here: prints the zip's files + sizes and the README, deletes the test zip on the server,
   uploads nothing, writes no record, leaves the videos on the server.
5. **Upload:** this Mac signs, the server sends the bytes: always a multipart upload (4K albums pass 5 GB, the limit
   of a single presigned POST), one presigned PUT per 256 MB part, each part retried 3×, completed (or aborted) here.
   Credentials = this Mac's AWS default chain (or `VG_AWS_PROFILE`); bucket / region / prefix in `remote.env`.
6. **Clean the server** once `head_object` confirms the size: the zip, the staging folder, both full videos (+ probes /
   check frames) and the pushed audio are deleted; loops, images and presets stay. `--keep-server` keeps everything.
   After cleaning, `package` again needs step 2 (and `video.py short`) again, so a Short made after a `--no-short`
   upload means re-rendering the album (or `--keep-server` on that upload).
7. **Report** the S3 URI from `<album>/s3-package.json` (one entry per upload: key, size, sha256, `parts` album/short
   with each video probe, `checks`, files, warnings). A Short's old separate record (`short/s3-package.json`,
   `shorts/NNN-slug/s3-package.json`) is still read by `shorts.py list` and the PM board.

## Notes

- The intro delays the first view of the photo by ~3 s; the music starts at 0 regardless.
  CLAUDE.md treats the first 10–15 s as critical, so point it out when retention is reviewed.
  Turn it off with `"intro": {"enabled": false}`.
- The bars exist only in step 2. Without bars, run `scripts/extend.py ... --no-bars`, which
  joins the copies without re-encoding (see internals.md).
- Outputs in `<dir>/video/` are gitignored. The loop can be reused with any audio.
- `--local` renders keep the full video on this Mac (`<dir>/video/<dir name>.mp4`); `package` only packs a
  server-rendered video.
- A round badge logo can be drawn by code: `$SK/.venv/bin/python $SK/scripts/make_logo.py --title <TOP> --sub <BOTTOM> --out channel/<ch>/image_source/logo.png`
  (the exact command a channel used goes in its `channel.md` → *Tài nguyên*).
