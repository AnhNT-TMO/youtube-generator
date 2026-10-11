# Public-domain audit of melody files

Goal: for every melody file `research/christmas-carols/melodies/<batch>/<slug>.json`, written proof that the notes we render come
from a public-domain print and the chords come from a public-domain harmony or are our own. A song with that proof can be
defended against a YouTube Content ID claim ("Copyright - Melody or lyrics"); a song without it is fixed before it is used.

Content ID matches melodies, so a clean audit does not prevent claims on famous carols. It makes the dispute winnable and
tells us the claim is wrong.

## What counts

**PD print** (proof for melody and chords):
- A printed book, hymnal, sheet or score published in **1930 or earlier** (US public domain as of 2026: 95 years after
  publication), seen as a scan: IMSLP, archive.org, HathiTrust, Google Books, hymnary.org page scans, Wikimedia Commons scans of
  old prints, national library scans. Record title, year, page.
- A typeset edition that states it is released into the **public domain** and names the old print it follows (Open Hymnal,
  Mutopia pieces whose licence line says "Public Domain", CPDL editions marked public domain). Record the licence line.

IMSLP file licences: only a file tagged **Public Domain** that is a scan of a print of 1930 or earlier counts (check the
file's own copyright line, not the wiki footer, and skip files flagged Non-PD US/EU). Files under Creative Commons
(CC BY, CC BY-SA, CC BY-NC) are modern editions: never proof, and never used as a source (BY needs credit, BY-SA would bind
our audio to the same licence, BY-NC forbids monetised use).

Blocked or slow sites: hymnary.org, HathiTrust, IMSLP file downloads and Google Books often refuse automated access; use
archive.org (scans + full text), Wikimedia Commons, Open Hymnal, Mutopia, CPDL, national library scans. volksliederarchiv
images need a browser User-Agent and Referer header and carry no imprint (the date rests on the site's label: say so in notes).
A Wikimedia Commons file tagged PD-old with an old date can still be a modern engraving: count it only when it is a scan of the print.

**Not proof** (fine for checking notes, never the only basis): modern transcriptions on websites (hymnsandcarolsofchristmas,
trillian ABC, Musikpiraten, lieder-archiv, volksliederarchiv texts, blogs, 8notes, tocapartituras, flutetunes…), Wikipedia LilyPond examples, Mutopia CC-BY / CC-BY-SA editions,
MIDI files without a named old print, our own memory.

**Chords** are one of:
- `pd_harmony`: the chord at each half bar is what a PD print's harmony (SATB, accompaniment) spells. Small simplifications
  (dropping a passing chord, adding or dropping a 7th on the same chord, an inversion) are fine; a different chord is not, unless it is our own choice at that spot (not from a modern source) and the note lists it.
- `own`: our own simple functional harmony written for the file (the file's `remarks` say so) and not copied from a modern
  chord-symbol source.
- `modern_source`: taken from a modern source's chord symbols or harmony and not confirmed by a PD print.

A harmony is `pd_harmony` only when its harmoniser (arranger, editor) died **1955 or earlier** as well (life + 70 in the UK/EU;
we publish worldwide). A 1930-or-earlier print by a later-dying arranger (Vaughan Williams, Martin Shaw, Willcocks…) proves
the melody only; its chords are `modern_source` unless ours are our own.
A harmony printed without any arranger's name in a print of 1930 or earlier counts as anonymous and is `pd_harmony`.
Not anonymous: a book whose preface or index credits its unnamed harmonies to an editor (English Hymnal 1906: Vaughan
Williams and helpers), or whose index marks a setting "(c)" (Carols Old and Carols New 1916): check the preface and index.

## Familiar by ear (PM 2026-10-07)

Separate from the verdict. A clean melody can still differ from the version most listeners know today (that version is often
a later arrangement still under copyright). `familiar` records it:

```json
"familiar": {"status": "familiar", "compared": "trillian ABC + 2 current hymnals, tool 97%", "note": ""}
```

- `familiar`: our notes match the commonly sung version (tool compare against ≥ 2 popular modern versions: current hymnals,
  most-downloaded or most-viewed sheets) apart from the allowed differences. Modern versions are reference only, never a source.
- `unfamiliar`: our notes (from the PD print) differ audibly from the commonly sung version; `note` lists where.
- `unchecked` (default when missing): counted as unfamiliar.
- `approved` (optional, e.g. `"CEO 2026-10-07: use normally"`): the owner listened to an `unfamiliar` song and accepts it;
  it stays `unfamiliar` but no longer counts toward the cap.
- An album may hold at most VIBES.json `rounds.max_unfamiliar` songs that are not `familiar` (CEO: 2); `ambient_keychain.py`
  `render` and `album` refuse more. When a PD fix changes notes, re-check `familiar`.
- When choosing a PD print to transcribe, prefer the ≤ 1930 print closest to the commonly sung version.

## Verdict

| verdict | meaning | next step |
|---|---|---|
| `clean` | melody `pd_confirmed` and chords `pd_harmony` or `own` | none; `pd_audit.py dispute <slug>` prints the dispute text |
| `fix_chords` | melody confirmed, chords `modern_source` | redo the chords from the PD print found, or own harmony; then re-audit |
| `fix_melody` | no PD print found, or our notes differ from every PD print beyond the allowed differences | re-transcribe from a PD print, or drop the song |
| `fix_both` | both of the above | as above |

Allowed melody differences against the PD print (PM 2026-10-07: these are our own arranging, not copying): transposition,
note values scaled by 2 or ½, written-out repeats, at any phrase end a note held through the rest that follows it or shortened with a rest added after it, a rest lengthened or shortened at a phrase end, ties
merged, a repeated note split or merged (same pitch, same total length), a pickup note shortened with a rest before it, a printed repeat played once, a grace note left out, sections
played in another order (every note still from the print), one documented variant per phrase that another PD
print has. A rhythm change on the same pitches (dotted ↔ even) is a difference. Everything else is a
difference and is listed.

## Audit file

`research/christmas-carols/pd-audit/<slug>.json`:

```json
{
  "slug": "what_child_is_this_greensleeves",
  "checked": "2026-10-07",
  "melody": {
    "status": "pd_confirmed",
    "pd_sources": [
      {"url": "https://imslp.org/wiki/...", "title": "Christmas Carols New and Old (Bramley & Stainer)", "year": 1871,
       "kind": "scan", "compared": "by eye, every bar", "differences": "none"}
    ]
  },
  "chords": {"status": "pd_harmony", "source": "Stainer 1871, same print", "note": ""},
  "verdict": "clean",
  "fix": "",
  "notes": ""
}
```

- `melody.status`: `pd_confirmed` | `pd_differs` | `no_pd_source`.
- `pd_sources[].kind`: `scan` | `pd_edition`. `year`: year of the old print (for `pd_edition`, of the print it follows).
- `compared`: `pd_audit.py compare` result (`tool 100%`) or `by eye, every bar`. `differences`: `none` or the list.
- `fix`: empty when clean, else the concrete change (which bars, which source).

## Commands

Run with the music21 venv: `PY=.claude/skills/audio-suno-generate/.venv/bin/python`.

- `$PY .claude/skills/audio-christmas-workflow/scripts/pd_audit.py compare <slug> <file.abc|.mid|.xml|.musicxml|.krn> [--pick <title part> | --x <X: number>] [--voice <ABC voice>] [--part N]`:
  our melody against a downloaded source, transposition-free, note values auto-scaled; prints coverage and every difference
  with beat positions. `--pick` chooses one tune from a multi-tune ABC (Open Hymnal).
- `pd_audit.py chords <slug> <file> [same options]`: our chords against the harmony of a machine-readable multi-voice source
  (Open Hymnal ABC with all voices, Mutopia MIDI, MusicXML). Lines the melody up as `compare` does, then lists every chord
  of ours that no sounding sonority of the source fits within its span (root + third or a rootless 7th, bass in the chord,
  at most one foreign tone). A screen, not a verdict: check the listed chords by eye on the scan.
- `pd_audit.py check`: validates every audit file, lists melody files without one.
- `pd_audit.py summary [--album <album.md>]`: verdict counts by tier and every non-clean song with its fix; `--album` limits to
  the songs named in that album.
- `pd_audit.py dispute <slug>`: English dispute rationale from the audit (paste into YouTube Studio → Dispute → public domain).

## When a claim arrives

1. Find the song at the claimed time (album.md table / master json `start_s`).
2. `pd_audit.py dispute <slug>`; if the song is not `clean`, fix it before disputing and tell the PM.
3. Record the claim (song, claimant, date, dispute date, outcome) in `production/results.md`.
