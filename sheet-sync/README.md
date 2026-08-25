# Sheet-driven slide updates

Slides in this deck can be backed by a Google Sheet. A scheduled task checks each
registered sheet daily; when a sheet's `modifiedTime` changes, the slide is
re-rendered from the live data and pushed. This repo (`imxp-deck-v2`, design
option B) is the ONLY deploy target — `imxp-deck` (option A) is frozen and must
not be touched by automation.

## Registered slides

See `registry.json`. Currently:

| Slide | Source sheet | Renderer |
|---|---|---|
| 7 · Platform Build Roadmap | "IMXP Product Dev GANTT" (Benjamin's) | `render_slide.py` |

## How it works

1. The sync task compares the sheet's Drive `modifiedTime` with
   `lastSyncedModifiedTime` in `registry.json`. No change → nothing happens.
2. On change, the sheet's task rows are converted to a canonical pipe-delimited
   file (`CATEGORY|TASK|STATUS|D-Mon-YY|D-Mon-YY|NOTES`).
3. `render_slide.py` matches rows to slide pills by exact task text via
   `label_map.json`, recomputes every pill's timeline position from the live
   Start/End dates, and renders the PNG.
4. Rows that are neither mapped nor in `excludedTasks` are reported as
   *unmapped* — they never get guessed onto the slide. A human adds them to
   `label_map.json` (label + lane) and the next sync picks them up.
5. On success the PNG replaces `slides/slide-07.png`, `registry.json` is
   stamped, and the change is committed and pushed. On any renderer error the
   deck is left untouched.

## Registering another slide

Add an entry to `registry.json` (sheet id + renderer + slide file), create a
label map, and write a renderer for that slide's layout. The scheduled task
iterates over every entry.

## Content-editor slides

`render_content_slide.py` re-renders the text zones of the editable slides
(2, 3, 4, 11, 15, 16) from the **"IMXP Deck - Content Editor"** sheet, on top
of pristine plates in `plates/`. Original text pixels are removed by inpainting
(grain/glow backgrounds preserved), then the sheet copy is re-typeset in the
deck fonts. Per-slide content hashes in `registry.json` ensure only slides whose
sheet row actually changed get re-rendered. Rows for non-editable slides are a
content reference only — changing them requires manual design work.
