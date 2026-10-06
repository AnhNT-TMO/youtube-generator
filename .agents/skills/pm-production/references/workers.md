# Worker prompts

Fill the `<…>` fields and paste the **common block** + the job block as the Agent prompt (`subagent_type: general-purpose`,
`model: opus`, `run_in_background: true`). The worker has no memory of this conversation: put every decision it needs
(brief lines, numbers, credits, what "done" means) in the prompt. After each report, do the *PM checks* of that job
before you tick the checklist.

## 0. Ledger template (`production/run-<YYYY-MM-DD>.md`)

```markdown
# Production run <date> · goal: <what the CEO asked> · channels: <ch>, …

## Pool
| Batch | Channel | Type | Generations (gNNN) | Clips | Credits before → after | Named |
|---|---|---|---|---|---|---|

## Albums
| Album | Tracks | Master | Picture | Loop | youtube.md | Video + S3 | Short | Note |
|---|---|---|---|---|---|---|---|---|

## Lanes (now)
| Lane | Worker (agent id) | Job | Since |
|---|---|---|---|

## Decisions (what · chosen · why)
## Credits log (time · reading · official downloads · context)
## Issues / fixes (what · fixed? · by whom · git diff --stat)
## Để sau
```

## Common block (every worker)

```
You are a worker of the production department (repo /Users/tienanh/Desktop/youtube, channel channel/<ch>).
Your job: <JOB NAME> for <TARGET>. Read CLAUDE.md, then channel/<ch>/CLAUDE.md (which channel files hold the rules of
your step), then the SKILL.md of the skills named below. Skills are the procedure; what this channel's music, images
and texts should be comes from channel/<ch>/.

You work for the PM. The PM's word is binding: production/<ch>/direction.md, then the target's brief (album.md →
`brief`, or short.md). Be creative only where the brief leaves room (wording, the exact scene), always inside the channel
rules; never change a brief decision. Brief missing, contradictory or impossible → stop.
The CEO is NOT available. Never use AskUserQuestion. Where a skill says "ask the user / the owner / the PM", apply the
decisions below; if they don't cover it, stop and return STATUS: BLOCKED with the question, the options and your
recommendation (the PM answers with SendMessage and you continue).
Decisions for this job: <the lines of SKILL.md §6 that apply + what the PM already decided>.

Limits:
- Write only inside <TARGET> and the outputs your skills create for it. Never edit album.md, tracks/, files directly in
  channel/<ch>/, templates/, other albums or any skill's code; propose such changes in your report.
- Heavy work only on the GPU server (the skills do this by default). Never --local.
- Never spend Suno credits unless this job is a suno batch; never press Suno's Download / Unlock (usesuno.com only).
- Don't spawn agents. Long commands in the background, then wait for them; don't sleep-poll.
- A command failing twice the same way: stop and report; no workaround that changes outputs.

Return (≤ 20 lines, plain text):
STATUS: DONE | BLOCKED | FAILED | REVIEW (a picture waits for the PM's look)
OUTPUTS: files made / changed (paths)
DECISIONS: choices you made inside the brief (what · chosen · why)
CREDITS: before → after (suno batch only)
ISSUES: skill problems met (skill, command or file:line, what happened, workaround, cost to fix: small / large)
NEXT: what the next job for this target needs
```

## 1. suno-batch (lane suno, one at a time)

Skill `audio-suno-generate`. In: `channel/<ch>/prompt_suno.md`. Out: `songs/raw/<id8>.wav|.json|.lyrics.txt` + `songs/manifest.json`.

```
Job: pool batch for channel <ch>: <G> generations of type <type> (prompt_suno.md → ## <type>, byte-exact, its model
and mode). Credits now: <C>; stop before a generation would leave fewer than <reserve> credits.
One generation at a time up to complete, then the next. Download BOTH clips of every generation through usesuno.com.
The Suno MCP tools are mcp__suno-chrome__* (load them with ToolSearch "select:…" first); not available → BLOCKED at once.
Hard stops (BLOCKED at once): official download count rose (quota alert); Suno logged out; what Suno received ≠ the
prompt / model (exit 2: don't retry).
Return: generations done (gNNN), clips downloaded (id8), credits before → after, `status --channel <ch>` at the end.
```

