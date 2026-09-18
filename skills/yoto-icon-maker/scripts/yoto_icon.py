#!/usr/bin/env python3
"""Prepare, validate, and preview 16x16 Yoto icon PNGs."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZE = 16


def icon_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".png")


def prepare(source: Path, output: Path, padding: int) -> None:
    if not 0 <= padding <= 7:
        raise ValueError("padding must be between 0 and 7 pixels")
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("source is fully transparent")
    image = image.crop(bbox)
    target = SIZE - 2 * padding
    scale = min(target / image.width, target / image.height)
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    image = image.resize((width, height), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((SIZE - width) // 2, (SIZE - height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=False)


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG":
                errors.append(f"format is {image.format}, expected PNG")
            if image.size != (SIZE, SIZE):
                errors.append(f"size is {image.width}x{image.height}, expected 16x16")
            if image.mode != "RGBA":
                errors.append(f"mode is {image.mode}, expected RGBA")
            alpha = image.convert("RGBA").getchannel("A")
            pixels = alpha.get_flattened_data() if hasattr(alpha, "get_flattened_data") else alpha.getdata()
            alpha_values = set(pixels)
            if alpha_values == {0}:
                errors.append("image is fully transparent")
            if 0 not in alpha_values:
                errors.append("no transparent pixels found")
            if any(value not in (0, 255) for value in alpha_values):
                errors.append("contains partial alpha; inspect for antialiased halos")
    except Exception as exc:
        errors.append(f"cannot read image: {exc}")
    return errors


def validate(paths: list[Path]) -> int:
    files: list[Path] = []
    for path in paths:
        files.extend(icon_files(path))
    if not files:
        print("No PNG files found.", file=sys.stderr)
        return 2
    failed = 0
    for path in files:
        errors = validate_file(path)
        if errors:
            failed += 1
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}")
    print(f"Validated {len(files)} icon(s); {failed} failed.")
    return 1 if failed else 0


def preview(directory: Path, output: Path, scale: int, labels: bool, columns: int) -> None:
    files = icon_files(directory)
    if not files:
        raise ValueError("no PNG files found")
    if scale < 1:
        raise ValueError("scale must be at least 1")
    tile = SIZE * scale
    label_height = 18 if labels else 0
    columns = max(1, min(columns, len(files)))
    rows = math.ceil(len(files) / columns)
    sheet = Image.new("RGB", (columns * tile, rows * (tile + label_height)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, path in enumerate(files):
        with Image.open(path) as opened:
            icon = opened.convert("RGBA").resize((tile, tile), Image.Resampling.NEAREST)
        x = (index % columns) * tile
        y = (index // columns) * (tile + label_height)
        sheet.paste(icon, (x, y), icon)
        if labels:
            label = path.stem[: max(1, tile // 6)]
            draw.text((x + 3, y + tile + 3), label, fill=(255, 255, 255), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    prep = commands.add_parser("prepare", help="fit a transparent source onto a 16x16 canvas")
    prep.add_argument("source", type=Path)
    prep.add_argument("output", type=Path)
    prep.add_argument("--padding", type=int, default=1)

    check = commands.add_parser("validate", help="validate one or more icons or directories")
    check.add_argument("paths", nargs="+", type=Path)

    view = commands.add_parser("preview", help="make a black-background nearest-neighbor contact sheet")
    view.add_argument("directory", type=Path)
    view.add_argument("output", type=Path)
    view.add_argument("--scale", type=int, default=12)
    view.add_argument("--columns", type=int, default=5)
    view.add_argument("--labels", action="store_true")
    return root


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source, args.output, args.padding)
            return 0
        if args.command == "validate":
            return validate(args.paths)
        if args.command == "preview":
            preview(args.directory, args.output, args.scale, args.labels, args.columns)
            return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
