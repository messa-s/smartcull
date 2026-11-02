import argparse, json, os, random, sys, time, zlib

import shutil, subprocess

def probe_duration(path):
    if shutil.which("ffprobe"):
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", path],
                capture_output=True, text=True, timeout=20).stdout.strip()
            return float(out)
        except Exception:
            pass
    return None


def log(*a, **kw):
    print(*a, file=sys.stderr, **kw)


def parse_args():
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]

    ap = argparse.ArgumentParser(description="Dummy backend: same API as backend.py, fake results.")
    ap.add_argument("-p", "--p", "--path", dest="path", required=True, help="path to the input video")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("-q", "--q", "--query", dest="query", help="text query")
    mode.add_argument("-ph", "--ph", "--photo", dest="photos", nargs="+", help="one or more face photos")

    ap.add_argument("-o", "--out", default=None, help="also write the JSON result to this file")
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--gap", type=float, default=2.0)
    ap.add_argument("--pad", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=32)

    # dummy-only options (the frontend never needs to pass these)
    ap.add_argument("--delay", type=float, default=3.0, help="simulated processing time in seconds")
    ap.add_argument("--duration", type=float, default=None, help="fake video duration in seconds")
    ap.add_argument("--fail", action="store_true", help="simulate a backend error")
    args = ap.parse_args(argv)

    if args.threshold is None:
        args.threshold = 0.15 if args.query else 0.4
    if args.fps is None:
        args.fps = 2 if args.query else 3
    return args


def fake_scores(args):
    """Deterministic fake scores: same video + query/photos always gives the same result."""
    seed_text = args.path + (args.query or "|".join(args.photos))
    rng = random.Random(zlib.crc32(seed_text.encode()))

    # text scores sit lower than face scores, like the real backend
    lo, hi = (0.05, 0.45) if args.query else (0.30, 0.80)
    noise = 0.12 if args.query else 0.25

    n = int(args.duration * args.fps)
    scores = [rng.uniform(0, noise) for _ in range(n)]

    for _ in range(rng.randint(3, 6)):                    # a few bursts where the "person" appears
        start = rng.randint(0, max(0, n - 1))
        length = int(rng.uniform(3, 15) * args.fps)
        for i in range(start, min(n, start + length)):
            scores[i] = max(scores[i], rng.uniform(lo, hi))

    return [(i / args.fps, s) for i, s in enumerate(scores)]


# same logic as backend.py
def make_segments(scores, threshold, gap, pad, duration):
    groups = []
    for t, s in scores:
        if s < threshold:
            continue
        if groups and t - groups[-1][1] <= gap:
            groups[-1][1] = t
            groups[-1][2] = max(groups[-1][2], s)
        else:
            groups.append([t, t, s])

    segments = []
    for a, b, s in groups:
        start, end = max(0.0, a - pad), min(duration, b + pad)
        if segments and start <= segments[-1]["end"]:
            segments[-1]["end"] = end
            segments[-1]["score"] = max(segments[-1]["score"], s)
        else:
            segments.append({"start": start, "end": end, "score": s})

    return [{"start": round(g["start"], 2), "end": round(g["end"], 2), "score": round(g["score"], 3)}
            for g in segments]


def main():
    args = parse_args()

    if not os.path.isfile(args.path):
        sys.exit(f"Video not found: {args.path}")
    for p in args.photos or []:
        if not os.path.isfile(p):
            sys.exit(f"Photo not found: {p}")
    
    args.duration = args.duration or probe_duration(args.path) or 180.0

    mode = "text" if args.query else "face"
    log(f"Device: cpu (dummy) | Mode: {mode}")
    if args.fail:
        time.sleep(min(args.delay, 1.0))
        sys.exit("Simulated failure (--fail)")

    scores = fake_scores(args)
    duration = args.duration

    # simulate work, printing progress the same way backend.py does
    for t, _ in scores:
        log(f"\rProcessed {t:6.1f}s / {duration:.1f}s", end="", flush=True)
        time.sleep(args.delay / len(scores))
    log()

    top = sorted(scores, key=lambda s: -s[1])[:10]
    log("Top scores:", [(round(t, 1), round(s, 3)) for t, s in top])

    result = {
        "video": args.path,
        "mode": mode,
        "duration": round(duration, 2),
        "segments": make_segments(scores, args.threshold, args.gap, args.pad, duration),
    }
    log(f"{len(result['segments'])} segments found")

    text = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
