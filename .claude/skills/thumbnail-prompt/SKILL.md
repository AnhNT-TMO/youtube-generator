---
name: thumbnail-prompt
description: Write the ChatGPT image prompt for a channel thumbnail - for a single song released on its own (channel/<ch>/singles/NNN-slug, built from the song's lyrics, imagery and emotion), an album, or an idea (idea.yaml packaging.thumbnail_brief) - on top of the channel's fixed CORE block in channel.md (only the amber lamp and the singer's face are constant), choosing wardrobe, framing, light, palette and the other variation axes by the song's vibe and keeping the album's visual signature, with the singer kept identical through the reference images in channel/<ch>/model/, title lettering chosen per album (the small "Lamplight Gospel" line fixed), and the corners that the video's logo / subscribe / spectrum overlays cover kept free; then fit ChatGPT's result to 16:9 and upscale it to a 4K 3840×2160 thumbnail.png on the GPU server (SeedVR2 7B, plus a ≤ 2 MB thumbnail.jpg for YouTube) and check it (size, covered zones, lamp position for video.json). Use when the user says "viết prompt ảnh", "prompt thumbnail", "tạo ảnh cho bài", "ảnh cho single", "thumbnail cho idea/album", "ChatGPT vẽ ảnh", sends a ChatGPT image to use as a thumbnail, or asks why an image does not fit the video. Does NOT render video (video-generator).
---

# Thumbnail prompt

The image step before `video-generator` step 1. The user makes images in **ChatGPT** (upload reference + paste prompt,
download PNG). Claude writes the prompt, the user generates, Claude fits + checks the result and looks at it.
The same image is both the YouTube thumbnail and the video background (video-generator animates it), so it must work
under the overlays: logo top-right, like/subscribe bottom-right, spectrum bars bottom-centre.

```bash
T=.claude/skills/thumbnail-prompt/scripts/thumb.py   # repo root; python3 + ffmpeg + ssh only, no venv; one word per var (zsh)
python3 $T list  channel/<ch>                       # text table of every thumbnail: album signature, wardrobe, framing, light, palette, setting…
python3 $T fit   <dir> <downloaded.png> [--x .5 --y .5]   # crop to 16:9 around (x, y) → GPU server SeedVR2 7B → <dir>/thumbnail.png 3840×2160 + thumbnail.jpg ≤ 2 MB (~1 min)
python3 $T fit   <dir> <downloaded.png> --no-upscale     # fallback when the server is down: Lanczos 1920×1080 on this Mac
python3 $T check <dir> [--image <file>]             # size/ratio (warns < 4K), detail in the 3 covered zones, warm bright spots, prompt vs channel CORE block
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
SeedVR2 7B (a one-step diffusion restorer) redraws it at 3840×2160 with real new detail (beard hairs, skin, crisp
lettering) while keeping colours, the singer's face and the text. Chosen by a measured test on 2026-09-24 against
Lanczos, HAT-L, UltraSharpV2, Real-ESRGAN, SeedVR2 3B / 7B-sharp and SUPIR. The server keeps nothing afterwards; this Mac
keeps the 4K `thumbnail.png`, which video-generator pushes back to the server for the loop and puts in the S3 zip as
`thumbnail_full.png`. Server down → ask the owner: wait, or `--no-upscale` (the video still works; the zip warns).

## Steps

1. **Inputs.**
   - Channel: `channel.md` section **Prompt ảnh mặc định (ChatGPT)** (the fixed CORE block), section **Biến thể hình ảnh**
     (the axes: wardrobe, framing, light, palette + free axes, each with an English snippet) and `model/README.md` (which
     reference file shows which angle). No block → write one with the user first (lamp, singer, lettering, free areas, avoid).
   - Single: `single.md` → `track` file: `title`, `emotion`, `imagery`, `lyric_keywords`, `hook_phrase`, the lyrics, and
     `arc_role`/`energy`; plus its album's `thumbnail-prompt.md` (`signature:` and the album image). Album: `album.md` +
     Track 01. Idea: `idea.yaml` `packaging.thumbnail_brief` (already a brief).
   - Album or idea: `python3 $T list channel/<ch>` (text only) to see the previous album's `signature`. Do not open every
     earlier image: many axes already keep images apart (channel owner 2026-09-24).
2. **Choose the image** (write it under *Ý tưởng*):
   - One concrete picture from the song, not its abstract theme: "Hold my trembling hands" → his hands cupped around the
     lantern; "Morning Is Coming" → first light on the horizon behind him, lamp still lit. The title goes on the image,
     the lyrics do not.
   - **Only two constants: the amber lamp flame (brightest point, its light reaches him) and the singer's face.** Pick every
     other axis from `channel.md` *Biến thể hình ảnh* **by the song's vibe** (lyrics, imagery, emotion, energy, arc role),
     and say why under *Ý tưởng*. Never pick at random or by tool. Examples: a closing song of peace → `close` + `dawn` +
     `sepia`; a desperate night → `wide` + `single` + `mono`; a road/waiting song → `traveler` + `rain`; a song retelling a
     scripture scene → `biblical` with a clay oil lamp; a choir peak → `sunday` (old choir robe) in a small wooden church.
   - **Album signature.** An album image picks a title `lettering` style + 2–3 axes as the album's signature (by the album's
     vibe; not the previous album's) and writes them in `signature:` / `lettering:`. The small "Lamplight Gospel" line never changes. Its singles copy that signature and change the other axes, so they read as
     the same season but never as the album video again (differ from the album image in setting and pose at least).
   - Keep the channel's theme (`channel.md` *Hình ảnh*): the light reaching a poor, weary, ageing man in a humble place, a
     lined and tired face that the light lifts. Clothes always poor, old, worn or mended, from one of the five wardrobe
     families; never the tuxedo, suit or bow tie of the `model/` images (they fix only the face), nothing that looks rich.
     `biblical`: the whole scene belongs to that time (stone, olive trees, clay lamp) and he is never Jesus.
   - Pose: pick the `model/` file closest to the wanted angle; the singer faces or turns toward the text or the light,
     not out of the frame. His face stays recognisable in every framing (no full silhouette, no back view).
   - Layout: title in one clear third, the singer or his face on the other side, lamp placed so its glow leads to him.
     Never text or face inside the covered zones (the CORE block states them in %); the "Lamplight Gospel" line too sits
     above the bottom 15 % (2026-09-24: it touched the spectrum bars in single 006). A `close` face may fill half the frame
     but stays out of the top-right and bottom-right corners.
3. **Write `thumbnail-prompt.md`** from the template: front matter filled (`wardrobe`, `framing`, `light`, `palette`,
   `lettering`, `signature`; the `list` table reads it), *Đính kèm*, and *Prompt* = the CORE block **verbatim** + a `THIS IMAGE` block
   (`Title text: "<exact title>"`, Title style = the album's lettering snippet, Look = the chosen framing + light + palette snippets, Scene, The singer, Clothing = the
   chosen wardrobe snippet, Light, Composition), in plain English sentences, one idea per line. Keep the title exactly as
   in the track file (capitalisation may follow the album's style, e.g. "When the night is long"). Run
   `python3 $T check <dir>` (prompt checks).
4. **Generate.** Automated (default): `chatgpt-chrome.sh`, then `python3 $G gen <dir>` (run in background; ~1–3 min;
   downloads every generated image into `thumbnail-drafts/`). Then, after picking, **always** `python3 $G delete <id>`:
   the ChatGPT account (PIXTA Inc. Business) is shared, so no thread is left behind. Chrome launched by agent-browser itself
   is blocked by ChatGPT; only the real Chrome on port 9223 works, logged in once by the user. Not logged in → ask the user.
   Manual fallback: the user pastes the prompt in a new chat and saves results to `<dir>/thumbnail-drafts/NN.png`.
   Log each round in *Các lượt thử*. ChatGPT returned 1672×941 in 2026-09 even when asked for 2560×1440; `fit` upscales it.
5. **Check each draft**: Read the image and judge what the script cannot: title and "Lamplight Gospel" spelled exactly,
   the face matches `model/` (bald, beard graying at the chin, same age), five fingers, nothing important in the corners,
   the lamp is the brightest point, it still reads at phone size. Then `python3 $T check <dir> --image <draft>`: ratio, size,
   zone detail (> 1.3 × the image average = busy), warm bright spots. Give one concrete follow-up edit
   (`references/chatgpt.md`) or say it is ready. **Claude picks the draft itself** (owner 2026-09-24, CLAUDE.md §4 Cổng
   duyệt; later the agent manager): the one passing every check above, and write why under *Các lượt thử*. Don't ask the owner.
6. **Finish**: `python3 $T fit <dir> <chosen draft>` (move `--x/--y` when the crop cuts the title or the head; ~1 min,
   run it only on the chosen draft, never on every draft). Read `thumbnail.png` and compare it with the draft: the upscaler
   must not have changed the title letters, the face or the hands (it never did in the test, but look). Then
   `python3 $T check <dir>`, set `status: chosen` + `chosen:`. Hand off to `video-generator` step 1: its first bright spot
   from `check` is the starting point for `lantern.center` in `<dir>/video.json`. An older 1920×1080 thumbnail can be
   brought to 4K the same way from its draft (or from `thumbnail.png` itself: `fit` backs it up to `thumbnail-drafts/prev-*.png` first).

## Principles

- **Inspired, not copied** (CLAUDE.md §1): never describe a reference channel's thumbnail, their singer or their lettering;
  no real person's likeness. The singer is the channel's own character in `model/`.
- ChatGPT prompts are plain descriptive sentences. No Midjourney syntax (`--ar`, weights, comma tag soup).
- Claude cannot see how ChatGPT will draw it. Promise nothing about the result; judge only images that exist.
- Say which numbers are measured (`check`) and which are Claude's visual judgement.
