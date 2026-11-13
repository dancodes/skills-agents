document.head.insertAdjacentHTML("beforeend", `<style>
.stage { display: grid; grid-template-columns: minmax(0, 1fr) 360px; grid-template-rows: minmax(0, 1fr); gap: 12px; min-width: 0; height: max(480px, calc(100vh - var(--stage-top, 197px))); }
.mapcard { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; min-width: 0; }
.crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 2px 4px; min-width: 0; font-family: var(--mono); font-size: 11.5px; }
.crumbs button { border: 0; background: transparent; padding: 1px 4px; border-radius: 4px; cursor: pointer; color: var(--muted); }
.crumbs button:hover { background: var(--surface); color: var(--ink); }
.crumbs button:last-child { color: var(--ink); font-weight: 500; cursor: default; }
.crumbs i { font-style: normal; color: var(--faint); }
.tools { display: flex; align-items: center; gap: 8px; }
.tools .seg button { padding: 2px 8px; font-size: 11.5px; }
.tools > span { font-size: 11.5px; color: var(--faint); }
.map { position: relative; min-height: 0; margin: 6px; overflow: hidden; }
.status { padding: 6px 12px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); min-height: 30px; display: flex; gap: 8px; align-items: baseline; min-width: 0; }
.status .p { font-family: var(--mono); color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: none; max-width: 60%; }
.status .d { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.bx, .lf { position: absolute; overflow: hidden; border-radius: 4px; cursor: pointer; }
.bx { border: 1px solid var(--line); background: var(--panel); }
.bx.g { background: var(--surface); }
.bx.g.fo { background: var(--panel); border-style: dashed; }
.bx.root { border: 0; background: transparent; cursor: default; }
.bx.t { --bgl: 0.968; background: oklch(var(--bgl) 0.022 var(--h)); border-color: oklch(0.8 0.06 var(--h)); }
.bx.t.alt { --bgl: 0.94; }
.hd { height: 18px; display: flex; align-items: center; gap: 5px; padding: 0 5px; white-space: nowrap; font-family: var(--mono); font-size: 11.5px; line-height: 18px; overflow: hidden; }
.hd .fn { color: var(--muted); flex: none; }
.hd .tn { font-weight: 500; flex: none; }
.bx.t > .hd .tn { color: oklch(0.36 0.12 var(--h)); }
.bx.g > .hd { font-family: var(--sans); font-size: 12px; font-weight: 600; }
.bx.g > .hd .sm { font-family: var(--mono); font-weight: 400; color: var(--faint); font-size: 11px; }
.hd .mk { color: var(--accent); font-size: 11px; flex: none; }
.hd .cnt { margin-left: auto; padding-left: 6px; color: var(--faint); font-size: 10.5px; flex: none; }
.lf { background: var(--surface); border: 1px solid var(--line); padding: 2px 5px; font-family: var(--mono); line-height: 14px; }
.lf .fn { display: block; font-size: 11px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lf .ty { display: block; font-size: 10.5px; color: var(--faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lf.atom { background: oklch(0.975 0.018 var(--h)); border-color: oklch(0.82 0.05 var(--h)); }
.lf.atom .ty { color: oklch(0.42 0.1 var(--h)); }
.lf.val { border-style: dashed; }
.lf.tiny { padding: 0; }
.bx.hot, .lf.hot { outline: 2px solid var(--accent); outline-offset: -2px; z-index: 2; }
.bx.root.hot { outline: 0; }
:root[data-mode="dark"] .bx.t { --bgl: 0.25; background: oklch(var(--bgl) 0.035 var(--h)); border-color: oklch(0.42 0.06 var(--h)); }
:root[data-mode="dark"] .bx.t.alt { --bgl: 0.21; }
:root[data-mode="dark"] .bx.t > .hd .tn { color: oklch(0.88 0.08 var(--h)); }
:root[data-mode="dark"] .lf.atom { background: oklch(0.28 0.04 var(--h)); border-color: oklch(0.42 0.06 var(--h)); }
:root[data-mode="dark"] .lf.atom .ty { color: oklch(0.85 0.07 var(--h)); }
.side { display: grid; grid-template-rows: auto minmax(0, 1fr); min-width: 0; }
.side-b { overflow-y: auto; min-height: 0; padding: 10px 12px 12px; display: flex; flex-direction: column; gap: 10px; }
.side-b > * { flex: none; }
.side h2 { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 13px; }
.side .chip { cursor: pointer; }
.side .meta { display: grid; gap: 2px; font-family: var(--mono); font-size: 11px; color: var(--muted); word-break: break-word; }
.side .meta i { font-style: normal; color: var(--faint); }
.side p { margin: 0; line-height: 1.5; }
.side table { font-size: 11.5px; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; border-collapse: separate; border-spacing: 0; overflow: hidden; }
.side td { padding: 5px 8px; white-space: normal; text-align: left; }
.side td.fname { font-family: var(--mono); font-size: 11.5px; }
.side td .ftype { display: block; margin-top: 2px; color: var(--faint); font-family: var(--mono); font-size: 11px; }
.side td .ftype .chip { font-size: 10.5px; line-height: 15px; padding: 0 4px; }
.side td .fdesc { display: block; margin-top: 2px; color: var(--muted); }
.side tr.on td { background: var(--accent-soft); }
.side .sec { font-size: 11px; color: var(--faint); font-family: var(--mono); }
.side .grp { display: grid; gap: 5px; }
.chips { display: flex; flex-wrap: wrap; gap: 4px; }
.btn { align-self: flex-start; border: 1px solid var(--line); background: var(--surface); border-radius: 6px; padding: 3px 9px; font-size: 12px; cursor: pointer; }
.btn:hover { border-color: var(--faint); }
@media (max-width: 960px) {
  .stage { grid-template-columns: minmax(0, 1fr); grid-template-rows: none; height: auto; }
  .map { height: 520px; }
  .side-b { max-height: 560px; }
}
</style>`);

