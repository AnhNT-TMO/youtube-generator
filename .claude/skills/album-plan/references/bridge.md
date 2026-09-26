# Bridge contract: analyzer → album-plan → production skills

This file is the contract. When a field is added, renamed or dropped in any of these files, update this table,
`templates/plan.yaml`, and the matching code in `scripts/album_plan.py` in the same change.

```
youtube-music-analyzer                 album-plan (this skill)                      production skills
───────────────────────                ───────────────────────                      ─────────────────
research/<slug>/reference.yaml ─┐
research/<slug>/analysis.md     ├─init─▶ <album>/plan.yaml ──build──▶ generation.yaml ──▶ suno-generate
channel/<ch>/ideas/NNN/idea.yaml┘        (+ notes/plan-reference.md)  selection.yaml  ──▶ verification-audio
                                         tracks/NN-*.md  ◀── Claude writes lyrics      tracks/NN-*.md ──▶ all three
                                         album.md (auto block)                          (album-assembly: track_no, energy, arc_role, audio)
```

## 1. Who owns which file, and when

| File | Written by | Read by | Notes |
|---|---|---|---|
| `research/<slug>/reference.yaml`, `analysis.md` | analyzer | album-plan (init, reference table) | facts; never edited here |
| `ideas/NNN/idea.yaml` | analyzer | album-plan init | init sets `status: promoted`, `album:` and a status_log line; a snapshot is copied to `<album>/idea.yaml` |
| `<album>/plan.yaml` | **album-plan** (Claude edits it) | album-plan | source of truth until generation starts |
| `<album>/generation.yaml` | album-plan build | suno-generate | after generation starts: suno-generate edits `overrides` / `changes` directly; build refuses to overwrite |
| `<album>/selection.yaml` | album-plan build | verification-audio | build keeps `anchor` (filled by `verify.py accept --slot 1`) |
| `<album>/tracks/NN-*.md` front matter | build (plan keys), then verify.py accept (measured keys) | all | build never touches a track md whose `audio` is set |
| `<album>/tracks/NN-*.md` `## Lyrics` block | Claude (album-plan); later suno-generate on REGENERATE with user OK | suno-generate, verification-audio | build never overwrites lyrics |
| `<album>/album.md` | build (between `album-plan:begin/end` markers) | people | text outside the markers is kept |
| `audio/raw_tracks/manifest.json` | suno-generate, verification-audio | album-plan build (freeze check), `catalog` (override flag) | |
| `<album>/thumbnail.png`, `video.json`, `video/loop*.mp4`, `thumbnail-prompt.md` | thumbnail-prompt / video-generator, in the album **or** in the source idea | video-generator, youtube-publish | made in any order: `build` and `sync` copy the idea's copy when it is newer (never delete, album's newer copy wins) |
| `library/catalog.md` | `album_plan.py catalog` (generated) | album-plan validate/build (library slots, freshness) | rebuilt from every selected track's front matter; also sets `use_count` / `used_in_albums` |

**Approval chain.** `approve` runs `validate --final` and stores a fingerprint of the plan + all lyrics in `status_log`.
If `build` later finds a different fingerprint, it sets both `plan.yaml` and `generation.yaml` back to `draft`,
and the user has to approve again. Build also writes `lyrics_sha8` per slot into `generation.yaml`. suno-generate refuses
to generate a slot whose lyrics no longer match, unless `--accept-lyrics-change` is given (a REGENERATE with edited
lyrics that the user OKed). That run is then recorded as `lyrics_changed_after_approval: true` in the manifest.

**Freeze.** Once the manifest has any generation past `prepared`, build refuses (unless `--force` on the user's
word). From then on, generation-time changes live in `generation.yaml` (`slots[].overrides`, `changes: []`) and in
the track md lyrics.

## 2. Units (the most common bridge bug)

| Quantity | Unit everywhere | Notes |
|---|---|---|
| tempo | **felt BPM** (`unit: felt`): dotted quarter in 6/8 and 12/8, quarter in 4/4 | analyzer `reference.yaml tracks[].bpm` / `album.tempo.felt_bpm_median` (older research: `felt_bpm_qc_median`), `plan.sound.tempo.bpm`, `slot.bpm`, `{bpm}` in the Style, `selection.yaml tempo.target_bpm`, verification's measured tempo. The analyzer's `pulse_bpm` / librosa BPM can sit on another metrical level; don't use it as the album tempo |
| prompt tempo | **= planned tempo** | No correction for how Suno might render. A measured offset is verification-audio's finding during generation (REGENERATE hints) and gets fixed then, in `generation.yaml` with a `changes` entry |
| duration | `m:ss` in plan/track md; seconds in `generation.yaml` (`overrides.duration`) | Suno custom duration 10–360 s |
| energy, valence | 1–10, relative within our album | reference energy is relative within *their* video, a shape to learn from, not a number to copy |
| intro_type | the channel's `rules.md` → `research.intro_vocab` | `intro_length`: cold_open (<3 s) · short (<10 s) · medium (<25 s) · long |

