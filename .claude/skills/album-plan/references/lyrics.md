# Writing lyrics for a slot

Lyrics go in the slot's track md, in the first ``` block under `## Lyrics (bản đã nhập vào Suno)`. That block is
exactly what suno-generate types into Suno and what verification-audio compares the sung words against. Write
**slot 1 first** and with the most care, then the rest in album order. Re-run `validate` after each slot.

How Suno reads the Style, tags and lines for this genre (tag reliability, line shape, pronunciation, words and real
song titles to avoid, max words per song for the slot's tempo and length) is in the channel's `channel/<ch>/rules.md`.
Read it before writing the Style or the first slot; validate prints each slot's word cap.

## Division of labour (CLAUDE.md)

- **Style** (shared, in `plan.yaml`) = who is playing: genre, voice, band, production, room, what to avoid.
- **Tags in the lyrics** = how *this* song is arranged: how the intro starts and how long it is, which instrument
  enters first, when drums come in, where a solo or break sits, how the outro ends.
- Keep the artist the same and vary the arrangement. Each slot's `intro_type`, `intro_length` and `arrangement` in the
  plan say how this song should differ from its neighbours, so turn them into the tags.

## Shape

- Structure: `lyrics_rules.structure_default` unless the slot says otherwise. Line counts: `lyrics_rules.lines_per_section`.
- Length: aim for `target.words_per_min` over the sung time. validate estimates it as
  `words ÷ (target_duration − intro estimate − ~25 s outro)`: cold_open ≈ 2 s, short ≈ 8 s, medium ≈ 20 s, long ≈ 35 s.
  Too few words for a 5-minute song invites long instrumental stretches. Too many invites rushing or dropped lines.
- Stay under `lyrics_rules.max_chars` (hard limit 5000 including tags).
- Tag syntax: one tag per line in square brackets, e.g. `[Verse 1]`, `[Chorus]`, `[Intro: 4 seconds, organ swell, soft male humming]`.
  Describe arrangement in plain words inside the tag. Every line outside brackets is sung, so directions never go
  on their own line.

## Opening (slot 1 above all; CLAUDE.md)

- Translate `opening_spec` into the intro tag: a short tag that asks for it, then `[Verse 1]` right after. Don't
  write an `[Instrumental Intro]` block. What intro tags really did for this channel (how early the voice came) is in
  its `rules.md` §7; when no tag brings the voice in early enough, the 0–15 s target is reached at assembly, which trims the intro. Earlier-voice
  ideas are tried as slot-1 `variants`.
- Other slots: follow `intro_type` / `intro_length` (an instrument intro type + `short` opens on that instrument for a few seconds; a
  `vocal` + `cold_open` slot starts on a sung line).
- These tags are our request. What Suno actually did is measured afterwards by verification-audio (vocal start, intro
  length). If a request is ignored repeatedly, the REGENERATE hints say so and the tags get adjusted then, with data.

## Hook, echoes, ending

- `hook_phrase` must appear word for word in the chorus (validate checks it). Repeat it; it is what listeners remember.
  Only slot 1's hook may equal its title.
- Quoting another slot's title or hook (3+ words) makes it an echo: list that slot in `echo_tracks`, and the two slots
  must not be adjacent (validate checks both).
- Ending: follow `lyrics_rules.outro`, written inside the tag and phrased positively, then `[End]`:
  `[Instrumental Outro: <the channel's lead instruments>, instrumental only, long sustained final chord]` + `[End]`.
  verification-audio flags vocals in the tail.

## Originality (hard rule)

- Our own words. Never transcribe or imitate the reference's lyrics or captions (the analyzer stores none on purpose).
  No lines from existing songs. Nothing from `copy_guard` (titles, hooks, branding).
- Lyric sources (`rules.md` → `sources`): paraphrase the slot's `source_ref`. Short public-domain phrases are fine
  (the channel's rules.md says which texts); refs in `copy_guard.source_avoid` are not.
- Avoid repeating the main image (`imagery[0]`) of the neighbouring slots.
- English only.

## Variants for slot 1

To try two different openings or lyric versions, add `variants` to slot 1, e.g.
`{name: hum-intro, rounds: 3}` and `{name: cold-line, rounds: 3, lyrics_file: tracks/01-<slug>.cold.md}`. A variant
lyrics file uses the same `## Lyrics` block format. suno-generate rotates through them. verification-audio compares
against the main track md lyrics, so once a variant wins, copy its lyrics into the main track md before accepting.
