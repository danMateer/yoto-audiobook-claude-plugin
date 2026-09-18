"""Balanced paragraph packer and chapter discovery, shared by the other scripts.

The plain greedy version left one chapter with a 235-character tail chunk, which
wastes a seam and gives the model almost no context to work with. Aiming every
chunk at total/n and absorbing runts removes the stub. If a runt cannot be absorbed
without breaching the ceiling, split the chapter one more way and try again.

No chunk ever splits a paragraph, so no seam falls mid-sentence.
"""
import math
import re

MAX_CHUNK = 1800   # see references/elevenlabs-api.md for why this number
MIN_RATIO = 0.35   # a chunk under this fraction of target is a runt


def chapters(directory, pattern):
    """Return [(number, path)] sorted by number, or raise.

    Every script takes the chapter number from the first two characters of the
    filename, so a leftover file sharing a prefix (12_old.txt beside
    12_chapter-twelve.txt) makes one chapter render twice, overwrite its own
    output, and inflate the ID3 track total. That is the same silent class of
    error that shipped a 14/13 track number once already, so it fails loudly.
    """
    found = {}
    for p in sorted(directory.glob(pattern)):
        if not p.name[:2].isdigit():
            raise ValueError(f"{p.name} does not start with a two-digit chapter "
                             f"number, so its chapter cannot be determined")
        num = int(p.name[:2])
        if num in found:
            raise ValueError(f"two files claim chapter {num:02d}: "
                             f"{found[num].name} and {p.name}; remove one")
        found[num] = p
    return sorted(found.items())


def _pack_to(paras, target, limit):
    chunks, cur, cur_len = [], [], 0
    for p in paras:
        grown = cur_len + (2 if cur else 0) + len(p)
        if cur and (grown > limit or abs(cur_len - target) < abs(grown - target)):
            chunks.append("\n\n".join(cur))
            cur, cur_len = [p], len(p)
        else:
            cur.append(p)
            cur_len = grown
    if cur:
        chunks.append("\n\n".join(cur))

    i = 0
    while i < len(chunks) and len(chunks) > 1:
        if len(chunks[i]) >= MIN_RATIO * target:
            i += 1
            continue
        if i > 0 and len(chunks[i - 1]) + 2 + len(chunks[i]) <= limit:
            chunks[i - 1] += "\n\n" + chunks.pop(i)
        elif i + 1 < len(chunks) and len(chunks[i + 1]) + 2 + len(chunks[i]) <= limit:
            runt = chunks.pop(i)
            chunks[i] = runt + "\n\n" + chunks[i]
            i += 1
        else:
            i += 1
    return chunks


def pack(text, limit=MAX_CHUNK):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return []
    total = sum(len(p) for p in paras) + 2 * (len(paras) - 1)
    base = max(1, math.ceil(total / limit))

    best = None
    for n in range(base, base + 4):
        chunks = _pack_to(paras, total / n, limit)
        sizes = [len(c) for c in chunks]
        if max(sizes) <= limit and min(sizes) >= MIN_RATIO * (total / n):
            return chunks
        if best is None:
            best = chunks

    # Last resort: a single paragraph longer than the ceiling cannot be packed
    # without splitting it, so say so rather than silently shipping a chunk that
    # will truncate.
    for c in best:
        if len(c) > limit:
            raise ValueError(
                f"a single paragraph is {len(c)} characters, over the {limit} "
                f"ceiling; split it in the manuscript rather than mid-sentence"
            )
    return best
