#!/usr/bin/env python3
"""Join each chapter's chunks into one master, level it, encode once. No credits.

Seam sizing is measured, not guessed. v3's own inter-paragraph pause runs about
1.10s, so a chunk seam has to match that or the join reads as a rushed beat against
the natural pauses around it. Each chunk already carries some silence at its edges,
so the inserted gap is the target minus the silence the model supplied.

Levelling is analytic rather than compressed: take the gain the peak target implies,
then clamp it if it would push RMS outside the window. One volume change per
chapter, no limiting, so a shouted line keeps its dynamics.

Everything is assembled in float32 at 44.1k and piped to ffmpeg as raw f32le, which
means exactly one MP3 encode. Concatenating encoded files with -c copy leaves a
mid-stream LAME header and players misreport the duration.

Usage:
  assemble.py --root <bookdir> [--skip 01]
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lib_pack import chapters  # noqa: E402

SR = 44100
SIL_DB = -55.0            # below this a frame is silence
FRAME_SEC = 0.010
RMS_LO, RMS_HI = -23.0, -18.0     # ACX window
PEAK_MAX = -3.0


def decode(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path),
                        "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def envelope_db(a, frame):
    n = len(a) // frame
    if n == 0:
        return np.array([])
    frames = a[:n * frame].reshape(n, frame).astype(np.float64)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-20)
    return 20 * np.log10(rms)


def edge_silence(a, frame):
    e = envelope_db(a, frame)
    live = np.where(e > SIL_DB)[0]
    if len(live) == 0:
        return 0.0, 0.0
    return live[0] * frame / SR, (len(e) - 1 - live[-1]) * frame / SR


def internal_gaps(a, frame, min_sec=0.20):
    """Silence runs strictly inside the audio, in seconds. Used as a seam sanity check."""
    e = envelope_db(a, frame)
    quiet = e <= SIL_DB
    gaps, run = [], 0
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run and i - run > 0:
                gaps.append(run * frame / SR)
            run = 0
    return [g for g in gaps if g >= min_sec]


def db(x):
    return 20 * math.log10(max(x, 1e-12))


def gain_for(rms_db, pk_db, target_peak, lo, hi):
    g = target_peak - pk_db
    if rms_db + g < lo:
        g = lo - rms_db
    if rms_db + g > hi:
        g = hi - rms_db
    return g


def title_for(num, cfg, src_text):
    titles = cfg.get("titles", {})
    if str(num) in titles:
        return titles[str(num)]
    if num == 0:
        return "Introduction"
    first = src_text.splitlines()[0].strip().lstrip("# ").strip()
    name = first.split(".", 1)[1].strip().rstrip(".") if "." in first else first
    return f"Ch {num} - {name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--skip", default="", help="chapter numbers to leave alone")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    cfg = json.loads((root / "book.json").read_text())
    seam = float(cfg.get("seam", 1.10))
    head = float(cfg.get("head", 0.60))
    tail = float(cfg.get("tail", 1.50))
    frame = int(FRAME_SEC * SR)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    try:
        srcs = chapters(root / "text", "*.txt")
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    n_total = len(srcs)
    out_dir = root / "mp3"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for num, src in srcs:
        if f"{num:02d}" in skip or str(num) in skip:
            print(f"ch{num:02d}: skipped")
            continue
        d = root / "audio" / f"ch{num:02d}"
        mp3s = sorted(d.glob("chunk*.mp3"))
        if not mp3s:
            print(f"ch{num:02d}: no chunks, skipped")
            continue

        parts = [decode(p) for p in mp3s]
        edges = [edge_silence(a, frame) for a in parts]
        gaps = [g for a in parts for g in internal_gaps(a, frame)]

        buf_parts = [np.zeros(int(head * SR), dtype=np.float32)]
        seams = []
        for i, a in enumerate(parts):
            buf_parts.append(a)
            if i + 1 < len(parts):
                gap = max(seam - edges[i][1] - edges[i + 1][0], 0.05)
                seams.append(round(float(gap), 2))
                buf_parts.append(np.zeros(int(gap * SR), dtype=np.float32))
        buf_parts.append(np.zeros(int(tail * SR), dtype=np.float32))
        buf = np.concatenate(buf_parts).astype(np.float64)

        rms_db, pk_db = db(np.sqrt((buf ** 2).mean())), db(np.abs(buf).max())
        g = gain_for(rms_db, pk_db, PEAK_MAX - 0.5, RMS_LO + 0.5, RMS_HI - 0.5)
        buf *= 10 ** (g / 20)
        f_rms, f_pk = db(np.sqrt((buf ** 2).mean())), db(np.abs(buf).max())

        title = title_for(num, cfg, src.read_text())
        # Chapter files are numbered from 00 for the intro, so the track number is
        # simply num+1. Getting this wrong is silent: players sort monotonically
        # either way, so the numbering looks fine in playback order while reading
        # 14/13 in the tag. Assert it instead of trusting it.
        track = num + 1
        if not 1 <= track <= n_total:
            print(f"ch{num:02d}: track {track} outside 1..{n_total}, check the "
                  f"chapter numbering in text/")
            continue
        out_path = out_dir / f"{src.stem}.mp3"
        enc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
             "-c:a", "libmp3lame", "-b:a", cfg.get("bitrate", "192k"),
             "-ar", str(SR), "-ac", "1",
             "-metadata", f"title={title}",
             "-metadata", f"track={track}/{n_total}",
             "-metadata", f"album={cfg.get('title','')}",
             "-metadata", f"artist={cfg.get('narrator','')}",
             "-metadata", f"album_artist={cfg.get('narrator','')}",
             "-metadata", "genre=Audiobook", "-id3v2_version", "3",
             str(out_path), "-y"],
            input=buf.astype(np.float32).tobytes(), capture_output=True)
        if enc.returncode != 0:
            print(f"ch{num:02d} encode failed: {enc.stderr.decode()[:200]}")
            continue

        longest_gap = max(gaps) if gaps else 0.0
        seam_ok = (not seams) or max(seams) <= longest_gap
        rows.append({"chapter": num, "title": title, "track": f"{track}/{n_total}",
                     "chunks": len(parts), "duration_s": round(len(buf) / SR, 2),
                     "seams": seams, "gain_db": round(g, 2),
                     "rms_db": round(f_rms, 2), "peak_db": round(f_pk, 2),
                     "internal_pause_median_s": round(float(np.median(gaps)), 2) if gaps else None,
                     "internal_pause_max_s": round(longest_gap, 2),
                     "seam_shorter_than_longest_pause": bool(seam_ok),
                     "file": out_path.name})
        print(f"ch{num:02d} {len(buf)/SR/60:5.2f}min  {len(parts)} chunks  "
              f"gain {g:+6.2f}  RMS {f_rms:6.2f}  peak {f_pk:6.2f}  "
              f"seams {seams}  seam<=longest pause {seam_ok}", flush=True)

    (root / "audio" / "master_manifest.json").write_text(json.dumps(rows, indent=2))
    bad = [r for r in rows
           if not (RMS_LO <= r["rms_db"] <= RMS_HI) or r["peak_db"] > PEAK_MAX]
    loud_seams = [r for r in rows if not r["seam_shorter_than_longest_pause"]]
    total = sum(r["duration_s"] for r in rows)
    print(f"\n{len(rows)} files, {total/60:.1f} min, written to {out_dir}")
    if not rows:
        print("nothing was assembled. Either render.py has not run yet or "
              f"{root/'audio'} holds no chNN directories with chunk mp3s.")
        return 1
    print(f"outside the ACX window: {len(bad)}")
    for r in bad:
        print(f"  ch{r['chapter']:02d} RMS {r['rms_db']} peak {r['peak_db']}")
    print(f"chapters where a seam is the longest pause: {len(loud_seams)}")
    for r in loud_seams:
        print(f"  ch{r['chapter']:02d} seams {r['seams']} vs longest internal "
              f"{r['internal_pause_max_s']}")
    return 1 if (bad or loud_seams) else 0


if __name__ == "__main__":
    sys.exit(main())
