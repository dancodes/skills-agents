document.head.insertAdjacentHTML("beforeend", `<style>
.tm-pane { display: grid; min-width: 0; }
.tm-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 6px 12px; padding: 6px 12px; border-bottom: 1px solid var(--line); }
.tm-crumbs { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 2px 6px; font-size: 12px; min-width: 0; color: var(--muted); }
.tm-crumbs b { color: var(--ink); font-weight: 600; }
.tm-crumbs .tm-cs { font-family: var(--mono); font-size: 11px; color: var(--faint); }
.tm-crumbs button { border: 0; background: none; padding: 0; color: var(--accent); cursor: pointer; font-size: 12px; }
.tm-crumbs button:hover { text-decoration: underline; }
.tm-crumbs i { font-style: normal; color: var(--faint); }
.tm-ctrls { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; }
.tm-ctrls .tm-lbl { font-size: 11px; color: var(--faint); }
.tm-ctrls .seg button { padding: 2px 8px; font-size: 11.5px; }
.tm-stage { position: relative; margin: 6px; overflow: hidden; }
.tm-grp, .tm-tile, .tm-blk { position: absolute; box-sizing: border-box; overflow: hidden; }
.tm-grp { border-radius: 4px; border: 1px solid oklch(0.78 0.04 var(--h)); background: oklch(0.955 0.012 var(--h)); }
.tm-grp.tm-d2, .tm-grp.tm-d3 { background: oklch(0.975 0.006 var(--h)); border-color: oklch(0.84 0.03 var(--h)); }
:root[data-mode="dark"] .tm-grp { background: oklch(0.22 0.015 var(--h)); border-color: oklch(0.38 0.04 var(--h)); }
:root[data-mode="dark"] .tm-grp.tm-d2, :root[data-mode="dark"] .tm-grp.tm-d3 { background: oklch(0.245 0.012 var(--h)); border-color: oklch(0.33 0.03 var(--h)); }
.tm-gh { all: unset; box-sizing: border-box; position: absolute; left: 0; right: 0; top: 0; height: 19px; display: flex; align-items: center; gap: 5px; padding: 0 6px; cursor: zoom-in; overflow: hidden; white-space: nowrap; }
.tm-gh:hover .tm-gl { text-decoration: underline; }
.tm-gh:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.tm-gd { width: 7px; height: 7px; border-radius: 50%; flex: none; background: oklch(0.62 0.12 var(--h)); }
.tm-gl { font-size: 11.5px; font-weight: 600; color: var(--ink); overflow: hidden; text-overflow: ellipsis; flex: 0 1 auto; min-width: 0; }
.tm-gs { font-family: var(--mono); font-size: 10.5px; color: var(--faint); flex: 0 100 auto; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.tm-tile { border: 1px solid var(--bg); border-radius: 3px; padding: 2px 4px; display: flex; flex-direction: column; }
.tm-tile:hover, .tm-blk:hover { outline: 2px solid var(--ink); outline-offset: -2px; z-index: 2; }
.tm-tile .tm-nm { font-family: var(--mono); font-size: 11px; line-height: 14px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tm-tile .tm-ln { font-family: var(--mono); font-size: 10.5px; line-height: 13px; color: var(--muted); white-space: nowrap; }
.tm-blk { border-radius: 4px; border: 1px solid oklch(0.72 0.07 var(--h)); background: oklch(0.9 0.045 var(--h)); padding: 4px 7px 10px; cursor: zoom-in; display: flex; flex-direction: column; gap: 1px; }
:root[data-mode="dark"] .tm-blk { background: oklch(0.33 0.055 var(--h)); border-color: oklch(0.5 0.07 var(--h)); }
.tm-blk .tm-bl { font-size: 12px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tm-blk .tm-bs { font-family: var(--mono); font-size: 10.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tm-blk .tm-bd { font-size: 11px; line-height: 1.35; color: var(--muted); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; margin-top: 2px; }
.tm-blk .tm-bar { position: absolute; left: 0; right: 0; bottom: 0; height: 6px; display: flex; border-top: 1px solid var(--bg); }
.tm-blk .tm-bar i { height: 100%; box-shadow: inset -1px 0 0 var(--bg); }
.tm-hue.tm-t0 { background: oklch(0.86 0.06 var(--h)); }
.tm-hue.tm-t1 { background: oklch(0.81 0.075 var(--h)); }
.tm-hue.tm-t2 { background: oklch(0.9 0.045 var(--h)); }
:root[data-mode="dark"] .tm-hue.tm-t0 { background: oklch(0.4 0.07 var(--h)); }
:root[data-mode="dark"] .tm-hue.tm-t1 { background: oklch(0.35 0.07 var(--h)); }
:root[data-mode="dark"] .tm-hue.tm-t2 { background: oklch(0.45 0.06 var(--h)); }
.tm-ok { background: var(--ok-soft); } .tm-crit { background: var(--crit-soft); } .tm-warn { background: var(--warn-soft); }
.tm-acc { background: var(--accent-soft); } .tm-grey { background: var(--line); } .tm-plain { background: var(--surface); }
.tm-tile.tm-ok { box-shadow: inset 3px 0 0 var(--ok); } .tm-tile.tm-crit { box-shadow: inset 3px 0 0 var(--crit); }
.tm-tile.tm-warn { box-shadow: inset 3px 0 0 var(--warn); } .tm-tile.tm-acc { box-shadow: inset 3px 0 0 var(--accent); }
.tm-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; padding: 7px 12px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); }
.tm-legend > span { display: inline-flex; gap: 5px; align-items: center; }
.tm-sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; border: 1px solid var(--line); }
.tm-legend .tm-sz { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--faint); }
.tm-tip { position: absolute; z-index: 10; max-width: 340px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; box-shadow: 0 6px 20px rgb(0 0 0 / 0.14); pointer-events: none; display: grid; gap: 3px; }
.tm-tip .tm-tp { font-size: 11px; color: var(--faint); }
.tm-tip .tm-tn { font-family: var(--mono); font-size: 12.5px; font-weight: 500; overflow-wrap: anywhere; }
.tm-tip .tm-tl { font-family: var(--mono); font-size: 11.5px; color: var(--muted); }
.tm-tip .tm-td { font-size: 12px; line-height: 1.45; }
.tm-tip .tm-tt { display: flex; flex-wrap: wrap; gap: 4px; }
</style>`);

