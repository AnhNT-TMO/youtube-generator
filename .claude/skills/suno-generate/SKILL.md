---
name: suno-generate
description: Generate an album's songs on suno.com by driving the user's logged-in Suno in the dedicated Chrome (Chrome DevTools MCP `suno-chrome`), exactly as the album's generation plan (`<album>/generation.yaml` - Style prompt, Voice, model, Max Mode, sliders, duration, per-slot title + lyrics, order, rounds, budget) says - verify every option on the form BEFORE pressing Create and again against what Suno received, then download every clip through usesuno.com into `audio/raw_tracks/` and index it in `raw_tracks/manifest.json` (clip id ↔ slot ↔ round ↔ settings ↔ why it was generated). Has a Cover branch for public-domain songs (a slot with `cover` in generation.yaml: render our own organ source from a PD score with pd_source.py, or use a PD recording / our own clip, upload it, Remix ▸ Cover, check the request carries the source). Also makes the extra rounds that verification-audio asks for (REGENERATE) or the user wants (more) and records them as such so they are never confused with planned ones. Use when the user says "tạo nhạc", "generate", "cover bài public domain", "cover hymn", "chạy Suno", "tạo bài 1", "tạo thêm bản", "tạo lại slot N", "tải bản nháp về", or wants the album plan turned into Suno drafts. Does NOT judge or pick clips (that is verification-audio).
---

# Suno generate

Step 3 *Tạo nhạc* of CLAUDE.md §3. Only three jobs: **type the plan into Suno exactly**, **download the drafts via
usesuno**, **keep the index**. Choosing clips belongs to `verification-audio`, mixing to `album-assembly`.

```
generation.yaml ──▶ suno_gen.py next ──spec──▶ fill form ─▶ read_form ─▶ check-form ✔ ─▶ Create
                                                                                     │
raw_tracks/*.wav + manifest.json ◀── ingest ◀── usesuno ◀── complete ◀── poll_feed ◀── submitted (request check)
        │
        ▼
verification-audio (verify.py check) ── SELECT → auto-accept (CLAUDE.md §5) → audio/tracks/
        └── REGENERATE (+hints) → PM OKs credits → next --purpose regenerate --reason "..."
```

Background facts (Suno v6, Sept 2026) are in `references/suno-research.md` §4 and §7. Read §7.2–7.3 (the page map) when a
selector breaks.

## Hard rules

1. **Never** click Suno's Download / "Unlock & Download" and never call `/api/download/*`. Each one uses up a monthly
   download (Pro: 20). Every download goes through usesuno.com. `suno_gen.py quota` stops the run if the official count rises.
2. **Never press Create unless `check-form` printed `FORM KHỚP SPEC`** for this exact gen id, read after your last edit.
   A wrong option costs credits and produces clips that look valid in the index.
3. Spend credits only when `generation.yaml` has `status: approved` (the plan approval is the OK for every planned round,
   CLAUDE.md §5). Every extra round (REGENERATE, or more at the PM's request) needs the PM's OK (§5 Cổng duyệt); don't ask
   the same thing twice.
4. One generation at a time **up to `complete`**: poll + `complete` (it checks what Suno stored) before the next `next`
   (the script enforces this). Downloads are batched: generate every planned round of the batch first, then download +
   ingest all clips at the end (`P status` lists the clips still waiting), then run verification-audio slot by slot.
   (Owner 2026-09-23: downloading after every round was too slow.)
5. If a Create click's result is unclear, **don't click again**. First check with `find_recent` whether clips were
   made; a double click is a double charge.
6. Keep the Suno tab in the foreground while working (background tabs ignore clicks).
7. Never edit `manifest.json` by hand and never delete drafts. Rejected clips are data for tuning verify thresholds.
8. Text going into Suno is English (CLAUDE.md). The plan is the only source: don't "improve" the Style or lyrics
   while typing. If the plan looks wrong, stop and say so.

## 0. Input: `<album>/generation.yaml` (built by album-plan)

`generation.yaml` is produced by the **album-plan** skill (`album_plan.py build`) from the approved `<album>/plan.yaml`.
Don't write it by hand. Contract: `.claude/skills/album-plan/references/bridge.md` §4.
- `status: approved` means the user approved the plan and its lyrics. If it says `draft`, or the file doesn't exist, run
  album-plan first. Never flip the status yourself.
- Values are exact numbers. `style.text` contains `{bpm}`, which is filled with the slot's tempo (`defaults.bpm` or
  `overrides.bpm`); that number is the planned tempo, typed as is. Custom duration per slot is in `overrides.duration`.
