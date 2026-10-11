# Self-arranged bell-piano lane

This lane renders the final arrangement itself, rather than providing a source to Mureka. Read the approved album brief, then `research/christmas-carols/experiments/piano-arrange/PRINCIPLES.md` for the current musical contract and `DECISIONS.md` for the latest approved changes. These are shared repository files, accessible from either assistant. Older ambient and Mureka instructions are separate lanes.

## Inputs and tools

The working directory is `research/christmas-carols/experiments/piano-arrange/`. Keep its scripts there for now: they share local dependencies and specs. It is ignored by git and must accompany a transfer to a different machine.

- `ensemble_arrange.py`: phrase-aware arrangement and rendering, including bell-register piano, instrument doubling, beds, sleigh and choir legato.
- `render_variants.py`: render the PM-approved variant JSON in a batch.
- `measure_tune.py`: tuning measurements for sample alignment.
- `master_album.py`: assemble the selected files from the approved join spec.
- `variants_*.json`, `join_*.json`: approved choices and ordering; use the album's actual spec, not a remembered example.

Use `--help` and inspect each script's arguments before running. Rendering, mastering and full-track analysis run on the GPU server through `.claude/skills/pm-production/scripts/server_guard/guard.sh run`. Required server assets include Piano in 162, `sfizz_render`, sample libraries, measured tuning and the approved choir soundfont. Missing assets block rendering; do not substitute instruments silently.

## Preserve the approved sound

- Every melody needs current clean PD evidence; use allowed keys and the approved song order. Keep piano as the lead and arrange each song for its own phrases and register.
- Consult PRINCIPLES for doubling ranges, tuning, grace limits and sparse sleigh accents. Instrument choice and levels belong to the musical contract, not to Mureka's three-instrument prompt rules.
- Choir is a chord bed entering from verse two. Apply the approved soundfont and level, tie common tones and overlap changing tones with `choir_legato`; do not revert to the earlier separated chords.
- Ensure the pool has the ordinary, sleigh and choir variants required by the join spec. Preserve the approved rotation across rounds; count actual selected files and master duration instead of assuming three full rounds fit.
- Validate variant stats before rendering; after assembly verify duration, integrated loudness and true peak. Preserve the master metadata and order in the album folder. Match picture duration to the final approved master and remux the retained silent montage when only audio changes.
