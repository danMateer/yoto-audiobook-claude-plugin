#!/usr/bin/env python3
"""Render tagged chapters through ElevenLabs v3 at concurrency 5.

RUN THIS ONLY AFTER THE USER HAS CONFIRMED THE SPEND. It is the one script here
that consumes credits.

Two assertions run inline on every chunk, both aimed at the documented
HTTP-200-with-short-audio truncation bug:

  1. alignment.characters round-trips the submitted text exactly
  2. duration is within 15% of characters/15.0

A chunk failing either re-renders on a fresh seed, up to 3 attempts. The transcript
coverage check (dropped words, tags spoken aloud) runs separately in qc_whisper.py
because it needs local ASR and no API call.

Alongside each chunkNN.mp3 this writes chunkNN.txt (the exact text submitted) and
alignNN.json (the per-character alignment). Both are load-bearing later: qc_whisper
reads the .txt rather than re-deriving the packing, and the alignment is the only
way to adjudicate a false QC flag by re-transcribing a disputed time window.

Usage:
  render.py --root <bookdir> [--only 03,04] [--dry-run]
"""
import argparse
import base64
import concurrent.futures as cf
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_pack import pack, chapters  # noqa: E402

BASE = "https://api.elevenlabs.io/v1"
CPS = 15.0
ATTEMPTS = 3
WORKERS = 5     # header-confirmed ceiling for v3


def load_cfg(root):
    cfg = json.loads((root / "book.json").read_text())
    cfg.setdefault("model", "eleven_v3")
    cfg.setdefault("stability", 0.5)
    cfg.setdefault("output_format", "mp3_44100_192")
    cfg.setdefault("seed_base", 40000)
    cfg.setdefault("dictionary", [])
    if not cfg.get("voice_id"):
        raise SystemExit("book.json needs a voice_id")
    return cfg


def tts(text, seed, hdr_path, cfg, key):
    body = {"text": text, "model_id": cfg["model"], "language_code": "en",
            "seed": seed, "voice_settings": {"stability": cfg["stability"]},
            "apply_text_normalization": "auto"}
    if cfg["dictionary"]:
        body["pronunciation_dictionary_locators"] = cfg["dictionary"]
    url = (f"{BASE}/text-to-speech/{cfg['voice_id']}/with-timestamps"
           f"?output_format={cfg['output_format']}")
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", "-H", f"xi-api-key: {key}",
         "-H", "Content-Type: application/json", "-d", json.dumps(body),
         "-D", hdr_path, url],
        capture_output=True, check=True)
    return r.stdout


def inline_qc(text, align):
    ch = align["characters"]
    ends = align["character_end_times_seconds"]
    dur = ends[-1] if ends else 0.0
    issues = []
    if "".join(ch) != text:
        issues.append(f"TRUNCATION: alignment {len(ch)} chars vs {len(text)} submitted")
    expected = len(text) / CPS
    if dur < 0.85 * expected:
        issues.append(f"SHORT AUDIO: {dur:.1f}s vs {expected:.1f}s expected")
    return dur, issues


