const MAP_CSS = `
.leaflet-pane,.leaflet-tile,.leaflet-marker-icon,.leaflet-marker-shadow,.leaflet-tile-container,.leaflet-pane>svg,.leaflet-pane>canvas,.leaflet-zoom-box,.leaflet-image-layer,.leaflet-layer{position:absolute;left:0;top:0}
.leaflet-container{overflow:hidden;-webkit-tap-highlight-color:transparent;background:var(--surface);font:11.5px var(--sans)}
.leaflet-marker-icon,.leaflet-marker-shadow{user-select:none;-webkit-user-drag:none}
.leaflet-zoom-box{width:0;height:0;z-index:800}
.leaflet-pane{z-index:400}.leaflet-tile-pane{z-index:200}.leaflet-overlay-pane{z-index:400}.leaflet-shadow-pane{z-index:500}.leaflet-marker-pane{z-index:600}.leaflet-tooltip-pane{z-index:650}.leaflet-popup-pane{z-index:700}
.leaflet-map-pane canvas{z-index:100}.leaflet-map-pane svg{z-index:200}
.leaflet-marker-icon,.leaflet-marker-shadow,.leaflet-image-layer,.leaflet-pane>svg path,.leaflet-tile-container{pointer-events:none}
.leaflet-marker-icon.leaflet-interactive,.leaflet-pane>svg path.leaflet-interactive{pointer-events:auto}
.leaflet-control{position:relative;z-index:800;pointer-events:auto;float:left;clear:both}
.leaflet-top,.leaflet-bottom{position:absolute;z-index:1000;pointer-events:none}
.leaflet-top{top:0}.leaflet-right{right:0}.leaflet-bottom{bottom:0}.leaflet-left{left:0}
.leaflet-right .leaflet-control{float:right}
.leaflet-top .leaflet-control{margin-top:10px}.leaflet-left .leaflet-control{margin-left:10px}
.leaflet-zoom-animated{transform-origin:0 0}
.leaflet-zoom-anim .leaflet-zoom-animated{transition:transform .25s cubic-bezier(0,0,.25,1)}
.leaflet-zoom-anim .leaflet-zoom-hide{visibility:hidden}
.leaflet-interactive{cursor:pointer}
.leaflet-grab{cursor:grab}.leaflet-dragging .leaflet-grab{cursor:move}
.leaflet-container.leaflet-touch-drag{touch-action:none}
.leaflet-bar{border:1px solid var(--line);border-radius:6px;overflow:hidden;box-shadow:0 1px 2px rgb(0 0 0 / .08)}
.leaflet-bar a{display:block;width:28px;height:28px;line-height:27px;text-align:center;text-decoration:none;background:var(--surface);color:var(--ink);font-size:16px}
.leaflet-bar a+a{border-top:1px solid var(--line)}
.leaflet-bar a:hover{background:var(--panel)}
.leaflet-bar a.leaflet-disabled{color:var(--faint);cursor:default}
.leaflet-control-attribution{background:color-mix(in srgb,var(--surface) 80%,transparent);padding:1px 6px;font-size:10.5px;color:var(--muted);border-top-left-radius:6px}
.leaflet-control-attribution a{color:var(--muted)}
.leaflet-tooltip{position:absolute;padding:3px 7px;background:var(--surface);border:1px solid var(--line);border-radius:4px;color:var(--ink);white-space:nowrap;font-family:var(--mono);font-size:11px;pointer-events:none;box-shadow:0 1px 3px rgb(0 0 0 / .12)}
.map-head{position:relative;width:18px;height:18px}
.map-head i{position:absolute;inset:3px;border-radius:50%;background:var(--accent);border:2px solid var(--surface);box-shadow:0 0 0 1px var(--accent)}
.map-head b{position:absolute;inset:-6px;border-radius:50%;border:2px solid var(--accent);opacity:0;animation:map-ping 2.4s ease-out infinite}
@keyframes map-ping{0%{transform:scale(.4);opacity:.7}100%{transform:scale(1.4);opacity:0}}
@media (prefers-reduced-motion:reduce){.map-head b{animation:none}}
.map-place{width:14px;height:14px;border-radius:3px;background:var(--c);border:2px solid var(--surface);box-shadow:0 0 0 1px var(--c)}
`;
document.head.insertAdjacentHTML("beforeend", `<style>${MAP_CSS}</style>`);

