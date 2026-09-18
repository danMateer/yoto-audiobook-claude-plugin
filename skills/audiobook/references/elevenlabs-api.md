# ElevenLabs v3 API, as measured

Claims are marked **[measured]** on a live account, **[documented]** from ElevenLabs,
or **[community]** from practitioner reports. They disagree in places, which is why
they are kept apart. Measurements come from a 54-chunk, 79,558-character render in
August 2026.

## Billing

**[measured] v3 bills 0.550 credits per character on the API.** The docs say only that
API generations are "discounted" and never publish the figure. The `character-cost`
response header does, and it read identically at 925 and 1,976 characters, so it is a
flat 45% discount rather than a tier or a floor.

**[documented] Tags bill as characters.** "Tags, SSML and audio tags are counted as
part of the character count for the request." That sentence lives in one help-center
article missing from the docs mirror, which is why a docs-only search concludes the
question is unanswered. The same article notes pronunciation dictionaries can also
move the count.

Check the balance with `GET /v1/user/subscription`. Do not use `GET /v1/user`: it
returns the API key in an `xi_api_key` field.

## What v3 accepts and rejects

**[measured] Only `stability` is honored.** `ElevenV3VoiceSettings` takes a float from
0.0 to 1.0, default 0.5. No `speed`, no `similarity_boost`, no `style`. Sending them is
not an error, they simply do nothing.

**[measured] Request stitching is rejected.** `previous_text` and `next_text` return
`"code": "unsupported_model"`. Chunk seams get real generated silence instead.

**[documented] `<break>` is unsupported** and gets read literally, and break tags are
trimmed at generation edges regardless. Pauses between chunks have to be silence you
generate yourself.

**[measured] Concurrency ceiling is 5**, from the `maximum-concurrent-requests` header,
which resolves a gap in the published table.

**[measured] `mp3_44100_192` needs Creator tier or above.**

## The endpoint to use

`POST /v1/text-to-speech/{voice_id}/with-timestamps` returns `audio_base64` plus
`alignment{characters, character_start_times_seconds, character_end_times_seconds}`.
**It costs nothing over a plain convert**; the `character-cost` header reads the same
on both.

Always use it, and always save the alignment. Two reasons:

1. Joining `alignment.characters` and comparing to the submitted text is the only
   reliable truncation check.
2. Per-character timestamps are accurate enough to slice a disputed passage out of the
   finished audio and re-transcribe it, which is how a false QC flag gets settled.
   Proven by extracting a 60-word passage from its window and getting it back at 1.00
   word overlap.

Request body that worked:

```json
{
  "text": "<chunk>",
  "model_id": "eleven_v3",
  "language_code": "en",
  "seed": 40301,
  "voice_settings": {"stability": 0.5},
  "apply_text_normalization": "auto",
  "pronunciation_dictionary_locators": []
}
```

Record the seed per chunk. Any second of the book is then reproducible.

## Chunking at 1,800 characters

Four independent reasons converge on this number.

- **[documented]** The hard cap is 5,000 characters, but staff reported truncation at
  as few as 1,766, so the cap is not the working limit.
- **[measured]** Speaking rate is 14.9 to 15.1 characters per second, stable across
  sizes. 1,800 characters runs about 120 seconds, and the reported truncation bug bites
  around three minutes, so every chunk lands under it by design.
- **[community]** Longer surrounding text reduces tag leakage: "if you make the
  passages to be longer, it is usually going to contain enough context." This pushes
  against the instinct to split small.
- **[measured]** Alignment stayed intact at 1,976 characters, round-tripping the input
  exactly with monotonic timestamps. A reported alignment collapse above 250 characters
  did not reproduce.

The 15.0 characters-per-second figure is also the duration predictor the QC pass needs.

**Pack balanced, not greedy.** A greedy packer leaves a stub chunk at the end of a
chapter, which wastes a seam and gives the model almost no context. Aim every chunk at
`total/n` and absorb runts into a neighbour. `lib_pack.py` does this and refuses to
split a paragraph.

## The truncation bug

**HTTP 200 with short audio.** Staff-confirmed, still open as of this writing
(`elevenlabs-python#649`). A pipeline that checks status codes ships a half-read
chapter and reports success. Two assertions catch it: alignment round-trip, and
duration against `characters / 15.0` with a 15% floor.

Across 54 chunks neither assertion ever fired, and the render came in between 0.95 and
1.08 of predicted duration. One clean run is not a reliability estimate; keep the
retry headroom in the budget.

## Pronunciation dictionaries

`POST /v1/pronunciation-dictionaries/add-from-rules`, attached as a single locator.
Creating one costs no credits.

**[documented]** Phoneme rules work on v3, first match wins, IPA is the safer alphabet.
Worth it for invented names and dialect spellings. Four rules covered a whole book:
one invented exclamation, one dialect word, one character catchphrase, one proper noun.

Attach as:

```json
[{"pronunciation_dictionary_id": "...", "version_id": "..."}]
```

## Music and sound effects

**[documented]** Sound effects bill 40 credits per second when you set
`duration_seconds`, and a flat 200 per generation when you leave it null. Music runs
900 credits per minute. `POST /v1/music/plan` returns a composition plan for free.

Both spend credits, so both need their own confirmation. **[documented]** ACX permits
background music in opening and closing credits only, never under body narration, and
an ambience bed counts toward the whole-file noise floor. **[documented]** Audiobooks
appear nowhere in ElevenLabs' music licensing tiers: not permitted, not prohibited,
and podcasts are named while audiobooks are not. That gap is a reason to keep music out
of the body.

## Mastering targets

ACX asks for -23 to -18 dB RMS with peaks under -3 dB. Compute the gain analytically
rather than compressing: take the gain the peak target implies, then clamp it if it
would push RMS outside the window. One volume change per chapter, no limiting, so a
shouted line keeps its dynamics. All 13 chapters of the reference book landed in-window
on the first pass.

ACX also bans unauthorized synthetic narration outright. Hitting their spec is craft,
not a submission path. Mark the artist tag as synthetic narration.

## Seams

**[measured] v3's own inter-paragraph pause runs 1.10 to 1.16 seconds**, across 57 such
gaps. Size chunk seams to match, or the join reads as a rushed beat against the natural
pauses on either side of it. A guessed 0.5s would have been audible.

Subtract the silence each chunk already carries at its edges from the target, floored
at 0.05s. Verify afterwards that no seam is the longest pause in its chapter: across
2,755 internal pauses in the reference book the median was 0.41s, the 90th percentile
0.99s, and the longest 1.59s, so no seam stood out.

**[documented] Concatenate with exactly one re-encode, never `-c copy`.** A mid-stream
LAME header makes players misreport duration. Assemble in float32 and pipe raw `f32le`
into ffmpeg, which gives one encode for the whole chapter. The exception is a
metadata-only change, where `-c copy` is correct and leaves the audio bit-identical.

## Unresolved

- `GET /v1/voices/{id}` returns 401 without the `voices_read` scope, so a voice's clone
  type and any owner-set credit multiplier cannot be checked. A measured 0.550 rate
  from a request on that voice already includes any multiplier.
- **[documented]** "Professional Voice Clones (PVCs) are currently not fully optimized
  for Eleven v3." The docs steer toward an Instant Voice Clone or a designed voice.
  **[community]** The guidance does not predict outcomes cleanly: one practitioner found
  a designed voice failed badly on v3 while their own professional clone worked well.
  Render one chapter and listen before committing to a voice for a whole book.
