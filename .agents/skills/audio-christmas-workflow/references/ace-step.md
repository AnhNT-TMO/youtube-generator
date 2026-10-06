# ACE-Step operations

Active paths, settings and state come from the pool config. The source is a simple three-part note plan; no external composition library is required. `run.sh` already runs every command below in the right environment; this page explains what they do and how to read their output when a phase fails.

## Tools and server

- `source_audio.py`: chord parsing/transposition, MIDI writing and SoundFont source rendering. Assign only piano, configured bed parts and the configured support part. Vibraphone uses GM program 11 on channel 10 (zero-based); viola uses GM program 41 on channel 11, cello program 42 on channel 12. Avoid percussion channel 9. Name actual SoundFonts; GM source instruments do not certify an AI cover's timbre. Piano melody/left hand are two tracks of one instrument.
- `source_effects.py`: source reverb. It has no reference-matching master/EQ stage.
- `cover_takes.py`: exact-caption cover requests with configured checkpoint, identity and cache verification. Checks configured style/base-parts and requires zero source accents.
- `select_takes.py`: existing provisional technical selection. New configurations have no choir exception.
- `mix_accents.py`: the configured documented real gestures added to the selected base, see [Real Accents](real-accents.md).
- Configured evaluation mirrors depend on the existing server analysis modules/reference corpus. The reference corpus is for copy diagnostics, not choosing another channel's vibe.

Machine layout: `~/ace-step/tools-venv` for source, `ACE-Step-1.5/.venv` for generation, `eval-venv` for evaluation/mixing and the existing Demucs environment for vocal proxies. The guarded accent integration was verified with `eval-venv`; `tools-venv` currently lacks soundfile. Mixing needs numpy, soundfile and ffmpeg. Keep SoundFonts, `ace_bench`, `prompt_lab`, `harsh`, `seed_diff`, `ref_eval` dependencies. Read access details from machine configuration; no credentials in shared tooling.

`run.sh sync` deploys the scripts, `WORKFLOW.json`, track plans and the melody file to the server tool and work directories (one copy, checksum-compared). Do not execute stale copies just because filenames match. Workdirs are `<slug>/<style>/<revision>/`; one source per workdir. Never use old multi-instrument Deck renderers as the new base template. They remain useful for asset provenance only.

Heavy source rendering, generation, evaluation, sample mixing, loudness and encoding run through `.claude/skills/pm-production/scripts/server_guard/guard.sh run` from the Mac. This activates guard and `youtube.slice`; cover also locks `/tmp/carol_gpu.lock` across loading/generation with cooling. Inspect guard kills after abnormal termination; never fall back to local audio processing. Lightweight JSON/plan validation can run locally.

## Revision files

- `track-plan.json`: meta/key/meter/tempo, style, ordered `base_parts`, `accents_in_source: 0`, exact `render.ace_step.caption`, tempo evidence, notation reference, concrete notes and phrase plan.
- `src_A.mid`, `src_A.wav`, `src_A.json`: metadata with `variant: A`, style, ordered base parts, zero source accents, key/meter/quarter BPM and exact `arrangement_caption`. A is only a filename convention, not a historical profile.
- Paired MIDI onset/off/duration verification and complete melody/part/channel accounting. Source metadata labels alone do not prove actual source instrumentation.
- `cov_*.flac`, full request/hash sidecars and `cover-revision.json`.
- `eval_a.json` with candidate and matching source metrics; `eval_b.json` with file basenames and vocal measurements; `picks.json`.
- `mix-plan.json`, accented WAV and its event/provenance/gain manifest.
- Audition MP3, encoded measurements, `NGHE_THU.md`, `listening-map.json` and checksums.

## Generate and select

`run.sh covers` calls `cover_takes.py <style-revision> --config <server WORKFLOW.json> --stage revision --spec track-plan.json` for each style. Default spec path is `track-plan.json`. Caption must equal source metadata exactly, with the configured physical base instruments and no requested accent runs/sweeps. Key/meter/BPM and configured matrix must match. `initial` uses configured seeds/noise strengths; `expansion` adds distinct seeds in the unchanged revision after defect diagnosis; `revision` uses its smaller matrix in a fresh source revision. Limits apply separately to each style. A held config refuses generation.

The checkpoint must equal `ace_bench.DIT`; identity records checkpoint configuration hashes and weight size/mtime, not a complete weight-content hash. Cache checks also include source audio/metadata/spec hashes, request settings and output SHA256. A source/caption/checkpoint change requires a new revision. Inspect interrupted `.d` directories/orphan metadata before resuming.

For unsupported meter hints, use only configured omitted meters. Keep true meter in source/spec/caption; empty API hint is a documented degradation, not permission to substitute 4/4 or proof that the cover kept the meter.

`run.sh covers` then runs `carol_eval_a.py`, `vocal_check.py`, `select_takes.py`, `key_gate.py` and `apply_pick_policy.py`; `run.sh gate` repeats only the selection and key gate. Exit 0 gives at least one passing primary; exit 2 requires review. Inspect missing/nonfinite measurements rather than spend seeds. `picks_instr`, `backups` and `retained_takes` distinguish selected base/backup. Default no-vocal gate applies to all new styles; choir historical parameters are inactive.

Harshness is source-relative. Opening metric is first-five-second HF peak minus active whole-track HF P95; gate on `max(0, cover_excess) - max(0, source_excess)` and keep signed values diagnostic. Audio-feature similarity is not note transcription, vocal proxy is not proof of no voice, and CLAP is not instrument detection. Musical/seasonal quality remains unverified until feedback.

## Add accents, finish and resume

After a base passes, confirm actual-cover phrase transitions and its musical end. If the raw lacks mixing headroom, prepare a separate fixed-gain base copy on the server, preserve the raw and record its hash and attenuation; do not limit or compress it. Validate/render the mix plan against the actual base copy with `mix_accents.py`. New raw backup is also a base: if replacing the pick, check its own boundaries and create its own mix manifest, never reuse the primary's timing evidence blindly.

Finish the resulting accented WAV using global fixed gain constrained by configured true peak. Leave quieter if necessary. Encode MP3, independently measure LUFS/true peak and reduce gain/re-encode from accented WAV if peak is too high. Analysis using loudnorm is not authorization to apply its processing. No base reference EQ, stereo matching, compression or cutting/splicing; sample-only fades/filtering are documented in the accent stage.

Deliver one primary MP3 and store a base backup per style, with provenance and records above. Keep raw and older packages unchanged. Source verified, technical pass, ready for listening and listener accepted are separate statuses. Accent-only changes reuse the exact raw base; piano/bed/support/tempo changes regenerate the full cover and its timing maps.
