import argparse, json, os, shutil, subprocess, sys


def log(*a, **kw):
    print(*a, file=sys.stderr, **kw)


def parse_args():
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]

    ap = argparse.ArgumentParser(description="Cut clips from a video using timestamps from backend.py.")
    ap.add_argument("--segments", required=True,
                    help="JSON file: backend.py output, or a plain list of {start, end}")
    ap.add_argument("-p", "--p", "--path", dest="path", default=None,
                    help="video path (default: the 'video' field in the JSON)")
    ap.add_argument("-o", "--out", default="clips", help="output folder (default: clips)")
    ap.add_argument("--exact", action="store_true",
                    help="re-encode for exact cut points (slower; default is fast stream copy)")
    return ap.parse_args(argv)


def load_segments(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return None, data
    return data.get("video"), data.get("segments", [])


def main():
    args = parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found. Install it and make sure it is on your PATH.")
    if not os.path.isfile(args.segments):
        sys.exit(f"Segments file not found: {args.segments}")

    json_video, segments = load_segments(args.segments)
    video = args.path or json_video
    if not video or not os.path.isfile(video):
        sys.exit(f"Video not found: {video}")
    if not segments:
        sys.exit("No segments to cut.")

    os.makedirs(args.out, exist_ok=True)

    if args.exact:
        codec, ext = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac"], ".mp4"
    else:
        codec, ext = ["-c", "copy"], (os.path.splitext(video)[1] or ".mp4")   # keep source container

    clips = []
    for i, seg in enumerate(segments):
        start, end = float(seg["start"]), float(seg["end"])
        out = os.path.join(args.out, f"clip_{i:03d}{ext}")
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-ss", f"{start:.3f}", "-i", video, "-t", f"{end - start:.3f}", *codec, out],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            log(f"Clip {i + 1} failed: {r.stderr.strip() or 'empty output'}")
            continue
        clips.append({"path": os.path.abspath(out), "start": start, "end": end})
        log(f"Cut clip {i + 1}/{len(segments)}: {start:.1f}s to {end:.1f}s")

    if not clips:
        sys.exit("No clips could be cut.")

    print(json.dumps({"video": video, "out_dir": os.path.abspath(args.out), "clips": clips}, indent=2))


if __name__ == "__main__":
    main()
