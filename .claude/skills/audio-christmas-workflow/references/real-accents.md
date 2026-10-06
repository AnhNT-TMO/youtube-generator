# The recorded chime after ACE-Step

The current standard is one recorded chime per version at the A1 → A2 boundary near 1/3; its asset, level, lowpass and window are `WORKFLOW.json` → `pipeline.chime`. `run.sh finish` builds the mix plan from that block and the selected cover, runs `mix_accents.py` and records everything; read this page when a chime has to change (that change is a PM decision). The active config owns the styles, each style's ordered gestures and the quiet level policy. This tool adds only those gestures to an otherwise finished piano + configured harmonic bed + support cover. A continuous support part is distinct from either brief accent. The gestures are not supplied to ACE-Step as source events when this post-cover route is used; confirm the chosen cover has no extra transition gestures before mixing.

Use a complete recording of the actual instrument and playing gesture, with recorded provenance and production permission. A synthesized bell scale is not a swept bar chime. The script cannot authenticate a recording or recognize instrument timbre from measurements; the provenance assertions are checked records, not acoustic proof. If a gesture sounds sharp, synthetic or unlike its instrument during the authorized audition, replace it or revise its sample treatment before acceptance.

Reference media and production assets are separate. Keep source URL, recordist, license text/link, recording evidence and SHA256 with each production sample. Preserve attribution where required. A known public reference without a downloaded, licensed, verified production asset cannot enter a mix. Do not use copyrighted piano recordings as the base or download assets whose permission is unresolved.

## Performance library and selection

Use the project's library target per gesture. Track `asset_id`, `performance_id`, `source_group`, recordist and performer separately, with the performer's identity evidence when available. Different uploads or encodings of one recording are one performance. Several takes from a shared session can offer gesture variety but do not establish several players; a recordist or library credit does not necessarily identify the player.

Keep acquisition and approval separate: discovered, provenance-checked, acquired, gesture-reviewed, tonally checked for the specific event, and approved for that mix. Preserve complete source files and their evidence. A file containing several sweeps is one source recording with potential child gestures, not several independent players. Extraction and audio review run on the guarded server; child assets retain parent hash and exact extraction times.

Select by gesture, local key/harmony, duration, attack and intact decay before considering variety. Among suitable recordings prefer a different performance, and then a different evidenced player or source, from recent neighboring tracks. Keep the configured events and their order. If only a repeated asset is compatible, record the reuse reason instead of inserting a mismatched sample. Store stable asset/performance IDs in the mix plan's sample metadata and append a usage record only after a mix has been produced, including song, style, revision, accent slot and output manifest. Do not invent performer diversity or a successful mix from library counts.

## Timing and tonal compatibility

Choose a phrase transition near the configured target fractions of the actual cover's musical body, excluding the closing decay. Inspect the actual selected cover to record its musical end and each target boundary. Do not transfer timestamps from the source MIDI, assume unchanged phrase timing because durations match, or use the album clock. Document the method and its evidence against the selected cover hash.

`onset_s` is the audible gesture entrance at that boundary. `tail_end_s` is reported separately after decoding and retaining the sample's natural decay. Both complete samples must fit the unchanged base duration and their tails must not overlap. A long sample must not be cut to force it into place. Replace it with a suitable shorter gesture if needed. The script trims only near-silent leading/trailing padding, adds a short edge fade and rejects an already truncated audible decay.

For harp and glockenspiel gestures, verify the actual sample notes/scale and the selected cover's key and local harmony. A chromatic glissando is not automatically compatible with every carol. Prefer a suitable recorded scale; this tool neither retunes recordings nor synthesizes replacement notes. A non-tonal bar-chime sweep still needs a documented timbre and compatibility review. If notes/harmony are unknown, stop at asset research rather than label compatibility verified.

## Mix plan

All media paths are relative to the mix plan's directory, or absolute server paths. SHA256 values must be lowercase, complete hashes. The config is required even for validation. Use its style identifier and gesture order verbatim. The `accents` list has one entry per configured accent, in order.