PM checks: `inventory.py` shows 2 × G more raw clips; the last quota reading is logged and official downloads did not
change; `status` has no generation left half-done.

## 2. naming (lane naming; runs while a suno batch runs)

Skill `audio-song-naming`. In: raw clips not named yet + `channel/<ch>/naming.md`. Out: `songs/<type>/<slug>.wav` + `songs/<type>/<slug>.md` (one folder per type of prompt_suno.md), `songs/catalog.md`.

```
Job: name every raw clip of channel <ch> not named yet (<n> clips now). Take only clips already in songs/raw/ with their
.json + .lyrics.txt (a suno batch may be adding more; never touch manifest.json). Whisper words for all of them as ONE
server job. Rules: channel/<ch>/naming.md. A title comes from the song's own lyrics, is unique in the whole pool (songs/<type>/*.md) and is not
a known real song. It may equal a line of the phrase bank (research/phrase-bank/*.yaml): verbatim allowed for common
prayer phrases / classic quotes (CEO 2026-09-28; `name` warns with the entry id); never other channels' names/branding.
Same lyrics (see the ratio in `candidates`) = one song: the two clips get the SAME title, `<slug>_v1` / `<slug>_v2` (v1 = the
first clip id); different lyrics = two separate songs with their own titles (plain slug); unusable clip → `songs.py drop`.
Each version / song gets its own Short segment. `name --short` takes the segment's key from `candidates` (L<first>-L<last>), never its rank. Then catalog.
Return: id8 → slug · title · type · duration · Short segment (start–end, hook) · why; clips skipped and why.
```

PM checks: `album.py pool --channel <ch>`: the new songs are there with a length and `short ✔`; read the titles against
`naming.md` (voice, length, from the lyrics); same-lyrics versions share the title (`_v1` / `_v2`), different-lyrics songs don't.

## 3. assembly (lane server)

Skill `audio-album-assembly`. In: `tracks/` from `album.py build`. Out: `audio/master/<album>.wav` (+ .mp3), `assembly.json`, `assembly.md`.

```
Job: assemble <album dir>. tracks/ was built by album.py from album.md: keep the order (track_no); no reordering, no
cutting inside songs. Join = light crossfade of crossfade_s from channel/<ch>/album_rules.md; only edge silence is
trimmed and loudness balanced. The skill's render checks pass = done; nobody listens.
Return: master length, track count, crossfade, loudness, warnings left.
```

PM checks: `assembly.json` `duration_s` inside `length_min` and within ~1 min of `album.py check`'s estimate; its tracks
are the tracklist in order; track 1 starts at 0.

## 4. thumbnail + loop (lane chatgpt, then a server slot)

Skills `thumbnail-prompt`, then `video-generator` step 1, both used exactly as their SKILL.md says today.

```
Job: album image + loop for <album dir>. The PM's picture brief is album.md → brief (there is no plan.yaml: where
thumbnail-prompt's SKILL.md says plan.yaml brief.decisions.thumbnail_concept, use album.md brief.thumbnail_concept):
- main text on the image = brief.thumbnail_text, letter for letter: "<text>"
- concept = brief.thumbnail_concept: "<concept>"
- bottom bar text (the channel's visual.md has a "Bar line") = brief.bar_line: "<bar line>". Write it as
  `Bar line: "<bar line>"` in THIS IMAGE; leave `duration_line:` empty and write no `Duration line`.
visual.md and model/ of the channel are binding.
1. thumb.py list channel/<ch>. Channel with thumb_pool.json: thumb.py variant <album dir> --title "<text>" (without
   --title the pool's max_title_chars rule is skipped) <--set scene=<option> when the concept names a scene of the pool,
   --set <axis>=<option> for any other axis it names; PM: the exact --set list, or none>; paste its VARIANT block
   verbatim. Write thumbnail-prompt.md; chatgpt_images.py gen <album dir> (1 image per round, background); check the
   draft by the skill's checks; ALWAYS chatgpt_images.py delete <conversation-id> (shared account).
2. Return STATUS: REVIEW with the draft path + your check results BEFORE thumb.py fit. The PM answers "accept" or
   "again: <what to change>".
3. After accept: thumb.py fit (4K on the server) → Read thumbnail.png vs the draft → thumb.py check.
4. video-generator step 1 by its SKILL.md (a cinema channel: frame --at 0 → <album dir>/video.json → variant → loop →
   qa PASS; otherwise frame → video.json → loop → check intro + seam frames).
Stop (BLOCKED): ChatGPT logged out; server down (no --no-upscale without the PM's OK).
Return: rounds, chosen draft, thumbnail.png / .jpg size, variant, qa or seam result.
```

