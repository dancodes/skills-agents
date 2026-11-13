#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LOOM = "https://www.loom.com"
HEADERS = {
    "content-type": "application/json",
    "apollographql-client-name": "web",
    "x-loom-request-source": "loom_web",
}
QUERIES = {
    "video": "query V($id: ID!) { getVideo(id: $id, password: null) { __typename ... on RegularUserVideo { name description createdAt playable_duration privacy totalComments views { total } owner { display_name } } } }",
    "transcript": "query T($id: ID!) { fetchVideoTranscript(videoId: $id, password: null) { __typename ... on VideoTranscriptDetails { source_url } } }",
    "chapters": "query C($id: ID!) { fetchVideoChapters(videoId: $id, password: null) { __typename ... on VideoChapters { content } } }",
    "comments": "query M($id: ID!) { getVideo(id: $id, password: null) { ... on RegularUserVideo { video_comments(includeDeleted: false, first: 200) { textContent time_stamp createdAt user_name children_comments { textContent time_stamp createdAt user_name } } } } }",
    "reactions": "query R($id: ID!) { videoReactionsForVideo(videoId: $id, password: null) { __typename ... on VideoReactionsSuccessPayload { reactions { reaction time } } } }",
}
BROWSER_JS = """const id = %s, queries = %s, headers = %s;
const gql = async (name) => (await (await fetch('/graphql', {method: 'POST', credentials: 'include', headers, body: JSON.stringify({query: queries[name], variables: {id}})})).json()).data;
const raw = {id};
for (const name of Object.keys(queries)) raw[name] = await gql(name);
const src = raw.transcript?.fetchVideoTranscript?.source_url;
raw.phrases = src ? (await (await fetch(src)).json()).phrases.map(({ts, value}) => ({ts, value})) : [];
delete raw.transcript;
const article = document.createElement('article');
article.textContent = JSON.stringify(raw);
document.body.replaceChildren(article);
article.textContent.length"""


def request(url, body=None):
    req = urllib.request.Request(url, body, HEADERS if body else {})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def gql(name, video_id):
    body = json.dumps({"query": QUERIES[name], "variables": {"id": video_id}}).encode()
    return request(f"{LOOM}/graphql", body).get("data")


def fetch(video_id):
    raw = {"id": video_id, **{name: gql(name, video_id) for name in QUERIES}}
    if not (raw["video"] or {}).get("getVideo"):
        return None
    src = (raw.pop("transcript")["fetchVideoTranscript"] or {}).get("source_url")
    raw["phrases"] = request(src)["phrases"] if src else []
    raw["mp4"] = request(f"{LOOM}/api/campaigns/sessions/{video_id}/transcoded-url", b"{}").get("url")
    return raw