- Lyrics come from the slot's track md (`## Lyrics` → first ``` block, the same place `verify.py` reads them).
  `slots[].lyrics_sha8` is the approved version. `next` refuses if the lyrics changed since approval (see §3).
- Title track = slot 1, always generated first, with the most rounds (4 clips to pick from).
- `templates/generation.yaml` documents every field.

## 1. Preflight (once per session)

```bash
SK=.claude/skills/suno-generate
$SK/scripts/suno-chrome.sh    # dedicated Chrome, profile ~/.suno-chrome/profile, port 9222 (already running = fine)
P() { $SK/.venv/bin/python $SK/scripts/suno_gen.py "$@"; }; A=channel/<channel>/albums/<NNN-slug>
P validate $A && P status $A
```

- The MCP tools are `mcp__suno-chrome__*`: a **local-scope** server (`claude mcp add suno-chrome -s local -- npx
  chrome-devtools-mcp@1.9.0 --browser-url=http://127.0.0.1:9222`, stored in `~/.claude.json` for this repo; attaches to
  port 9222). Not in `.mcp.json`: the VS Code extension cannot show the approval prompt for project servers and
  rejects them. If the tools aren't available: `claude mcp get suno-chrome` (missing → run the add command above;
  then a new session). **Don't** fall back to the plugin's own Chrome, because Google sign-in is blocked there.
- `list_pages` → a `suno.com/create` tab (open one with `new_page` if missing) and a `usesuno.com/tools/downloader/` tab.
  Logged in = the sidebar shows the profile and "Credits remaining".
- Account baseline: `evaluate_script` with the output of `P js account` → `P quota $A --credits C --downloads-used D --context "start"`.
- Before the first Create of a batch, report slots, rounds and credits (from `validate`/`status`) in your log; the approved
  plan is the OK (CLAUDE.md §5).

MCP can only write files inside the repo, so every evidence file goes to `$A/notes/suno/<gen>.*.json`.

## 2. One generation (repeat per round)

**a. Spec.** `P next $A` (picks the next slot/round from `order`), or `--slot N`. For extra rounds:
`--slot N --purpose more|regenerate --reason "<verify decision + hints>"`, optionally `--variant NAME`.
It prints `GEN=sNN-rMM` and writes `notes/suno/<gen>.spec.json` (+ `.style.txt`, `.lyrics.txt`, the exact text to type).

**b. Fill the form** on `suno.com/create`, in this order. `take_snapshot` to get uids and re-snapshot after each dialog.
1. Advanced mode: if the page is in Simple mode (`?mode=SIMPLE`, no "Lyrics editor"), switch to Advanced/Custom.
2. Model: button `v6…` → pick the spec's model (never "Create Custom Model").
3. Voice: "Add Voice" → dialog "Voice" → click the voice name (or "Remove selected Voice" when spec voice is null).
   **Choosing a Voice overwrites the Style box**, so Style always comes after this.
4. Style: set the Style textarea (the one with the `N/1000` counter; its placeholder changes randomly) with the **native value
   setter + `input` event** (`Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el, text)`), then
   confirm the counter shows the new length. MCP `fill` can look filled while React keeps an empty Style → Suno receives no Style
   (seen 2026-09-23, 10 credits lost). The Style box can also reset after a Create: re-check before every round.
