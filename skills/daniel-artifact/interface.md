# Interface pages

Use this page shape when asked to describe, browse or explain an interface:
the classes, models, DTOs, schemas, enums or types that a change, module or
API adds. The reference is `examples/interface-boxes.html`, the ORD-12
Invoice and Quote classes, with nested folder boxes. Copy its structure, not its data.

Every interface page has two tabs over one `TYPES` object:

- **Boxes**, the default. A nested-box map like DiskTree. A box is a class and
  a cell is a field. A box's size is the number of fields it holds, counted
  down to the last level. It opens at depth 2. Click a box to zoom in; the
  breadcrumb and Esc go back out. The mouse back and forward buttons (and
  Alt+Left / Alt+Right) step through every zoom, type and field the reader
  opened. A side panel shows the selected class.
- **Tree.** The same types as expandable rows (`tree.js`).

## Page layout

Top to bottom, nothing else:

1. **Header** from `base.html`. Title: `<Ticket or module> Classes`, or
   `<Name> Interface` when the scope is not a ticket. The mono sub line has
   the branch or path, the change id in `<b>`, `<n> new classes` (count it
   from `TYPES` in the script, never by hand) and `box size = fields held`.
   On the right: the Light / Dark switch, then the tabs `Boxes` / `Tree`
   (`data-view="boxes"` / `data-view="tree"`).
2. **Rules strip** (`.rules`, four cells), only in the Boxes view. The
   cells, in this order:
   - one cell per entry point, showing its path as chips joined by `→`
     (input → internal figures → output). Use one or two cells.
   - **Folders.** Where each kind of class lives, e.g. pydantic models in
     one package and dataclasses in another.
   - **Moved / changed.** Classes moved or changed rather than added. When
     there are none, give the biggest class and its field count.
3. **Boxes view:** `<div id="boxes"></div>`, filled by `renderBoxes`.
4. **Tree view:** a `.pane.treecard` with the pane header
   `<b>Type tree</b> · click a row to open it` and an
   `Open one more level` button (`.btn`, calls `openLevel`), then
   `<div class="pane-b" id="tree">`.

Page CSS under `/* page */` is only:

```css
.app { padding-bottom: 0; }
#v-boxes { --stage-top: 197px; }
```

`--stage-top` is the space above the stage plus 12px. Use 197px with a
one-line sub title and a rules strip whose lines wrap to three or fewer.
Raise it if the 1280×760 check scrolls.

## Script order

Paste these in this order in one `<script>`: base.html's script, then
`TYPES`, then `tree.js`, then `boxes.js`, then the glue. Put every class name
in `CHIP_ORDER`, roots first, then each class the first time a root reaches
it, then externals. Reuse the order of an older page for names it already has.

## TYPES

The `tree.js` shape plus keys that only the side panel reads:

```js
Name: {
  doc: "One plain sentence: what it is or holds.",
  kind: "enum" | "union" | "external",   // omit for a class
  py: "pydantic" | "dataclass" | "StrEnum" | "Annotated union" | "TypedDict" | ...,
  file: "domain/entity/order/quote_report/output.py",  // relative to the src prefix
  by: "to_quote_report · transform/quote_report/output.py",  // who builds it; "Caller" for inputs
  base: "OfferInput",                      // parent class, when it extends one
  change: "moved",                         // only for moved or changed classes
  fields: [[name, "type as written", "description", { base: "Parent" }]],
  values: [[value, "when it applies"]],    // enums
  members: [["unit = dollars", "MemberType"]],  // unions
}
```

- **Types as written in the code**: `float | None`, `list[OfferRow]`,
  `Literal['dollars']`. `| None` shows as `?`, `list[...]` as `[]`.
- **Inherited fields** are listed again on the subclass with `{ base }`, so
  the box holds them and the side panel tags them `from Parent`.
- **External types** the fields point at (other modules, stdlib) get
  `{ kind: "external" }` and no fields, so they chip but never open.
- **Descriptions** come from the code (`Field(description=...)`,
  docstrings), shortened. When the code has none, write one line from what
  the code does, and say so in the report to the user.

## renderBoxes options

```js
renderBoxes(document.getElementById("boxes"), {
  title: "ORD-12",                         // root crumb
  src: "src/services/shop/src/",           // prefix for each file
  atoms: ["ReportValue", "ReportDate"],
  groups: [
    { folder: "domain/entity/order/", sm: "pydantic", groups: [
      { folder: "invoice_report/", groups: [
        ["input.py", "", ["InvoiceReportInput"]],
        ["output.py", "", ["InvoiceReport", "SkippedReport"]],
      ] },
    ] },
  ],
  index: [[label, file, [allTypesInGroup]]],
});
```

- **groups** follow the code's folders. A folder is
  `{ folder: "name/", sm?, groups: [...] }` and holds sub-folders and files.
  A file is `[fileName, "", [rootTypes]]`. Each folder box contains its
  sub-folder and file boxes, so the map shows the real tree, not a row of
  columns. The top-level entries are the columns. Leave `sm` empty where it
  repeats the folder name; a short kind (`pydantic`, `dataclasses`) on the
  top folders is enough. Roots are the types that no other new type points
  at. Every other type must be reachable from a root.
- **Flat code** with no sub-folders still uses plain files as top-level
  entries: `groups: [["Inputs", "order.py", [...]], ...]`.
- **Depth** buttons count files and types, not folders.
- **atoms** are small value types used on almost every field (a value and
  its printed text, a money type, an id wrapper). Each one draws as a single
  colored cell instead of a box. Use one only when it would otherwise repeat
  in most boxes. Atoms still get their own entry in the index.
- **index** lists every class once in the side panel's start view. Use the
  same groups as `groups`, plus a group for shared parts when several roots
  use them. The group counts must add up to the class count.

The Tree view uses the same roots, with a `{ sep: "path/to/file.py" }`
before each file's roots:

```js
renderTree(treeEl, [{ sep: "order/invoice_report/input.py" }, { t: "InvoiceReportInput" }, ...]);
```

## Check

At 1280×760 in light mode: the page does not scroll in either direction,
zooming into the biggest root works, mouse back and forward retrace it,
clicking a cell highlights its row in
the side panel, the Tree tab opens, and the console has no errors. Then
switch to dark mode once and check that box labels still read.
