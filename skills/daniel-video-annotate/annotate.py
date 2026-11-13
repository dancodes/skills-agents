#!/usr/bin/env python3
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import NamedTuple, Optional

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
HOLD_SECONDS = 6
READ_WPM = 350
LEAD_SECONDS = 1.5
MIN_HOLD_SECONDS = 2.5
CLEARANCE_LINES = 3
DIM = "color=black@0.45:t=fill"
HIGHLIGHT = "0xFFB300"
ENCODE = ["-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]


class Video(NamedTuple):
    width: int
    height: int
    fps: int
    duration: float


class Pause(NamedTuple):
    frame: int
    box: Optional[tuple]
    caption: str
    hold: float


def fail(message):
    sys.exit(f"annotate.py: {message}")


def run(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        fail(f"{command[0]} failed:\n{result.stderr.strip()[-3000:]}")
    return result


def require_filters(*names):
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            fail(f"{tool} is not on PATH")
    available = run(["ffmpeg", "-hide_banner", "-filters"]).stdout
    for name in names:
        if not re.search(rf"\s{name}\s", available):
            fail(f"this ffmpeg build has no {name} filter")


def probe(path):
    if not Path(path).is_file():
        fail(f"{path} is not a file")
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
        "-of", "json", str(path),
    ])
    data = json.loads(result.stdout)
    if not data.get("streams"):
        fail(f"{path} has no video stream")
    stream = data["streams"][0]
    numerator, denominator = (float(part) for part in stream["avg_frame_rate"].split("/"))
    rate = numerator / denominator if denominator else 0
    fps = min(30, max(5, round(rate))) if rate else 15
    return Video(stream["width"], stream["height"], fps, float(data["format"]["duration"]))


def find_font(override):
    for candidate in [override] if override else FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate.replace(":", "\\:")
    fail("no font file found, pass --font /path/to/font.ttf")


def resolved(path):
    return str(Path(path).expanduser().resolve())


def refuse_overwrite(source, target):
    if resolved(source) == resolved(target):
        fail("the output path is the input path")


def trim(args):
    require_filters("freezedetect")
    refuse_overwrite(args.video, args.out)
    if args.keep >= args.min_freeze:
        fail("--keep must be shorter than --min-freeze")
    video = probe(args.video)
    detect = f"fps={video.fps},freezedetect=n={args.noise}:d={args.min_freeze}"
    log = run(["ffmpeg", "-hide_banner", "-i", args.video, "-vf", detect, "-map", "0:v:0", "-f", "null", "-"]).stderr
    starts = [float(value) for value in re.findall(r"freeze_start: ([\d.]+)", log)]
    ends = [float(value) for value in re.findall(r"freeze_end: ([\d.]+)", log)]
    if not starts:
        print("no still stretches found, nothing written")
        return
    half_frame = 0.5 / video.fps
    cuts = []
    for index, start in enumerate(starts):
        cut_from = start + args.keep - half_frame
        if index < len(ends):
            cuts.append(f"gte(t,{cut_from:.4f})*lt(t,{ends[index] - half_frame:.4f})")
        else:
            cuts.append(f"gte(t,{cut_from:.4f})")
    chain = ",".join([
        f"fps={video.fps}",
        f"select='not({'+'.join(cuts)})'",
        f"setpts=N/({video.fps}*TB)",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    ])
    run(["ffmpeg", "-hide_banner", "-y", "-i", args.video, "-vf", chain, "-r", str(video.fps), *ENCODE, args.out])
    print(f"cut {len(starts)} still stretches: {video.duration:.1f}s -> {probe(args.out).duration:.1f}s")
    print(f"wrote {args.out}")


def sheets(args):
    require_filters("drawtext")
    video = probe(args.video)
    folder = Path(args.dir)
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("sheet-*.png"):
        stale.unlink()
    chain = ",".join([
        f"drawtext=fontfile={find_font(args.font)}:text='%{{pts\\:hms}}':x=10:y=10"
        f":fontsize={max(20, video.width // 28)}:fontcolor=yellow:box=1:boxcolor=black",
        f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{args.every - 0.001})'",
        "scale=960:-2",
        "tile=2x3",
    ])
    run(["ffmpeg", "-hide_banner", "-y", "-i", args.video, "-vf", chain, "-fps_mode", "vfr",
         str(folder / "sheet-%02d.png")])
    for sheet in sorted(folder.glob("sheet-*.png")):
        print(sheet)


