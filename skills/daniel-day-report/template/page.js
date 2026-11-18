const R = REPORT;
const TASKS_ORDER = R.tasks_order;
const T0 = R.axis.t0, T1 = R.axis.t1;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const hue = n => +/--h:(\d+)/.exec(chipStyle(n))[1];
const mk = n => `oklch(0.7 0.11 ${hue(n)})`;
const hm = m => { m = Math.round(m); return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); };
const dur = m => { m = Math.round(m); return m < 60 ? m + " min" : Math.floor(m / 60) + " h " + String(m % 60).padStart(2, "0") + " min"; };
const $ = id => document.getElementById(id);
const S = R.sessions.slice().sort((a, b) => TASKS_ORDER.indexOf(a.task) - TASKS_ORDER.indexOf(b.task) || a.start - b.start);

$("kpis").innerHTML = R.kpis.map(([v, t]) => `<li><b class="v">${esc(v)}</b><span>${esc(t)}</span></li>`).join("");

function drawTimeline() {
  const el = $("tl"), W = el.clientWidth - 16;
  if (W < 200) return;
  const L = 140, R0 = 24, RH = 21, x = m => L + (m - T0) / (T1 - T0) * (W - L - R0);
  let y = 24, o = "";
  const rows = S.map(s => { const r = { s, y }; y += RH; return r; });
  y += 8;
  const yG = y, yL = y + 20, yJ = y + 42, yP = y + 58, H = y + 76;
  const all = S.flatMap(s => s.prompts).sort((a, b) => a - b);
  for (let i = 1; i < all.length; i++) if (all[i] - all[i - 1] >= 20) {
    o += `<rect class="away" x="${x(all[i - 1])}" y="18" width="${x(all[i]) - x(all[i - 1])}" height="${yG - 22}"><title>No prompt ${hm(all[i - 1])}–${hm(all[i])} (${Math.round(all[i] - all[i - 1])} min)</title></rect>`;
  }
  const step = Math.max(1, Math.ceil((T1 - T0) / 60 * 44 / (W - L - R0)));
  for (let h = T0 / 60; h <= T1 / 60; h += step) o += `<line class="grid" x1="${x(h * 60)}" x2="${x(h * 60)}" y1="18" y2="${H - 4}"/><text x="${x(h * 60)}" y="11" text-anchor="middle">${h}:00</text>`;
  for (const { s, y } of rows) {
    const c = mk(s.task);
    o += `<rect x="6" y="${y + 6}" width="8" height="8" rx="2" fill="${c}"/><text class="lab" x="20" y="${y + 14}">${esc(s.label)}</text>`;
    for (const [a, b] of s.idle) o += `<rect class="stop" x="${x(a)}" y="${y + 5}" width="${Math.max(1, x(b) - x(a))}" height="10" rx="2"><title>${esc(s.label)} · stopped ${hm(a)}–${hm(b)} (${Math.round(b - a)} min)</title></rect>`;
    for (const [a, b] of s.work) o += `<rect x="${x(a)}" y="${y + 5}" width="${Math.max(1.5, x(b) - x(a))}" height="10" rx="2" fill="${c}"><title>${esc(s.label)} · work ${hm(a)}–${hm(b)} (${Math.round(b - a)} min)</title></rect>`;
    for (const p of s.prompts) o += `<line class="tick" x1="${x(p)}" x2="${x(p)}" y1="${y + 2}" y2="${y + 18}"><title>prompt ${hm(p)}</title></line>`;
    if (s.result && s.result.state !== "ok" && x(s.end) + 90 < W) o += `<text x="${x(s.end) + 6}" y="${y + 14}" style="fill:var(--${s.result.state === "crit" ? "crit" : "warn"})">${esc(s.result.text.length > 24 ? s.result.text.slice(0, 23) + "…" : s.result.text)}</text>`;
  }
  o += `<text class="grp" x="6" y="${yG + 12}">GitLab</text><text class="grp" x="6" y="${yL + 12}">Linear</text><text class="grp" x="6" y="${yJ + 10}">jj operations</text><text class="grp" x="6" y="${yP + 10}">prompts</text>`;
  const grp = {};
  for (const e of R.gitlab) { const k = Math.round(e.t) + "|" + e.a; (grp[k] = grp[k] || []).push(e); }
  for (const k in grp) {
    const g = grp[k], e = g[0], cx = x(e.t), cy = yG + 8, n = g.length;
    const tip = `<title>${hm(e.t)} ${esc(e.a)} ${g.map(v => (v.iid ? "!" + v.iid + " " : "") + esc(v.title)).join(" · ")}</title>`;
    if (e.a === "accepted") o += `<circle cx="${cx}" cy="${cy}" r="4.5" style="fill:var(--ok)">${tip}</circle>`;
    else if (e.a === "opened") o += `<path d="M${cx} ${cy - 5}l5 5l-5 5l-5 -5z" style="fill:var(--accent)">${tip}</path>` + (n > 1 ? `<text x="${cx + 7}" y="${cy + 4}">×${n}</text>` : "");
    else if (e.a === "approved") o += `<circle cx="${cx}" cy="${cy}" r="3.5" style="fill:var(--surface);stroke:var(--muted);stroke-width:1.4">${tip}</circle>`;
    else if (e.a === "closed") o += `<path d="M${cx - 3} ${cy - 3}l6 6m0 -6l-6 6" style="stroke:var(--crit);stroke-width:1.6;fill:none">${tip}</path>`;
    else if (e.a === "pushed") o += `<line x1="${cx}" x2="${cx}" y1="${cy - 5}" y2="${cy + 5}" style="stroke:var(--faint);stroke-width:1.5">${tip}</line>`;
  }
  const lg = {};
  for (const t of R.linear.filter(t => t.created != null)) (lg[Math.round(t.created)] = lg[Math.round(t.created)] || []).push(t.id);
  for (const t in lg) o += `<rect x="${x(+t) - 3}" y="${yL + 5}" width="6" height="6" style="fill:var(--ink)"><title>${hm(+t)} created ${esc(lg[t].join(", "))}</title></rect>` + (lg[t].length > 1 ? `<text x="${x(+t) + 6}" y="${yL + 12}">×${lg[t].length}</text>` : "");
  const bw = x(10) - x(0), maxO = Math.max(1, ...R.ops.map(v => v[1]));
  for (const [b, n] of R.ops) if (b * 10 >= T0 && b * 10 < T1) o += `<rect x="${x(b * 10)}" y="${yJ}" width="${bw - 1}" height="12" style="fill:var(--accent)" opacity="${0.15 + 0.85 * n / maxO}"><title>${hm(b * 10)} ${n} jj operations</title></rect>`;
  const pb = {};
  for (const p of all) pb[Math.floor(p / 10)] = (pb[Math.floor(p / 10)] || 0) + 1;
  const maxP = Math.max(1, ...Object.values(pb));
  for (const b in pb) o += `<rect x="${x(b * 10)}" y="${yP}" width="${bw - 1}" height="12" style="fill:var(--ink)" opacity="${0.15 + 0.85 * pb[b] / maxP}"><title>${hm(b * 10)} ${pb[b]} prompts</title></rect>`;
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="Timeline of sessions"><defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" style="fill:var(--crit-soft)"/><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(--crit);stroke-width:1.6"/></pattern></defs>${o}</svg>`;
}

const maxS = Math.max(1, ...S.map(s => s.work_min + s.idle_min));
$("ws").innerHTML = S.map(s => `<div class="brow"><span class="nm"><i class="sw" style="background:${mk(s.task)};width:8px;height:8px;margin-right:6px"></i>${esc(s.label)}</span><span class="track"><i style="width:${s.work_min / maxS * 100}%;background:${mk(s.task)}" title="work ${s.work_min} min"></i><i class="b-stop" style="width:${s.idle_min / maxS * 100}%" title="stopped ${s.idle_min} min"></i></span><span class="num"><b>${s.work_min}</b> · ${s.idle_min}</span></div>`).join("");
$("wsTot").textContent = "work · stopped";
$("taskLegend").innerHTML = TASKS_ORDER.map(t => `<span>${chip(t)}</span>`).join("");
{
  const bins = {}; let mx = 1;
  for (const s of S) for (const p of s.prompts) { const b = Math.floor(p / 30); (bins[b] = bins[b] || {})[s.task] = (bins[b][s.task] || 0) + 1; }
  const list = []; for (let b = T0 / 30; b < T1 / 30; b++) { const v = bins[b] || {}; const n = Object.values(v).reduce((a, c) => a + c, 0); mx = Math.max(mx, n); list.push([b, v, n]); }
  const every = list.length > 24 ? 4 : 2;
  $("cols").innerHTML = list.map(([b, v, n]) => `<div class="c" title="${hm(b * 30)} · ${n} prompts">${TASKS_ORDER.filter(t => v[t]).map(t => `<i style="height:${v[t] / mx * 120}px;background:${mk(t)}"></i>`).join("")}${n ? `<span style="bottom:${n / mx * 120 + 2}px">${n}</span>` : ""}</div>`).join("");
  $("colx").innerHTML = list.map(([b]) => `<span>${b % every ? "" : b / 2}</span>`).join("");
}

const F = R.finds.slice().sort((a, b) => b.min - a.min);
F.forEach((f, i) => { f.i = i; });
const KIND = { "user-wait": "Stopped for you", "agent-slow": "Slow agent work", rework: "Rework", "scope-creep": "Off-scope work", "waiting-on-ci-or-review": "CI", "tool-failure": "Tool failure", "unclear-prompt": "Unclear question", other: "Other" };
let filt = null;
function agg(key) { const m = {}; for (const f of F) m[key(f)] = (m[key(f)] || 0) + f.min; return Object.entries(m).sort((a, b) => b[1] - a[1]); }
function bars(id, rows, dim) {
  if (!rows.length) { $(id).innerHTML = `<div class="brow"><span class="nm">no findings</span></div>`; return; }
  const mx = rows[0][1];
  $(id).innerHTML = rows.map(([n, v]) => `<div class="brow click${filt && filt[0] === dim && filt[1] === n ? " on" : filt && filt[0] === dim ? " dim" : ""}" data-dim="${dim}" data-v="${esc(n)}"><span class="nm">${dim === "task" ? chip(n) : esc(dim === "kind" ? KIND[n] || n : n)}</span><span class="track"><i style="width:${v / mx * 100}%;background:${dim === "kind" ? "var(--muted)" : mk(n)};border-radius:3px"></i></span><span class="num"><b>${Math.round(v)}</b></span></div>`).join("");
}
function drawWaste() {
  bars("bTheme", agg(f => f.theme), "theme"); bars("bKind", agg(f => f.kind), "kind"); bars("bTask", agg(f => f.task), "task");
  const rows = F.filter(f => !filt || (filt[0] === "theme" ? f.theme : filt[0] === "kind" ? f.kind : f.task) === filt[1]);
  const mx = (F[1] || F[0] || { min: 1 }).min || 1;
  $("fBody").innerHTML = rows.map((f, n) => `<tr class="f" data-i="${f.i}"><td class="n">${n + 1}</td><td class="l mono"><i class="fbar" style="width:${Math.min(f.min, mx) / mx * 90}px;background:${mk(f.theme)}"></i>${f.min}</td><td class="l">${chip(f.theme, "enum")}</td><td class="l">${chip(f.task)} <span class="s">${esc(f.label.replace(f.task, "").trim())}</span></td><td class="l mono">${esc(f.start)}</td><td class="l wrap">${esc(f.short)}</td></tr>`).join("");
  $("fCount").textContent = rows.length + " findings · " + Math.round(rows.reduce((a, f) => a + f.min, 0)) + " min";
  $("fFilter").textContent = filt ? (filt[0] === "kind" ? KIND[filt[1]] || filt[1] : filt[1]) : "all";
  $("thTot").textContent = Math.round(F.reduce((a, f) => a + f.min, 0)) + " min";
}
drawWaste();
$("wasteFoot").textContent = "Minutes are for each session. Sessions ran in parallel, so the sum is more than wall time." + (R.meta.data_to ? ` The day is not over: data stops at ${R.meta.data_to}.` : "");
$("v-waste").addEventListener("click", e => {
  const b = e.target.closest(".brow.click"), r = e.target.closest("tr.f");
  if (b) { filt = filt && filt[0] === b.dataset.dim && filt[1] === b.dataset.v ? null : [b.dataset.dim, b.dataset.v]; drawWaste(); }
  else if (e.target.id === "fReset") { filt = null; drawWaste(); }
  else if (r) { const nx = r.nextElementSibling; if (nx && nx.classList.contains("fx")) nx.remove(); else { const f = F[+r.dataset.i]; r.insertAdjacentHTML("afterend", `<tr class="fx"><td colspan="6">${esc(f.what)}${f.fix ? `<br><b>Fix:</b> ${esc(f.fix)}` : ""}</td></tr>`); } }
});

const PHN = { build: "build", plan: "plan, questions", proof: "proof video", wait: "stopped for you", ci: "CI, main moved", rework: "rework, off-scope", admin: "ship, MR, uploads" };
$("phLegend").innerHTML = Object.entries(PHN).map(([k, v]) => `<span><i class="lg seg-${k}"></i>${v}</span>`).join("") + `<span style="color:var(--faint)">phase times are approximate, from the transcripts</span>`;
const CARDS = S.filter(s => !s.short && s.phases && s.phases.length);
$("taskCards").innerHTML = CARDS.map(p => {
  const segs = p.phases.filter(s => s.minutes > 0), tot = segs.reduce((a, s) => a + s.minutes, 0), by = {};
  for (const s of segs) by[s.kind] = (by[s.kind] || 0) + s.minutes;
  const top = Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => `${PHN[k] || k} ${Math.round(v)}`).join(" · ");
  const span = [hm(p.start), hm(p.end)];
  return `<div class="card"><div class="pane-h"><span class="th">${chip(p.task)} <b>${esc(p.name || p.label)}</b> <span class="fl ${esc(p.result.state)}">${esc(p.result.text)}</span></span><span class="big">${span.join("–")} · ${dur(tot)}</span></div>
  <div class="strip">${segs.map(s => `<div class="seg-${esc(s.kind)}" style="flex:${s.minutes} 1 0" title="${esc(s.what)} · ${s.minutes} min" data-full="${s.minutes}′ ${esc(s.what)}" data-min="${s.minutes}′"></div>`).join("")}</div>
  <div class="axis"><span>${span[0]}</span><span>${top}</span><span>${span[1]}</span></div>
  <ul class="facts">${(p.facts || []).map(f => `<li>${esc(f)}</li>`).join("")}</ul></div>`;
}).join("");
const SHORT = S.filter(s => s.short || !(s.phases && s.phases.length));
$("psCount").textContent = SHORT.length + " sessions";
$("psState").textContent = SHORT.every(s => s.result.state === "ok") ? "all done" : SHORT.filter(s => s.result.state !== "ok").length + " not done";
$("psBody").innerHTML = SHORT.map(s => `<tr><td>${chip(s.task)} ${esc(s.label)}</td><td class="l mono">${hm(s.start)}</td><td class="l mono">${hm(s.end)}</td><td>${s.n_prompts}</td><td>${s.work_min}</td><td>${s.idle_min}</td><td class="l wrap">${esc(s.result.text)}</td></tr>`).join("");

if (R.stacks.length) {
  const n = R.stacks.reduce((a, c) => a + c.mrs.length, 0);
  $("stackSub").textContent = `${n} open MRs in ${R.stacks.length} stack${R.stacks.length > 1 ? "s" : ""}`;
  $("stackState").textContent = R.stacks.some(c => c.mrs.some(m => m.conflicts)) ? "conflicts" : "";
  $("stacks").innerHTML = R.stacks.map(c => `<div class="stack"><span class="mr"><b>${esc(c.base)}</b><small>base</small></span>` + c.mrs.map(m => `<span class="ar">←</span><span class="mr${m.conflicts ? " bad" : ""}" title="${esc(m.title)}"><b>!${m.iid}</b><small>${esc(m.ticket || "")}${m.draft ? " · draft" : ""}${m.conflicts ? " · conflict" : ""}</small></span>`).join("") + `</div>`).join("");
} else $("stackCard").hidden = true;
$("openTitle").textContent = R.meta.data_to ? `Still open at ${R.meta.data_to}` : "Still open at the end of the day";
$("openBody").innerHTML = R.open.map(o => `<tr><td class="l">${esc(o.item)}</td><td class="l"><span class="fl ${esc(o.state)}">${esc(o.flag)}</span></td><td class="l wrap">${esc(o.detail)}</td></tr>`).join("");
$("openCount").textContent = R.open.length + " items";

{
  const T = R.tasks, mx = Math.max(1, ...T.map(t => t.saves_min));
  $("fxBody").innerHTML = T.map(t => `<tr class="f" data-r="${t.rank}"><td class="n">${t.rank}</td><td class="l mono"><i class="fbar" style="width:${t.saves_min / mx * 160}px;background:var(--${t.type === "tool" ? "accent" : "ok"})"></i>${t.saves_min}</td><td class="l wrap"><b style="font-weight:500">${esc(t.title)}</b></td><td class="l"><span class="fl ${t.type === "tool" ? "a" : "ok"}">${esc(t.type)}</span></td><td class="l"><span class="fl">${esc(t.effort)}</span></td></tr>`).join("");
  $("fxTot").textContent = T.reduce((a, t) => a + t.saves_min, 0) + " session min · " + T.filter(t => t.type === "tool").length + " tool changes · " + T.filter(t => t.type === "habit").length + " habits";
  $("fxBody").addEventListener("click", e => {
    const r = e.target.closest("tr.f"); if (!r) return;
    const nx = r.nextElementSibling; if (nx && nx.classList.contains("fx")) return nx.remove();
    const t = T.find(v => v.rank === +r.dataset.r);
    r.insertAdjacentHTML("afterend", `<tr class="fx"><td colspan="5"><b>Change:</b> ${esc(t.change)}${t.file ? `<br><b>File:</b> <code>${esc(t.file)}</code>` : ""}<br><b>Evidence:</b> ${esc(t.evidence)}<br><b>Check:</b> ${esc(t.check)}</td></tr>`);
  });
}
const meas = document.createElement("canvas").getContext("2d");
function fitStrips() {
  meas.font = "10.5px Geist, sans-serif";
  document.querySelectorAll(".strip > div").forEach(d => {
    const w = d.clientWidth - 10; if (w <= 0) return;
    d.textContent = meas.measureText(d.dataset.full).width <= w ? d.dataset.full : meas.measureText(d.dataset.min).width <= w ? d.dataset.min : "";
  });
}
function redraw() { drawTimeline(); fitStrips(); }
redraw();
if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
window.addEventListener("resize", redraw);
window.addEventListener("hashchange", () => setTimeout(redraw, 0));
document.querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => setTimeout(redraw, 0)));
