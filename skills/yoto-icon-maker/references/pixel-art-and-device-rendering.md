# Pixel art and Yoto device rendering

## Physical constraint

Yoto Players and Yoto Minis display chapter artwork on a 16x16 pixel matrix. A desktop preview can make weak art look successful because each source pixel becomes a large square. The meaningful test is the unscaled icon viewed at normal distance against black.

Yoto recommends preparing custom artwork as a 16x16 PNG with a transparent background. Keep the final artifact in that form even if the creation tool accepts larger images or other formats.

## Pixel budget

A character face usually works best when the head spans roughly 11 to 15 pixels in width and height. Use the remaining pixels for ears, hair, a hat, or one small prop. Preserve at least a narrow transparent margin unless the crop is intentionally edge-to-edge.

Useful minimums:

- eyes: one bright pixel each, or a two-pixel shape for large eyes;
- eye separation: at least one contrasting pixel where anatomy permits;
- mouth: one to three pixels with strong contrast;
- outline or silhouette division: generally one pixel;
- signature accessory: usually three or more connected pixels.

These are heuristics. Break them when the character remains clearer another way.

## Contrast and color

Unlit display pixels appear dark. Near-black details at the outer edge may disappear, even when they look elegant on a light editor canvas.

- Use bright or mid-value colors along important outer edges.
- Keep adjacent regions distinct in both hue and brightness.
- Reserve the lightest pixels for eyes, teeth, highlights, windows, or one focal cue.
- Avoid using many nearly identical shades.
- Prefer a limited palette, often about 4 to 10 visible colors, including outline and highlights.

Do not force a universal palette when a character's signature colors carry recognition.

## Transparency

The output must contain a real alpha channel. Transparent pixels should have alpha 0. Watch for:

- gray-and-white checkerboards rendered as image content;
- white matte backgrounds;
- partially transparent halos from antialiasing;
- isolated low-alpha pixels around the silhouette.

Hard transparency normally renders more cleanly than soft feathering on a 16x16 display. If semitransparent pixels do not add a deliberate glow, make them fully opaque or transparent.

## Pixel integrity

Use nearest-neighbor scaling for both downscaling and previews. Bilinear, bicubic, and Lanczos filters mix colors and create blurred or semitransparent edges.

Automatic downscaling is only a starting point. Inspect and repair the final grid. Generative source art commonly produces asymmetrical eyes, one-pixel holes, disconnected outlines, and clusters that disappear at actual size.

## Device-oriented review

Review each icon on:

1. transparent or checkerboard canvas, to inspect alpha;
2. black canvas, to approximate the device;
3. exact 16x16 scale, to judge recognition;
4. enlarged nearest-neighbor scale, to diagnose pixel construction.

Reduce screen brightness briefly during review. If the icon depends on subtle shade differences, revise it.

## Common failure modes

| Failure | Cause | Repair |
| --- | --- | --- |
| Face reads as a blob | Head too small or too many tones | Enlarge head; merge color regions |
| Character identity is lost | Generic silhouette | Exaggerate ears, hair, muzzle, hat, or signature color |
| Expression disappears | Eyes and mouth too fine | Use fewer, higher-contrast pixels |
| Dark outline vanishes | Black-on-black outer edge | Add a colored rim or brighter adjacent fill |
| Muddy border | Antialiased resize | Re-export with nearest-neighbor and clean alpha |
| Icon feels crowded | Multiple scene elements | Keep one subject and one modifier |
| Repeated chapters look identical | Same face and mood | Add one chapter-specific cue while preserving base model |
| Landmark looks generic | Too many tiny buildings | Simplify skyline and emphasize one signature structure |