## 3. idea.yaml → plan.yaml (`init`, mechanical)

| plan.yaml | from idea.yaml | rule |
|---|---|---|
| `sources.idea`, `sources.research` | path of the idea, `provenance.research[].path` | research slug for the reference table from `provenance.research[].reference` (reference.yaml) when present |
| — (guard) | `todo:` list, `TODO(claude)` markers | init refuses an unfinished idea |
| `concept` | `hypothesis.statement` | usually rewrite into an album journey |
| `differentiation.keep/change` | same | |
| `copy_guard.titles/branding/hooks/lyric_rule` | `differentiation.copy_guard.*` | |
| `copy_guard.source_avoid` | `copy_guard.source_avoid` (older ideas: `scripture_avoid`) | ints become strings with rules.md `sources.numbered.format` (e.g. `"<Book> {n}"`); matched against `slot.source_ref` (`Psalm 3` ≠ `Psalm 34`; `Psalm 23:4` hits `Psalm 23`). `--from-research`: `copy_guard_seed.sources_used` (older: `psalms_used`), same format |
| `identity.vocal_persona/band_profile` | `identity.*` | an unanswered `persona_decision` stays an open question |
| `identity.voice` | `identity.suno_voice {name, id}` | |
| `identity.vocal_gender` | `generation.settings.vocal_gender` | `null`/missing → template default, and init says so |
| `sound.tempo.bpm` | `target.tempo.felt_bpm_qc` | **`prompt_bpm` is ignored** (init says so) |
| `sound.tempo.meter` | `target.tempo.meter` | |
| `sound.style.text` | `style_prompt.text` | every hard-coded `NN BPM` becomes `{bpm} BPM` (init lists them) |
| `sound.style.version/exclude` | `style_prompt.version/exclude_styles` | |
| `target.*` | `target.duration_min/track_count/track_duration.range/adjacent_bpm_delta_max_pct` | `peak_slots` from slots with `arc_role: peak` |
| `target.tempo_range` | `target.tempo.felt_bpm_qc_range` | validate: album and slot bpm must sit inside |
| `target.vocal.first_voice_max_s / first_lyric_max_s / first_hook_max_s / words_per_min` | `target.vocal.presence_max_s / first_lyric_max_s / first_hook_max_s / words_per_min` | `vocal_at_s` has no idea source: set it in the plan when the opening needs the voice earlier/later than min(8, first_voice_max_s) |
| `target.vocal.f0_median_hz`, `singer_similarity_min` (+ `_ref`) | `target.vocal.f0_median_hz`, `target.vocal.ecapa_vs_<ref>_min` | `<ref>` kept as `singer_similarity_ref` |
| `target.drums_in_s_max / loudness / transition / key_policy` | same keys | carried verbatim (loudness/transition are for album-assembly) |
| `lyrics_rules` | `lyrics_rules` (minus `file_format` and `null` values) | |
| `generation.*` | `generation.model/max_mode/settings.*`, `budget` | ranges become the middle value rounded to 5 (init lists them); `rounds.track01` = max(`budget.gens.track01`, ceil(`track01.candidates_min`/2)) |
| `qc.references/style/rules/thresholds/intro_types/extra_checks` | `qc.*` | repo paths become album-relative; `null` rule values dropped; `qc.anchor` is NOT copied (verification fills it on slot-1 accept); `qc.tempo` is not copied (tempo comes from `sound.tempo`, init warns if they differ) |
| `library_check` | `library_check` | |
| `slots[]` | `slots[]` (slots[0] is authoritative for the title track) | `source_ref` as is (older ideas: `scripture`→`source_ref`), `arrangement_note`→`arrangement`, `note`→`notes`, `bpm`/`valence` as is; missing `target_duration` ← `generation.settings.duration.seconds`. Slot 1 also gets `track01.opening_spec`, `gate`, `reference_recipe`, `variants` (list only), `lyric_tags_hint` (→`arrangement`), `concept` + `listener` (→`notes`) |
| `open_questions` | `open_questions` | `answer: null` until the user answers; blocking ones stop `approve` |
| — | `packaging`, `metrics`, `hypothesis.evidence/risks` | stay in `<album>/idea.yaml` (the snapshot) for the publish step |

Only research, no idea → init writes a skeleton, `notes/plan-reference.md` (per-song numbers, preferring
`reference.yaml`), and the copy guard from `reference.yaml copy_guard_seed`. Claude fills in the rest (SKILL.md §2).

## 4. plan.yaml → production files (`build`, deterministic)

### generation.yaml (suno-generate)

