# Yoto Audiobook + Icon Maker

A Claude Code plugin with two Yoto-focused skills.

`audiobook` turns a one-line premise into a finished, narrated children's
audiobook. Claude writes the book, reviews it through four specialist passes,
directs the read with audio tags, renders it through ElevenLabs v3, checks every
chunk against a local transcript, and masters the result to the ACX loudness
window. The output is a set of chapter MP3s you can load onto a Yoto player, a
phone, or any player that reads MP3.

`yoto-icon-maker` designs 16x16 pixel-art icons for the chapters or tracks of a
Yoto card, sized and judged for the player's physical display. The output is one
transparent PNG per track, a chapter-to-icon mapping, an enlarged preview sheet,
and a ZIP of the set.

Between them they cover both halves of a Yoto card: the audio and the track art.

## What to expect

You give a premise. Claude gives back a manuscript and a folder of mastered MP3s,
one per chapter, with a report of durations, levels, credits spent, and anything
the quality pass flagged.

The pipeline was built and calibrated on a 12-chapter, 14,440-word book rendered
to 13 MP3s and 91 minutes of audio. Those numbers set every threshold in the
skill: the 1,800-character chunk size, the 15 characters-per-second duration
predictor, the 1.10-second chunk seam, and the loudness targets.

One rule sits above the rest. **Claude never spends a credit before you say yes.**
Before any paid call, it runs a free cost estimate, shows you the chunk count,
the characters billed, the projected credits, your remaining balance, and the
balance after, then waits for a clear yes. Approving one book does not approve the
next one, and approving narration does not approve music or sound effects.

## Prerequisites

- Claude Code with plugin support.
- Python 3.9 or newer.

The `audiobook` skill also needs:

- An ElevenLabs account. The 192 kbps MP3 output needs the Creator tier or above.
- Two Python packages:
  ```bash
  pip install numpy openai-whisper
  ```
  `openai-whisper` pulls in PyTorch, so the first install is large and slow.
- `ffmpeg` and `curl` on your PATH:
  ```bash
  brew install ffmpeg
  ```

The `yoto-icon-maker` skill also needs the Pillow imaging library:

```bash
pip install pillow
```

## Set up your API key

The scripts read your ElevenLabs key from a file in your home directory. Create it
once, and keep it out of any repo:

```bash
printf '%s' 'YOUR_ELEVENLABS_API_KEY' > ~/.elevenlabs_key
chmod 600 ~/.elevenlabs_key
```

Replace `YOUR_ELEVENLABS_API_KEY` with your real key. Nothing in this plugin ever
prints the key or commits it. The `.gitignore` here also blocks `.elevenlabs_key`
and `*.key` so you cannot check one in by accident.

## Install

This repo is its own plugin marketplace, so two commands install it:

```bash
/plugin marketplace add danMateer/yoto-audiobook-claude-plugin
/plugin install yoto-audiobook@danmateer
```

To test a local copy before or instead of installing:

```bash
claude --plugin-dir /path/to/yoto-audiobook-claude-plugin
```

Run `/reload-plugins` after editing any file in a local copy.

## Prompting the audiobook skill

The argument is the premise. Invoke the skill by name, or just ask Claude for an
audiobook and it activates on its own.

```
/yoto-audiobook:audiobook a shy tugboat learns she is stronger than the big ships
```

```
/yoto-audiobook:audiobook three raccoons open a midnight bakery, and a health inspector visits
```

```
/yoto-audiobook:audiobook a lighthouse keeper's cat is afraid of water until the night of the big storm
```

Plain requests work too: "Write me an audiobook about a dragon who collects lost
socks, for a 6-year-old." Claude restates the premise as a one-paragraph brief and
confirms a few things before it writes 14,000 words, so answer those and the rest
runs on its own up to the spend gate.

### Get the brief right

The questions Claude asks at the start are the ones that cost a whole draft if you
skip them. Have answers ready for:

- **The cast.** If you want established or recurring characters, name their voices
  and quirks. A reader who knows a character catches a wrong line instantly.
- **The age band.** A book for a 5-year-old reads differently at the sentence level
  from one for an 8-year-old.
- **Older listeners in the room.** Say whether you want a few jokes that land for a
  parent or an older sibling. The skill layers them so they still play as pure
  silliness for the youngest listener.
- **The emotional throughline.** One character learns one thing. Say who, and what.

## Tips

