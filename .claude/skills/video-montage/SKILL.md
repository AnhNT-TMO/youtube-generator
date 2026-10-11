---
name: video-montage
description: Choose and sequence accepted resource clips into a long music-album montage, preview on the GPU server, then render a 4K video with the channel intro and album master. Use for montage albums, cast selection, scene ordering, silent renders, or remuxing updated music. Still-image loops use video-generator; vertical countdowns use video-shorts.
---

# Album montage

Run commands from the repo root. Read the album's `album.md`, the resource set's `resource.json` and montage contract (`image_source/MONTAGE.md` for the original library), and the channel's `intro.json`. The approved brief determines cast, hero exceptions, duration and opening order; preserve an already approved sequence.

```bash
M=.claude/skills/video-montage/scripts/montage.py
python3 "$M" status <set>
python3 "$M" pick <album-name> --channel <channel> --set <set> --lead <family> --mood <mood> --minutes <minutes> --seed <seed>
python3 "$M" preview <album-name> --channel <channel> --first <slots>
python3 "$M" render <album-name> --channel <channel> --audio <server-master-path>
```

- `pick` writes `montage.json`, `clips.txt` and sequence checks in the album folder. For an existing PM-selected cast, pass `--keep-cast <montage-json>`; review checks and `timeline.txt` before rendering.
- `measure`, `preview` and `render` run on the GPU server; `setup` provisions its tooling. Connection settings are in this skill's `remote.env` (see `remote.env.example`). Use the source skill command so the existing local config is found.
- `video-upscale` prepares the selected cast in `~/video_sources/<library>/`; `<library>` comes from the set's `resource.json`. Render waits for missing clips; `--wait-clips 0` fails immediately instead. `--after-unit <unit>` waits for another server job.
- Render composes 1080p clips, scales to 3840x2160, encodes HEVC NVENC and adds the channel intro. Outputs stay in `~/video-montage/out/<album-name>/`.
- Keep `<album-name>-2160p-silent.mp4` when music changes. Remux the approved master with video stream copy and AAC 320k through the server guard; do not repeat the full scene render. Check audio/video duration and the beginning, middle and end of the output.
- Thumbnail: use the approved scene's original image and `thumbnail-prompt` for 4K fit; apply the channel branding. Publish fields come from `upload-youtube-publish`.
- Read the album's delivery decision before packaging. The existing `video.py package` flow is not the montage packager; do not force a montage/countdown release through its lyric-Short checks. Record the delivered archive in the album's package record. Countdown production and its approval/zip are handled by `video-shorts`.
