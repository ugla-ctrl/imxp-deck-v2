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
