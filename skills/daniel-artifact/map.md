# Maps

Use a Map page when the reader needs to see where things are: a moving
vehicle, a route, a set of sites, points with coordinates. `map.js` draws a
Leaflet map whose streets are vector lines bundled with the page, a path
tracer with a pulsing head, and place markers. All of it follows the page
tokens, light and dark.

## What the Artifact sandbox allows

- **No raster tiles.** Images from tile servers (OpenStreetMap, CARTO, any
  `{z}/{x}/{y}.png` URL) are blocked. A tile layer leaves the map blank, with
  only the markers and lines showing. The console of the artifact iframe
  shows nothing, so don't wait on an error message.
- **Scripts** load only from the CDNs the Artifact tool names. Leaflet works
  from `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js`.
- **Stylesheets** load only from Google Fonts, so Leaflet's CSS can't be
  linked. `map.js` injects the subset the map needs, styled with the tokens.
- **Same-origin files work.** Publish the street data through `files`
  (`{"basemap.json": "<local path>"}`) and `fetch("basemap.json")` it.

## Steps

1. **Get the streets.** Pick a bounding box that holds everything the map
   will show, with room to spare. Moving things leave a small box, and beyond
   it the path draws on blank ground. Download the box from an Overpass
   server and convert it (commands below). A suburban 11 × 12 km box was
   6,154 ways: 4.7 MB raw, 640 KB converted.
2. **Build the page** from `base.html`. Add the Leaflet script tag after the
   body, then paste `map.js` into the page script after base.html's script.
   Give the map element a height: `#map { height: min(62vh, 620px); min-height: 340px; }`.
3. **Call it.**
   ```js
   const m = renderMap(document.getElementById("map"), {
     basemap: "basemap.json",
     headLabel: "Van",
     onFollow: on => { followBox.checked = on; },
   });
   m.setPlaces([{ lat, lng, label: "You", tone: "ok" }]);
   m.setPath(points);
   ```
   `points` is `[{ lat, lng, label? }]`, oldest first, and the last point is
   the head. Points without numeric coordinates are dropped. `tone` is a
   status token name: `ok`, `warn`, `crit` or `accent`. `m.follow(true)`
   keeps the head and the places in view after each update. Dragging the map
   turns following off and calls `onFollow(false)`. `m.fit()` shows
   everything. `meters(a, b)`, `pathLength(points)` and `fmtDist(m)` cover
   distances.
4. **Layout.** Put a rules strip above the map for the numbers the reader
   wants first, such as distance left, count left, last update and distance
   covered. Put a table below it with one row per point, newest first, in a
   scrolling body with a sticky header. Put "Follow" and "Show all" controls
   in the map pane header.
5. **Check once** in Chrome at 1280 × 760. After a navigate, the first
   screenshot usually shows the claude.ai loading spinner, so take a second
   screenshot before you judge the page.

## Street data

Overpass servers are often full. `overpass-api.de` returned 502 at
capacity, `overpass.kumi.systems` returned 502, and
`overpass.private.coffee` worked. Try them in order and stop at the first
one whose reply starts with `{`. Keep the downloaded file in its own
directory and run the converter with `python3 -I`.

The bounding box tells the Overpass server which area the user cares about.
When that area is private, such as a home address, make the box generous so
it doesn't point at one street. Fetch it only when the user asked for the
map.

```bash
BBOX="40.38,-3.75,40.48,-3.65"   # south,west,north,east
Q='[out:json][timeout:140];(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]('$BBOX');way["waterway"~"river|canal"]('$BBOX');way["railway"="rail"]('$BBOX'););out geom;'
for u in https://overpass-api.de/api/interpreter https://overpass.private.coffee/api/interpreter https://overpass.kumi.systems/api/interpreter https://maps.mail.ru/osm/tools/overpass/api/interpreter; do
  curl -s --max-time 150 -A 'map-client/1.0' "$u" --data-urlencode "data=$Q" -o osm/raw.json
  head -c 1 osm/raw.json | grep -q '{' && break
done
```

```python
import json, sys
src, out = sys.argv[1], sys.argv[2]
cls = {"motorway": 0, "trunk": 0, "motorway_link": 1, "trunk_link": 1, "primary": 1, "primary_link": 1,
       "secondary": 2, "secondary_link": 2, "tertiary": 2, "tertiary_link": 2,
       "unclassified": 3, "residential": 3, "living_street": 3}
feats = []
for e in json.load(open(src))["elements"]:
    t, g = e.get("tags", {}), e.get("geometry")
    k = cls.get(t.get("highway")) if "highway" in t else 4 if "waterway" in t else 5
    if g and k is not None:
        feats.append([k, [round(v * 1e5) for p in g for v in (p["lat"], p["lon"])]])
json.dump(feats, open(out, "w"), separators=(",", ":"))
```

The format is `[[class, [lat1e5, lng1e5, lat1e5, lng1e5, ...]], ...]`. The
classes are 0 motorway, 1 primary, 2 secondary or tertiary, 3 residential,
4 water and 5 rail. `map.js` draws the higher classes first, so main roads
sit on top.

## Live data

When the points keep arriving, such as a tracker or a feed, keep them in the
`db` capability and not in the page.

- Declare `capabilities: {db: {rules: [{path: "", read: "view", write: "owner"}]}}`.
  Viewers read and only the owner, which includes Claude through
  `ArtifactData`, writes.
- Store one document per point in `points`, with the event time as the id
  (`p<epoch>`) and a `t` field. Store fixed facts, such as the destination
  and the item id, in `meta/<name>`. Seed both after the first publish,
  never in the page source.
- In the page, subscribe once with
  `db.collection("points").orderBy("t").onSnapshot(s => m.setPath(s.docs.map(d => d.data())))`.
  Handle `claude.use("db")` resolving `null` with a visible offline callout.
- Collect the points with a poll script run under **Monitor**. The guards
  hook blocks `sleep` loops in Bash. Monitor runs at most 30 minutes, so
  re-arm it each time it expires. Have the script print a line only when the
  value changes, and a line on every failure. Each printed line wakes the
  session, which writes that point with `ArtifactData`.
- Base the page's "live" dot on the newest point's own time, not the last
  poll, because a poll that finds nothing new writes nothing.