- **Render one chapter before committing to a voice.** ElevenLabs voices differ in
  emotional range and in speaking rate. Pick a voice with wide range for a book
  with lots of shouting or whispering, and listen to a single chapter first. The
  reference book's voice ran near 158 words per minute; another voice ran 141, so
  a script sized for 15 minutes came out at 18.
- **Trust the gate, and read the estimate.** The `estimate.py --balance` numbers are
  measured, not guessed. If the projected credits plus the 15% retry headroom
  exceed your balance, the estimate warns you before you approve.
- **Let the quality pass adjudicate itself.** The local transcript check produces
  false alarms that look exactly like real failures. It re-transcribes disputed
  windows and marks each flag adjudicated or real. Read `references/qc.md` before
  acting on a flag.
- **Listen to about ten minutes by ear.** The automation proves the words are all
  there, in order, at the right level, with no audio tag spoken aloud. It proves
  nothing about whether the performance is good. Listen to the first and last
  chunk, one chapter seam, the emotional climax, and every whispered span.
- **Keep music out of the body.** ACX allows background music only in opening and
  closing credits, and ElevenLabs' own licensing tiers do not name audiobooks. The
  skill keeps narration clean by default.

## What it costs

ElevenLabs v3 bills a flat 0.550 credits per character on the API, tags included.
The reference book, roughly 14,000 words and about 80,000 characters, billed close
to 44,000 credits in its render. Your dollar cost depends on your plan, so check
your tier. The estimate step shows the exact projected credits for your book
before you commit.

## What it will not do

- **It does not submit to ACX or any store.** ACX bans unauthorized synthetic
  narration. Hitting the ACX loudness spec is a craft target for a clean master,
  not a submission path. The artist tag is marked as synthetic narration.
- **It does not clone or impersonate a real person's voice.** Use an ElevenLabs
  library voice or a voice you are entitled to use.
- **It does not guarantee a perfect performance.** It guarantees the text is intact
  and the levels are right. The listen-by-ear step is yours.

## What the audiobook gives you, on disk

```
<bookdir>/
  <title>.md              the manuscript
  book.json               render and metadata config
  text/NN_slug.txt        one file per chapter, 00 is the intro
  tagged/NN_*_tagged.txt  the tagged read, written by apply_tags.py
  tags.json               the tag plan
  audio/chNN/             per-chunk mp3, alignment, text, and a manifest
  audio/qc_whisper.json   the transcript quality report
  audio/master_manifest.json
  mp3/                    the deliverable
```

## Using the icon maker

Invoke the icon skill by name, or hand Claude a book, chapter list, manuscript,
or existing icon set and ask for Yoto icons.

```
/yoto-audiobook:yoto-icon-maker make chapter icons for this 12-chapter manuscript
```

```
/yoto-audiobook:yoto-icon-maker one icon for a story about a shy tugboat, her face against the harbor
```

Claude reads each chapter for its distinctive beat, picks one unmistakable motif
per track (a character face, a landmark, or a single object), holds one visual
system across the set, and resolves each icon onto the 16x16 grid with
nearest-neighbor scaling. It judges every icon at actual size against black,
since a 16x16 icon that only reads in an enlarged preview fails on the device.

The skill directs an image-generation tool to make clean pixel-art source, then
fits and validates that source with the bundled script. If Claude has no image
generator in your setup, supply your own source art and the skill will resolve
and check it.

The `yoto_icon.py` helper does the deterministic work: `prepare` fits a
transparent source onto a 16x16 canvas, `validate` checks size, mode, and real
transparency, and `preview` builds a labeled contact sheet. It makes no artistic
decisions and calls no external service, so this skill spends nothing and needs
no API key.

You get one 16x16 RGBA PNG per track with zero-padded filenames, a
chapter-to-icon mapping, an enlarged preview sheet, and a ZIP of the set. Ask for
a single icon and you get the PNG and one preview instead.

## Provenance

This packages two personal Claude skills for sharing. The skill files under
`skills/audiobook/` and `skills/yoto-icon-maker/` are unchanged from their
originals, except that the script invocation paths in each `SKILL.md` now use
`${CLAUDE_PLUGIN_ROOT}` so they resolve wherever the plugin installs, and each
gained a short setup note near the top. The audiobook reference files record
which API claims are measured, which are documented by ElevenLabs, and which come
from practitioner reports, so you can weigh each one.

## License

MIT. See [LICENSE](LICENSE).
