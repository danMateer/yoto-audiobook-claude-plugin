# Audio tags: directing the read

Tags are what separate a flat narration from a performance. They are also the single
most-reported v3 defect, because a tag the voice cannot perform gets spoken aloud as
a word. Both facts argue for the same thing: tag deliberately, then verify.

Claims are marked **[documented]** from ElevenLabs, or **[community]** from
practitioner reports, or **[measured]** from a 141-tag render.

## Find the lines that need direction

Two categories, and they are not the same job.

**Fully-uppercase sentences inside quotes.** These are the ones the author already
marked as loud. Sort them by closing punctuation, because caps alone are a weak
signal to the model:

| Ending | Treatment |
|---|---|
| `!` | Already carries the strongest lever. `[shouts]` on the loudest beats only. |
| `,` | Caps are doing all the work and doing it poorly. These get `[shouts]`. |
| `?` | `[shouts]` where the line is a demand, plain where it is a real question. |
| `.` | Hand-read every one. Several will not be shouts. |

That last row is where the craft is. `"NOTHING."` and `"WHAT."` from a furious
character are suppressed fury, not volume, and a shout tag flattens the joke. They get
`[deadpan]` or nothing at all.

**Single capitalized words inside otherwise lowercase sentences** (`a LOT of rain`, `a
PREMIUM pile of rocks`). These are emphasis on one word, not a raised voice. **They get
no tag.** Count them separately or your tag budget will be nonsense: the reference book
had 78 of the first kind and 89 of the second.

Count sentences, not quoted spans. A span can hold several sentences, and the thing you
are tagging is a sentence.

**[community]** A live test of whole-sentence caps got "maybe there's a slight
improvement," then "it's still not quite right" after regenerating. The same test found
the tag route decisive: "because we have this tag, it's usually going to be treated as
yelling even when it is not uppercase." Exclamation marks ranked second, narrative
context with quotation marks third.

## Rules

- **Emotion in front of the beat, breath behind it.** **[documented]** The enhance
  prompt allows either side: "immediately before the dialogue segment they modify or
  immediately after. (e.g., [annoyed] This is hard. or This is hard. [sighs])". A
  community claim that trailing tags do nothing contradicts the docs; follow the docs.
- **Lowercase, square brackets.** **[documented]** "Audio tags live inline with your
  script and are formatted with lowercase square brackets." **[community]** Round
  parentheses get read aloud, and one-word tags beat multi-word ones: `[giggling sound]`
  loses to `[giggles]`.
- **Stacking is allowed.** **[documented]** "You can combine multiple audio tags for
  complex emotional delivery," with a published example stacking two:
  `[overlapping] [annoyed]`. A widely-copied community skill file says otherwise; the
  documentation wins. Keep stacking rare anyway, and verify each stacked pair.
- **A tag decays after roughly 4 to 5 words.** **[documented]** "Each tag affects
  approximately the next 4-5 words of speech before returning to normal delivery."
  Published for `eleven_v3_conversational` inside Agents, with no base-model equivalent,
  so treat it as a hypothesis with teeth. A 14-word shouted run needs one tag per
  sentence, not one at the front.
- **Prefer tags from ElevenLabs' own documented list.** It covers more emotional range
  than a first read suggests: `[sheepishly]`, `[warmly]`, `[curious]`, `[dramatically]`,
  `[sympathetic]`, `[reassuring]`, `[delighted]`, `[amazed]`, `[deadpan]`, `[thoughtful]`,
  `[sadly]`, `[annoyed]`, `[excited]`, `[shouts]`, `[sighs]`, `[whispers]`, `[laughs]`,
  `[pause]`.
- **No stage directions.** `[grinning]`, `[pacing]`, `[to the sky]` get stripped or
  spoken. ElevenLabs' own enhancement prompt bans them.
- **Prose stays prose.** **[documented]** v3 will speak emotional direction written as
  narration, so "said the professor sadly" is a line to read, never a cue. If you tag
  the line, cut the adverb from the prose.
- **Ellipses stay exactly as written.** **[documented]** Ellipses add weight, and a beat
  like `"I GOT HIM! I GOT HIM! I GOT..."` needs it.
