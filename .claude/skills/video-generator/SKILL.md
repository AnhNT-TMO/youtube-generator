---
name: video-generator
description: Turn a channel's still thumbnail into its YouTube video, in three steps - (1) add the channel's effects to the image to make a seamless 5-minute loop video (breathing light, drifting dust/snow, channel logo top-right, like/subscribe clicks bottom-right, 4 s logo intro), no music needed; (2) once the album audio has been mixed (by another skill), repeat that loop to the audio's exact length and add the audio-reactive spectrum bars, the full video staying on the GPU server; (3) zip that video with the thumbnails (YouTube JPG + full-resolution original), youtube.md and paste-ready fields on the server and upload the zip to S3 through presigned requests signed on this Mac ("zip lên S3", "đóng gói upload", "package"). Use when the user wants a loop/video made or re-rendered for an idea or album, wants loops batch-rendered for many ideas, wants to tune how the effects sit on an image ("chỉnh ánh sáng", "bụi bay hướng nào", "logo", "subscribe", "intro"), sets up the video look of a new channel, or says "tạo video 5 phút", "render loop", "ghép video với nhạc", "thêm sóng nhạc".
---

# Video generator

Three steps, run on an **idea, album or single folder** inside `channel/<name>/` (`ideas/`, `albums/`, `singles/`):

| Step | Input | Command | Output |
|---|---|---|---|
| 1. Image → 5-min video | `<dir>/thumbnail.png` + channel look | `video.py loop <dir>` | `<dir>/video/`: `loop.mp4` (seamless 5 min), `loop_intro.mp4` (4 s logo intro), `loop_seam.mp4` (check clip) |
| 2. Loop → full video | step 1's loop + the **mixed album audio** | `video.py album <dir> <audio>` | full video **on the server** (intro, loop repeated to the audio's length, spectrum bars, audio); `<dir>/video/` gets only `video.mp4.json` (ffprobe), `check_5s.png`, `check_mid.png`, `remote.json` |
| 3. Package → S3 | step 2's video + `<dir>/youtube.md` + thumbnail | `video.py package <dir>` (run by step 2 itself when `youtube.md` exists) | zip on S3 `s3://$VG_S3_BUCKET/$VG_S3_PREFIX<channel>/<kind>/<slug>/<slug>-<time>.zip` (`remote.env`), recorded in `<dir>/s3-package.json` |

Step 1 needs no music, so loops can be made for many ideas ahead of time (`video.py batch`), before or after
their album is planned. Step 2 runs whenever the album's master exists.
Step 2 does not mix music; it takes the finished album audio from the mixing skill as-is.

```bash
SK=.claude/skills/video-generator
V="python3 $SK/scripts/video.py"      # run from the repo root; creates $SK/.venv on first use
```

Needs python3 and ffmpeg/ffprobe. `loop` / `batch` / `album` render on the GPU server in `$SK/remote.env` by default
(3840×2160, encoded with NVENC on the server GPU, inside the capped `youtube.slice` (CLAUDE.md §4); a 5-min loop ~1 min,
a single ~2.5 min, a 50-min album ~10 min including transfers). `--local` renders on this Mac
(~2 min / ~12 min, heats the Mac and stalls other work): only when the server is unreachable **and the user said yes**
(CLAUDE.md §4). `frame` (one still) always runs here.

## Where the settings live

| Layer | File | Holds |
|---|---|---|
| tool defaults | `$SK/scripts/config.py` `DEFAULTS` | layout shared by every channel: logo top-right, like/subscribe bottom-right every 30–45 s, 4 s logo intro, spectrum row, 5-min loop |
| channel | `channel/<name>/video.json` + `channel/<name>/image_source/logo.png` | the channel's look: particle kind/colour/direction, light colour, bar colours |
| idea / album | `<dir>/video.json` (optional) | what depends on this one image: light shaft shape, lamp flicker position, dust lanes |

