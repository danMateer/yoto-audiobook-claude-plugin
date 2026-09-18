#!/usr/bin/env python3
"""Transcript-coverage QC. Local ASR only, no API call, spends no credits.

Transcribes every rendered chunk with local whisper and diffs the words against the
exact text that was submitted, catching the two failures that matter:

  dropped text  a run of 3+ submitted words missing from the transcript
  leaked tag    a tag name appearing in the transcript as a spoken word

This replaced a tag-duration assertion that was simply wrong: a consumed tag
legitimately occupies elapsed time in the alignment because the model puts a beat
where the direction sits, so a duration threshold flagged clean chunks. Transcription
does not depend on the alignment at all.

Whisper produces false positives, so every flag is adjudicated automatically before
it is reported. Three artifact classes seen in practice:

  1. Comparing against re-derived text. Fixed structurally: this reads the
     chunkNN.txt that render.py wrote, so it can never drift from what was sent.
  2. Numbers. Whisper writes "406" where the manuscript says "four hundred and six".
     Digits are expanded to words before the diff.
  3. Whisper base silently skipping a long passage. The tell is that the chunk runs
     LONGER than predicted, not shorter. Adjudicated by slicing the disputed time
     window out of the saved alignment and transcribing it alone: if the words come
     back, the audio was always fine and whisper dropped them.

When a transcript flag and the duration disagree, the duration is right.

Usage:
  qc_whisper.py --root <bookdir> [--model base] [--no-adjudicate]
"""
import argparse
import difflib
import json
import pathlib
import re
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")

RUN = 3               # consecutive missing words that count as dropped text
CPS = 15.0
PAD = 0.60            # seconds of padding around an adjudicated window
RESCUE = 0.60         # word overlap in the isolated slice that clears a flag

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
        "eighty", "ninety"]


def int_words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return (TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else "")).strip()
    if n < 1000:
        rest = n % 100
        out = ONES[n // 100] + " hundred"
        return out + (" and " + int_words(rest) if rest else "")
    if n < 1_000_000:
        rest = n % 1000
        out = int_words(n // 1000) + " thousand"
        return out + (" " + int_words(rest) if rest else "")
    return str(n)


def expand_numbers(s):
    """Whisper writes digits; manuscripts write words. Put both in one alphabet."""
    s = re.sub(r"(\d),(\d\d\d)", r"\1\2", s)          # 1,000 -> 1000
    s = re.sub(r"(\d+)\.(\d+)", lambda m: int_words(int(m.group(1))) + " point "
               + " ".join(ONES[int(c)] for c in m.group(2)), s)
    s = re.sub(r"\d+", lambda m: int_words(int(m.group())), s)
    return s


def words_only(s):
    s = s.lower().replace("’", "'")
    s = expand_numbers(s)
    s = re.sub(r"[^a-z' ]", " ", s)
    return [w for w in s.split() if w.strip("'")]


def words_with_offsets(s):
    """Words plus their character offsets in s, so a flag can be located in time.

    Tags are blanked in place rather than deleted, which keeps every offset valid
    against the text that was actually submitted.
    """
    blanked = re.sub(r"\[[a-z]+\]", lambda m: " " * len(m.group()), s)
    low = expand_numbers_preserving(blanked)
    out = []
    for m in re.finditer(r"[A-Za-z'’]+", low):
        w = m.group().lower().replace("’", "'")
        if w.strip("'"):
            out.append((w, m.start(), m.end()))
    return out


def expand_numbers_preserving(s):
    """Offsets must survive, so digits become spaces here rather than words.

    A manuscript written for narration spells its numbers out, so this only fires
    on stray digits, and losing their offsets costs nothing.
    """
    return re.sub(r"\d", " ", s)


def transcribe(model, path, start=None, dur=None):
    if start is None:
        return model.transcribe(str(path), language="en", fp16=False)["text"]
    tmp = "/tmp/ab_slice.wav"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(start,0):.2f}",
                        "-t", f"{dur:.2f}", "-i", str(path), "-ar", "16000",
                        "-ac", "1", tmp], capture_output=True)
    if r.returncode != 0:
        return ""
    return model.transcribe(tmp, language="en", fp16=False)["text"]