def render_chunk(job):
    (num, idx), text, out_dir, base_seed, cfg, key = job
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / f"chunk{idx:02d}.mp3"
    hdr = f"/tmp/abhdr_{num}_{idx}.txt"

    for attempt in range(ATTEMPTS):
        seed = base_seed + 1000 * attempt
        raw = tts(text, seed, hdr, cfg, key)
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            time.sleep(3 + 5 * attempt)
            continue
        if "audio_base64" not in d:
            err = json.dumps(d)[:200]
            if "system_busy" in err or "too_many" in err:
                time.sleep(5 + 10 * attempt)
                continue
            return {"id": (num, idx), "error": err, "seed": seed}

        dur, issues = inline_qc(text, d["alignment"])
        cost = 0
        for line in pathlib.Path(hdr).read_text(errors="replace").splitlines():
            if line.lower().startswith("character-cost:"):
                cost = int(line.split(":", 1)[1].strip())

        if not issues or attempt == ATTEMPTS - 1:
            mp3.write_bytes(base64.b64decode(d["audio_base64"]))
            (out_dir / f"align{idx:02d}.json").write_text(json.dumps(d["alignment"]))
            (out_dir / f"chunk{idx:02d}.txt").write_text(text)
            return {"id": (num, idx), "chunk": idx, "seed": seed,
                    "attempt": attempt + 1, "chars": len(text),
                    "duration_s": round(dur, 2), "cost": cost,
                    "issues": issues, "file": mp3.name}
        print(f"  ch{num:02d} chunk{idx:02d} attempt {attempt+1} failed: {issues}"
              f" -> new seed", flush=True)
    return {"id": (num, idx), "error": "exhausted attempts"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--only", help="comma-separated chapter numbers, e.g. 00,03")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    cfg = load_cfg(root)
    # Read the key only when something is actually going to be sent, so a dry run
    # is provably incapable of spending and works on a machine without the key.
    key = ("" if args.dry_run
           else pathlib.Path(os.path.expanduser("~/.elevenlabs_key")).read_text().strip())

    keep = {int(s) for s in args.only.split(",")} if args.only else None
    try:
        found = chapters(root / "tagged", "*_tagged.txt")
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    files = [(n, f) for n, f in found if keep is None or n in keep]
    if not files:
        print(f"nothing to render from {root/'tagged'}", file=sys.stderr)
        return 1

    jobs, plan = [], []
    for num, f in files:
        chunks = pack(f.read_text())
        out_dir = root / "audio" / f"ch{num:02d}"
        sizes = [len(c) for c in chunks]
        plan.append((num, sum(sizes), len(chunks), min(sizes), max(sizes)))
        for i, c in enumerate(chunks, 1):
            jobs.append(((num, i), c, out_dir,
                         cfg["seed_base"] + num * 100 + i, cfg, key))

    total_chars = sum(p[1] for p in plan)
    print(f"{'ch':>3} {'chars':>7} {'chunks':>7} {'min':>6} {'max':>6}")
    for num, ch, n, lo, hi in plan:
        print(f"{num:>3} {ch:>7} {n:>7} {lo:>6} {hi:>6}")
    print(f"\n{len(jobs)} chunks, {total_chars:,} chars, "
          f"~{int(total_chars * 0.55):,} credits\n", flush=True)

    if args.dry_run:
        print("dry run, nothing sent")
        return 0

    results = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(render_chunk, jobs):
            results.append(r)
            num, idx = r["id"]
            if "error" in r:
                print(f"ch{num:02d} chunk{idx:02d}  ERROR {r['error']}", flush=True)
            else:
                flag = "OK" if not r["issues"] else "FAIL"
                print(f"ch{num:02d} chunk{idx:02d}  {r['chars']:5d}ch "
                      f"{r['duration_s']:6.1f}s  {r['cost']:5d}cr  seed {r['seed']} "
                      f"try{r['attempt']}  [{flag}]", flush=True)
                for it in r["issues"]:
                    print(f"      !! {it}", flush=True)

    by_ch = {}
    for r in results:
        by_ch.setdefault(r["id"][0], []).append(r)
    for num, rs in by_ch.items():
        rs.sort(key=lambda x: x["id"][1])
        d = root / "audio" / f"ch{num:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.json").write_text(json.dumps(
            [{k: v for k, v in r.items() if k != "id"} for r in rs], indent=2))

    ok = [r for r in results if "error" not in r]
    print(f"\n{len(ok)}/{len(results)} chunks rendered")
    print(f"credits spent  {sum(r['cost'] for r in ok):,}")
    print(f"audio          {sum(r['duration_s'] for r in ok)/60:.1f} min")
    bad = [r for r in results if r.get("issues") or "error" in r]
    print(f"unresolved after {ATTEMPTS} attempts: {len(bad)}")
    for r in bad:
        print(f"  ch{r['id'][0]:02d} chunk{r['id'][1]:02d} "
              f"{r.get('issues') or r.get('error')}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
