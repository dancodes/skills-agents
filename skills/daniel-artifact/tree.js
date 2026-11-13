document.head.insertAdjacentHTML("beforeend", `<style>
.row { display: flex; align-items: center; gap: 6px; min-height: 23px; padding-inline: 6px 8px; white-space: nowrap; font-family: var(--mono); font-size: 12.5px; border-radius: 4px; min-width: 0; }
.row.x { cursor: pointer; }
.row.x:hover { background: var(--surface); }
.row.root { font-weight: 500; }
.row.doc { font-family: var(--sans); font-size: 11.5px; color: var(--faint); }
.row.doc .g { font-family: var(--mono); font-size: 12.5px; }
.car { width: 16px; flex: none; color: var(--faint); font-size: 14px; line-height: 1; text-align: center; }
.row.x .car { color: var(--accent); }
.g { color: var(--faint); white-space: pre; }
.f, .ty { color: var(--muted); }
.row.root .chip { font-weight: 600; }
.row.x:hover .chip { border-color: oklch(0.55 0.1 var(--h)); }
.row[aria-expanded="true"] .chip { box-shadow: 0 0 0 1px oklch(0.5 0.11 var(--h)); }
.m { color: var(--accent); font-size: 11.5px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex: none; display: inline-block; }
.d { color: var(--faint); font-family: var(--sans); font-size: 11.5px; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.row > :not(.d) { flex: none; }
.row.doc > span:last-child { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.cnt { margin-left: auto; padding-left: 14px; color: var(--faint); font-size: 11px; font-variant-numeric: tabular-nums; }
.sep { margin: 8px 12px 4px; padding-top: 6px; border-top: 1px dashed var(--line); font-size: 11px; color: var(--faint); }
</style>`);

const treeEsc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
for (const t of Object.values(TYPES)) {
  t.fields = t.fields || [];
  t.changed = !!t.change || t.fields.some(f => f[3] && (f[3].was || f[3].added));
}

function typeChip(name) { const t = TYPES[name]; const c = chip(name, t && t.kind || "model"); return t && t.title ? c.replace(/>[^<]*<\/b>$/, ">" + treeEsc(t.title) + "</b>") : c; }
function typeHtml(s) { return treeEsc(s).replace(/\b[A-Za-z_][A-Za-z0-9_]*\b/g, w => TYPES[w] ? typeChip(w) : w); }
function chipCode(html) { return html.replace(/<code>([A-Za-z_][A-Za-z0-9_]*)<\/code>/g, (m, w) => TYPES[w] ? typeChip(w) : m); }

function refOf(typeStr) {
  const words = String(typeStr).match(/\b[A-Za-z_][A-Za-z0-9_]*\b/g) || [];
  return words.find(w => TYPES[w] && (TYPES[w].fields.length || TYPES[w].values || TYPES[w].members)) || null;
}
function countOf(name) {
  const t = TYPES[name];
  if (t.label) return t.label;
  if (t.values) return `${t.values.length} values`;
  if (t.members) return `${t.members.length} members`;
  return `${t.fields.length} fields`;
}
function childrenOf(name) {
  const t = TYPES[name];
  if (t.values) return t.values.map(([k, v]) => ({ f: k, ty: "", d: v }));
  if (t.members) return t.members.map(([label, m]) => ({ f: label, ty: m, d: "" }));
  return t.fields.map(([f, ty, d, fl]) => ({ f, ty, d, fl: fl || {} }));
}

function makeNode(item, prefix, last, root) {
  const node = document.createElement("div");
  const ref = refOf(item.ty);
  const fl = item.fl || {};
  const list = /^list\[/.test(item.ty);
  const nullable = /\| None/.test(item.ty);
  const shown = item.ty.replace(/^list\[(.*)\]$/, "$1").replace(/ \| None$/, "");
  const row = document.createElement("div");
  row.className = "row" + (root ? " root" : "") + (ref ? " x" : "");
  row.innerHTML = `<span class="car">${ref ? "▸" : ""}</span><span class="g">${root ? "" : prefix + (last ? "└─ " : "├─ ")}</span>`
    + (item.f ? `<span class="f">${treeEsc(item.f)}</span>` : "")
    + (shown ? `<span class="ty">${typeHtml(shown)}</span>` : "")
    + (list ? `<span class="m">[]</span>` : "")
    + (nullable ? `<span class="m">?</span>` : "")
    + (ref && TYPES[ref].changed ? `<i class="dot" title="Changed"></i>` : "")
    + (fl.opt ? `<span class="fl">optional</span>` : "")
    + (fl.base ? `<span class="fl">from ${treeEsc(fl.base)}</span>` : "")
    + (fl.added ? `<span class="fl a">added</span>` : "")
    + (fl.was ? `<span class="fl a">was ${treeEsc(fl.was)}</span>` : "")
    + (fl.tags ? fl.tags.map(([c, t]) => `<span class="fl ${c}">${treeEsc(t)}</span>`).join("") : "")
    + (item.d ? `<span class="d">${treeEsc(item.d)}</span>` : "")
    + (ref ? `<span class="cnt">${countOf(ref)}</span>` : "");
  node.appendChild(row);
  if (!ref) return node;
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-expanded", "false");
  const kids = document.createElement("div");
  kids.hidden = true;
  node.appendChild(kids);
  const childPrefix = root ? "" : prefix + (last ? "   " : "│  ");
  node.toggle = open => {
    const want = open ?? kids.hidden;
    if (want && !kids.childElementCount) {
      const t = TYPES[ref];
      if (t.doc) {
        const doc = document.createElement("div");
        doc.className = "row doc";
        doc.innerHTML = `<span class="car"></span><span class="g">${childPrefix}│  </span><span>${treeEsc(t.doc)}</span>`;
        kids.appendChild(doc);
      }
      const items = childrenOf(ref);
      items.forEach((it, i) => kids.appendChild(makeNode(it, childPrefix, i === items.length - 1, false)));
    }
    kids.hidden = !want;
    row.setAttribute("aria-expanded", String(want));
    row.querySelector(".car").textContent = want ? "▾" : "▸";
  };
  row.addEventListener("click", () => node.toggle());
  row.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); node.toggle(); }
    if (e.key === "ArrowRight") node.toggle(true);
    if (e.key === "ArrowLeft") node.toggle(false);
  });
  return node;
}

function renderTree(el, roots) {
  el.innerHTML = "";
  for (const r of roots) {
    if (r.sep) { el.insertAdjacentHTML("beforeend", `<div class="sep">${treeEsc(r.sep)}</div>`); continue; }
    const n = makeNode({ f: "", ty: r.t, d: "" }, "", true, true);
    el.appendChild(n);
    n.toggle(true);
  }
}

function openLevel(el) {
  const closed = [];
  const walk = parent => {
    for (const n of parent.children) {
      if (!n.toggle) continue;
      const kids = n.children[1];
      if (kids.hidden) closed.push(n); else walk(kids);
    }
  };
  walk(el);
  closed.forEach(n => n.toggle(true));
}
