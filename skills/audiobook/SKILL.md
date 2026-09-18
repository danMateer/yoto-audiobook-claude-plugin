---
name: audiobook
description: Write an original multi-chapter children's book from a one-line premise and produce it as a narrated audiobook through ElevenLabs v3. Use when the user asks for an audiobook, a story rendered to audio, or invokes /audiobook with a premise. Covers manuscript drafting, specialist review passes, audio-tag direction, rendering, transcript QC, and mastering. Contains a mandatory spend-confirmation gate before any paid API call.
---

# Audiobook

Turn a premise into a finished narrated audiobook. Built and proven on a 12-chapter,
14,440-word book rendered to 13 MP3s in 91 minutes of audio, with the numbers from
that run used to calibrate every threshold here.

The argument to the skill is the premise. `/audiobook Rapunzel and the Tangled cast
have a holiday party` means: write that book, then produce it.

## Running the bundled scripts

The Python scripts ship inside this plugin. In the commands below,
`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's install directory when this file
loads, so the paths work wherever the plugin is installed. If you copied the scripts
somewhere else, point the commands at that directory instead.

The scripts need Python 3 with `numpy` and `openai-whisper`, plus `ffmpeg` and `curl`
on your PATH. Store your ElevenLabs API key in a file at `~/.elevenlabs_key`. The
README covers setup.

## The gate

**Never call a credit-spending ElevenLabs endpoint before the user has confirmed the
spend in this conversation.** This is the one rule in the skill that has no
exceptions and no judgment call attached.

Spends credits: `POST /v1/text-to-speech/*`, `POST /v1/music`,
`POST /v1/sound-generation`.
Spends nothing: `GET /v1/user/subscription`, `POST /v1/pronunciation-dictionaries/*`,
and every local script here except `render.py`.

At the gate, run `estimate.py --balance` and put its real numbers in front of the
user through AskUserQuestion: chunk count, characters billed, projected credits,
their remaining balance, and the balance after. Then wait. Approval for one book is
not approval for the next one, and approval to render is not approval to also
generate music or sound effects.

The API key lives at `~/.elevenlabs_key`. Read it only inside a request, never echo
it, never print a response body that could contain it. `GET /v1/user` returns the key
itself in an `xi_api_key` field, which is why the balance check uses
`/v1/user/subscription` instead.

## Phases

Work through these in order. Each one has a reference file with the detail.

### 1. Confirm the brief

Restate the premise as a one-paragraph brief and get agreement before drafting
14,000 words. Settle: cast and their established voices, the age band, the emotional
throughline, chapter count, and whether the user wants elevated jokes layered in for
older listeners. See `references/story-craft.md` for the questions that matter and
the ones you can decide yourself.

Established characters carry constraints a reader will notice instantly. Get the
verbal tics and the relationships right in the brief, not in revision.

### 2. Draft the manuscript

Write it as one Markdown file, chapter headings numbered, roughly 1,200 words a
chapter. `references/story-craft.md` holds the structural pattern: what carries the
emotional line, where the humor sits, how the moral stays unspoken, and how the two
audience bands get served in the same sentence.

### 3. Review passes

Four specialist reviewers in parallel, then generalist passes until the prose reads
fluidly. Reviewer briefs are in `references/story-craft.md`. Reviewers read; you
revise. Keep revising until a fresh read turns up nothing structural.

### 4. Split to chapter files

One `.txt` per chapter under `text/`, named `NN_slug.txt`, `00` for the intro. The
intro is the only file you write rather than extract: a short framing paragraph in
the narrator's voice.

Then write `book.json` at the project root:

```json
{
  "title": "Album title as listeners will see it",
  "narrator": "ElevenLabs v3 <VoiceName> (synthetic narration)",
  "voice_id": "<voice id>",
  "model": "eleven_v3",
  "stability": 0.5,
  "output_format": "mp3_44100_192",
  "seed_base": 40000,
  "seam": 1.10,
  "head": 0.60,
  "tail": 1.50,
  "dictionary": []
}
```

### 5. Direct the read with audio tags

This is where a flat narration becomes a performance, and it is the phase most worth
slowing down for. Read `references/tagging.md` in full before writing a single tag.

Build a plan file mapping each chapter filename to `[anchor, tag]` pairs, where the
anchor is a verbatim substring that appears exactly once, then:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/apply_tags.py --root <bookdir> --plan tags.json
```

It writes nothing unless every anchor matched exactly once and the tagged text
reduces back to the source byte for byte. An anchor with zero matches means you
mistyped it; two matches means the tag would land somewhere you did not intend. Both
are silent corruption, which is why they are assertions rather than warnings.

### 6. Optional: a pronunciation dictionary

Invented names, dialect spellings, and anything a general-purpose model will
mispronounce. Creating a dictionary costs no credits. See
`references/elevenlabs-api.md`.

### 7. The gate

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/estimate.py --root <bookdir> --balance
```

For the exact per-chapter plan the renderer will execute, add a dry run. It never
reads the key and returns before a single request is built:

```bash
python3 -u ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/render.py --root <bookdir> --dry-run
```

Then ask, with those numbers, and wait for a clear yes.

### 8. Render

Only after approval:

```bash
python3 -u ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/render.py --root <bookdir>
```

Concurrency 5, two inline assertions per chunk, three seed attempts. Use `-u`, since
Python buffers stdout when you redirect it and you will otherwise watch an empty log
for ten minutes. `--only 03,04` re-renders specific chapters.

### 9. QC

```bash
python3 -u ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/qc_whisper.py --root <bookdir>
```

Local whisper, no API call. It transcribes every chunk, diffs against the exact text
submitted, and auto-adjudicates its own false positives by re-transcribing disputed
time windows in isolation. Exit code 1 means a real defect, or that it found nothing
to check, which is not a pass. Read `references/qc.md` before acting on any flag: the
three known artifact classes are documented there and all of them look like real
failures at first.

### 10. Assemble and master

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audiobook/scripts/assemble.py --root <bookdir>
```

Measured seams, analytic gain, one encode, ID3v2.3. Exit code 1 means a file fell
outside the ACX loudness window or a seam became the longest pause in its chapter.

### 11. Report

Give the user the file list with durations and levels, the credits spent against the
estimate, and anything the QC pass flagged and how it resolved. Say plainly what you
did not verify by ear.

## Layout

```
<bookdir>/
  <title>.md              the manuscript
  book.json               render and metadata config
  text/NN_slug.txt        one file per chapter, 00 is the intro
  tagged/NN_*_tagged.txt  written by apply_tags.py
  tags.json               the tag plan
  audio/chNN/             chunk mp3 + align json + chunk txt + manifest
  audio/qc_whisper.json   transcript QC report
  audio/master_manifest.json
  mp3/                    the deliverable
```

## Things that will bite you

- **ffmpeg `-v error` hides `silencedetect` output**, which logs at info level. Use a
  numpy RMS envelope for silence work, as the scripts here do.
- **The Bash tool's working directory persists between calls.** One `cd` breaks every
  later relative path in ways that look like missing data. Use absolute paths.
- **`\bIT\b` matches the `IT` inside `IT'S`**, because an apostrophe is a word
  boundary. `\bIT\b(?!')` is the pattern you wanted.
- **Truncation returns HTTP 200 with short audio.** Checking status codes is not
  checking for truncation. That is what assertion 1 in `render.py` is for.
- **Do not re-encode when only metadata changes.** `-c copy` rewrites tags and leaves
  the audio bit-identical.
- **A wrong ID3 track number is silent.** Players sort monotonically, so bad
  numbering never sounds wrong. It cost a shipped album a `14/13`. The assembler
  asserts the range now.
- **Two files sharing a two-digit prefix wreck the run quietly.** Every script reads
  the chapter number from the first two characters of the filename, so a leftover
  `12_old.txt` beside `12_chapter-twelve.txt` renders that chapter twice into the
  same directory and inflates the track total. `lib_pack.chapters()` refuses, and all
  three scripts route their file discovery through it.
- **A run that finds nothing exits 1, not 0.** Both `qc_whisper.py` and
  `assemble.py` treat an empty audio directory as a failure, because "0 chunks
  checked" printed next to a zero exit code reads exactly like a pass.

## References

- `references/story-craft.md` - brief, structure, dual-audience humor, reviewer briefs
- `references/elevenlabs-api.md` - measured API behavior, billing, what v3 rejects
- `references/tagging.md` - audio tag rules, sourced and separated by confidence
- `references/qc.md` - the QC method, the three artifact classes, one retired assertion
