#!/usr/bin/env python3
"""Insert ElevenLabs v3 audio tags at unique anchors, with two safety assertions.

Reads a plan file mapping each source chapter to a list of [anchor, tag] pairs.
An anchor is a verbatim substring of the chapter, and the tag is inserted directly
in front of it.

Two assertions, and nothing is written unless both pass on every chapter:

  1. Every anchor matches exactly once. Zero matches means the anchor was
     mistranscribed; two or more means the tag would land somewhere unintended.
     Both are silent corruption if unchecked.
  2. Stripping the inserted tags back out reproduces the source byte for byte.
     This is what catches an anchor that overlapped a previous insertion.

Usage:
  apply_tags.py --root <bookdir> --plan <plan.json>

Layout under <bookdir>:
  text/NN_*.txt          source chapters, 00 is the intro
  tagged/NN_*_tagged.txt written here

Plan format:
  {"00_intro.txt": [["Nobody in the clubhouse", "warmly"], ...], ...}
"""
import argparse
import json
import pathlib
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    plan = json.loads(pathlib.Path(args.plan).read_text())
    out_dir = root / "tagged"
    out_dir.mkdir(parents=True, exist_ok=True)

    pending, errors, counts = {}, [], {}
    for src in sorted((root / "text").glob("*.txt")):
        original = src.read_text()
        text = original
        items = plan.get(src.name, [])
        n_tags = 0

        for anchor, tag in items:
            hits = text.count(anchor)
            if hits != 1:
                errors.append(f"{src.name}: {hits} matches for {anchor!r}")
                continue
            text = text.replace(anchor, f"[{tag}] {anchor}", 1)
            n_tags += 1

        stripped = re.sub(r"\[[a-z]+\] ", "", text)
        if stripped != original:
            errors.append(f"{src.name}: text changed beyond tag insertion")

        pending[out_dir / f"{src.stem}_tagged.txt"] = text
        counts[src.name] = n_tags

    if errors:
        print("NOTHING WRITTEN. Fix these first:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        return 1

    for path, text in pending.items():
        path.write_text(text)

    total = sum(counts.values())
    for name in sorted(counts):
        print(f"{name:44s} {counts[name]:3d} tags")
    print(f"\n{total} tags inserted across {len(counts)} files")
    print("every anchor matched exactly once; text verified unchanged under tag-strip")

    census = {}
    for path in pending:
        for t in re.findall(r"\[([a-z]+)\]", path.read_text()):
            census[t] = census.get(t, 0) + 1
    print("\ntag census:")
    for t, c in sorted(census.items(), key=lambda kv: -kv[1]):
        print(f"  [{t}] {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