function meters(a, b) {
  const R = 6371000, r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r, dLng = (b.lng - a.lng) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const fmtDist = m => m == null ? "–" : m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(m < 10000 ? 2 : 1)} km`;
const pathLength = pts => pts.reduce((s, p, i) => i ? s + meters(pts[i - 1], p) : 0, 0);

const ROAD_STYLE = [[3.4, "--faint", 0.75], [2.6, "--faint", 0.75], [1.8, "--faint", 0.75], [1, "--line", 1], [2, "--faint", 0.45], [1, "--faint", 1, "4 4"]];

function renderMap(el, opts = {}) {
  const tok = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const map = L.map(el).setView(opts.center || [40.4, -3.7], opts.zoom || 6);
  map.attributionControl.addAttribution('© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors');

  const base = L.layerGroup().addTo(map);
  const canvas = L.canvas({ padding: 0.5 });
  let roads = [];
  function drawBase() {
    base.clearLayers();
    roads.forEach(([k, c]) => {
      const ll = [];
      for (let i = 0; i < c.length; i += 2) ll.push([c[i] / 1e5, c[i + 1] / 1e5]);
      const [weight, color, opacity, dashArray] = ROAD_STYLE[k];
      L.polyline(ll, { renderer: canvas, interactive: false, weight, color: tok(color), opacity, dashArray: dashArray || null, lineCap: "round" }).addTo(base);
    });
  }
  if (opts.basemap) fetch(opts.basemap).then(r => r.json()).then(d => { roads = d.sort((a, b) => b[0] - a[0]); drawBase(); }).catch(() => {});

  const trail = L.polyline([], { weight: 4, opacity: 0.9, lineJoin: "round" }).addTo(map);
  const dots = L.layerGroup().addTo(map);
  const head = L.marker([0, 0], { zIndexOffset: 1000, icon: L.divIcon({ className: "", html: '<div class="map-head"><b></b><i></i></div>', iconSize: [18, 18], iconAnchor: [9, 9] }) });
  const placeLayer = L.layerGroup().addTo(map);
  let path = [], places = [], following = opts.follow !== false, fitted = false;

  function paint() {
    trail.setStyle({ color: tok("--accent") });
    dots.eachLayer(d => d.setStyle({ color: tok("--accent"), fillColor: tok("--surface") }));
  }
  new MutationObserver(() => requestAnimationFrame(() => { drawBase(); paint(); }))
    .observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode"] });

  const allPoints = () => [...path, ...places].map(p => [p.lat, p.lng]);
  function fit() { const ll = allPoints(); if (ll.length) map.fitBounds(ll, { padding: [40, 40], maxZoom: 16 }); }
  function track() {
    const last = path[path.length - 1];
    if (!last) return fit();
    const ll = [[last.lat, last.lng], ...places.map(p => [p.lat, p.lng])];
    ll.length > 1 ? map.fitBounds(ll, { padding: [60, 60], maxZoom: 16 }) : map.setView(ll[0], 15);
  }
  function setFollow(on) { following = on; if (opts.onFollow) opts.onFollow(on); if (on) track(); }
  map.on("dragstart", () => { if (following) setFollow(false); });
  function settle() {
    if (!fitted && allPoints().length) { fitted = true; following ? track() : fit(); }
    else if (following) track();
  }

  function setPath(points) {
    path = points.filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng));
    trail.setLatLngs(path.map(p => [p.lat, p.lng]));
    dots.clearLayers();
    path.slice(0, -1).forEach(p => {
      const d = L.circleMarker([p.lat, p.lng], { radius: 3, weight: 2, fillOpacity: 1 }).addTo(dots);
      if (p.label) d.bindTooltip(p.label, { direction: "top" });
    });
    paint();
    const last = path[path.length - 1];
    if (last) { head.setLatLng([last.lat, last.lng]).addTo(map); head.unbindTooltip(); if (opts.headLabel) head.bindTooltip(opts.headLabel, { direction: "top", offset: [0, -10] }); }
    else head.remove();
    settle();
  }

  function setPlaces(list) {
    places = list.filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lng));
    placeLayer.clearLayers();
    places.forEach(p => {
      const m = L.marker([p.lat, p.lng], { icon: L.divIcon({ className: "", html: `<div class="map-place" style="--c:var(--${p.tone || "ok"})"></div>`, iconSize: [14, 14], iconAnchor: [7, 7] }) }).addTo(placeLayer);
      if (p.label) m.bindTooltip(p.label, { direction: "top", offset: [0, -8] });
    });
    settle();
  }

  return { map, setPath, setPlaces, fit: () => { setFollow(false); fit(); }, follow: setFollow };
}