def frames(args):
    require_filters("drawtext")
    video = probe(args.video)
    for seconds in args.times:
        if not 0 <= seconds < video.duration:
            fail(f"{seconds}s is outside the video ({video.duration:.2f}s)")
    indexes = sorted({round(seconds * video.fps) for seconds in args.times})
    folder = Path(args.dir)
    folder.mkdir(parents=True, exist_ok=True)
    font = find_font(args.font)
    label = f"fontfile={font}:fontsize={max(12, video.width // 100)}:fontcolor=red:box=1:boxcolor=white@0.8"
    chain = [
        f"fps={video.fps}",
        "select='" + "+".join(f"eq(n,{index})" for index in indexes) + "'",
        "drawgrid=w=100:h=100:t=1:c=red@0.4",
    ]
    chain += [f"drawtext={label}:text='{x}':x={x + 3}:y=2" for x in range(100, video.width, 100)]
    chain += [f"drawtext={label}:text='{y}':x=2:y={y + 3}" for y in range(100, video.height, 100)]
    for stale in folder.glob("unnamed-*.png"):
        stale.unlink()
    run(["ffmpeg", "-hide_banner", "-y", "-i", args.video, "-vf", ",".join(chain), "-fps_mode", "vfr",
         str(folder / "unnamed-%03d.png")])
    unnamed = sorted(folder.glob("unnamed-*.png"))
    if len(unnamed) != len(indexes):
        fail(f"asked for {len(indexes)} frames, ffmpeg wrote {len(unnamed)}")
    for index, path in zip(indexes, unnamed):
        named = folder / f"frame-{index / video.fps:07.3f}.png"
        path.replace(named)
        print(named)


def read_spec(path):
    try:
        spec = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")
    if not isinstance(spec, list) or not spec:
        fail("the spec must be a non-empty JSON list of pauses")
    return spec


def hold_for(caption, wpm, lead, shortest):
    return round(max(shortest, lead + len(caption.split()) * 60 / wpm), 1)


def holds(args):
    spec = read_spec(args.spec)
    for entry in spec:
        caption = str(entry.get("caption", ""))
        entry["hold"] = hold_for(caption, args.wpm, args.lead, args.min)
        print(f"{entry['hold']:5.1f}s  {len(caption.split()):3d} words  {caption}")
    Path(args.spec).write_text(json.dumps(spec, indent=2) + "\n")


def load_pauses(path, video):
    pauses = []
    previous = -1
    last_frame = int(video.duration * video.fps) - 1
    for number, entry in enumerate(read_spec(path), 1):
        caption = str(entry.get("caption", "")).strip()
        if not caption:
            fail(f"pause {number} has no caption")
        if "at" not in entry:
            fail(f"pause {number} has no 'at' time")
        frame = round(float(entry["at"]) * video.fps)
        if frame <= previous:
            fail(f"pause {number} must come after the pause before it")
        if frame > last_frame:
            fail(f"pause {number} at {entry['at']}s is past the end of the video ({video.duration:.2f}s)")
        box = entry.get("box")
        if box is not None:
            if len(box) != 4:
                fail(f"pause {number} box must be [x, y, width, height]")
            x, y, w, h = (int(value) for value in box)
            if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > video.width or y + h > video.height:
                fail(f"pause {number} box {box} is outside the {video.width}x{video.height} frame")
            box = (x, y, w, h)
        pauses.append(Pause(frame, box, caption, float(entry.get("hold", HOLD_SECONDS))))
        previous = frame
    return pauses


def balanced_wrap(caption, limit):
    lines = textwrap.wrap(caption, limit)
    for width in range(math.ceil(len(caption) / len(lines)), limit + 1):
        candidate = textwrap.wrap(caption, width)
        if len(candidate) == len(lines):
            return candidate
    return lines


