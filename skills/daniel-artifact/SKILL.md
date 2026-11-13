---
name: daniel-artifact
description: House style for every HTML Artifact page — explorer, explanation, document, report, dashboard, interface browser. Load before writing the page, and when asked to describe an interface, its classes or its types.
---

# daniel-artifact

Every HTML page published with the Artifact tool uses this style: warm
off-white panels, Geist type, hairline borders, one colored chip per named
thing, and a Light / Dark switch in the header. The Quote Report DTO page in
`examples/order-pricing-dtos.html` is the reference.

## Steps

1. **Copy `<SKILL_DIR>/base.html`** to the scratchpad and fill its
   placeholders. Keep its tokens, fonts, header, theme switch and component
   classes as they are. Page-specific CSS goes under `/* page */` and uses
   only the tokens. Prose sits in a 72ch column (`.prose`); tables, trees and
   panels use the full width.
2. **Nested data uses `<SKILL_DIR>/tree.js`.** Types, schemas, config, call
   trees: paste it into the page script after base.html's script, define
   `TYPES` before it, then call `renderTree(el, [{ t: "Root" }, { sep: "label" }])`.
   `openLevel(el)` opens one more level. Rows open on click, to any depth.
   `TYPES` shape: `{ Name: { doc, kind?, change?, title?, label?, fields?: [[name, type, desc, { opt, added, was, base, tags }]], values?: [[key, desc]], members?: [[label, type]] } }`.
   `title` shows in the chip in place of the key, `label` replaces the
   `n fields` count, and `tags` is `[[class, text]]` drawn as `.fl` tags.
3. **Interfaces use `<SKILL_DIR>/interface.md`.** To describe, browse or
   explain classes, models, DTOs, schemas or types, read it first and build
   a Boxes + Tree page with `boxes.js` and `tree.js`. The example is
   `examples/interface-boxes.html`.
4. **Weighted hierarchies use `<SKILL_DIR>/treemap.md`.** Files in a change,
   disk use, cost by service: anything where groups hold items that have a
   size. Read it first and build a Map + List page with `treemap.js` and
   `tree.js`: a DiskTree-style map with Depth, Size and Color switches. The
   example is `examples/change-treemap.html`.
5. **Check once** at 1280×760 in light mode, then publish. Done when no text
   clips and the page has no sideways scroll.

## Style

- **Fonts.** Geist for text, Geist Mono for code, names and tree rows.
- **Sizes.** Title 18/600. Body 13/1.45. Mono rows 12.5. Tables and chips 12.
  Labels and secondary text 11.5. Tags 10.5–11.
- **Spacing.** Header 14 top / 12 bottom over a hairline. Sections 12 block
  padding. Gaps 10–12. Pane header 6×12. Table cells 5×12. Rule cells 9×12.
  Radius 8 panels, 6 tabs, 4 chips, 99 tags. Side gutter
  `max(16px, env(safe-area-inset-*))`. Max width 1480.
- **Color.** Only the tokens: `--bg --panel --surface --ink --muted --faint
  --line --accent --accent-soft`, plus `--crit --warn --ok` and their `-soft`
  pairs for status. Light is the default and has high contrast. Dark
  redefines the tokens under `:root[data-mode="dark"]`.
- **Theme switch.** Every page has the Light / Dark switch, light first,
  saved in `localStorage` key `daniel-artifact-mode`. It sets `data-mode`;
  `data-theme` belongs to the viewer.
- **Chips.** Every name the reader must spot again — type, service, table,
  ticket, person — is a `chip(name)`: its own hue, low saturation, three
  lightness tiers. List names in a fixed `CHIP_ORDER` so a name keeps its
  color across pages. The kind shows in the mark: in Dot styles a round dot
  is a thing, a square an option set, a diamond an alternative, a ring
  external; in Chip, a solid, dashed, dotted or outline-only border.
- **Name style.** Every page has the Name style switch after the theme
  switch: Dot, Dot + wash (default), Left bar, Chip. ← and → step through
  it when nothing else has focus. It sets `data-chips`, saved in
  `localStorage` key `daniel-artifact-chips`. Page CSS styles `.chip` only
  through these rules.
- **Tables.** Hairline rows, 11px muted headers, right-aligned tabular
  numbers, muted row numbers only when order matters.
- **Tabs.** Optional. A segmented control in the header, routed by `#hash`,
  for pages with distinct views.
- **Facts.** A rules strip: a four-column bordered grid, each cell a bold
  title and one or two short lines.
- **Words.** Plain English, short labels, real values over invented ones.