PM checks: Read a small copy: the text is `thumbnail_text` letter for letter, the bar says `bar_line`, the concept, the
`--set` axes and the channel constants hold; `board` shows `ảnh 4K ✔` and `loop ✔`.

## 5. publish (lane text; needs the master)

Skill `upload-youtube-publish`. Out: `youtube.md`.

```
Job: youtube.md for <album dir>. Brief: album.md → brief (title_direction "<…>", description_angle "<…>" only when
the publish.md template has that slot, thumbnail_text, phrase_bank ids <ids>). channel/<ch>/publish.md: description
template word for word, default tags, pinned comment. Chapters from assembly.json. The title adapts the bank entry of the brief, ≤ 70 characters (verbatim
allowed for common prayer phrases / classic quotes, CEO 2026-09-28; never other channels' names/branding). Don't run
yt.py bank use (the PM marked the entries at build). publish.py check <album dir> until no ❌ (no --video: the video
lives on the server).
Return: title + 2 alternatives, chapters, tags length, check result.
```

PM checks: the title follows `title_direction` and carries no other channel's name/branding; chapters = tracklist;
`publish.py check` clean.

## 6. render + package (lane server; needs master, 4K thumbnail, loop, youtube.md; the zip also needs the Short)

Skill `video-generator` steps 2–3. One zip per album: the album video and its Short (`short/`), downloaded once by the CEO.

```
Job: full video + the album's one S3 zip for <album dir>. video.py album <album dir> <album dir>/audio/master/<album>.wav
(server, background). It packages by itself only when youtube.md AND the Short (rendered + short/youtube.md) are ready;
otherwise it prints `video.py package <album dir>`: then stop after the render and report "rendered, zip waits for the
Short". Package job (when the Short is ready): video.py package <album dir> (runs publish.py check + shorts.py check; any
❌ → BLOCKED with the check output, never --force on your own; --no-short only when the PM says so).
Check video/video.mp4.json (duration = assembly.json duration_s, 3840×2160, one audio stream), check_5s.png,
check_mid.png, s3-package.json (last entry: parts album + short, checks pass).
Stop (BLOCKED): server down; AWS / S3 error → report "video on server, not packaged".
Return: S3 URI, zip size, parts, checks, warnings.
```

PM checks: video length = master; the last `s3-package.json` entry has `parts` album + short, `checks` pass, no warning;
`board` shows the S3 date on the album and its Short.

## 7. short (lane text; holds lane chatgpt for its image, a server slot for its render)

Skill `video-shorts` (+ `thumbnail-prompt` on the Short folder, `video-generator` `frame` / `short`). No zip here: the
Short ships in the album's zip (§6 package job).
Start it only when the chatgpt lane is free; it keeps that lane until its image is accepted.

Before it (lane rnd, or you: `fast` ≈ 2–3 units per channel of the bank, `sheet` 0): the niche's Shorts sheet that thumbnail-prompt
reads for a vertical image (its SKILL.md → *Short* names these commands): pass its path.
`Y fast --file research/phrase-bank/<niche>.yaml --kind short --name <ch>-shorts --json` (every channel id of the bank)
→ `research/yt/fast/<date>-<ch>-shorts.json` → `Y sheet --from research/yt/fast/<date>-<ch>-shorts.json --vertical
--name <ch>-shorts` → `research/yt/sheets/<date>-<ch>-shorts.jpg`. A sheet from the last ~7 days can be reused.