def highlight_filters(box, video, recording_top):
    if box is None:
        return []
    x, y, w, h = box
    around = [
        (0, 0, video.width, y),
        (0, y + h, video.width, video.height - y - h),
        (0, y, x, h),
        (x + w, y, video.width - x - w, h),
    ]
    thickness = max(3, video.width // 320)
    left, top = max(0, x - thickness), max(0, y - thickness)
    right, bottom = min(video.width, x + w + thickness), min(video.height, y + h + thickness)
    filters = [
        f"drawbox=x={dx}:y={dy + recording_top}:w={dw}:h={dh}:{DIM}"
        for dx, dy, dw, dh in around
        if dw > 0 and dh > 0
    ]
    filters.append(
        f"drawbox=x={left}:y={top + recording_top}:w={right - left}:h={bottom - top}"
        f":color={HIGHLIGHT}:t={thickness}"
    )
    return filters


def annotate(args):
    require_filters("drawtext")
    refuse_overwrite(args.video, args.out)
    video = probe(args.video)
    pauses = load_pauses(args.spec, video)
    font = find_font(args.font)
    font_size = max(16, round(video.width / 53))
    spacing, padding = font_size // 3, font_size * 5 // 6
    limit = args.wrap or int((video.width - 2 * font_size) / (font_size * 0.55))
    wrapped = [balanced_wrap(pause.caption, limit) for pause in pauses]
    rows = max(len(lines) for lines in wrapped)
    clearance = round(args.clearance * (font_size + spacing)) if args.position == "bottom" else 0
    strip = rows * font_size + (rows - 1) * spacing + 2 * padding + clearance
    strip += strip % 2
    recording_top = strip if args.position == "top" else 0
    caption_top = padding if args.position == "top" else video.height + padding
    width = video.width + video.width % 2
    height = video.height + strip
    height += height % 2

    with tempfile.TemporaryDirectory() as work:
        segments = []
        previous = 0
        for index, pause in enumerate(pauses):
            Path(work, f"caption-{index}.txt").write_text("\n".join(wrapped[index]))
            if pause.frame > previous:
                segments.append(f"trim=start_frame={previous}:end_frame={pause.frame},setpts=PTS-STARTPTS")
            segments.append(",".join([
                f"trim=start_frame={pause.frame}:end_frame={pause.frame + 1}",
                "setpts=PTS-STARTPTS",
                f"tpad=stop_mode=clone:stop_duration={pause.hold}",
                *highlight_filters(pause.box, video, recording_top),
                f"drawtext=fontfile={font}:textfile=caption-{index}.txt:expansion=none:fontsize={font_size}"
                f":fontcolor=white:x={font_size}:y={caption_top}:line_spacing={spacing}",
            ]))
            previous = pause.frame
        segments.append(f"trim=start_frame={previous},setpts=PTS-STARTPTS")

        count = len(segments)
        graph = [
            f"[0:v]fps={video.fps},pad={width}:{height}:0:{recording_top}:black,split={count}"
            + "".join(f"[s{index}]" for index in range(count))
        ]
        graph += [f"[s{index}]{segment}[c{index}]" for index, segment in enumerate(segments)]
        graph.append("".join(f"[c{index}]" for index in range(count)) + f"concat=n={count}:v=1:a=0[out]")
        run(["ffmpeg", "-hide_banner", "-y", "-i", resolved(args.video), "-filter_complex", ";".join(graph),
             "-map", "[out]", "-r", str(video.fps), *ENCODE, resolved(args.out)], cwd=work)

    result = probe(args.out)
    print(f"wrote {args.out}: {result.width}x{result.height}, {result.duration:.1f}s, {len(pauses)} pauses")


def check(args):
    video = probe(args.video)
    folder = Path(args.dir)
    folder.mkdir(parents=True, exist_ok=True)
    added = 0.0
    for number, entry in enumerate(read_spec(args.spec), 1):
        hold = float(entry.get("hold", HOLD_SECONDS))
        middle = round(float(entry["at"]) * video.fps) / video.fps + added + hold / 2
        if middle >= video.duration:
            fail(f"pause {number} would sit at {middle:.1f}s, past the end; is this the annotated video?")
        shot = folder / f"pause-{number:02d}.png"
        run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{middle:.3f}", "-i", args.video, "-frames:v", "1", str(shot)])
        print(shot)
        added += hold + 1 / video.fps


def selftest(args):
    require_filters("freezedetect", "drawtext")
    with tempfile.TemporaryDirectory() as work:
        source, trimmed, explained = (str(Path(work, name)) for name in ("source.mp4", "trimmed.mp4", "explained.mp4"))
        run(["ffmpeg", "-hide_banner", "-y",
             "-f", "lavfi", "-i", "color=c=navy:s=640x360:r=15:d=4",
             "-f", "lavfi", "-i", "testsrc=s=640x360:r=15:d=2",
             "-filter_complex", "[0][1]concat=n=2:v=1:a=0", *ENCODE, source])
        trim(argparse.Namespace(video=source, out=trimmed, keep=1.0, min_freeze=1.5, noise=0.003))
        Path(work, "spec.json").write_text(json.dumps([
            {"at": 0.5, "box": [100, 100, 200, 60], "caption": "The self test pauses here, 100% sure that it's fine: yes.", "hold": 2},
        ]))
        before, cut = probe(source), probe(trimmed)
        assert 2.5 < cut.duration < 3.5, f"trim left {cut.duration}s of a 6s clip with 4s still"
        heights = {}
        for position in ("top", "bottom"):
            annotate(argparse.Namespace(video=trimmed, spec=str(Path(work, "spec.json")), out=explained,
                                        font=args.font, wrap=None, position=position, clearance=CLEARANCE_LINES))
            after = probe(explained)
            heights[position] = after.height
            assert abs(after.duration - cut.duration - 2) < 0.3, "annotate did not add the 2s pause"
        assert before.height < heights["top"] < heights["bottom"], f"caption strip heights are wrong: {heights}"
    print("selftest passed")


def main():
    parser = argparse.ArgumentParser(description="Trim, inspect and annotate a screen recording with ffmpeg.")
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("trim", help="cut each still stretch down to its first --keep seconds")
    command.add_argument("video")
    command.add_argument("out")
    command.add_argument("--keep", type=float, default=1.0)
    command.add_argument("--min-freeze", type=float, default=1.5)
    command.add_argument("--noise", type=float, default=0.003)
    command.set_defaults(handler=trim)

    command = commands.add_parser("sheets", help="write timestamped contact sheets, six frames each")
    command.add_argument("video")
    command.add_argument("dir")
    command.add_argument("--every", type=float, default=1.0)
    command.add_argument("--font")
    command.set_defaults(handler=sheets)

    command = commands.add_parser("frames", help="write full-size frames with a labelled 100px grid")
    command.add_argument("video")
    command.add_argument("dir")
    command.add_argument("times", type=float, nargs="+")
    command.add_argument("--font")
    command.set_defaults(handler=frames)

    command = commands.add_parser("annotate", help="pause, highlight and caption at each pause of the spec")
    command.add_argument("video")
    command.add_argument("spec")
    command.add_argument("out")
    command.add_argument("--font")
    command.add_argument("--wrap", type=int)
    command.add_argument("--position", choices=["top", "bottom"], default="bottom")
    command.add_argument("--clearance", type=float, default=CLEARANCE_LINES)
    command.set_defaults(handler=annotate)

    command = commands.add_parser("holds", help="set each pause's hold from its word count and a reading speed")
    command.add_argument("spec")
    command.add_argument("--wpm", type=float, default=READ_WPM)
    command.add_argument("--lead", type=float, default=LEAD_SECONDS)
    command.add_argument("--min", type=float, default=MIN_HOLD_SECONDS)
    command.set_defaults(handler=holds)

    command = commands.add_parser("check", help="write one frame from the middle of each pause of an annotated video")
    command.add_argument("video")
    command.add_argument("spec")
    command.add_argument("dir")
    command.set_defaults(handler=check)

    command = commands.add_parser("selftest", help="trim and annotate a generated clip to prove ffmpeg works here")
    command.add_argument("--font")
    command.set_defaults(handler=selftest)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
