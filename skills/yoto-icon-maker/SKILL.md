---
name: yoto-icon-maker
description: Create cohesive 16x16 pixel-art icons for Yoto audiobook chapters, stories, playlists, or tracks. Use when the user provides a book, chapter list, manuscript, synopsis, or existing icon set and wants narrative-specific Yoto icons, previews, mappings, or a packaged icon collection.
---

# Yoto Icon Maker

Create icons that a listener can recognize on a Yoto Player's 16x16 display. Treat the physical display, not an enlarged desktop preview, as the final medium.

## Running the bundled script

The helper script ships inside this plugin. In the commands below,
`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's install directory when this file
loads, so the paths work wherever the plugin is installed. Run it with Python 3 and
the Pillow imaging library (`pip install pillow`). If you copied the script
somewhere else, point the commands at that directory instead.

## Required output

Unless the user asks for something narrower, deliver:

- one 16x16 RGBA PNG per chapter or track;
- transparent backgrounds;
- zero-padded, ordered filenames such as `01-fox-mayor.png`;
- a chapter-to-icon mapping in Markdown or CSV;
- an enlarged nearest-neighbor preview sheet with labels;
- a ZIP containing the icons, mapping, and preview.

If the user asks for one icon, return the individual PNG and one enlarged preview. Do not add a ZIP unless useful.

## Read supporting guidance

- Read [references/narrative-selection.md](references/narrative-selection.md) when choosing what each chapter should depict or differentiating repeated characters.
- Read [references/pixel-art-and-device-rendering.md](references/pixel-art-and-device-rendering.md) before generating or revising artwork.
- Read [references/prompt-patterns.md](references/prompt-patterns.md) when using an image-generation tool or commissioning a source render.

## Workflow

### 1. Establish the chapter set

Extract the ordered chapter or track list from the user's source. Read enough of each chapter to identify its distinctive narrative beat. Do not infer the icon from the title alone when chapter text or a useful synopsis is available.

Build a private working table with:

| Field | Purpose |
| --- | --- |
| Number and title | Keeps delivery order stable |
| Focal character | Best face candidate |
| Defining moment | The chapter-specific action, mood, or change |
| Visual identifiers | Species, hair, hat, uniform, color, silhouette, prop |
| Alternate motif | Landmark or simple object if a face is weak |
| Spoiler sensitivity | Whether the icon would reveal a late twist |

Ask for clarification only when chapter order, source access, or the desired scope is genuinely ambiguous. Otherwise make a reasonable mapping and include it with the deliverable.

### 2. Select one unmistakable motif

Use this priority order:

1. **Character face:** Prefer the face of the chapter's focal or most memorable character. Use a large head, recognizable silhouette, signature colors, and one readable expression.
2. **Landmark:** Use a place when the setting is the chapter's main identity or no character face is distinctive. Reduce it to one skyline, building, vehicle, room feature, or natural formation.
3. **Simple narrative object or action:** Use one iconic prop, emblem, creature, or two-shape interaction only when it identifies the chapter more clearly than a face or landmark.

Do not illustrate the whole scene. At 16x16, one strong noun plus one optional modifier is the practical limit. Examples: `worried rabbit + carrot`, `smiling sloth + conductor cap`, `city skyline + central tower`.

For repeated characters, keep the base face consistent and change one or two chapter-specific signals: expression, headwear, a foreground prop, lighting color, or a small secondary silhouette. The user should recognize both the character and the specific chapter.

Favor narrative recognition over visual variety. Repeating a central character is correct when that character truly anchors multiple chapters.

### 3. Define a set-wide visual system

Before generating the first icon, choose and maintain:

- face scale and crop;
- outline weight;
- eye and mouth construction;
- palette size and saturation;
- direction of light;
- transparent-edge treatment;
- landmark perspective;
- handling for recurring characters.

Use hard-edged pixel art. Avoid gradients, soft shadows, photographic detail, thin lines, text, decorative frames, and busy backgrounds. Use a small, bright palette with clear light-dark separation.

When matching an existing set, inspect its actual icons and preserve their proportions, palette behavior, edge treatment, and degree of exaggeration. Do not merely repeat the words "same style" in a prompt.

### 4. Generate or draw a clean source

Use an available image-generation or raster-art tool. Generate a larger source only if necessary, but compose it as if every block must survive on a 16x16 grid. Ask for:

- one centered subject;
- face-only or head-and-shoulders framing for characters;
- a transparent background, with no checkerboard pattern drawn into the image;
- square pixels, crisp edges, no antialiasing, and no texture;
- exaggerated identity cues and expression;
- no text, watermark, border, or extra objects.

Image generators often imitate pixel art while retaining blur, tiny details, or fake transparency. Treat the generated result as source material, not automatically as the final icon.

### 5. Resolve onto the final 16x16 grid

Prefer deliberate 16x16 pixel placement. If resizing a larger source:

1. crop to the smallest square that contains the intended subject with a narrow margin;
2. remove any real or simulated background;
3. resize with nearest-neighbor sampling;
4. inspect the exact 16x16 result pixel by pixel;
5. repair eyes, mouth, silhouette, holes, stray pixels, and transparency manually when needed.

Use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/yoto-icon-maker/scripts/yoto_icon.py prepare SOURCE OUTPUT` for deterministic square fitting and nearest-neighbor export. The helper does not make artistic decisions and does not remove backgrounds.

### 6. Test for the Yoto display

Judge each icon in all three views:

- at exactly 16x16 pixels;
- enlarged with nearest-neighbor scaling;
- against solid black, approximating unlit pixels on the device.

At actual size, verify that the subject is recognizable without reading the filename. Faces should read from silhouette, eye placement, color blocks, and expression. Landmarks should read from outline and one signature feature.

Reject or revise an icon when:

- the face becomes a colored blob;
- both eyes or the mouth disappear;
- dark edges merge into the black display;
- the silhouette could describe several characters or places;
- a prop is too small to identify;
- fake checkerboard pixels remain;
- antialiased fringe creates muddy halos;
- the icon only makes sense in the enlarged preview.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/yoto-icon-maker/scripts/yoto_icon.py validate <files-or-directory>` before delivery. Generate a contact sheet with `python3 ${CLAUDE_PLUGIN_ROOT}/skills/yoto-icon-maker/scripts/yoto_icon.py preview ICON_DIR preview.png --labels`.

### 7. Review the set as a sequence

Check the full contact sheet for:

- stable character identity across chapters;
- enough chapter-specific differentiation;
- consistent scale and visual weight;
- no accidental duplicates;
- no icon that is markedly dimmer or busier than the rest;
- correct chapter order and filenames.

When two icons are too similar, change the narrative modifier before changing the character's core design.

### 8. Package and report

Keep the delivery concise. State the number of icons, confirm `16x16 RGBA PNG`, provide the ZIP or individual file, show the enlarged preview, and mention any interpretive mapping that may merit user review.

Do not claim the icon was tested on physical hardware unless it actually was. Say it was validated or previewed for the Yoto display.

## Non-negotiable quality bar

- Every final icon is exactly 16x16 pixels.
- Every final icon is a valid PNG in RGBA mode.
- Transparency is genuine, not a painted checkerboard.
- Pixel edges stay crisp under nearest-neighbor enlargement.
- The depicted motif has a direct, explainable link to its chapter.
- Recognition at display scale outranks detail, realism, and ornamental beauty.