Change a setting at the lowest layer it belongs to. Do not copy channel settings into an
idea's `video.json`: `particles` merges by position, so `[{"lanes": [0.3, 1.02]}]` is enough.
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
3. **Render.** `$V loop <dir>`. For every idea / album / single that has a thumbnail but no loop yet:
   `$V batch channel/<name>` (albums that can use their idea's loop are skipped).
4. **Verify.** Read frames from `loop_intro.mp4` (≈0.5 s, 1.6 s, 3.3 s) and from `loop_seam.mp4`
   around 4 s, where the loop joins. Report anything odd. Never claim to have watched a video.

## Step 2 — loop → full-length video with spectrum bars

1. **Input audio** is the mixed album file from the `album-assembly` skill (WAV preferred;
   AAC `.m4a` is muxed without re-encoding), normally `channel/<name>/albums/<album>/audio/master/*.wav`; for a single song released on its own,
   `singles/<NNN-slug>/audio/master/<NNN-slug>.wav` (album-assembly `single`). An album planned from an idea
   (album-plan) needs nothing copied: when the album folder has no `thumbnail.png` / `video.json` / `video/loop.mp4`,
   `video.py` uses the source idea's (`plan.yaml sources.idea`), and warns when the idea's thumbnail is newer than
   the album's. `album_plan.py sync <album>` copies them into the album for good (youtube-publish reads the album's
   `thumbnail.png`).
2. **Render.** `$V album <dir> <audio>`. It re-renders the loop on the server (cheap),
   puts the intro first, repeats the loop to the audio's length and draws the bars from the
   audio. The full video **stays on the server** (`~/video-generator/out/<job>/video.mp4`); it is not downloaded
   to this Mac (`--download` fetches it anyway, e.g. to watch it locally). Then, if `<dir>/youtube.md` exists,
   step 3 runs by itself (`--no-package` to skip).
3. **Verify.** Read `<dir>/video/video.mp4.json` (ffprobe of the server file): the duration matches the audio, with
   video and audio streams present, and the resolution is 3840×2160 (the renderer's frame, `config.py` `W, H`). Read
   `<dir>/video/check_5s.png` (bars fading in) and `check_mid.png` (mid-album).

## Step 3 — package for YouTube → S3

`$V package <dir>` (again any time, e.g. after editing `youtube.md`; each run uploads a new timestamped zip).
Needs step 2's video on the server and `<dir>/youtube.md` from the `youtube-publish` skill. Since the video is not
here, youtube-publish measures chapters on the master audio (`publish.py chapters <dir> --audio <master.wav>`:
the video's audio is the master itself, starting at 0:00).

1. **Here:** builds the package folder: `youtube.md`; `upload/title.txt`, `description.txt`, `tags.txt`,
   `pinned_comment.txt` (the ``` blocks of youtube.md, paste-ready); `thumbnail.jpg` = the largest JPEG YouTube
   accepts (≤ 2 MB, same size as the source when possible; also saved as `<dir>/thumbnail.jpg` unless an up-to-date
   one is there); `thumbnail_full.<ext>` = the original at full resolution (4K). Then `publish.py check <dir>`
   must pass (`--force` to skip). The thumbnail is the one the video was made from (already 4K from thumbnail-prompt `fit`;
   an older 1920×1080 one → re-run `fit` from its draft); `--thumbnail FILE` for another.
2. **Server:** hard-links the video in as `<slug>.mp4`, writes `manifest.json` (ffprobe of the video, size + sha256
   of every file, warnings) and `README.txt` (what each file is + the Studio steps), zips it all (stored, zip64).
   Warns when the video or the thumbnail is not 4K, or the video length ≠ the mixed audio.
3. **Upload:** this Mac signs, the server sends the bytes: always a multipart upload (4K albums pass 5 GB, the limit
   of a single presigned POST), one presigned PUT per 256 MB part, each part retried 3×, completed (or aborted) here.
   Credentials = this Mac's AWS default chain (or `VG_AWS_PROFILE`); bucket / region / prefix in `remote.env`.
4. **Clean the server** once `head_object` confirms the size: the zip, the package folder, the full `video.mp4`
   (+ its probe / check frames) and the pushed master audio are deleted; loop, image and preset stay (~65 MB, a
   re-render skips the loop). `--keep-server` keeps everything. After cleaning, `package` again needs step 2 again.
5. **Report** the S3 URI from `<dir>/s3-package.json` (one entry per upload: key, size, sha256, video probe,
   files, warnings) and any warning.

## Notes

- The intro delays the first view of the photo by ~3 s; the music starts at 0 regardless.
  CLAUDE.md §3 treats the first 10–15 s as critical, so point it out when retention is reviewed.
  Turn it off with `"intro": {"enabled": false}`.
- The bars exist only in step 2. Without bars, run `scripts/extend.py ... --no-bars`, which
  joins the copies without re-encoding (see internals.md).
- Outputs in `<dir>/video/` are gitignored. The loop can be reused with any audio.
- `--local` renders keep the full video on this Mac (`<dir>/video/<dir name>.mp4`); `package` only packs a
  server-rendered video.
- The logo PNG of Lamplight Gospel is drawn by code: `$SK/.venv/bin/python $SK/scripts/make_logo.py --channel lamplight_gospel`.
