---
name: audio-suno-generate
description: Make songs for a channel's song pool on suno.com in Simple mode - paste the channel's fixed prompt for a song type (channel/<ch>/prompt_suno.md, e.g. `spoken` / `sung`) byte-exact into Suno's single prompt box with the model from that file, driving the owner's logged-in Suno in the dedicated Chrome (Chrome DevTools MCP `suno-chrome`); Suno writes lyrics and title itself. Checks the form before Create, the request Suno received and what Suno stored (prompt not truncated, model, Voice = the one in prompt_suno.md or none, no Style/lyrics), records credits before/after, downloads BOTH clips of every generation through usesuno.com (never Suno's own Download) into channel/<ch>/songs/raw/<id8>.wav + <id8>.json (clip facts) + <id8>.lyrics.txt (lyrics as Suno stored them) and keeps songs/manifest.json. Input from the PM - channel, type, number of generations (e.g. "10 lượt spoken, 10 lượt sung"). Use when the PM or the owner says "tạo nhạc", "tạo bài cho kho", "generate", "chạy Suno", "tạo N lượt spoken/sung", "tải clip về", "làm tiếp lượt Suno dở". Does NOT name songs or pick Short segments (audio-song-naming) or choose songs for albums (pm-production).
---

# Suno generate (Simple mode → song pool)

One generation = one fixed prompt (channel/<ch>/prompt_suno.md, `## <type>` → its ```text block) in Suno **Simple mode**,
model + Voice (optional) from the file's front matter → Suno writes lyrics + title → **2 clips, both downloaded via usesuno** → each clip is
one raw song in `channel/<ch>/songs/raw/`. Naming (title from lyrics, rename, song card, Short segment) is `audio-song-naming`.

```
P next ─▶ tab Simple + model + Voice + js fill_prompt ─▶ read_form ─▶ check-form ✔ ─▶ Create (once) ─▶ submitted (request check)
     ─▶ js poll_feed ─▶ complete (feed check, credits) ─▶ per clip: js usesuno_download ─▶ ingest ─▶ quota
```

## Hard rules

1. **Never** click Suno's Download / "Unlock & Download", never call `/api/download/*`: each one burns 1 of the 20
   monthly official downloads. Every download goes through usesuno.com. `quota` exit 3 (official count went up) → stop the
   Suno lane of the whole run and report to the PM.
2. **Create only after `check-form` printed `FORM KHỚP SPEC`** for this gen, read after your last edit. Never Upgrade,
   Buy, Create Custom Model, Voice creation, or anything else that spends credits/quota.
3. **Never click Create twice** for one gen without proof nothing was sent: the preserved network list has no
   `v2-web` entry AND the Library shows no new clip (`js find_recent` does not list clips in `error` state, so an empty
   result alone is no proof). A double click is a double charge.
4. **One generation at a time up to `complete`** (`next` refuses while one is `submitted`). Downloads may wait:
   `status` lists the clips still to fetch.
5. **The prompt is the CEO's, byte for byte.** Never shorten, fix or "improve" it; never add Lyrics / Styles / Audio /
   Image from the "+" menu or the chips above the box, and no Voice other than the front matter's `voice` (none if absent). A prompt that does not fit, a model that is not in the menu,
   a form that cannot match → stop and report to the PM (`BLOCKED`, exit 4). Changes go into prompt_suno.md (PM/CEO).
6. Exit 2 from `submitted` / `complete` = Suno received or stored something else (credits already spent): stop this
   channel's Suno job, show the mismatch, report to the PM. `ingest` takes such a clip only with `--pm-ok "<PM decision>"`.
7. Keep the Suno tab in the foreground (background tabs ignore clicks). Only suno.com/create and usesuno.com/tools/downloader.
8. This skill is the only writer of `songs/manifest.json` and writes only inside `songs/raw/` (+ the manifest); never
   `songs/*.md`, never edit the manifest by hand, never delete clips.

## Input

- From the PM: channel, type, number of generations. "10 spoken + 10 sung" = 20 generations = 40 clips. Alternate the types
  unless told otherwise; `status` counts done generations per type (and today).
- `channel/<ch>/prompt_suno.md`: front matter `mode: simple`, `model`, optional `voice: {name, id}` (a Voice of the Suno
  account: exact name as the Voice dialog shows it + its uuid; absent = no Voice), `clips_per_generation`, `download: all`, `types`;
  one `## <type>` heading per type with exactly one ```text block. `status` shows whether the file is usable.

## Preflight (once per session)

```bash
SK=.claude/skills/audio-suno-generate; P() { $SK/.venv/bin/python $SK/scripts/suno_gen.py "$@"; }; CH=<channel>
$SK/scripts/suno-chrome.sh      # dedicated Chrome, profile ~/.suno-chrome/profile, port 9222 (already running = fine)
P status --channel $CH
```

- MCP tools `mcp__suno-chrome__*` = local-scope server (`claude mcp get suno-chrome`; missing → `claude mcp add
  suno-chrome -s local -- npx chrome-devtools-mcp@1.9.0 --browser-url=http://127.0.0.1:9222`, then a new session). Don't
  use the plugin's own Chrome (Google sign-in is blocked there).
- `list_pages`: a `suno.com/create` tab (`new_page` if missing) and a `usesuno.com/tools/downloader/` tab. Logged in = the
  sidebar shows the profile and "Credits remaining".
- Baseline: `evaluate_script` with `P js account` → `P quota --channel $CH --credits C --downloads-used D --context start`.

`evaluate_script` / `get_network_request` can only write inside the repo: evidence goes to
`channel/<ch>/songs/raw/gen/<gen>.{form,request,response,feed}.json` (the default paths the commands read).

## One generation

**a. Spec.** `P next --channel $CH --type <type>` → `GEN=gNNN` (status `prepared`; running `next` again before Create
reuses the same gen, nothing spent).

**b. Form** on `suno.com/create` (`take_snapshot` for uids):
1. Tab **Simple** (`[role=tab]` "Simple", `aria-selected=true`).
2. Model: the button showing the current model (e.g. "v6-mini") → menu → click the item whose label is the spec's model →
   check the button text. Never "Create Custom Model".
3. Voice (only when `next` printed one): button "Add Voice" → dialog "Voice" (grid "My Voices") → `click` the Voice's
   **name** text (the card picture only plays a preview; scroll the card into view first or the click times out) → the
   prompt box shows a chip `span[data-thumb][title="<name>"]` + `button "Remove <name>"`, and "Add Voice" is gone. No Voice
   in the spec: the form must still show "Add Voice" (a chip → its "Remove …" button).
4. Prompt, AFTER the Voice: `evaluate_script` with `P js fill_prompt --channel $CH` (native value setter + `input` event on
   the single Simple textarea; returns `ok`, `length`). `ok:false` → read its `error`, fix, run again.
5. Nothing else: no "+" additions, no audio/image.

**c. Check.** `evaluate_script` with `scripts/js/read_form.js`, `filePath: channel/$CH/songs/raw/gen/<gen>.form.json` →
`P check-form --channel $CH` (tab, model, Voice name = spec, prompt byte-exact, no extra box/attachment). Fix every ✖ and
re-read until `FORM KHỚP SPEC`. A `null` / wrong field = the UI changed:
fix `read_form.js`, never skip the check. First run of a session: one screenshot to confirm read_form reads the right box.

**d. Create.** `P js account` → credits = C. Real mouse `click` on `button[aria-label="Create song"]`, once. Wait ~5 s →
`list_network_requests` (fetch/xhr, **`includePreservedRequests: true`**) → `POST …/api/generate/v2-web/` →
`get_network_request` with `requestFilePath` / `responseFilePath` in `…/gen/` (the MCP saves them as
`<gen>.request.network-request` / `<gen>.response.network-response` whatever the name: `mv` them to
`<gen>.request.json` / `<gen>.response.json`) → `P submitted --channel $CH --credits-before C` (checks prompt,
`mv`, `persona_id` = spec Voice id or null, and records `request_persona_id`). Clips found without a response → `--clips id1,id2` (from `js find_recent`).

**e. Wait.** `evaluate_script` with `P js poll_feed --channel $CH`, `filePath: …/gen/<gen>.feed.json` (waits ≤ 4 min;
`done:false` → again) → `P js account` → `P complete --channel $CH --credits-after C2`. It checks, per clip, the prompt
Suno stored (byte-exact, catches server-side truncation), model, Voice (`persona.id` = spec id, none if no spec), not
instrumental, lyrics present; prints title,
length, lyric lines and credits spent vs expected.

**f. Download each clip** (usesuno tab): `navigate_page` to `https://usesuno.com/tools/downloader/` (reload every time:
the "Download complete" modal blocks the next one) → `evaluate_script` with `P js usesuno_download --channel $CH --clip
<id8>` (pastes the private `suno.com/song/<id>` link, waits for this clip's duration, Audio → WAV → Continue download) →
`P ingest --channel $CH --clip <id8>`. Ingest waits for `*usesuno.com*.wav` in ~/Downloads, matches it by duration
(±0.6 s), writes `raw/<id8>.lyrics.txt`, `raw/<id8>.json`, then moves the file to `raw/<id8>.wav` (written last), and
indexes it. One clip at a time: the 2 clips of a generation share one title (same file name, "(1)" suffix) and can have
near-equal durations (ingest warns). `ok:false` → same steps by hand (`fill` the textarea, "Find download options",
`wait_for` "Ready —", check the duration, Audio → WAV → "Continue download"). A duration mismatch = wrong file: don't force.

**g. Quota.** `P js account` → `P quota --channel $CH --credits … --downloads-used … --context "after <gen>"`.

Report per generation, one line: gen, type, clip id8 + title + length, credits left.

## Resume

`P status --channel $CH`: prompt file state, generations per type (done / today / failed), clips downloaded, clips waiting,
credits measured, quota readings, raw clips not yet named, and every open generation with its next step
(`prepared` → form/check/Create · `submitted` → poll_feed/complete · `complete` → download/ingest · `failed` → PM).

## Output (`channel/<ch>/songs/`, local only)

| Path | What |
|---|---|
| `raw/<id8>.wav` | the clip from usesuno (id8 = first 8 chars of the Suno clip id); audio-song-naming later moves it to `songs/<slug>.wav` |
| `raw/<id8>.json` | `clip_id, id8, generation, type, prompt, title` (Suno's), `duration` (feed, s), `created, model` (menu label), `model_name` (Suno key), `voice` (feed persona `{id, name}` or null), `sibling_clip_id, suno_url, tags` (Suno's rewritten style), `audio, lyrics_file, file_duration, sha256, source, downloaded_at` (+ `feed_mismatch, pm_ok` when taken with `--pm-ok`) |
| `raw/<id8>.lyrics.txt` | lyrics exactly as Suno stored them (feed `metadata.prompt`, section tags included) |
| `raw/gen/<gen>.*.json` | evidence: form, request, response, feed |
| `manifest.json` | `generations[]` (id gNNN, type, model, mv, voice, prompt, prompt_sha8, status, clip_ids, credits_before/after/credits, form/request checks, request_keys, request_persona_id, feed facts incl. lyrics) · `clips[]` (clip_id, id8, generation, type, file, duration, sha256) · `quota_log[]` |

## Verified live (g001 no Voice, g002 Voice; 2026-09-28)

- Form: a fresh `suno.com/create` tab opens on **Advanced** with the last model (click tab "Simple" every time). The Simple
  prompt box is the only visible `<textarea>`; the setter fill is accepted (Create enables, request carries all 556 chars)
  even though "Clear all form inputs" stays disabled. Model menu: `menuitemradio` "v6 Pro …" → button text `v6`.
- Request `POST /api/generate/v2-web/` (Simple): `gpt_description_prompt` = prompt, `prompt: ""`, no `tags`, `mv`,
  `metadata.create_mode: "simple"`, `task: "agentic_thinking"`, `generation_type: "TEXT"`, `make_instrumental: false`,
  `metadata.control_sliders.aug_creativity: 0`; with a Voice: `persona_id` = Voice id, `persona_voice_ref` = the Voice's
  source clip, `audio_refs[]` (that clip's id, duration, lyrics, style prompt). Create → v2-web ≈ 5 s (Cloudflare check
  first), both clips `complete` ≈ 1–1.5 min later.
- Credits: 10 per v6 Simple generation, with or without Voice. Downloads through usesuno: official count unchanged.
- Feed: lyrics in `metadata.prompt` (both clips same lyrics + title, own `tags`), Voice in `persona {id, name}` and
  `metadata.persona_id`. Clip lengths seen: 3:57–4:34.
- Voice dialog: the card picture plays the Voice preview in the page's player (pause it if it keeps playing).

## Files

| Path | What |
|---|---|
| `scripts/suno_gen.py` | prompt file check, gen spec, form/request/feed checks, ingest, manifest, status, quota |
| `scripts/js/*.js` | page scripts: `read_form`, `fill_prompt`, `account`, `poll_feed`, `find_recent`, `usesuno_download` (printed with parameters by `P js`) |
| `scripts/suno-chrome.sh` | dedicated Chrome on port 9222 |
| `references/suno-research.md` | Suno facts (limits, page map, request/feed keys, measured credits) |