function renderTreemap(el, opts) {
  const o = Object.assign({
    depths: [1, 2, "all"],
    depth: "all",
    height: "max(460px, calc(100vh - 250px))",
    unit: ["item", "items"],
    leafLine: () => "",
    groupLine: null,
    leafTip: () => "",
  }, opts);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const root = o.root;
  (function link(g, top) {
    g.items.forEach((it, i) => {
      it.parent = g;
      it.top = top || (it.items ? it : null);
      it.tier = it.items ? i % 3 : (g.tier || 0);
      if (it.items) link(it, it.top);
    });
  })(root, null);

  let size = o.sizes[0], color = o.colors[0], focus = root;
  let maxDepth = o.depth === "all" ? Infinity : o.depth;
  const hueOf = key => +(chipStyle(key).match(/--h:(\d+)/) || [0, 250])[1];
  const leafHue = l => hueOf((l.top || l.parent).key);
  const leafVal = l => Math.max(+size.value(l) || 0, 0);
  const val = n => n.items ? n.items.reduce((a, c) => a + val(c), 0) : leafVal(n);
  const leavesOf = n => { const out = []; (function w(g) { g.items.forEach(i => i.items ? w(i) : out.push(i)); })(n); return out; };
  const count = n => { const k = leavesOf(n).length; return `${k} ${o.unit[k === 1 ? 0 : 1]}`; };
  const groupLine = n => o.groupLine ? o.groupLine(n, leavesOf(n)) : count(n);
  const leafCls = l => color.cls ? color.cls(l) || "tm-plain" : "tm-hue tm-t" + l.tier;
  const trail = n => { const p = []; for (let x = n.parent; x && x !== root; x = x.parent) p.unshift(x.label); return p.join(" › "); };
  const tagsHtml = tags => tags.length ? `<div class="tm-tt">${tags.map(([c, s]) => `<span class="fl ${c}">${esc(s)}</span>`).join(" ")}</div>` : "";

  const segHtml = (name, list, cur, lab) => `<span class="tm-lbl">${name}</span><span class="seg" role="radiogroup" aria-label="${name}">`
    + list.map(x => `<button type="button" role="radio" data-k="${name}" data-v="${esc(x.id ?? x)}" aria-checked="${(x.id ?? x) === cur}">${esc(lab(x))}</button>`).join("") + `</span>`;
  el.classList.add("pane", "tm-pane");
  el.innerHTML = `<div class="tm-head"><span class="tm-crumbs"></span><span class="tm-ctrls">`
    + (o.depths.length > 1 ? segHtml("Depth", o.depths, o.depth, d => d === "all" ? "All" : d) : "")
    + (o.sizes.length > 1 ? segHtml("Size", o.sizes, size.id, s => s.label) : "")
    + (o.colors.length > 1 ? segHtml("Color", o.colors, color.id, c => c.label) : "")
    + `</span></div><div class="tm-stage" style="height:${o.height}"><div class="tm-tip" hidden></div></div><div class="tm-legend"></div>`;
  const stage = el.querySelector(".tm-stage"), tip = el.querySelector(".tm-tip");

  function worst(row, side) {
    const s = row.reduce((a, b) => a + b, 0);
    return Math.max(side * side * Math.max(...row) / (s * s), (s * s) / (side * side * Math.min(...row)));
  }
  function layoutRow(row, r, out) {
    const s = row.reduce((a, b) => a + b, 0);
    if (r.w >= r.h) {
      const cw = s / r.h; let y = r.y;
      row.forEach(a => { out.push({ x: r.x, y, w: cw, h: a / cw }); y += a / cw; });
      return { x: r.x + cw, y: r.y, w: r.w - cw, h: r.h };
    }
    const rh = s / r.w; let x = r.x;
    row.forEach(a => { out.push({ x, y: r.y, w: a / rh, h: rh }); x += a / rh; });
    return { x: r.x, y: r.y + rh, w: r.w, h: r.h - rh };
  }
  function squarify(values, rect) {
    const total = values.reduce((a, b) => a + b, 0);
    if (total <= 0 || rect.w <= 0 || rect.h <= 0) return values.map(() => null);
    const areas = values.map(v => v * rect.w * rect.h / total);
    const out = []; let r = { ...rect }, row = [], i = 0;
    while (i < areas.length) {
      const side = Math.min(r.w, r.h);
      if (!row.length || worst([...row, areas[i]], side) <= worst(row, side)) { row.push(areas[i]); i++; }
      else { r = layoutRow(row, r, out); row = []; }
    }
    if (row.length) layoutRow(row, r, out);
    return out;
  }

  const box = (cls, r, hue) => {
    const d = document.createElement("div");
    d.className = cls;
    d.style.cssText = `left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px;--h:${hue}`;
    return d;
  };
  const HEAD = 19, PAD = 3;
  function draw(n, r, depth, frag) {
    if (!r || r.w < 1 || r.h < 1) return;
    if (!n.items) {
      const d = box("tm-tile " + leafCls(n), r, leafHue(n));
      d.leaf = n;
      if (r.w > 34 && r.h > 15) {
        const line = r.w > 70 && r.h > 32 ? o.leafLine(n) : "";
        d.innerHTML = `<span class="tm-nm">${esc(n.name)}</span>` + (line ? `<span class="tm-ln">${esc(line)}</span>` : "");
      }
      frag.appendChild(d);
      return;
    }
    if (n !== focus && depth >= maxDepth) return drawBlock(n, r, frag);
    let inner = r;
    if (n !== focus) {
      const g = box("tm-grp tm-d" + Math.min(depth, 3), r, hueOf((n.top || n).key));
      if (r.w > 44 && r.h > HEAD + 10) {
        g.innerHTML = `<button type="button" class="tm-gh" title="Zoom into ${esc(n.label)}"><span class="tm-gd"></span><span class="tm-gl">${esc(n.label)}</span><span class="tm-gs">${esc(groupLine(n))}</span></button>`;
        g.firstChild.addEventListener("click", () => zoom(n));
        inner = { x: r.x + PAD, y: r.y + HEAD, w: r.w - PAD * 2, h: r.h - HEAD - PAD };
      } else {
        inner = { x: r.x + 1, y: r.y + 1, w: r.w - 2, h: r.h - 2 };
      }
      frag.appendChild(g);
    }
    const kids = n.items.filter(k => val(k) > 0).sort((a, b) => val(b) - val(a));
    const rects = squarify(kids.map(val), inner);
    kids.forEach((k, i) => draw(k, rects[i], depth + 1, frag));
  }
  function drawBlock(n, r, frag) {
    const b = box("tm-blk", r, hueOf((n.top || n).key));
    b.group = n;
    const leaves = leavesOf(n).filter(l => leafVal(l) > 0), total = leaves.reduce((a, l) => a + leafVal(l), 0);
    const bar = leaves.map(l => `<i class="${leafCls(l)}" style="width:${(leafVal(l) / total * 100).toFixed(3)}%;--h:${leafHue(l)}"></i>`).join("");
    b.innerHTML = (r.w > 40 && r.h > 22 ? `<span class="tm-bl">${esc(n.label)}</span>` : "")
      + (r.w > 70 && r.h > 40 ? `<span class="tm-bs">${esc(groupLine(n))}</span>` : "")
      + (n.doc && r.w > 140 && r.h > 80 ? `<span class="tm-bd">${esc(n.doc)}</span>` : "")
      + `<span class="tm-bar">${bar}</span>`;
    b.addEventListener("click", () => zoom(n));
    frag.appendChild(b);
  }

  function render() {
    stage.querySelectorAll(".tm-tile, .tm-grp, .tm-blk").forEach(e => e.remove());
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    const frag = document.createDocumentFragment();
    draw(focus, { x: 0, y: 0, w, h }, 0, frag);
    stage.insertBefore(frag, tip);
    const path = [];
    for (let n = focus; n; n = n.parent) path.unshift(n);
    const crumbs = el.querySelector(".tm-crumbs");
    crumbs.innerHTML = path.map((n, i) => i === path.length - 1
      ? `<b>${esc(n.label)}</b> <span class="tm-cs">${esc(groupLine(n))}</span>`
      : `<button type="button" data-i="${i}">${esc(n.label)}</button><i>›</i>`).join("");
    crumbs.querySelectorAll("button").forEach(b => b.addEventListener("click", () => zoom(path[+b.dataset.i])));
    const legend = color.legend
      ? color.legend.map(([c, l]) => `<span><i class="tm-sw ${c}"></i>${esc(l)}</span>`)
      : root.items.filter(g => g.items).map(g => `<span><i class="tm-sw tm-hue tm-t0" style="--h:${hueOf(g.key)}"></i>${esc(g.label)}</span>`);
    el.querySelector(".tm-legend").innerHTML = legend.join("") + `<span class="tm-sz">Tile area = ${esc(size.note || size.label)}</span>`;
  }
  function zoom(n) { focus = n; tip.hidden = true; render(); }

  function placeTip(e) {
    tip.hidden = false;
    const b = stage.getBoundingClientRect();
    let x = e.clientX - b.left + 14, y = e.clientY - b.top + 14;
    if (x + tip.offsetWidth > b.width - 4) x = e.clientX - b.left - tip.offsetWidth - 14;
    if (y + tip.offsetHeight > b.height - 4) y = e.clientY - b.top - tip.offsetHeight - 14;
    tip.style.left = Math.max(4, x) + "px";
    tip.style.top = Math.max(4, y) + "px";
  }
  function leafTipHtml(l) {
    const t = trail(l), line = o.leafLine(l);
    return (t ? `<div class="tm-tp">${esc(t)}</div>` : "") + `<div class="tm-tn">${esc(l.name)}</div>`
      + (line ? `<div class="tm-tl">${esc(line)}</div>` : "") + o.leafTip(l)
      + (l.d ? `<div class="tm-td">${esc(l.d)}</div>` : "") + tagsHtml(l.tags || []);
  }
  function groupTipHtml(n) {
    const counts = {};
    leavesOf(n).forEach(l => (l.tags || []).forEach(([c, s]) => { counts[s] = counts[s] || [c, 0]; counts[s][1]++; }));
    const t = trail(n);
    return (t ? `<div class="tm-tp">${esc(t)}</div>` : "") + `<div class="tm-tn">${esc(n.label)}</div>`
      + `<div class="tm-tl">${esc(groupLine(n))}</div>` + (n.doc ? `<div class="tm-td">${esc(n.doc)}</div>` : "")
      + tagsHtml(Object.entries(counts).map(([s, [c, k]]) => [c, `${s} ×${k}`])) + `<div class="tm-tp">Click to zoom in</div>`;
  }
  stage.addEventListener("mousemove", e => {
    const t = e.target.closest(".tm-tile, .tm-blk");
    if (!t) { tip.hidden = true; return; }
    tip.innerHTML = t.leaf ? leafTipHtml(t.leaf) : groupTipHtml(t.group);
    placeTip(e);
  });
  stage.addEventListener("mouseleave", () => { tip.hidden = true; });
  stage.addEventListener("click", e => {
    const t = e.target.closest(".tm-tile");
    if (t && t.leaf && t.leaf.parent !== focus) zoom(t.leaf.parent);
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && focus.parent && el.offsetParent) zoom(focus.parent);
  });
  el.querySelectorAll(".tm-ctrls [data-k]").forEach(b => b.addEventListener("click", () => {
    el.querySelectorAll(`.tm-ctrls [data-k="${b.dataset.k}"]`).forEach(x => x.setAttribute("aria-checked", String(x === b)));
    const v = b.dataset.v;
    if (b.dataset.k === "Depth") maxDepth = v === "all" ? Infinity : +v;
    if (b.dataset.k === "Size") size = o.sizes.find(s => s.id === v);
    if (b.dataset.k === "Color") color = o.colors.find(c => c.id === v);
    render();
  }));
  new ResizeObserver(render).observe(stage);
  render();
  return { render, zoom, root };
}

function treemapTypes(root, leafRow, countLabel = (g, n) => `${n} items`) {
  const types = {};
  const tally = g => {
    let n = 0;
    g.items.forEach(it => { n += it.items ? tally(it) : 1; });
    types[g.key] = {
      title: g.label,
      doc: g.doc,
      label: countLabel(g, n),
      fields: g.items.map(it => it.items ? ["", it.key, "", {}] : leafRow(it)),
    };
    return n;
  };
  root.items.forEach(tally);
  return types;
}
