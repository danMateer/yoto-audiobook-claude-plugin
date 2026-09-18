#!/usr/bin/env python3
"""Pre-flight cost estimate. Spends nothing. Run this before the confirmation gate.

Packs every tagged chapter exactly the way render.py will, then reports the chunk
count, the character count that will actually be billed (tags included), and the
projected credits at the measured 0.550 credits per character.

With --balance it also reads GET /v1/user/subscription, which is a read and costs
no credits, so the gate can show remaining balance alongside projected spend.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_pack import pack, chapters, MAX_CHUNK  # noqa: E402

CREDITS_PER_CHAR = 0.550   # measured from the character-cost header, flat 45% off


def balance():
    key_path = pathlib.Path(os.path.expanduser("~/.elevenlabs_key"))
    if not key_path.exists():
        return None
    r = subprocess.run(
        ["curl", "-s", "-H", f"xi-api-key: {key_path.read_text().strip()}",
         "https://api.elevenlabs.io/v1/user/subscription"],
        capture_output=True)
    try:
        d = json.loads(r.stdout)
        used = d["character_count"]
        limit = d["character_limit"]
        return {"used": used, "limit": limit, "remaining": limit - used,
                "resets": d.get("next_character_count_reset_unix")}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--balance", action="store_true")
    args = ap.parse_args()
    root = pathlib.Path(args.root)

    try:
        files = [p for _, p in chapters(root / "tagged", "*_tagged.txt")]
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    if not files:
        print(f"no tagged chapters in {root/'tagged'}", file=sys.stderr)
        return 1

    rows, jobs = [], 0
    for f in files:
        text = f.read_text()
        chunks = pack(text)
        sizes = [len(c) for c in chunks]
        rows.append((f.name.replace("_tagged.txt", ""), sum(sizes), len(chunks),
                     min(sizes), max(sizes)))
        jobs += len(chunks)

    total = sum(r[1] for r in rows)
    credits = int(total * CREDITS_PER_CHAR)

    print(f"{'chapter':34s} {'chars':>7} {'chunks':>7} {'min':>6} {'max':>6}")
    for name, ch, n, lo, hi in rows:
        print(f"{name:34s} {ch:>7} {n:>7} {lo:>6} {hi:>6}")
    print(f"{'TOTAL':34s} {total:>7} {jobs:>7}")
    print()
    print(f"chunks to render      {jobs}")
    print(f"characters billed     {total:,}  (tags included, they bill as characters)")
    print(f"projected credits     {credits:,}  at {CREDITS_PER_CHAR}/char")
    print(f"retry headroom 15%    {int(credits * 0.15):,}")
    print(f"worst case            {credits + int(credits * 0.15):,}")
    print(f"est. audio            {total / 15.0 / 60:.0f} min at 15.0 char/sec")
    if max(r[4] for r in rows) > MAX_CHUNK:
        print(f"\nWARNING: a chunk exceeds the {MAX_CHUNK} ceiling")

    if args.balance:
        b = balance()
        if b:
            print(f"\naccount used          {b['used']:,} / {b['limit']:,}")
            print(f"account remaining     {b['remaining']:,}")
            after = b["remaining"] - credits
            print(f"remaining after       {after:,}")
            if after < 0:
                print("WARNING: projected spend exceeds the remaining balance")
        else:
            print("\ncould not read the account balance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
