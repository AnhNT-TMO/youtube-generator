---
name: album-plan
description: Turn a researched idea (youtube-music-analyzer's idea.yaml / reference.yaml / analysis.md) into a complete, approved album plan before anything is generated on Suno - how many songs (e.g. 10, 12 or 14), each song's title, role in the arc, mood, energy, tempo, intro type, length, hook, imagery, arrangement and lyrics - checked against the channel rules (title track first and new, energy steps ≤ 2, tempo steps ≤ 8 %, varied intros, unique hooks, copy guard, library reuse), then build the exact inputs of the production skills - generation.yaml for suno-generate, selection.yaml for verification-audio, tracks/NN-*.md (metadata + lyrics) and album.md. It is the bridge between the analyzer and suno-generate. Use when the user wants an album planned or a tracklist made ("lên plan album", "lên kế hoạch", "tracklist", "làm album từ idea này", "promote idea", "viết lời", "bài nào mood gì tempo gì"), wants to change the plan before generating, or when suno-generate finds no approved plan. Does NOT touch Suno.
---

# Album plan

BLUEPRINT step of CLAUDE.md (step 3). Input: an idea from the analyzer (preferred) or research only. Output: an
approved `<album>/plan.yaml` plus the files the next skills read. No credits are spent here, so this is the place to
think, check and ask. After approval, suno-generate only types what this plan says.

```
analyzer: reference.yaml + analysis.md + idea.yaml
   │ init (mechanical mapping, lists what needs deciding)
   ▼
plan.yaml ── Claude decides / fills ── validate ── build ──▶ tracks/NN-*.md ── Claude writes lyrics ── validate
   │                                                                                                   │
   └──────────── summary → user approves → approve (validate --final + build + status approved) ◀─────┘
                                   ▼
          generation.yaml (suno-generate) · selection.yaml (verification-audio) · tracks/*.md · album.md
```

**Channel rules first:** `channel/<ch>/rules.md` is the one source of truth for this channel's music (house Style +
Exclude, lyric density, how Suno reads the Style / tags / lines for this genre, words and real song titles to avoid,
how albums may differ). There is no shared Suno rules file: each channel (genre) has its own. validate reads its YAML block. When something new is learned
(owner listened, verify measured, retention came in, a real-song collision was found), add one line there.

The field-by-field contract (what comes from where, who owns which file, units) is in `references/bridge.md`.
Read it before changing any mapping. How to write lyrics and tags: `references/lyrics.md`.

**Order-free.** Every skill works from files, so steps run whenever the user wants: analyze 20 videos today, plan
some of them next week, make thumbnails/loops for all ideas in between, generate music months later. Rules that make
this safe:
- `P board --channel <ch>` shows every idea / album / single, what exists (plan, tracks n/N, drafts, thumbnail,
  loop, master, video, uploaded) and the remaining jobs per item — music lane and picture lane listed separately
  because they don't wait for each other. Start any session with it when the user asks "làm tiếp gì".
- Images may be made in the idea folder after the plan exists: `build` (and `P sync <album>`) copies the idea's
  thumbnail / `video.json` / `thumbnail-prompt.md` / `video/loop*.mp4` into the album when the idea's copy is newer.
  Nothing is deleted; an album copy that is newer wins.
- Planning many albums ahead: album numbers are given in the order plans are made (not release order). `validate`
  checks new titles/hooks against the other albums that have a `plan.yaml` (`cross_plan`), not only the catalog.
- `P catalog --channel <ch>` rebuilds `library/catalog.md` (+ `use_count`/`used_in_albums`) from the tracks'
  front matter. Run it after accepting tracks or finishing an album; library reuse (step 2.7) reads it.

```bash
SK=.claude/skills/album-plan; P() { $SK/.venv/bin/python $SK/scripts/album_plan.py "$@"; }
# first run: python3 -m venv $SK/.venv && $SK/.venv/bin/pip install -r $SK/requirements.txt
```

## Principles