```json
{
  "style": "celesta",
  "base": {"path": "selected-cover.flac", "sha256": "<64 lowercase hex characters>"},
  "musical_end_s": 180.0,
  "musical_end_evidence": "Actual cover inspection: final piano phrase ends at 3:00, followed by decay.",
  "base_has_no_accent_gestures": true,
  "accents": [
    {
      "gesture": "harp_glissando",
      "onset_s": 59.2,
      "relative_db": -18,
      "phrase_boundary": {
        "timeline": "actual_cover",
        "base_sha256": "<same base hash>",
        "time_s": 59.2,
        "method": "actual-cover phrase review",
        "evidence": "The melody resolves and begins the next phrase at 0:59.2 in this cover."
      },
      "sample": {
        "path": "assets/harp-glissando.wav",
        "sha256": "<64 lowercase hex characters>",
        "gesture": "harp_glissando",
        "real_recording": true,
        "source": "<recording URL or owned recording identifier>",
        "recordist": "<recordist name>",
        "license": "<actual license>",
        "license_evidence": "<license URL or retained permission file>",
        "recording_evidence": "<source statement or owned recording session evidence>",
        "production_use_authorized": true,
        "trim_start_s": 0,
        "lowpass_hz": 6000
      },
      "tonal_compatibility": {
        "verified": true,
        "sample_notes": "<actual verified pitch collection>",
        "cover_key": "<actual cover key>",
        "boundary_harmony": "<actual local harmony>",
        "evidence": "<how pitches and local harmony were verified>"
      }
    }
  ]
}
```

The example is a schema excerpt, not a valid production plan or a verified recording. A bar-chime entry instead uses `tonal_compatibility: {"non_tonal": true, "evidence": "<verified non-tonal sweep and local suitability>"}`. Do not copy illustrative timestamps or assertions without checking the actual media.

## Validate and render

Lightweight local inspection reads JSON and checks file existence only; it does not load audio, hash media, measure loudness or certify listening quality:

```bash
python3 .claude/skills/audio-christmas-workflow/scripts/mix_accents.py mix-plan.json \
  --config research/christmas-carols/WORKFLOW.json \
  --output finished-with-accents.wav --validate-only
```

Deploy the current script, config, plan and licensed sample files to an isolated revision on the server. Run decoding/mixing through the existing guarded server command, using the server's Python with numpy/soundfile and ffmpeg:

```bash
.claude/skills/pm-production/scripts/server_guard/guard.sh run \
  '<server-python> <server-tools>/mix_accents.py <revision>/mix-plan.json --config <server-config> --output <revision>/finished-with-accents.wav'
```

The renderer refuses execution outside Linux `youtube.slice`, verifies all media hashes and never overwrites existing output or raw inputs. It decodes to 48 kHz stereo, leaves the base arrangement and duration intact, and writes 24-bit WAV plus `finished-with-accents.wav.json` containing plan/config/output hashes, per-gesture onset/tail times, gain and measurements. Paths must point to the server copies when rendering.

Gain is fixed for each sample. A median of non-silent 100 ms base windows within four seconds of the boundary sets a local level reference. Sample RMS uses its louder active gesture frames, excluding its quiet decay, to avoid making a short attack loud because of a long tail. Requested level and range come from config, with a safety upper bound of -10 dB active RMS. The separate `transient_peak_relative_db` ceiling relative to local base RMS (legacy default -6 dB; supported range -18 to +3 dB) and output headroom can make it quieter. Record requested versus actual RMS, sample crest factor and the limiting constraint; high-crest recordings can be inaudible under the legacy cap despite a louder RMS request. Policy changes need a project brief, never a worker bypass. Final encoded true peak still must meet the project limit. There is no ducking, pumping, compression or normalization of the base. No EQ is applied to the base; optional sample-only two-pole lowpass and tiny edge fades are recorded.

The provisional brightness gate rejects sample power above 5 kHz exceeding 30% of total power after the optional filter. It is a coarse excessive-brightness diagnostic, not proof of soft/magical timbre or an instrument classifier. Changing this gate requires documented evidence; do not bypass a rejection by falsely asserting the timbre is verified. Sample peaks do not measure true peak: downstream fixed-gain audition finishing must still independently measure the encoded MP3's LUFS and true peak using the configured limits.

The resulting status is `needs_listening_review`. Technical validation does not confirm musical phrasing, harmonic-bed balance, the absence of an unwanted generated gesture, or natural recorded timbre. Include the actual onsets and instrument names in listening notes, preserve this manifest alongside the original cover, and use the existing audition/album finishing steps after this authorized addition.

For an authorized audition whose actual-cover diagnostics cannot establish the complete audible gesture count, omit `base_has_no_accent_gestures` or set it to null, set `audition_only: true`, and supply `base_gesture_review: {"status": "unverified", "evidence": "<actual-cover diagnostic evidence and perceptual limitation>"}`. This narrow route produces a listening-review candidate, never release approval or a claim of total base compliance. Missing review, an explicit false assertion, or `status: known_extra` still rejects the mix; known extra gestures require another base or a source revision. The inserted events remain separately verified.