5. Lyrics: `click` "Lyrics editor" → `press_key Meta+A` → `press_key Backspace` → `type_text` with `.lyrics.txt`.
   Real key presses are the only method that keeps line breaks (paste/insertText lose them). Instrumental → leave it empty.
6. Title: same setter on `input[placeholder="Song Title (Optional)"]` (every copy; Meta+A doesn't select-all there).
7. "More Options" (expand; its label may read "More Options Variety"): setter on `input[placeholder="Exclude styles"]`; Vocal Gender `Male`/`Female` (click the active one again to
   clear it when spec is null); Duration `Auto`, or `Custom` + `fill` the m:ss box (`input[aria-label="Duration"]`);
   Max Mode `On`/`Off`; Personalize `Off`.
8. Sliders: `evaluate_script` with `P js set_sliders --album $A --gen <gen>`. It returns each slider's value; any
   `ok:false` → click that slider and `press_key ArrowLeft/ArrowRight` step by step.

An active toggle has class `hxc-btn-variant-standard-legacy`; an inactive one has `…tertiary-legacy`.

**c. Verify the form (mandatory).** `evaluate_script` with `scripts/js/read_form.js` (pass the file content as
`function`), `filePath: $A/notes/suno/<gen>.form.json` →
`P check-form $A <gen> $A/notes/suno/<gen>.form.json`. Fix every ✖ row and re-read until it prints `FORM KHỚP SPEC`.
On the first run of a session, also look at one screenshot to confirm `read_form` is reading the right boxes.
If a field reads `null`, the UI has changed: fix the selector in `read_form.js`, don't skip the check.

**d. Create.** `P js account` → note credits (= credits_before). Real mouse `click` on `button[aria-label="Create song"]`.
Then wait ~5 s and `list_network_requests` (resourceTypes fetch/xhr, **`includePreservedRequests: true`**: Create
soft-reloads the page and the default list comes back empty) → the `POST …/api/generate/v2-web/` entry → `get_network_request`
with `requestFilePath: $A/notes/suno/<gen>.request.json`, `responseFilePath: $A/notes/suno/<gen>.response.json` →
`P submitted $A <gen> --request … --response … --credits-before C`.
- **Never click Create a second time** for the same gen until you have proof nothing was sent: the preserved list has no
  v2-web entry AND the Library shows no new clip. `find_recent` does not return clips in `error` state (e.g. a lyrics
  refusal), so an empty `find_recent` is not proof. Clips found without a captured response → `submitted --clips id1,id2`.
- A v2-web 200 does not mean accepted: the lyrics filter answers seconds later in the feed (clip status `error`,
  "Your lyrics contain copyrighted material…", 0 credits). Same lyrics are refused again: don't regenerate, report to the PM.
- Exit code 2 = what Suno received differs from the spec (credits already spent). Stop this album's Suno job, show the mismatch
  and report to the PM (CLAUDE.md §5); the PM decides.
- The first real run will print which request keys it couldn't match ("chưa kiểm được"). Pin them in
  `REQ_SLIDER_KEYS`/`compare_request` in `scripts/suno_gen.py` once seen, and note them in `references/suno-research.md` §2.2.

**e. Wait.** `evaluate_script` with `P js poll_feed --album $A --gen <gen>`, `filePath: $A/notes/suno/<gen>.feed.json`
(waits up to 4 min per call; `done:false` → call again; usually 1–3 min) → `P js account` →
`P complete $A <gen> $A/notes/suno/<gen>.feed.json --credits-after C2`. It re-checks style/exclude/voice/max/model/lyrics
as Suno stored them, and credits spent vs expected. Exit 2 = mismatch or Suno error → report, don't download as valid.

**f. Download each clip via usesuno.** For each clip id:
`navigate_page` the usesuno tab to `https://usesuno.com/tools/downloader/` (always reload; the "Download complete"
modal blocks the next one) → `evaluate_script` with `P js usesuno_download --album $A --clip <id8>`. It pastes
`suno.com/song/<id>` (private links work), waits until the page shows **this clip's duration**, then clicks
Audio → WAV → Continue download. Then `P ingest $A --clip <id8>`: it waits for the file in `~/Downloads`, matches it by
duration (±0.6 s), moves it to `audio/raw_tracks/<slug> <id8>.wav` (usesuno's "[usesuno.com]" suffix is dropped; the id8 tells the 2 clips of a round apart), and appends the clip to the manifest
(`status: draft`, slot, round, generation, purpose, reason, settings, sha256).
- `ok:false` (buttons render late, a JS click is ignored) → do the same by hand: `take_snapshot`, `fill` the textarea,
  `click` "Find download options", `wait_for` "Ready —", check the duration text, click Audio → WAV → "Continue download".
- ingest refuses a file whose duration doesn't match → wrong clip; don't force it.

**g. Quota check.** `P js account` → `P quota $A --credits … --downloads-used … --context "after <gen>"`.
Exit 3 = official downloads went up → stop the Suno lane and report to the PM (CLAUDE.md §5).

## 3. Hand-off and extra rounds

When a slot's planned rounds are downloaded (`ingest` prints the command), run the **verification-audio** skill for
that slot. Its decision drives what happens next:

| verify decision | this skill |
|---|---|
| `SELECT` | nothing; verification-audio auto-accepts it (CLAUDE.md §5) |
| `REGENERATE` | hints marked `[cả N clip]` come from the prompt/lyrics: change `generation.yaml` (slot `overrides`) or the track md lyrics, add a line to `changes:`; hints marked `[1/N clip]` are random, re-run as is. PM OKs credits (and the lyric change, if any) → `next --slot N --purpose regenerate --reason "<hints>"` (+ `--accept-lyrics-change` when the lyrics were edited; the manifest records it) |
| verify / PM picks "dùng bản tốt nhất" (`best_available`) | nothing; verification-audio accepts it with `--why` (recorded as `accept_override`) |

**Tempo.** The prompt carries the planned tempo; there is no built-in guess about Suno. verification-audio measures each
clip's tempo against the BPM typed in its prompt (`settings.bpm`) and prefers the closer clip; album-assembly reports
tempo jumps between songs. Change `defaults.bpm` / a slot's `overrides.bpm`
only on measured data and the user's OK, with a `changes:` line.

After 3 rounds without a SELECT on one slot, accept `best_available` and report it to the PM (verification-audio's stop rule). Slot 1 must be accepted
before any other slot is generated (`gates.anchor_first`); `--force` only when the PM says so.
If the Anchor defines a new persona, the user creates a Voice from it (song menu → Voice) and you put its name/id in
`defaults.voice` before slot 2.

Batch runs: go through `order`, one round at a time, and verify each slot as it completes. Give the user a short line
per round (gen id, clip durations, credits left). At the end, show `P status $A`.

## 3b. Cover branch (public-domain slots, `cover` in generation.yaml)

A slot whose plan has `public_domain.mode: lyrics` is an ordinary slot (the PD lyrics are its lyrics). `mode: cover` makes
album-plan write `cover: {kind, file | clip_id, year}` into the slot: Suno keeps the source's melody and structure and sings
our lyrics, Style and Voice over it. Same hard rules, same `next → check-form → Create → submitted → complete → ingest`.
**First live run of this branch:** the steps marked (live) are written from Suno's menus (`references/suno-research.md` §7:
⋯ ▸ Remix ▸ Cover) but their selectors and request keys were not seen yet: take a snapshot at each one, fix `read_form.js`
(`cover_of`) and `compare_request` if needed, and record what you saw in `references/suno-research.md`.

**The source** (CLAUDE.md §5 — only what the slot names, never other audio):

| `cover.kind` | Source | Before `next` |
|---|---|---|
| `own_rendition` | a plain organ rendering of the PD tune, made by us from a PD score | `$SK/.venv/bin/python $SK/scripts/pd_source.py <score.mid/.musicxml/.abc> $A/notes/suno/sNN-cover-source.wav --bpm <slot bpm> [--transpose N] [--parts melody\|all] [--repeat <verses>]`; the score comes from a PD edition (the plan's `public_domain.source_url`) or is typed by us in ABC; a file with its own copyright notice is not used |
| `pd_recording` | a recording that is itself public domain (US: published ≥ 100 years ago) | the file in the repo path named by `cover.file` |
| `own_suno_clip` | one of our Suno clips (`cover.clip_id`), e.g. a clip already in our library | nothing to upload |

`validate` refuses a missing file, a source over 8 min, or an unknown kind.

**One Cover round:**
1. `P next $A --slot N` → the spec says `COVER (<kind>)` and the source.
2. Source into Suno:
   - `own_rendition` / `pd_recording` (live): on `suno.com/create` click "Upload Audio" (or "+ Audio"), `upload_file` the
     exact `cover.file` into the file input, accept Suno's terms dialog only if it asks to confirm you own the rights
     (true for these kinds), wait until the uploaded clip appears in the workspace, note its clip id (`P js find_recent`
     by title / the song link) → `P cover-source $A <gen> --clip <id>`. Suno refusing the upload (copyright match) →
     stop, report to the PM; never try another file.
   - `own_suno_clip`: `P cover-source $A <gen> --clip <cover.clip_id>`.
3. (live) Open the source clip's ⋯ menu → Remix → **Cover**. The create form now shows the Cover source (read_form's
   `cover_of`). Then fill the form exactly as §2 b (Voice first, then Style, lyrics = the PD lyrics, title, options,
   sliders). In Cover mode "Audio Influence" is how closely the melody is followed: the spec's value.
4. `read_form` → `check-form`: besides the usual rows it needs `cover_source_clip` (recorded) and `cover_mode` (form shows
   Cover). Only `FORM KHỚP SPEC` → Create.
5. `submitted` checks that the request carries the source clip id (a request without it is a normal song: exit 2) and
   prints the request keys that contain "cover" (pin them after the first run). Then `complete`, usesuno download, `ingest`
   exactly as §2. The manifest keeps the source (`cover.kind`, `source_clip`) on the generation.
6. verification-audio as usual; its lyric check compares against the PD lyrics.

## 4. Resume / recovery## 4. Resume / recovery

`P status $A` lists every slot (planned vs extra rounds, clips downloaded, clips waiting, verify decision, selected clip)
and every unfinished generation with its next step:
`prepared` → fill/check/Create · `submitted` → poll_feed/complete · `complete` → download/ingest.
Running `next` again on a `prepared` round reuses the same gen id (nothing was spent).

## Manifest (`audio/raw_tracks/manifest.json`)

- `clips[]`: one entry per downloaded file. This is verification-audio's input contract (`file`, `title`, `clip_id`,
  `suno_url`, `status: draft`, `slot`, `round`), plus `generation`, `purpose` (planned | variant | more | regenerate | test),
  `reason`, `variant`, `settings` (incl. `style_version`, `lyrics_file`, `lyrics_sha8`, `spec`), `checks`, `sha256`.
  verify.py later adds its results and sets `selected`/`rejected`.
- `generations[]`: every round, including ones whose clips aren't downloaded yet: spec path, status, clip ids,
  credits before/after, form/request/feed check results.
- `quota_log[]`: account readings; an `alert` means the official download count went up.
- Older entries (the first spike album) have no `generation` field; leave them as they are.

## Files

| Path | What |
|---|---|
| `scripts/suno_gen.py` | plan validation, spec per round, form/request/feed checks, ingest, manifest, status, quota |
| `scripts/js/*.js` | page scripts: `read_form`, `set_sliders`, `account`, `poll_feed`, `find_recent`, `usesuno_download` (printed with parameters by `suno_gen.py js`) |
| `templates/generation.yaml` | plan template (input) |
| `<album>/notes/suno/<gen>.*` | spec, typed text, form/request/response/feed evidence per round (text, in git) |
| `scripts/suno-chrome.sh` | dedicated Chrome; MCP server `suno-chrome` = local scope (`claude mcp get suno-chrome`) |
