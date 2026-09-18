# QC: catching failures a listener would otherwise catch by ear

Three checks, in the order they run. The first two are inline in `render.py` and cost
nothing extra. The third is local ASR and costs nothing at all.

## 1. Truncation

Join the returned `alignment.characters` and compare to the text submitted.

This catches the documented failure where ElevenLabs returns **HTTP 200 with short
audio**. Staff have confirmed it and it is still open. A pipeline that checks status
codes ships a half-read chapter and reports success.

## 2. Duration

Predict `characters / 15.0` seconds and flag any chunk more than 15% short. A second net
under the same bug, for the case where alignment reports text the audio does not
contain.

Across 54 chunks the render came in between 0.95 and 1.08 of prediction and neither
assertion fired. **Keep the duration ratio even when it passes**, because it is what
settles a disputed transcript flag later.

## 3. Transcript coverage

Transcribe every chunk with local whisper and diff the words against the exact text
submitted. A run of three or more submitted words missing from the transcript is dropped
text. A tag name appearing in the transcript as a spoken word is a leaked tag.

Compare against the `chunkNN.txt` that `render.py` saved, never against text you
re-derive from the manuscript. Re-deriving works until the packer changes, at which
point the diff compares audio against text that was never sent and every chunk after the
first divergence looks broken.

## The three artifact classes

Whisper produces false positives that look exactly like real failures. All three of these
appeared on a book with zero real defects.

| Class | Tell | Handling |
|---|---|---|
| Comparing against re-derived text | Similarity decaying chunk over chunk (0.857, 0.668, 0.462, 0.308), the signature of an accumulating offset | Structural: read the saved chunk text |
| Numbers | `four hundred and six` reported missing, whisper wrote "406" | Expand digits to words before the diff |
| Whisper skipping a long passage | **The chunk runs longer than predicted, not shorter** | Re-transcribe the isolated window |

The third one is the one that will fool you. A 60-word passage showed as entirely
dropped from a chunk that ran 1.08x longer than predicted, so nothing could have been
missing. Slicing that window out of the audio using the saved alignment and transcribing
it alone returned the passage at 1.00 word overlap.

**When a transcript flag and the duration disagree, the duration is right.**

`qc_whisper.py` handles all three automatically and reports each flag as adjudicated or
real. Its exit code is 1 only when something survives adjudication.

## The assertion that was wrong

Worth knowing about, because it is the obvious thing to build and it does not work.

The original design detected tag leakage by timing: sum the character durations inside
each `[tag]` span, and fail the chunk if the span runs over 0.15 seconds, on the theory
that a consumed tag takes no time while a spoken "shouts" takes half a second.

**It failed every clean chunk.** Measured spans on a verified-clean chapter:
`[annoyed]` 0.504s, `[excited]` 0.656s, `[shouts]` 0.446s. Whisper transcripts confirmed
none of them was spoken aloud.

A consumed tag legitimately occupies elapsed time, because the model puts a beat or a
breath where the direction sits. The 0.15s threshold came from a single earlier
`[shouts]` sample that measured 0.060s, and one sample is not a distribution.

A companion assertion went with it: flagging letters under 12ms as swallowed and over
0.20s as drawled. Transcript coverage catches dropped words directly and does not depend
on the alignment, so both timing tests were retired.

The lesson generalizes past this API. A metric that correlates with a failure in one
sample is not a discriminator. Test a proposed assertion against known-good output before
you trust it to gate anything.

## What to verify by ear anyway

The pipeline proves the words are all there, in the right order, with no tag spoken
aloud, at the right level. It proves nothing about whether the performance is good.

Listen to: the first and last chunk of the book, one chapter seam, the emotional climax,
and every `[whispers]` span. That is about ten minutes and it covers what the automation
cannot see.
