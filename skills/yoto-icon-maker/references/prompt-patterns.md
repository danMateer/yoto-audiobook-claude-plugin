# Prompt patterns

Use these patterns as ingredients, not rigid scripts. Adapt character, place, expression, palette, and tool syntax to the source.

## Character face source

```text
Create a single square pixel-art portrait for a 16x16 Yoto display.
Subject: [character], shown as a centered [front/three-quarter] face.
Chapter cue: [expression, hat, or one tiny prop].
Preserve unmistakable identifiers: [ears/hair/muzzle/colors/accessory].
Use a large head filling most of the frame, a bold readable silhouette,
hard square pixel clusters, a limited saturated palette, and high contrast.
Transparent background. No checkerboard, scenery, text, border, watermark,
soft shading, gradients, blur, antialiasing, or extra objects.
Design every feature to remain legible after reduction to exactly 16x16 pixels.
```

## Landmark source

```text
Create one centered pixel-art landmark icon for a 16x16 Yoto display.
Place: [landmark or setting].
Reduce it to [signature silhouette] plus [one defining feature].
Use two or three large architectural masses, crisp square pixels, bright
edge separation, a limited saturated palette, and genuine transparency.
No people, text, border, checkerboard, realistic texture, gradients, blur,
antialiasing, or background scene. It must read against black at 16x16.
```

## Object source

```text
Create one centered 16x16-style pixel-art icon of [object].
Make [defining shape/color] unmistakable. Let the object occupy most of the
square and use only one optional narrative modifier: [modifier].
Hard pixel edges, high contrast, limited palette, transparent background.
No text, border, checkerboard, scenery, soft shadow, gradient, or clutter.
```

## Existing-set continuation

Describe observed characteristics explicitly:

```text
Match the supplied set's [head scale], [one-pixel outline], [eye construction],
[palette behavior], [lighting direction], and [transparent edge treatment].
Keep recurring character [name]'s established [silhouette and colors].
For this chapter, change only [expression/accessory/prop].
```

Do not rely on "same style" without naming the visible traits to preserve.

## Repair prompt

```text
Edit only the following: [specific defect]. Preserve the subject, crop,
palette, silhouette, expression, and all other pixels. Return a square image
with genuine transparency; do not draw a checkerboard background.
```

Use a repair request when the composition already works. Regenerate only when the motif or silhouette is fundamentally wrong.
