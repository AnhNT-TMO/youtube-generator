---
name: pool-production-flow
description: CEO 2026-09-28 refactor - skills grouped pm-/rnd-/audio-/video-/upload-; Suno Simple-mode song pool reused across albums; CEO+PM plan albums; 1 album + 1 Short; titles from the phrase bank (verbatim allowed)
metadata:
  node_type: memory
  type: project
  originSessionId: bf98b055-3b54-48b0-8e13-5ecb5b380d81
  modified: 2026-09-28T13:42:58.951Z
---

CEO 2026-09-28 (after Lamplight Gospel failed in a week): new main channel `shelter_stone_gospel`, whole flow simplified.
- Skills renamed `<group>-<job>`: pm-production, rnd-youtube-api, audio-suno-generate, audio-song-naming (new), audio-album-assembly, video-shorts, upload-youtube-publish, upload-youtube-translate (logic unchanged). Removed: album-plan, verification-audio, youtube-music-analyzer (old code only in git history; the local archive/ was deleted 2026-09-29 by CEO order).
- Music: per-channel fixed prompts `channel/<ch>/prompt_suno.md` (Stone: `spoken` = spoken intro+outro, `sung` = straight in), Suno **Simple mode**, model `v6` (CEO said "v6-pro"; the menu only has v6 with a Pro badge / v6-wild / v6-mini), download BOTH clips via usesuno. No verify. Pool `channel/<ch>/songs/<type>/` (spoken/ vs sung/ folders, CEO 2026-09-28). A generation's 2 clips with the SAME lyrics = one song, files `<title-slug>_v1` / `_v2` (v1 = first clip id; CEO: never lose track of versions); DIFFERENT lyrics (~half of long-form generations, ~20 credits) = 2 separate songs with own titles; empty clip → drop, keep the good one (PM standing rule). Chapters show the plain title. Short segment chosen per version at naming (Whisper on server). Long-form clause at the end of each prompt gives ~6-min songs; Voice Male 04 (314 Hz) in prompt_suno.md.
- Albums: no plan.yaml. CEO + PM plan directly → `albums/NNN/album.md` (brief + tracklist) → `album.py check/build`. Stone rules: 60–80 min, alternate spoken → sung → …, track 1 spoken, light 3 s crossfade, no cutting.
- Release = 1 album + 1 Short per day; no singles. The Short is part of the album: `albums/NNN-slug/short/` (CEO 2026-09-28). Short image = the singer standing upright, frontal, eye contact, chapel with the album's vibe, no mic, no props, no lettering.
- Titles + thumbnail text come from `research/phrase-bank/gospel.yaml` (fast-growing niche videos by views/day). CEO 2026-09-28 (later the same day): common prayer phrases / classic quotes owned by nobody may be used VERBATIM, even when many channels use them, especially if still viral; adapting is optional; never other channels' names/logos/branding/images; two of our own videos never share a title/thumbnail line. Checks only warn on bank overlap, never block.

**Why:** new songs per album cost too much; big niche channels reuse a small pool and still grow.
**How to apply:** follow CLAUDE.md §0–§7 as rewritten 2026-09-28. Video group (`thumbnail-prompt`, `video-generator`) was NOT refactored because another session was editing it: rename to `video-thumbnail` / `video-render`, drop their idea/single/plan logic and the "production-manager" text in the shared LIMIT line only after the CEO says that session is done. Related: [[company-model]], [[mercyharbor-clone-candidate]], [[never-use-suno-download]]