function renderBoxes(host, opts) {
  const { title = "Root", groups, index = [], atoms = [], src = "" } = opts;
  const ATOMS = new Set(atoms);
  const isClass = n => TYPES[n] && TYPES[n].kind !== "external";
  const classNames = Object.keys(TYPES).filter(isClass);
  host.innerHTML = `<div class="stage">
    <div class="pane mapcard">
      <div class="pane-h"><nav class="crumbs" aria-label="Zoom path"></nav>
        <div class="tools"><span>Depth</span><div class="seg depth" role="radiogroup" aria-label="Depth">
          ${[2, 3, 4, 99].map(d => `<button type="button" role="radio" data-depth="${d}" aria-checked="${d === 2}">${d === 99 ? "All" : d}</button>`).join("")}
        </div></div></div>
      <div class="map"></div>
      <div class="status"></div>
    </div>
    <aside class="pane side">
      <div class="pane-h"><span><b class="side-title"></b></span><span class="side-count"></span></div>
      <div class="side-b"></div>
    </aside></div>`;
  const $ = s => host.querySelector(s);
  const mapEl = $(".map"), statusEl = $(".status"), sideEl = $(".side-b"), crumbsEl = $(".crumbs");

  const boxRef = ty => { const r = refOf(ty); return r && !ATOMS.has(r) ? r : null; };
  const atomRef = ty => { const r = refOf(ty); return r && ATOMS.has(r) ? r : null; };
  const weigh = n => {
    n.w = n.kids ? n.kids.reduce((s, k) => s + k.w, 1) : 1;
    n.l = n.kids ? n.kids.reduce((s, k) => s + k.l, 0) : 1;
    return n;
  };
  const kidsOf = name => {
    const t = TYPES[name];
    if (t.values) return t.values.map(([k, d]) => weigh({ f: k, ty: "", d, owner: name, val: true }));
    if (t.members) return t.members.map(([label, m]) => fieldNode(label, m, TYPES[m].doc, name));
    return t.fields.map(([f, ty, d]) => fieldNode(f, ty, d, name));
  };
  const fieldNode = (f, ty, d, owner) => {
    const n = { f, ty, d, owner };
    const r = boxRef(ty);
    if (r) { n.type = r; n.kids = kidsOf(r); } else n.atom = atomRef(ty);
    return weigh(n);
  };
  const typeNode = name => weigh({ f: "", ty: name, type: name, kids: kidsOf(name) });
  const groupNode = g => Array.isArray(g)
    ? weigh({ group: g[0], sm: g[1], kids: g[2].map(typeNode) })
    : weigh({ group: g.folder, sm: g.sm, folder: true, kids: g.groups.map(groupNode) });
  const ROOT = weigh({ group: title, root: true, kids: groups.map(groupNode) });

  const worst = (row, s) => {
    const sum = row.reduce((t, r) => t + r.a, 0);
    const mx = Math.max(...row.map(r => r.a)), mn = Math.min(...row.map(r => r.a));
    return Math.max((s * s * mx) / (sum * sum), (sum * sum) / (s * s * mn));
  };
  const squarify = (items, x, y, w, h) => {
    const out = [];
    const total = items.reduce((s, n) => s + n.w, 0);
    if (!total || w <= 0 || h <= 0) return out;
    const scale = (w * h) / total;
    let rest = items.map(n => ({ n, a: n.w * scale })).sort((p, q) => q.a - p.a);
    while (rest.length) {
      const short = Math.min(w, h);
      const row = [rest[0]];
      let i = 1;
      while (i < rest.length && worst([...row, rest[i]], short) <= worst(row, short)) row.push(rest[i++]);
      const sum = row.reduce((s, r) => s + r.a, 0);
      if (w >= h) {
        const cw = sum / h;
        let yy = y;
        for (const r of row) { const ih = r.a / cw; out.push([r.n, x, yy, cw, ih]); yy += ih; }
        x += cw; w -= cw;
      } else {
        const rh = sum / w;
        let xx = x;
        for (const r of row) { const iw = r.a / rh; out.push([r.n, xx, y, iw, rh]); xx += iw; }
        y += rh; h -= rh;
      }
      rest = rest.slice(row.length);
    }
    return out;
  };
  const columns = (items, x, y, w, h) => {
    const total = items.reduce((s, n) => s + n.w, 0);
    let xx = x;
    return items.map(n => { const cw = (w * n.w) / total; const r = [n, xx, y, cw, h]; xx += cw; return r; });
  };

  const HEAD = 18, PAD = 3, GAP = 1.5;
  let path = [ROOT], maxDepth = 2, focus = null, hot = null;
  const backStack = [], forwardStack = [];
  const marks = ty => (/^list\[/.test(ty) ? `<span class="mk">[]</span>` : "") + (/\| None$/.test(ty) ? `<span class="mk">?</span>` : "");
  const nodeLabel = n => n.group ? n.group : n.type ? (n.f ? n.f + ": " : "") + n.type : n.f;

  function drawNode(n, x, y, w, h, depth) {
    const el = document.createElement("div");
    el._n = n;
    let style = `left:${x}px;top:${y}px;width:${w}px;height:${h}px;`;
    if (!n.kids) {
      el.className = "lf" + (n.atom ? " atom" : "") + (n.val ? " val" : "");
      if (n.atom) style += chipStyle(n.atom);
      if (w >= 26 && h >= 13) {
        const ty = n.val ? "" : n.ty;
        el.innerHTML = `<span class="fn">${treeEsc(n.f)}</span>` + (ty && h >= 30 ? `<span class="ty">${treeEsc(ty)}</span>` : "");
      } else el.classList.add("tiny");
      el.style.cssText = style;
      return el;
    }
    const top = depth === 0 && n.root;
    el.className = top ? "bx root" : n.folder ? "bx g fo" : n.group ? "bx g" : "bx t" + (depth % 2 ? " alt" : "");
    if (n.type) style += chipStyle(n.type);
    el.style.cssText = style;
    const head = top ? 0 : HEAD;
    const iw = w - 2 - 2 * PAD, ih = h - 2 - head - PAD;
    const open = depth < maxDepth && iw >= 24 && ih >= 14;
    if (!top) {
      const inner = n.group
        ? `<span class="tn">${treeEsc(n.group)}</span><span class="sm">${treeEsc(n.sm || "")}</span>`
        : (n.f ? `<span class="fn">${treeEsc(n.f)}</span>` : "") + `<span class="tn">${treeEsc(n.type)}</span>` + marks(n.ty);
      el.innerHTML = `<div class="hd">${inner}<span class="cnt">${open ? "" : n.l}</span></div>`;
    }
    if (open) {
      const lay = top ? columns : squarify;
      for (const [k, cx, cy, cw, ch] of lay(n.kids, PAD, top ? PAD : head, iw, ih)) {
        el.appendChild(drawNode(k, cx + GAP, cy + GAP, Math.max(0, cw - 2 * GAP), Math.max(0, ch - 2 * GAP), depth + (n.folder ? 0 : 1)));
      }
    }
    return el;
  }

  function draw() {
    const W = mapEl.clientWidth, H = mapEl.clientHeight;
    if (!W || !H) return;
    mapEl.innerHTML = "";
    hot = null;
    mapEl.appendChild(drawNode(path[path.length - 1], 0, 0, W, H, 0));
    crumbsEl.innerHTML = path.map((n, i) => `${i ? "<i>›</i>" : ""}<button type="button" data-i="${i}">${treeEsc(nodeLabel(n))}</button>`).join("");
  }
  function go(nextPath, nextFocus) {
    backStack.push({ path, focus });
    forwardStack.length = 0;
    path = nextPath; focus = nextFocus;
    draw(); drawSide();
  }
  function step(from, to) {
    if (!from.length) return;
    to.push({ path, focus });
    ({ path, focus } = from.pop());
    draw(); drawSide();
  }
  const goBack = () => step(backStack, forwardStack);
  const goForward = () => step(forwardStack, backStack);
  function zoomTo(i) {
    if (i < 0 || i >= path.length - 1) return;
    const n = path[i];
    go(path.slice(0, i + 1), n.type ? { type: n.type } : null);
  }
  function openType(name) {
    if (!isClass(name)) return;
    go([ROOT, typeNode(name)], { type: name });
  }
  const chainOf = el => {
    const out = [];
    for (let e = el; e && e !== mapEl; e = e.parentElement) if (e._n) out.unshift(e._n);
    return out;
  };
  const DEFAULT_STATUS = `<span class="d">Click a box to zoom in. Esc goes out. Mouse back and forward retrace your steps. Click a cell to see its field.</span>`;
  function setStatus(el) {
    if (!el) { statusEl.innerHTML = DEFAULT_STATUS; return; }
    const n = el._n;
    const p = [...path.slice(0, -1), ...chainOf(el)].filter(x => !x.root).map(nodeLabel).join(" › ");
    const d = n.group ? n.sm || "" : n.d || (n.type && TYPES[n.type].doc) || "";
    statusEl.innerHTML = `<span class="p">${treeEsc(p || title)}</span><span class="d">${treeEsc(d)}</span>`;
  }

  function usedIn(name) {
    const out = [];
    for (const [owner, t] of Object.entries(TYPES)) {
      if (!isClass(owner)) continue;
      for (const [f, ty, , fl] of t.fields || []) if (refOf(ty) === name && !(fl && fl.base)) out.push([owner, f]);
      for (const [label, m] of t.members || []) if (m === name) out.push([owner, label]);
    }
    return out;
  }
  function drawSide() {
    const titleEl = $(".side-title"), countEl = $(".side-count");
    sideEl.scrollTop = 0;
    if (!focus) {
      titleEl.textContent = "All classes";
      countEl.textContent = `${classNames.length}`;
      sideEl.innerHTML = `<div class="legend" style="display:grid;gap:4px">
          <span>A box is a class. A cell is a field.</span>
          <span>Size is the number of fields a box holds, down to the last level.</span>
          ${atoms.length ? `<span>${atoms.map(a => chip(a)).join(" ")} cells: one value, not opened.</span>` : ""}
          <span>Dashed cell: an enum value. <span style="color:var(--accent)">[]</span> list. <span style="color:var(--accent)">?</span> can be None.</span>
        </div>`
        + index.map(([label, file, names]) => `<div class="grp"><div class="sec">${treeEsc(label)} · ${treeEsc(file)} · ${names.length}</div><div class="chips">${names.map(typeChip).join("")}</div></div>`).join("");
      return;
    }
    const name = focus.type;
    const t = TYPES[name];
    titleEl.textContent = name;
    const rows = t.values ? t.values.map(([k, d]) => [k, "", d, {}])
      : t.members ? t.members.map(([label, m]) => [label, m, TYPES[m].doc, {}]) : t.fields;
    countEl.textContent = `${rows.length} ${t.values ? "values" : t.members ? "members" : "fields"}`;
    const used = usedIn(name);
    const extendedBy = classNames.filter(n => TYPES[n].base === name);
    sideEl.innerHTML = `
      <h2>${typeChip(name)}${t.py ? `<span class="fl">${treeEsc(t.py)}</span>` : ""}${t.change ? `<span class="fl a">${treeEsc(t.change)}</span>` : ""}</h2>
      <div class="meta">
        ${t.file ? `<span><i>file </i>${treeEsc(src + t.file)}</span>` : ""}
        ${t.by ? `<span><i>built by </i>${treeEsc(t.by)}</span>` : ""}
        ${t.base ? `<span><i>extends </i>${typeChip(t.base)}</span>` : ""}
      </div>
      ${t.doc ? `<p>${treeEsc(t.doc)}</p>` : ""}
      <table><tbody>${rows.map(([f, ty, d, fl]) => `<tr${focus.field === f ? ' class="on"' : ""}><td class="fname">${treeEsc(f)}${fl && fl.base ? ` <span class="fl">from ${treeEsc(fl.base)}</span>` : ""}${ty ? `<span class="ftype">${typeHtml(ty)}</span>` : ""}<span class="fdesc">${treeEsc(d || "")}</span></td></tr>`).join("")}</tbody></table>
      ${used.length ? `<div class="grp"><div class="sec">Used in · ${used.length}</div><div class="chips">${used.map(([o, f]) => `<span>${typeChip(o)}<span class="sec"> .${treeEsc(f)}</span></span>`).join("")}</div></div>` : ""}
      ${extendedBy.length ? `<div class="grp"><div class="sec">Extended by</div><div class="chips">${extendedBy.map(typeChip).join("")}</div></div>` : ""}
      <button type="button" class="btn" data-home>All classes</button>`;
    const on = sideEl.querySelector("tr.on");
    if (on) on.scrollIntoView({ block: "nearest" });
  }

  crumbsEl.addEventListener("click", e => { const b = e.target.closest("button"); if (b) zoomTo(+b.dataset.i); });
  mapEl.addEventListener("mouseover", e => {
    const el = e.target.closest(".bx, .lf");
    if (el === hot) return;
    if (hot) hot.classList.remove("hot");
    hot = el;
    if (hot) hot.classList.add("hot");
    setStatus(hot && !hot.classList.contains("root") ? hot : null);
  });
  mapEl.addEventListener("mouseleave", () => { if (hot) hot.classList.remove("hot"); hot = null; setStatus(null); });
  mapEl.addEventListener("click", e => {
    const el = e.target.closest(".bx, .lf");
    if (!el) return;
    const n = el._n;
    if (!n.kids) { go(path, { type: n.owner, field: n.f }); return; }
    const chain = chainOf(el);
    if (chain.length < 2) return;
    go(path.concat(chain.slice(1)), n.type ? { type: n.type } : null);
  });
  document.addEventListener("keydown", e => {
    if (!host.offsetParent) return;
    if (e.key === "Escape") zoomTo(path.length - 2);
    else if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); goBack(); }
    else if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); goForward(); }
  });
  const isSideButton = e => e.button === 3 || e.button === 4;
  document.addEventListener("mousedown", e => { if (isSideButton(e) && host.offsetParent) e.preventDefault(); });
  document.addEventListener("mouseup", e => {
    if (!isSideButton(e) || !host.offsetParent) return;
    e.preventDefault();
    e.button === 3 ? goBack() : goForward();
  });
  sideEl.addEventListener("click", e => {
    if (e.target.closest("[data-home]")) { go([ROOT], null); return; }
    const c = e.target.closest(".chip");
    if (c) openType(c.textContent);
  });
  host.querySelectorAll(".depth button").forEach(b => b.addEventListener("click", () => {
    maxDepth = +b.dataset.depth;
    host.querySelectorAll(".depth button").forEach(x => x.setAttribute("aria-checked", String(x === b)));
    draw();
  }));

  let raf = 0;
  new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); }).observe(mapEl);
  statusEl.innerHTML = DEFAULT_STATUS;
  draw();
  drawSide();
  return { openType, zoomTo, goBack, goForward };
}
