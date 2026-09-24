---
name: thumbnail-prompt
description: Write the ChatGPT image prompt for a channel thumbnail - for a single song released on its own (channel/<ch>/singles/NNN-slug, built from the song's lyrics, imagery and emotion), an album, or an idea (idea.yaml packaging.thumbnail_brief) - on top of the channel's fixed CORE block in channel/<ch>/visual.md, choosing the channel's variation axes (wardrobe, framing, light, palette…) by the song's vibe and keeping the album's visual signature, with the channel's character kept identical through the reference images in channel/<ch>/model/, title lettering chosen per album, and the corners that the video's logo / subscribe / spectrum overlays cover kept free; then fit ChatGPT's result to 16:9 and upscale it to a 4K 3840×2160 thumbnail.png on the GPU server (SeedVR2 7B, plus a ≤ 2 MB thumbnail.jpg for YouTube) and check it (size, covered zones, bright light spot for video.json). Use when the user says "viết prompt ảnh", "prompt thumbnail", "tạo ảnh cho bài", "ảnh cho single", "thumbnail cho idea/album", "ChatGPT vẽ ảnh", sends a ChatGPT image to use as a thumbnail, or asks why an image does not fit the video. Does NOT render video (video-generator).
---

# Thumbnail prompt

The image step before `video-generator` step 1. Images are made in **ChatGPT** (reference images + prompt, PNG back).
Claude writes the prompt, generates, picks, fits and checks the result. The same image is both the YouTube thumbnail and
the video background (video-generator animates it), so it must work under the overlays: logo top-right, like/subscribe
bottom-right, spectrum bars bottom-centre.

**This skill is the procedure; the channel decides the picture.** Everything about what the images look like (the
channel's visual world, its constants, the CORE block, the variation axes and their English snippets, the lettering
styles, what to check on a draft) lives in `channel/<ch>/visual.md`, with the character references in
`channel/<ch>/model/` (`model/README.md`: which file shows which angle). Read both first. No `visual.md` → write one with
the owner before any image (constants, character, lettering, free areas, avoid list; template: `channel/_template/`).

```bash
T=.claude/skills/thumbnail-prompt/scripts/thumb.py   # repo root; python3 + ffmpeg + ssh only, no venv; one word per var (zsh)
python3 $T list  channel/<ch>                       # text table of every thumbnail: album signature, wardrobe, framing, light, palette, setting…
python3 $T fit   <dir> <downloaded.png> [--x .5 --y .5]   # crop to 16:9 around (x, y) → GPU server SeedVR2 7B → <dir>/thumbnail.png 3840×2160 + thumbnail.jpg ≤ 2 MB (~1 min)
python3 $T fit   <dir> <downloaded.png> --no-upscale     # fallback when the server is down: Lanczos 1920×1080 on this Mac
python3 $T check <dir> [--image <file>]             # size/ratio (warns < 4K), detail in the 3 covered zones, warm bright spots, prompt vs the channel CORE block
python3 $T upscale-setup                            # once / when broken: SeedVR2 repo (pinned) + venv + 7B model (~17 GB) in ~/thumbnail-prompt on the server
G=.claude/skills/thumbnail-prompt/scripts/chatgpt_images.py
.claude/skills/thumbnail-prompt/scripts/chatgpt-chrome.sh   # dedicated real Chrome for ChatGPT, profile ~/.chatgpt-chrome/profile, port 9223
python3 $G gen <dir> [--n 3]                        # new chat → attach model refs → paste prompt → wait → drafts NN.png; prints conversation id
python3 $G fetch <dir>                              # download the images of the thread open now (if gen stopped early)
python3 $G delete <conversation-id>                 # delete exactly that thread: real click on the ⋯ inside its own link, dialog title checked
```

`<dir>` = `channel/<ch>/singles/NNN-slug`, `albums/NNN-slug` or `ideas/NNN-slug`. Images can be made for many ideas
ahead of time, before or after their album is planned: an idea that already became an album (`idea.yaml status:
promoted`) can still be done in the idea folder; album-plan `build`/`sync` copies the newer image into the album and
video-generator falls back to the idea's. Output: `<dir>/thumbnail-prompt.md`
(template `templates/thumbnail-prompt.md`), drafts in `<dir>/thumbnail-drafts/` (gitignored), final `<dir>/thumbnail.png`
(**3840×2160**, the 4K copy kept on this Mac) + `<dir>/thumbnail.jpg` (≤ 2 MB, the file YouTube uploads).
How to drive ChatGPT and fix its usual mistakes: `references/chatgpt.md`.

**Why upscale, and where.** ChatGPT returns 1672×941. `fit` sends the chosen crop to the GPU server (`remote.env`), where
SeedVR2 7B (a one-step diffusion restorer) redraws it at 3840×2160 with real new detail (hair, skin, crisp lettering)
while keeping colours, faces and the text. Chosen by a measured test on 2026-09-24 against Lanczos, HAT-L,
UltraSharpV2, Real-ESRGAN, SeedVR2 3B / 7B-sharp and SUPIR. The server keeps nothing afterwards; this Mac keeps the 4K
`thumbnail.png`, which video-generator pushes back to the server for the loop and puts in the S3 zip as
`thumbnail_full.png`. Server down → ask the owner: wait, or `--no-upscale` (the video still works; the zip warns).

## Steps

1. **Inputs.**
   - Channel: `channel/<ch>/visual.md` (world, constants, **Prompt ảnh mặc định (ChatGPT)** = the CORE block,
     **Biến thể hình ảnh** = the axes with their snippets, checks) and `model/README.md`.
   - Single: `single.md` → `track` file: `title`, `emotion`, `imagery`, `lyric_keywords`, `hook_phrase`, the lyrics, and
     `arc_role`/`energy`; plus its album's `thumbnail-prompt.md` (`signature:` and the album image). Album: `album.md` +
     Track 01. Idea: `idea.yaml` `packaging.thumbnail_brief` (already a brief).
   - Album or idea: `python3 $T list channel/<ch>` (text only) to see the previous album's `signature`. Do not open every
     earlier image: the axes already keep images apart.
2. **Choose the image** (write it under *Ý tưởng*):
   - One concrete picture from the song, not its abstract theme (`visual.md` has examples for this channel). The title goes
     on the image, the lyrics do not.
   - Keep the channel's constants from `visual.md`; pick every other axis from its *Biến thể hình ảnh* **by the song's vibe**
     (lyrics, imagery, emotion, energy, arc role) and say why under *Ý tưởng*. Never pick at random or by tool.
   - **Album signature.** An album image picks a title `lettering` style + 2–3 axes as the album's signature (by the album's
     vibe; not the previous album's) and writes them in `signature:` / `lettering:`. Whatever `visual.md` fixes for every
     image (e.g. a channel name line) never changes. Its singles copy that signature and change the other axes, so they
     read as the same season but never as the album video again (differ from the album image in setting and pose at least).
   - Pose: pick the `model/` file closest to the wanted angle; the character faces or turns toward the text or the light,
     not out of the frame, and stays recognisable in every framing.
   - Layout: title in one clear third, the character on the other side. Never text or faces inside the covered zones (the
     CORE block states them in %), including any small fixed line, which also stays above the bottom 15 % (spectrum bars).
3. **Write `thumbnail-prompt.md`** from the template: front matter filled (the axis keys of `visual.md`, `lettering`,
   `signature`; the `list` table reads them), *Đính kèm*, and *Prompt* = the CORE block **verbatim** + a `THIS IMAGE` block
   (`Title text: "<exact title>"`, Title style = the album's lettering snippet, Look = the chosen axis snippets, Scene, the
   character, Clothing, Light, Composition), in plain English sentences, one idea per line. Keep the title exactly as
   in the track file (capitalisation may follow the album's style). Run `python3 $T check <dir>` (prompt checks).
4. **Generate.** Automated (default): `chatgpt-chrome.sh`, then `python3 $G gen <dir>` (run in background; ~1–3 min;
   downloads every generated image into `thumbnail-drafts/`). Then, after picking, **always** `python3 $G delete <id>`:
   the ChatGPT account is shared, so no thread is left behind. Chrome launched by agent-browser itself is blocked by
   ChatGPT; only the real Chrome on port 9223 works, logged in once by the owner. Not logged in → ask the owner.
   Manual fallback: the owner pastes the prompt in a new chat and saves results to `<dir>/thumbnail-drafts/NN.png`.
   Log each round in *Các lượt thử*. ChatGPT returned 1672×941 in 2026-09 even when asked for 2560×1440; `fit` upscales it.
5. **Check each draft**: Read the image and judge what the script cannot, using `visual.md`'s check list (text spelled
   exactly, the character matches `model/`, hands, nothing important in the corners, the constants hold, it reads at
   phone size). Then `python3 $T check <dir> --image <draft>`: ratio, size, zone detail (> 1.3 × the image average = busy),
   warm bright spots. Give one concrete follow-up edit (`references/chatgpt.md`) or say it is ready. **Claude picks the
   draft itself** (the owner does not review drafts): the one passing every check, and write why under *Các lượt thử*.
6. **Finish**: `python3 $T fit <dir> <chosen draft>` (move `--x/--y` when the crop cuts the title or the head; ~1 min,
   run it only on the chosen draft, never on every draft). Read `thumbnail.png` and compare it with the draft: the upscaler
   must not have changed the title letters, faces or hands (it never did in the test, but look). Then
   `python3 $T check <dir>`, set `status: chosen` + `chosen:`. Hand off to `video-generator` step 1: its first bright spot
   from `check` is the starting point for `lantern.center` in `<dir>/video.json`. An older 1920×1080 thumbnail can be
   brought to 4K the same way from its draft (or from `thumbnail.png` itself: `fit` backs it up to `thumbnail-drafts/prev-*.png` first).

## Principles

- **Inspired, not copied** (CLAUDE.md): never describe a reference channel's thumbnail, their artist or their lettering;
  no real person's likeness. The character is the channel's own, in `model/`.
- ChatGPT prompts are plain descriptive sentences. No Midjourney syntax (`--ar`, weights, comma tag soup).
- Claude cannot see how ChatGPT will draw it. Promise nothing about the result; judge only images that exist.
- Say which numbers are measured (`check`) and which are Claude's visual judgement.
- Something learned about this channel's images (a recurring ChatGPT mistake, a zone that keeps getting hit): one line
  in `channel/<ch>/visual.md`, not here.
