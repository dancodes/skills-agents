# Treemap pages

Use this page shape for any hierarchy where groups hold items that have a
size: the files of a change, disk use, cost by service, tests by suite. The
reference is `examples/change-treemap.html`, the files of an invented
ORD-31 change grouped by the job each file does. Copy its structure, not its
data.

Every treemap page has two tabs over one data tree:

- **Map**, the default. A DiskTree-style map from `treemap.js`. A tile is an
  item and its area is the item's size. Groups nest as boxes with a title
  bar. The header has a breadcrumb and three switches:
  - **Depth** (1, 2, All): how many levels open below the current view. A
    group at the limit is one closed block, with its name, its counts, its
    doc when there is room, and a strip along the bottom that shows its items
    in the current colors.
  - **Size**: what a tile's area counts. One entry per measure.
  - **Color**: the first entry colors by group, the others by a rule you
    give, each with its own legend.

  Click a group's title bar or a closed block to zoom in. Click a crumb or
  press Esc to zoom out. Hover a tile or block for its path, counts, doc and
  tags.
- **List.** The same tree as expandable rows (`tree.js`), through
  `treemapTypes`.

## Grouping

The grouping is the content of the page. Do not group by folder unless the
reader asked for folders.

- Group by the job each item does. For a change: the product change first,
  then the plumbing under it, then the checks.
- Order groups from the highest level to the lowest. Put tests last, in
  sub-groups that mirror the jobs they check.
- Give every group a one-sentence `doc` that says what its items do together.
- Count from the data, never by hand. Check that the leaf count and the size
  totals match the source (`git diff --numstat`, `du`, the bill).

## Page layout

Top to bottom, nothing else:

1. **Header** from `base.html`. Title: `<Ticket or scope> <Noun>`, two to
   four words. The mono sub line has the branch or path, the change id in
   `<b>`, and the totals (count them in the script). On the right: the
   Light / Dark switch, the Name style switch, then the tabs `Map` / `List`
   (`data-view="map"` / `data-view="list"`).
2. **Rules strip** (`.rules`, four cells), only in the Map view: the four
   numbers a reader asks first. For a change: new source, tests, renames
   only, and flagged items. Compute each one from the data.
3. **Map view:** `<div id="map"></div>`, filled by `renderTreemap`, then one
   `.hint` line on how to zoom.
4. **List view:** a `.pane` with the pane header `<b>Items by job</b>` and the
   `Open one level` / `Open all` / `Collapse` buttons, then
   `<div class="pane-b" id="tree">`.

## Script order

Paste these in this order in one `<script>`: base.html's script, then the
data, then `treemap.js`, then `const TYPES = treemapTypes(...)`, then
`tree.js`, then the glue. Put every group key in `CHIP_ORDER`, top-level
groups first, so a group keeps its color on the map, in the legend and in
the list.

## Data

A group is `{ key, label, doc, items }`. `key` is one identifier, used as the
chip and color key. `items` holds groups or leaves, mixed freely and to any
depth.

A leaf is `{ name, d, tags, ...your fields }`. `d` is one short line on what
it does. `tags` is `[[class, text]]`, where class is `""`, `a`, `ok`, `warn`
or `crit` from the `.fl` styles. Put your own measures on the leaf, such as
`add`, `del` or `bytes`.

## renderTreemap(el, opts)

- `root`: `{ label, items }`, the top of the tree. Its label is the first
  crumb.
- `sizes`: `[{ id, label, value: leaf => number, note }]`. The first is the
  default. `note` fills the legend's `Tile area = …` text. A leaf of size 0
  is left out of the map.
- `colors`: `[{ id, label, cls?: leaf => class, legend?: [[class, label]] }]`.
  An entry without `cls` colors by top-level group. The classes are
  `tm-ok tm-warn tm-crit tm-acc tm-grey tm-plain`, from the status tokens.
- `depths`: default `[1, 2, "all"]`. `depth`: the one it opens on, default
  `"all"`. Use `2` when the tree has more than about 60 leaves.
- `unit`: `["file", "files"]`, used in counts.
- `leafLine(leaf)`: the mono second line on a tile and in its tip, e.g.
  `+12 −3`.
- `groupLine(group, leaves)`: the counts after a group's name. Default:
  the leaf count.
- `leafTip(leaf)`: extra HTML lines for the tip.
- `height`: CSS height of the stage. Default
  `max(460px, calc(100vh - 250px))`.

It returns `{ render, zoom, root }`. The map lays itself out again when the
stage changes size, so it draws on its own when its tab opens.

## treemapTypes(root, leafRow, countLabel)

It turns the same tree into `TYPES` for `tree.js`. Each group becomes a type
with `title` (shown in its chip) and `label` (its count). `leafRow(leaf)`
returns one `tree.js` field: `[name, type, desc, { added, tags }]`. Put the
leaf's measure in `type`, for example `+12 −3`. `countLabel(group, n)` writes
the count, e.g. `` `${n} files · +40 −2` ``. Render with one root per
top-level group and `{ sep }` rows between the bands.