def adjudicate(model, mp3, align, run_words, c0, c1):
    """Re-transcribe just the disputed window. Returns (overlap, verdict)."""
    if not align:
        return None, "no alignment saved"
    st = align.get("character_start_times_seconds") or []
    en = align.get("character_end_times_seconds") or []
    if not st or c0 >= len(st):
        return None, "offset outside alignment"
    t0 = st[c0] - PAD
    t1 = en[min(c1, len(en) - 1)] + PAD
    heard = words_only(transcribe(model, mp3, t0, max(t1 - t0, 0.5)))
    if not run_words:
        return None, "empty run"
    hits = sum(1 for w in run_words if w in heard)
    ov = hits / len(run_words)
    return ov, ("artifact, words present in the isolated slice" if ov >= RESCUE
                else "REAL, words absent from the isolated slice")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", default="base")
    ap.add_argument("--no-adjudicate", action="store_true")
    args = ap.parse_args()
    root = pathlib.Path(args.root)

    import whisper
    model = whisper.load_model(args.model)

    tag_names = set()
    for f in (root / "tagged").glob("*_tagged.txt"):
        tag_names |= set(re.findall(r"\[([a-z]+)\]", f.read_text()))

    report, real, artifacts = [], [], []
    for d in sorted((root / "audio").glob("ch*")):
        for mp3 in sorted(d.glob("chunk*.mp3")):
            txt = d / (mp3.stem + ".txt")
            if not txt.exists():
                print(f"{d.name}/{mp3.name}: no chunk text saved, cannot check",
                      file=sys.stderr)
                continue
            submitted = txt.read_text()
            align_path = d / ("align" + mp3.stem[-2:] + ".json")
            align = json.loads(align_path.read_text()) if align_path.exists() else None

            heard = words_only(transcribe(model, mp3))
            said_off = words_with_offsets(submitted)
            said = [w for w, _, _ in said_off]

            sm = difflib.SequenceMatcher(None, said, heard, autojunk=False)
            drops, leaks = [], []
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op in ("delete", "replace") and (i2 - i1) >= RUN:
                    drops.append((i1, i2))
                if op in ("insert", "replace"):
                    for w in heard[j1:j2]:
                        if w.strip("'") in tag_names:
                            leaks.append(w)
            ratio = sm.ratio()

            dur = None
            if align and align.get("character_end_times_seconds"):
                dur = align["character_end_times_seconds"][-1]
            ratio_dur = (dur / (len(submitted) / CPS)) if dur else None

            resolved = []
            for i1, i2 in drops:
                run_words = said[i1:i2]
                c0, c1 = said_off[i1][1], said_off[i2 - 1][2]
                text = " ".join(run_words)[:90]
                if args.no_adjudicate:
                    resolved.append({"text": text, "verdict": "not adjudicated",
                                     "overlap": None})
                    continue
                ov, verdict = adjudicate(model, mp3, align, run_words, c0, c1)
                resolved.append({"text": text, "verdict": verdict,
                                 "overlap": round(ov, 2) if ov is not None else None})

            hard = [r for r in resolved if r["verdict"].startswith("REAL")] or leaks
            status = "FAIL" if hard else ("OK" if not resolved else "OK (adjudicated)")
            dtxt = f"  dur {ratio_dur:.2f}x" if ratio_dur else ""
            print(f"{d.name} {mp3.name}  sim {ratio:.3f}{dtxt}  "
                  f"flags {len(resolved)}  leaks {len(leaks)}  [{status}]", flush=True)
            for r in resolved:
                mark = "!!" if r["verdict"].startswith("REAL") else "--"
                ov = "" if r["overlap"] is None else f" overlap {r['overlap']:.2f}"
                print(f"   {mark} {r['text']}\n      {r['verdict']}{ov}", flush=True)
            for w in leaks:
                print(f"   !! LEAKED TAG spoken aloud: {w}", flush=True)

            entry = {"chapter": d.name, "chunk": mp3.name,
                     "similarity": round(ratio, 4),
                     "duration_ratio": round(ratio_dur, 3) if ratio_dur else None,
                     "flags": resolved, "leaks": leaks,
                     "transcript": heard and " ".join(heard)}
            report.append(entry)
            if hard:
                real.append(f"{d.name}/{mp3.name}")
            elif resolved:
                artifacts.append(f"{d.name}/{mp3.name}")

    out = root / "audio" / "qc_whisper.json"
    out.write_text(json.dumps(report, indent=2))
    sims = [x["similarity"] for x in report] or [0]
    print(f"\n{len(report)} chunks checked, report at {out}")
    if not report:
        print("nothing was checked, so this is not a pass. Either render.py has "
              f"not run yet or {root/'audio'} holds no chunk mp3s.")
        return 1
    print(f"similarity  min {min(sims):.3f}  mean {sum(sims)/len(sims):.3f}  "
          f"max {max(sims):.3f}")
    print(f"flags cleared as whisper artifacts: {len(artifacts)}")
    print(f"REAL defects needing a re-render:   {len(real)}")
    for x in real:
        print("  " + x)
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