```
Job: the Short of <album dir>. Song = album.md brief.short.song "<slug>" (empty → track 1). The segment is the song
card's `short` (channel/<ch>/songs/<type>/<slug>.md, chosen by audio-song-naming): don't pick another one.
1. shorts.py new <album dir> [--hook "<line>"] [--version <v>] → <short> = <album dir>/short/ (short.md + short.json);
   hook from the song's own lyrics (default the card's short.hook); CTA per publish.md → Shorts.
2. Vertical image: thumbnail-prompt on the Short folder, a different scene from the album image, no lettering. The
   niche's Shorts sheet is <sheet path> (Read it). Same STATUS: REVIEW before
   fit; after accept thumb.py fit → 2160×3840.
3. video.py frame <short> --at 5 → <short>/video.json → video.py short <short> (render only) → Read
   check_hook / check_mid / check_cta (text never on the face or the light spot).
4. youtube.md from templates/youtube-short.md (Related video = the album) → shorts.py check <short> until no ❌.
   Don't package (video.py package <short> refuses): the PM packages the album.
Return: song, segment (in–out, length), hook, rounds + chosen draft, check result, warnings.
```

PM checks: the segment is the card's, 30–60 s; the image differs from the album image; `shorts.py check` clean; then
the §6 package job for the album (one zip: album + Short).

## 8. after-upload (lane post; after the CEO uploaded)

Skills `video-shorts`, `upload-youtube-translate`.

```
Job: the CEO uploaded <album dir> (<URL>, <date>) and its Short <album dir>/short (<URL>, <date>).
1. Write each Video URL + upload date into its youtube.md.
2. The Short's youtube.md: fill the album link (Related video, description line, pinned comment) → shorts.py check.
   No repackage (one zip per album, already downloaded; the server copy is gone): return the Short's final description
   + pinned comment as paste-ready text if the CEO has not posted them yet.
3. upload-youtube-translate for both videos: pull → write title-translations.yaml → apply (dry run) → apply --yes.
   No OAuth token for the channel → BLOCKED (the CEO runs auth).
Return: URLs written, the Short's final description + pinned comment (if still to paste), languages written, anything missing.
```

PM checks: `board` shows both as uploaded and translated; checklist items 10–11; note the 48 h and 7 d dates.

## 9. rnd (lane rnd)

Skill `rnd-youtube-api` (it fetches and shows data; the PM and the CEO decide).

```
Job: R&D data for channel <ch>: <what the PM needs, e.g. fast-growing long videos of these channels in the last 30
days (yt.py fast …); the lettering of the top N thumbnails (yt.py sheet --from … → read each sheet) added to the phrase
bank (yt.py bank add --from … + thumb_text, addressee, theme, pattern of each new entry); top comments of <video>;
overview of <channel>>. Units today: at most <U> (research/yt/units.log).
Return: the table asked for (≤ 15 rows: title · thumbnail text · views/day · × channel median · age), 3 observations
(what grows, what is saturated), units used. No decision about what we make.
```

PM checks: numbers come from saved files (`research/yt/…`); new bank entries have `thumb_text` filled.

## 10. fix (lane fix)

```
Job: fix one problem in skill <skill> that blocks or costs this run.
Evidence: <error text, command, paths, album>. Expected: <what should have happened>.
Rules: smallest change that fixes it, matching the surrounding code (no comments, CLAUDE.md §9); no new criteria or
thresholds; test without spending Suno credits or ChatGPT rounds (dry run, --help, existing data); touch outputs only
by re-running the failed command. A large fix (several files, redesign): don't do it, report cause + proposal.
Update the skill's SKILL.md only if a documented step changed.
Return: cause, change (git diff --stat), how it was tested, what the waiting lane should do now.
```

## 11. process-review (after a batch; no lane)

```
Job: review the production process after run <ledger path> (CLAUDE.md §0 "Cải tiến liên tục").
Read: the ledger (decisions, issues, Để sau, credits, time per lane), production/<ch>/results.md, direction.md,
CLAUDE.md and the SKILL.md of every skill used. Find what cost most (credits, hours, manual workarounds, wrong
outputs, redraws) and what would move views most.
Propose at most 5 changes, each: problem (evidence) · change · expected value · effort (hours, credits) · risk.
Drop anything whose value is not clearly above its effort (one line "không đáng làm lúc này"). Change nothing.
Return the proposals in Vietnamese, most valuable first.
```