| generation.yaml | from plan.yaml |
|---|---|
| `status` | `draft`; `approved` only when the plan is approved and its fingerprint matches |
| `source` | `plan.yaml`, `sources.*` |
| `budget.max_credits`, `budget.credits_per_generation` | `generation.budget_max_credits`, `generation.credits_per_generation` |
| `gates.anchor_first` | `generation.anchor_first` |
| `style.version/text/exclude` | `sound.style.*` (`text` keeps `{bpm}`) |
| `defaults.model/max_mode/variety/weirdness/audio_influence` | `generation.*` |
| `defaults.style_influence` | `generation.style_influence.others` |
| `defaults.voice/vocal_gender` | `identity.voice/vocal_gender` |
| `defaults.bpm` | `sound.tempo.bpm` |
| `order` | new slots in album order (slot 1 first) |
| `slots[].n/title/track` | slot n, title, `tracks/NN-<slug(title)>.md` |
| `slots[].rounds` | `slot.rounds` or `generation.rounds.track01/others` |
| `slots[].overrides` | `duration` (s, when `generation.duration: custom`), `bpm` (when ≠ album bpm), slot-1 `style_influence` (when ≠ others), then `slot.generation_overrides` |
| `slots[].variants` | `slot.variants` |
| `slots[].lyrics_sha8` | hash of the track md lyrics at build time |
| library slots | not listed (nothing to generate) |

- `slots[].cover` = the plan slot's `public_domain.cover_source` when `public_domain.mode: cover` (else null); suno-generate's
  Cover branch (its SKILL.md §3b) reads it. `cover.file` is relative to the album dir. The plan slot's `public_domain`
  itself is copied from the idea slot by `init`.

### selection.yaml (verification-audio)

| selection.yaml | from plan.yaml |
|---|---|
| `anchor` | kept from the existing file |
| `references` | `qc.references` |
| `tempo.target_bpm`, `tempo.meter` | `sound.tempo.bpm`, `sound.tempo.meter` |
| `style.positive/negative` | `qc.style.*` |
| `rules` | `qc.rules`; `duration_range` defaults to `track_duration` −60 s / +90 s |
| `slots.N.track/energy` | every slot (new and library) |
| `thresholds` | `qc.thresholds` |
| `plan_targets` | `target.tempo_range`, `target.vocal.*` (voice/lyric/hook seconds, f0, singer similarity), `drums_in_s_max`, `loudness`, slot-1 `gate` (`slot_checks`), `qc.intro_types`, `intro_type_by_slot`, `qc.extra_checks` |

**What verification-audio reads (v2, 4 criteria):** only `rules.duration_range`, `tempo.target_bpm`, `slots.N.track`
(title, lyrics, `target_bpm`) and `anchor` (written on slot-1 accept). `plan_targets`, `style`, `tempo`, `references`, `thresholds` are no longer
read by verify; build still writes them (album-assembly and later analysis may use them).

### album-assembly

`assemble.py plan <album>` reads `plan.yaml` when it exists: `target.vocal.vocal_at_s` (else min(8,
`first_voice_max_s.track01`)) → the opening, `target.loudness.master_lufs` → `--target-lufs`. Command-line
`--vocal-at` / `--target-lufs` still win. Order and energy/arc_role come from `tracks/*.md` as before.

### tracks/NN-slug.md

Front matter keys written by build (CLAUDE.md + plan keys): `id` (`<id_prefix>-NN`), `title`, `origin_album`,
`track_no`, `genre_family`, `subgenre`, `time_signature`, `vocal_persona`, `band_profile`, `style_prompt_version`,
`energy`, `valence`, `emotion`, `theme`, `arc_role`, `intro_type`, `hook_phrase`, `lyric_keywords`, `imagery`,
`echo_tracks`, `target_bpm`, `target_duration`, `source_ref`. The measured keys (`audio`, `suno_url`, `duration`,
`lufs_integrated`, `true_peak`, `outro_type`, `vocal_entry_seconds`, `bpm`) belong to verify.py accept. The body gets a regenerated
`## Brief` block (between `album-plan:brief` markers), `## Arrangement tags / ghi chú generate`, and an empty
`## Lyrics` ``` block for Claude. A library slot gets a copy of the source track md, with `track_no` changed and
`audio` pointing (relative path) at the original album's WAV.

## 5. What each consumer needs, checked by `validate`

| Consumer | Needs | Checked |
|---|---|---|
| suno-generate | exact numbers, ≤ 1000-char Style after `{bpm}`, English text, lyrics ≤ 5000 chars in the track md, duration 10–360 s | yes |
| verification-audio | `rules.duration_range`, slot → track path, lyrics present (lyrics check), ≥ 4 slot-1 clips | yes |
| album-assembly | `track_no` 1..N in final order, `energy`, `arc_role` | yes (order is fixed at plan time; assembly never reorders) |
| CLAUDE.md | energy step ≤ 2, tempo step ≤ 8 %, no back-to-back `intro_type`, unique hooks (vs titles, other hooks and library titles/hooks), echo tracks not adjacent, title track new, library checked, ≤ 4 library songs in the album (`reuse_total`), ≤ 2 library songs from any one earlier album (`album_overlap`) | yes; conscious exceptions go in `waivers` with a reason |
| other plans of the channel | a new slot's title must not repeat a new slot of another album that has a `plan.yaml` (plans made ahead, not yet in the catalog); same hook → warning | yes (`cross_plan`) |
