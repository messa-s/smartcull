import argparse, os, shutil, subprocess, sys

import cv2
import numpy as np


def parse_args():
    argv = sys.argv[1:]
    if argv and argv[0] == "--":          # allow: backend.py -- --p ... -q ...
        argv = argv[1:]

    ap = argparse.ArgumentParser(description="Find clips in a video by text query or by a person's face.")
    ap.add_argument("-p", "--p", "--path", dest="path", required=True, help="path to the input video")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("-q", "--q", "--query", dest="query", help='text query, e.g. "person wearing black"')
    mode.add_argument("-ph", "--ph", "--photo", dest="photos", nargs="+",
                      help="one or more photos with a clear face of the person to search for")

    ap.add_argument("-o", "--out", default="clips", help="output folder (default: clips)")
    ap.add_argument("--threshold", type=float, default=None,
                    help="match cutoff (default: 0.15 for -q, 0.4 for -ph)")
    ap.add_argument("--fps", type=float, default=None,
                    help="frames analysed per second (default: 2 for -q, 3 for -ph)")
    ap.add_argument("--gap", type=float, default=2.0, help="merge matches closer than this many seconds")
    ap.add_argument("--pad", type=float, default=1.0, help="seconds added before/after each clip")
    ap.add_argument("--batch", type=int, default=32, help="SigLIP batch size (-q mode)")
    ap.add_argument("--exact", action="store_true",
                    help="re-encode for exact cut points (slower; default is fast stream copy)")
    args = ap.parse_args(argv)

    if args.threshold is None:
        args.threshold = 0.15 if args.query else 0.4
    if args.fps is None:
        args.fps = 2 if args.query else 3
    return args


# ---------------------------------------------------------------- text mode
def scan_text(args, fps, total, step):
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModel
    from ultralytics import YOLO

    MODEL = "google/siglip-base-patch16-224"
    MIN_W, MIN_H, BOX_PAD = 40, 80, 0.05

    query = args.query if args.query.lower().startswith("a photo") else f"a photo of {args.query}"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} | Query: {query!r}")

    yolo = YOLO("yolov8n.pt")
    proc = AutoProcessor.from_pretrained(MODEL)
    siglip = AutoModel.from_pretrained(MODEL).to(device).eval()
    if device == "cuda":
        siglip = siglip.half()

    @torch.no_grad()
    def score_images(imgs):
        inputs = proc(text=[query], images=imgs, padding="max_length", return_tensors="pt").to(device)
        if device == "cuda":
            inputs["pixel_values"] = inputs["pixel_values"].half()
        logits = siglip(**inputs).logits_per_image
        return torch.sigmoid(logits.float()).squeeze(-1).cpu().tolist()

    def person_crops(frame):
        h, w = frame.shape[:2]
        det = yolo(frame, classes=[0], verbose=False)[0]
        crops = []
        for x1, y1, x2, y2 in det.boxes.xyxy.cpu().numpy():
            bw, bh = x2 - x1, y2 - y1
            if bw < MIN_W or bh < MIN_H:
                continue
            x1 = int(max(0, x1 - bw * BOX_PAD)); x2 = int(min(w, x2 + bw * BOX_PAD))
            y1 = int(max(0, y1 - bh * BOX_PAD)); y2 = int(min(h, y2 + bh * BOX_PAD))
            crops.append(Image.fromarray(cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)))
        return crops

    cap = cv2.VideoCapture(args.path)
    pending_imgs, pending_ts, best_by_t = [], [], {}

    def flush():
        nonlocal pending_imgs, pending_ts
        if pending_imgs:
            for t, s in zip(pending_ts, score_images(pending_imgs)):
                best_by_t[t] = max(best_by_t.get(t, 0.0), s)
        pending_imgs, pending_ts = [], []

    idx = 0
    while cap.grab():
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                t = idx / fps
                best_by_t.setdefault(t, 0.0)
                for c in person_crops(frame):
                    pending_imgs.append(c); pending_ts.append(t)
                    if len(pending_imgs) >= args.batch:
                        flush()
            print(f"\rProcessed {idx / fps:6.1f}s / {total / fps:.1f}s", end="", flush=True)
        idx += 1
    flush()
    cap.release()
    print()
    return sorted(best_by_t.items())


# ---------------------------------------------------------------- face mode
def scan_face(args, fps, total, step):
    import onnxruntime as ort
    from insightface.app import FaceAnalysis

    MIN_FACE_PX, MIN_DET = 40, 0.5

    for p in args.photos:
        if not os.path.isfile(p):
            sys.exit(f"Photo not found: {p}")

    use_gpu = "CUDAExecutionProvider" in ort.get_available_providers()
    app = FaceAnalysis(name="buffalo_l",
                       providers=["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu
                       else ["CPUExecutionProvider"])
    app.prepare(ctx_id=0 if use_gpu else -1, det_size=(640, 640))
    print(f"Device: {'cuda' if use_gpu else 'cpu'} | Photos: {len(args.photos)}")

    def face_width(f):
        return f.bbox[2] - f.bbox[0]

    ref_embs = []
    for path in args.photos:
        faces = app.get(cv2.imread(path))
        if not faces:
            print(f"No face found in {path}, skipping")
            continue
        ref_embs.append(max(faces, key=face_width).normed_embedding)   # largest face in the photo
    if not ref_embs:
        sys.exit("No usable face in the reference photos.")
    ref = np.mean(ref_embs, axis=0)
    ref /= np.linalg.norm(ref)
    print(f"Reference built from {len(ref_embs)} photo(s)")

    cap = cv2.VideoCapture(args.path)
    scores = []
    idx = 0
    while cap.grab():
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                faces = [f for f in app.get(frame)
                         if f.det_score >= MIN_DET and face_width(f) >= MIN_FACE_PX]
                best = max((float(np.dot(f.normed_embedding, ref)) for f in faces), default=0.0)
                scores.append((idx / fps, best))
            print(f"\rProcessed {idx / fps:6.1f}s / {total / fps:.1f}s", end="", flush=True)
        idx += 1
    cap.release()
    print()
    return scores


# ---------------------------------------------------------------- shared
def make_segments(scores, threshold, gap):
    segments = []
    for t, s in scores:
        if s < threshold:
            continue
        if segments and t - segments[-1][1] <= gap:
            segments[-1][1] = t
        else:
            segments.append([t, t])
    return segments


def cut_clips(args, segments, duration):
    os.makedirs(args.out, exist_ok=True)
    codec = (["-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac"]
             if args.exact else ["-c", "copy"])
    for i, (a, b) in enumerate(segments):
        start, end = max(0, a - args.pad), min(duration, b + args.pad)
        out = os.path.join(args.out, f"clip_{i:03d}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-ss", str(start), "-i", args.path, "-t", str(end - start),
                        *codec, out], check=True)
        print(f"{out}: {start:.1f}s to {end:.1f}s")


def main():
    args = parse_args()

    if not os.path.isfile(args.path):
        sys.exit(f"Video not found: {args.path}")
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found. Install it and make sure it is on your PATH.")

    cap = cv2.VideoCapture(args.path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration = total / fps
    step = max(1, int(round(fps / args.fps)))

    scores = scan_text(args, fps, total, step) if args.query else scan_face(args, fps, total, step)

    top = sorted(scores, key=lambda s: -s[1])[:10]
    print("Top scores:", [(round(t, 1), round(s, 3)) for t, s in top])

    segments = make_segments(scores, args.threshold, args.gap)
    cut_clips(args, segments, duration)
    print(f"{len(segments)} clips found")


if __name__ == "__main__":
    main()