- **No preprocessing of the manuscript.** Resist rewriting text to help the model. One
  earlier version of this pipeline lowercased standalone `IT` tokens on the theory they
  drew a drawl; the evidence for the drawl came from an assertion since retired, most of
  those tokens sat inside fully-uppercase sentences where lowercasing one word just made
  the line inconsistent, and v3 read all of them correctly anyway. Send the tagged text
  unchanged.

## Density

Aim near one tag per 100 to 120 words. This is judgment, not a published limit.

**[documented]** No official maximum exists, and official copy runs the other way,
encouraging combination. The docs' single over-tagging warning covers SSML `<break>`,
which v3 does not support, so it does not transfer. **[community]** The only quantified
caution calls one-per-80 its default and warns that overstuffing gives "chaotic
delivery."

**[measured]** The reference book carried 141 tags across 14,440 words, one per 102
words, distributed:

| Tag | Count |
|---|---|
| `[shouts]` | 39 |
| `[deadpan]` | 23 |
| `[excited]` | 18 |
| `[warmly]` | 15 |
| `[delighted]` | 8 |
| `[amazed]` | 8 |
| `[sympathetic]` | 6 |
| `[annoyed]` | 5 |
| `[thoughtful]` | 4 |
| `[sadly]` | 4 |
| `[whispers]`, `[sighs]`, `[dramatically]` | 3 each |
| `[curious]`, `[reassuring]` | 1 each |

Zero leaked. Not one of the 141 was spoken aloud.

## Insert them safely

Two assertions, both in `apply_tags.py`, and nothing gets written unless both pass:

1. **Every anchor matches exactly once.** Zero means you mistyped the anchor. Two or
   more means the tag lands somewhere you did not intend. Both are silent corruption.
   This caught a real error on the reference book: an anchor beginning with a quotation
   mark that turned out to sit mid-quote.
2. **Stripping the tags back out reproduces the source byte for byte.** This catches an
   anchor that overlapped an earlier insertion.

## Why leakage should be low

**[documented]** ElevenLabs names one cause for a tag being spoken aloud, and it is not
tag count: "This typically occurs when the selected voice doesn't match the requested
delivery, such as a naturally soft-spoken voice being asked to perform several
`[shouts]`." Their fix is to "choose a voice with a wide emotional range for tag-heavy
scripts."

So pick the voice for range before tuning anything else. If you cannot read the voice's
metadata, measure instead: pitch spread in semitones over a passage containing the
book's loudest line. The reference voice measured 5.77 to 6.59 semitones against a
local TTS baseline of 4.67.

The failure is real and well attested when the match is wrong. An open ElevenLabs SDK
issue with no reply reports tags leaking as text, including a mangled `[warmlyly]`, and
one video's own demo produced "Sarcastically, not the burn it all down kind." Its
author's conclusion: "there is no proven way. There is no official mention from 11 to
fix this issue." Detection beats a fix that does not exist, which is what
`qc_whisper.py` is for.

**[community] Untested:** placing `[pause]` at the very start of a chunk reportedly
reduces leakage. `[pause]` is an official tag, so the probe costs seven characters and
risks nothing. Skipped on the reference book because nothing leaked without it.

## Findings to check by ear

**[measured] `[whispers]` did not lower the level.** Two whispered spans measured +1.37
and +1.07 dB against their chapter average and +0.72 dB against untagged dialogue. A
high-frequency-to-low-frequency ratio test came back -3.40 dB, pointing at less
breathiness rather than more. With n=2 per group there is no conclusion here, only a
flag: listen to your `[whispers]` spans before assuming the tag does what the word
implies.

## One lever usually worth leaving alone

**[documented]** ElevenLabs endorses one voice playing several roles through identity
tags: `[deep voice]`, `[childlike tone]`, `[pirate voice]`, and the claim that "what
used to require a full cast can now be scripted in a single voice track."

Ask before using it. A listener who wanted one narrator with acting range did not ask
for a one-person cast, and the two read very differently. The defensible middle is a
single identity tag on one character's set-piece speeches, where it reads as a
storyteller doing a voice rather than as a cast.
