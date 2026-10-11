---
name: christmas-music-direction
description: "CEO 2026-10-05: ACE-Step dropped and deleted; PD carols now = our MIDI rendered by virtual instruments on server (no AI audio); piloting ambient/cinematic 'Interstellar-vibe' style; piano solo rejected"
metadata:
  type: project
---

CEO 2026-10-05 changed the Christmas PD carol direction. The old flow (MIDI → ACE-Step cover) sounded smeared and buzzy. The CEO heard the raw MIDI in MuseScore sound clearly better.
- ACE-Step was uninstalled. Server `~/ace-step` and `youtube-qc/ace-steps` were deleted, and so was Mac `ace-steps/`. Track plans and MIDI were kept in `research/christmas-carols/plans-archive/`. Soundfonts (Salamander V3, MuseScore_General, FluidR3) are in server `~/music-tools/sf2/`.
- Render path: we write MIDI by rules, then render it on the server.
  - Tools in `~/music-tools/` (3.5 GB):
    - venv: DawDreamer 0.9; tinysoundfont is installed with `--no-deps` because pyaudio fails to build.
    - Surge XT VST3: load factory .fxp presets by swapping the "sub3" chunk into the JUCE state (`jstate.py`).
    - Dragonfly Hall VST3: parameters are linear in their ranges.
    - VSCO-2-CE CC0 WAVs only (strings, organ, flute; no SFZ). A numpy sampler plays them, using `index.json`: name octave +1, organ midi = number − 86.
    - No sfizz. MuseScore 4.7.5 is at `~/apps/musescore` (run via `xvfb-run`).
  - Run DawDreamer with `env -u DISPLAY`: xvfb crashes when loading Surge state.
  - The server cannot download from GitHub. Download on the Mac and rsync over the LAN.
  - 
  - Finish at −18 LUFS fixed gain. The chime step is kept.
- Piano solo was tried on Silent Night and rejected: human pianists win that genre. 
- Interstellar-vibe pilot v1 was rendered, then rejected by the CEO on 10-05 as not Christmassy. It was modelled on the "Interstellar soft cover" vibe (Piano Pill, 13M views). It uses a soft repetitive arpeggio ostinato with the carol melody slow on top, plus pad/organ and strings that build gradually.
  - About 100/137 carols fit. Fast/children carols do not fit (Jingle Bells, Deck, We Wish You).
  - The CEO accepts reusing tier I songs across albums.
- CEO 10-05 picked vibes "snow globe" (piano + harp + cello/viola + celesta + sleigh) and "candlelight church" (piano + organ + choir + tubular bell). The flute-lead orchestral vibe was rejected as not the channel's vibe. Use only real-recorded instruments, no GM soundfont: `~/music-tools/sfz/real/` holds SSO celeste (CC0), SSO mixed chorus (CC Sampling Plus: don't redistribute raw samples), and VCSL tubular bells + hand chimes (CC0; VCSL/VSCO name octave +1). Renderer is `audio-christmas-workflow/scripts/ambient_batch.sh` (+ ambient_render/ambient_harmony). Output goes to `audio/christmas/<slug>/` (gitignored). CEO 10-05 approved the real-sample sound; a 6-song test (eval5 songs + Hark) was delivered. Test dirs (ambient-pilot, musescore-pilot, server tmp-*) were deleted, except server tmp-album001 (old album master).
- Knowledge must be our own rules, not clones of reference videos. Measure references only for aggregate targets.
- Suno blocks uploads of existing songs, so Suno Cover of PD melodies is not possible.
- Chord-colour rules (function-based reharm with a melody-fit check, richer per pass) live in `scripts/ambient_harmony.py`.

**Why:** AI-generated audio sounded bad. Ambient depends on sound design rather than human performance, so deterministic MIDI rendering can compete there.

**How to apply:** do not propose ACE-Step on my own. CEO 2026-10-10 re-tested ACE-Step 1.5 XL Base (cover→complete, lego, Mureka-style remix with doubling captions): complete/lego barely added instruments, cfg 7 made the piano buzzy, celesta/glock stayed tiny; CEO had already found xl-sft no better. Branch closed again and everything deleted on server + Mac. The `audio-christmas-workflow` skill and STANDARD.md still describe the old flow; rewrite them after the CEO approves the ambient pilot.

Related: [[christmas-instrumental-brainstorm]] [[no-listening-questions]] [[heavy-work-on-server]]