def clock(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def seconds_of(value, duration):
    return value if value <= duration + 1 else value / 1000


def sections(phrases, duration):
    step = max(30, duration / 40)
    out = []
    for phrase in phrases:
        if not out or phrase["ts"] - out[-1]["start"] >= step:
            out.append({"start": phrase["ts"], "text": []})
        out[-1]["text"].append(phrase["value"])
    if not out:
        out = [{"start": i * step, "text": []} for i in range(int(duration // step) + 1)]
    ends = [s["start"] for s in out[1:]] + [duration]
    for section, end in zip(out, ends):
        section["frame_at"] = (section["start"] + end) / 2
    return out


def grab_frames(mp4, parts, frames_dir):
    if not mp4 or not shutil.which("ffmpeg"):
        return
    frames_dir.mkdir(parents=True, exist_ok=True)

    def grab(section):
        path = frames_dir / f"{int(section['start']):05d}.jpg"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{section['frame_at']:.2f}", "-i", mp4,
               "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "4", str(path)]
        if subprocess.run(cmd).returncode == 0:
            section["frame"] = f"frames/{path.name}"

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(grab, parts))


def header_lines(raw, video, duration):
    lines = [
        f"# {video['name']}",
        "",
        f"- Link: {LOOM}/share/{raw['id']}",
        f"- Owner: {(video.get('owner') or {}).get('display_name', 'Unknown')}",
        f"- Recorded: {video['createdAt'][:16].replace('T', ' ')} UTC",
        f"- Duration: {clock(duration)}",
        f"- Views: {(video.get('views') or {}).get('total', 'Unknown')}",
        f"- Privacy: {video.get('privacy')}",
        f"- Comments: {video.get('totalComments', 0)}",
    ]
    chapters = ((raw.get("chapters") or {}).get("fetchVideoChapters") or {}).get("content")
    if video.get("description"):
        lines += ["", "## Loom Summary", "", video["description"]]
    if chapters:
        lines += ["", "## Chapters", "", chapters]
    return lines


def transcript_lines(parts):
    lines = ["", "## Transcript"]
    for section in parts:
        lines += ["", f"### {clock(section['start'])}"]
        if "frame" in section:
            lines += ["", f"![{clock(section['start'])}]({section['frame']})"]
        if section["text"]:
            lines += ["", " ".join(section["text"])]
    return lines


def comment_lines(raw, duration):
    comments = ((raw.get("comments") or {}).get("getVideo") or {}).get("video_comments") or []
    if not comments:
        return []
    lines = ["", "## Comments", ""]
    for comment in comments:
        at = "General" if comment["time_stamp"] is None else clock(seconds_of(comment["time_stamp"], duration))
        lines.append(f"- **{at}** {comment['user_name'] or 'Anonymous'}: {' '.join(comment['textContent'].split())}")
        for reply in comment.get("children_comments") or []:
            lines.append(f"  - {reply['user_name'] or 'Anonymous'}: {' '.join(reply['textContent'].split())}")
    return lines


def reaction_lines(raw, duration):
    reactions = ((raw.get("reactions") or {}).get("videoReactionsForVideo") or {}).get("reactions") or []
    times = defaultdict(list)
    for reaction in reactions:
        times[reaction["reaction"]].append(clock(seconds_of(reaction["time"] or 0, duration)))
    if not times:
        return []
    return ["", "## Reactions", "", *(f"- {emoji} ×{len(at)}: {', '.join(at)}" for emoji, at in times.items())]


def render(raw, out_dir):
    video = raw["video"]["getVideo"]
    phrases = raw.get("phrases") or []
    duration = video.get("playable_duration") or (phrases[-1]["ts"] if phrases else 0)
    parts = sections(phrases, duration)
    grab_frames(raw.get("mp4"), parts, out_dir / "frames")
    lines = header_lines(raw, video, duration) + transcript_lines(parts) + comment_lines(raw, duration) + reaction_lines(raw, duration)
    path = out_dir / f"{slug(video['name'])}.md"
    path.write_text("\n".join(lines) + "\n")
    return path, sum("frame" in s for s in parts)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "loom"


def main():
    parser = argparse.ArgumentParser(description="Write a Loom recording to Markdown with frames.")
    parser.add_argument("url")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--browser-js", action="store_true", help="print the Chrome fallback snippet")
    parser.add_argument("--from-json", type=Path, help="render the JSON the Chrome snippet collected")
    args = parser.parse_args()
    match = re.search(r"[0-9a-f]{32}", args.url)
    if not match:
        sys.exit(f"No Loom video id in {args.url}")
    video_id = match.group()
    if args.browser_js:
        print(BROWSER_JS % (json.dumps(video_id), json.dumps(QUERIES), json.dumps(HEADERS)))
        return
    raw = json.loads(args.from_json.read_text()) if args.from_json else fetch(video_id)
    if raw is None or not (raw.get("video") or {}).get("getVideo"):
        sys.exit(f"PRIVATE: Loom returned no video for {video_id} without a login.")
    out_dir = args.out or Path.home() / "Documents" / "loom" / f"{slug(raw['video']['getVideo']['name'])}-{video_id[:8]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path, frames = render(raw, out_dir)
    print(f"{path}\n{frames} frames")


if __name__ == "__main__":
    main()