- **Our job, not Suno's.** Plan what the album should be, in measurable targets. Never bake in guesses about how
  Suno will behave (e.g. "it renders slower, so write a higher BPM"). The prompt tempo is the planned tempo. What Suno
  actually delivers is measured by verification-audio during generation and corrected there, with data.
- **Album-first** (CLAUDE.md §4): one continuous performance (50–90 min, Suno's real lengths vary) by one artist. Lock the artist (persona, Voice, band,
  Style), vary the arrangement, and make every transition deliberate.
- **Track 01 decides most of it** (CLAUDE.md §3): new song, strongest concept, voice/hook in the first seconds,
  most rounds.
- **Inspired, not copied:** keep the reference's spirit (genre, tempo family, opening strategy, lyric source). Change
  the identity (titles, hooks, imagery, arc, look). Everything of theirs goes into `copy_guard`.
- **Numbers over taste** (the user doesn't judge music by ear): every target is something validate or
  verification-audio can check. Ask the user decisions (persona, tempo, count, budget), never "which sounds better".

## 1. Start

**From an idea** (normal path): the analyzer's `idea.yaml` must be finished (its `validate_idea.py` passes, no `TODO(claude)`).
```bash
P init --channel <channel> --from-idea channel/<channel>/ideas/NNN-<slug>
```
This creates `channel/<channel>/albums/NNN-<slug>/` with `plan.yaml` (mapped from the idea), `notes/plan-reference.md`
(the reference's per-song numbers), and a snapshot of `idea.yaml`/`idea.md`/`thumbnail.png`/`video.json`. It also marks
the source idea `promoted`. It prints every non-trivial mapping decision: fields ignored (e.g. a `prompt_bpm`), hard-coded
BPMs turned into `{bpm}`, ranges resolved to one number, fields left empty. Tell the user about those.

**From research only:** `P init --channel <ch> --from-research <slug> [<slug2>] --slug <album-slug> --title "<working title>"`.
You get a skeleton plus the reference table and copy guard; do the idea work yourself in step 2 (concept, differentiation).

Use `--out <dir> --no-promote` to try the mapping somewhere without touching the channel.

## 2. Decide and fill `plan.yaml`

Sources: `notes/plan-reference.md`, the research `analysis.md` (§4–§9), `channel/<ch>/channel.md`, `library/catalog.md`,
the previous album's `album.md`/`selection.yaml`, and `.claude/skills/suno-generate/references/suno-research.md` for what
the Suno UI accepts. Field meanings are in `templates/plan.yaml`. Work in this order:

0. **Read the channel:** `channel/<ch>/rules.md` and `P themes --channel <ch>` (concept, tempo, title track, closer,
   scripture, imagery, opening, thumbnail of every album). Pick a concept, tempo and opening the channel doesn't have yet.
1. **Open questions first.** Blocking ones (persona, tempo, count, budget…) go to the user with AskUserQuestion, with
   your recommendation first and the measured reason. Record each answer in `open_questions[].answer` and apply it.
2. **Tempo and voice follow the reference (~50 % of the album is the reference, rules.md §1b).** Tempo (`sound.tempo`):
   the reference's felt tempo itself (`research/<slug>/reference.yaml criteria.tempo.felt_bpm_median`, ≤ 5 % off) +
   meter + `why`. Voice (`identity.voice`): the channel Voice (rules.md `voices`) whose measured f0 is closest to the
   reference's `criteria.voice.f0_median_hz` (≤ 15 % off); the Style's vocal sentence comes with it. Lyric density ≈ the
   reference's words per sung minute. validate checks all three (`reference_follow`, `voice`). **One album =
   one tempo band:** a slot may differ (`slot.bpm`, e.g. slightly faster peaks) within `bpm_adjacent_max_pct` of its
   neighbours, and the fastest / slowest slot of the album (library songs by their measured BPM) stay within 20 %
   (validate `tempo_band`). **Across albums the band is free and should vary** — the channel wants albums at different
   tempos, not one channel tempo: don't pull an album toward Album 001 or the other albums' tempo. Library reuse
   follows from this: only songs whose tempo fits this album's band can be reused.
3. **Style** (`sound.style.text`, ≤ 1000 chars, same text for every song): init builds it from the channel's
   `house_style` (rules.md): `<genre_lead>, <album mood phrase>. <artist_block> Slow <meter> groove, {bpm} BPM.` +
   the house Exclude. Only the mood phrase, meter and tempo are the album's. **Variety is wanted:** an album may differ
   from the house sound on purpose (higher voice, unusual tempo, energy spikes, another band colour…) to test what
   listeners like — declare it in `experiment` (`axes`, `what`, `why`, `measure`), usually because the reference has
   that trait; ask the owner (open question with a recommendation). Undeclared differences are a `house_style` error.
   Inside one album: still one artist, one Style, one tempo band.
3b. **Highlight** (`highlight`, required): one new song at slot 4 or 7 that is unusual on ONE axis (higher register /
   key lift in the last chorus, energy spike, a cappella opening, clearly faster tempo, choir-led…) with the same artist
   and Voice. It is exempt from the energy/tempo/intro step rules with its neighbours and from the album tempo band, and
   is released as a single after the album (singles/NNN-slug) to read listener response on its own.
4. **Track count and lengths:** `track_count × target_duration` inside `target.duration_min` (assembly trims a few
   percent). Around 5–5½ min songs → ~10 for 50–56 min; shorter songs (as the reference) → 12–15. Anything from 50 to 90 min after assembly is fine; the count follows the reference's song length.
5. **Arc:** energy 1–10 per slot, rising to `peak_slots`, landing low; steps ≤ 2. `arc_role`: anchor, build, peak, release, closer…
6. **Per slot:** our own English `title`, `hook_phrase` (real chorus line, unique), `emotion`, `theme`, `source_ref`,
   `imagery` (vary the main image), `intro_type` + `intro_length` (never the same type back to back; mix the lengths),
   `target_duration`, and `arrangement` (what makes this song's arrangement different). **Web-check every new
   title and hook** (WebSearch `"<phrase>" song`) and write the result in `title_check`; a hit → change it and add
   the song to `known_titles` in rules.md. Slot 1 also gets `opening_spec`
   (0–15 s of the video), more `rounds`, and optionally `variants`.
7. **Library** (CLAUDE.md §7.2): look at `library/catalog.md`. A slot can be `source: library` + `library_id` when an
   existing song fits: same persona/band, fits the energy/tempo curve, freshness OK, never slot 1, at most
   `target.reuse_total_max` (4) library songs in the whole album (every other slot is new), and at most
   `target.reuse_per_album_max` (2) songs from any one earlier album — counted over every album the song appeared in
   (catalog `Albums`), so mix reused songs from several albums or write new ones. Record what you
   checked in `library_check.result` and set `done`.
8. **Generation settings** (`generation`): exact numbers only. Credits (CLAUDE.md §4): `max_mode: false`, slot 1
   `generation_overrides: {max_mode: true}`, `rounds: {track01: 2, others: 1}` (Max = 20 credits, normal = 10 per round
   of 2 clips) → planned ≈ 40 + 10 × (new songs − 1). `budget_max_credits` ≤ 250 (a 14–15-song album still fits).
   init sets all of this; anything more needs the owner's OK (validate warns `credits_policy`).
9. **QC** (`qc`): `rules.duration_range` is the only part verification-audio reads (plus each slot's `target_bpm`). CLAP descriptions (`qc.style`),
   `references` and `thresholds` are no longer used by anything; leave them empty in new plans.
10. **Opening numbers** (`target.vocal`, `target.loudness`): `first_voice/lyric/hook_max_s`, optional `vocal_at_s`,
   `first15s_max_below_body_db`, `master_lufs`. album-assembly places the first voice with them (verification-audio
   no longer reads them: it only picks the clip that is not broken, sings the lyrics and starts them earlier).

Then `P validate <album>` and fix every ✖. A rule broken on purpose goes into `waivers: [{rule, slots, why}]`, never
silently. Then `P build <album>` → track md skeletons with a Brief, `generation.yaml`, `selection.yaml`, `album.md`.

## 3. Write the lyrics

Follow the channel's `rules.md` (§5–§9: Style, tags, opening, line shape, fixes), then `references/lyrics.md`. Length is capped by
rules.md §2 (words per beat measured on Album 001: max words ≈ words_per_beat_max × bpm/60 × (duration − 55 s));
validate prints the cap per slot — write to it instead of trimming afterwards. Each new slot's lyrics go into `tracks/NN-*.md` → `## Lyrics` ``` block. Start with slot 1.
Re-run `P validate <album>` after each slot (hook present, echo declared and not adjacent, words/min, length,
English, copy guard). Build never overwrites lyrics.

## 4. Approval

1. `P summary <album>` → show the user the tracklist (title, role, mood, energy, tempo, intro, length, hook, source,
   rounds), totals (duration, credits), and remaining open questions. Mention any waivers and what init ignored or changed.
2. Only after an explicit yes: `P approve <album> --by user` (`validate --final`: lyrics for every new slot, blocking
   questions answered, library checked → build → `plan.yaml` + `generation.yaml` `status: approved`, with a fingerprint).
3. Hand off: the **suno-generate** skill starts from `generation.yaml` (slot 1 first).

Edits after approval: change `plan.yaml`/lyrics → `P build` notices the fingerprint changed, puts both files back to
`draft`, and the user approves again. Once suno-generate has submitted a generation, the plan is frozen (build
refuses). Generation-time changes (REGENERATE hints) then go in `generation.yaml` and the track md, owned by
suno-generate and verification-audio (see bridge.md §1).

## Checks `validate` runs

Channel: a new title equal to a new slot of another planned album (error), same hook (warning), hook of a library
song (warning). Album: identity locked, Voice set (or a warning to create one before slot 2), felt tempo + meter, no hard-coded BPM in
the Style, Style ≤ 1000 chars after `{bpm}`, English, QC style descriptions present, total duration vs target, credits
vs budget. Per slot: title/hook present, English, not in the copy guard or the library, `source_ref` not avoided,
duration within 0:10–6:00 (Suno custom) and the target range, rounds (slot 1 ≥ 4 clips), lyrics present (final),
≤ 5000 chars, hook in the lyrics, words/min estimate. Channel rules (rules.md): Style = genre_lead + the chosen Voice's vocal_line + band_block and Exclude = house list unless an
`experiment` declares otherwise (`house_style`); Voice is a channel Voice close to the reference's f0 (`voice`,
`reference_follow`); tempo ≤ 5 % from the reference, lyric density ±20 % (warning); a `highlight` at slot 4/7 (final); experiment
complete, title/hook near a real song title or any reference's title in the channel (`known_title`, line = warning),
avoid words / heteronyms (warning), words per beat over the cap (`density`), `title_check` present (final), scripture
chapter or title-track/closer image used by another album (`cross_plan` warning).
Credits: `budget_max_credits` ≤ 250 (error), lean rounds / Max only on slot 1 (warning). Between slots: energy step,
tempo step, one tempo band for the whole album (fastest/slowest ≤ 1.20), same intro type, 3 equal
intro lengths in a row, repeated main image, repeated hook / hook = another title, undeclared or adjacent echoes,
peak position, quiet ending. Final: library checked, blocking questions answered.

## Files

| Path | What |
|---|---|
| `scripts/album_plan.py` | init / validate / build / summary / approve / board / themes / sync / catalog |
| `channel/<ch>/rules.md` | the channel's music rules = source of truth (house style, density, avoid lists, experiments) |
| `scripts/channel_tools.py` | board (channel status), sync (idea → album images), catalog (library index) |
| `references/bridge.md` | contract with the analyzer, suno-generate, verification-audio, album-assembly |
| `references/lyrics.md` | how to write lyrics + arrangement tags |
| `templates/plan.yaml` | plan schema with explanations |
| `<album>/plan.yaml` | the plan (source of truth before generation) |
| `<album>/notes/plan-reference.md` | reference numbers from research (context, not decisions) |
