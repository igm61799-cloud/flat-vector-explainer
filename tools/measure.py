"""Measure the visual + pacing fingerprint of a video clip, frame by frame at 30 fps.

Usage:
  python -I measure.py VIDEO --out report.json [--start S] [--end S] [--vtt captions.vtt]
                       [--words words.json] [--sheet sheet.jpg]

Metrics (all computed on frames downscaled to 320 px wide):
  palette        8 dominant colours (k-means on ~2 frames/s) + share of pixels
  hsv_hist       18 hue x 3 sat x 3 val histogram (for palette similarity)
  pure_black_pct pixels with value < 6 %
  darkest_hex    colour of the darkest palette cluster
  mean_lum, mean_sat, saturated_pct
  camera_moving_pct  frames where the whole frame moves (affine: shift > 0.15 px or scale change > 0.15 %)
  camera_speed_px_s  median global shift speed (in 1920-px units) while moving
  animating_pct  frames where something moves after camera motion is removed (residual > 0.2 % px)
  events_per_s   rising edges of residual change (a new element / new action starts)
  cuts_per_min, median_shot_s
  narration_wps  words per second (from VTT captions or a whisper words.json)
"""
import argparse
import json
import math
import re
import subprocess
import sys

import cv2
import numpy as np

W, H = 320, 180
FPS = 30


def read_frames(path, start=None, end=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    cmd += ["-vf", f"fps={FPS},scale={W}:{H}:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()


def kmeans(x, k=8, iters=25, seed=0):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)].astype(np.float64)
    for _ in range(iters):
        d = ((x[:, None, :] - c[None]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = x[lab == j]
            if len(m):
                c[j] = m.mean(0)
    d = ((x[:, None, :] - c[None]) ** 2).sum(-1)
    lab = d.argmin(1)
    share = np.bincount(lab, minlength=k) / len(lab)
    return c, share


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in c)


def hsv_hist(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h = cv2.calcHist([hsv], [0, 1, 2], None, [18, 3, 3], [0, 180, 0, 256, 0, 256])
    return h.flatten()


def global_motion(g0, g1, orb, bf):
    """Return (dx, dy, scale) of g1 relative to g0, or None."""
    k0, d0 = orb.detectAndCompute(g0, None)
    k1, d1 = orb.detectAndCompute(g1, None)
    if d0 is None or d1 is None or len(k0) < 12 or len(k1) < 12:
        (dx, dy), resp = cv2.phaseCorrelate(np.float32(g0), np.float32(g1))
        return (dx, dy, 1.0) if resp > 0.2 else None
    m = bf.match(d0, d1)
    if len(m) < 10:
        return None
    p0 = np.float32([k0[x.queryIdx].pt for x in m])
    p1 = np.float32([k1[x.trainIdx].pt for x in m])
    A, inl = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=1.5)
    if A is None or inl is None or inl.sum() < 8:
        return None
    s = math.sqrt(A[0, 0] ** 2 + A[1, 0] ** 2)
    return float(A[0, 2]), float(A[1, 2]), float(s), A


def vtt_words(path, start, end):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    blocks = re.split(r"\n\n+", txt)
    total = 0
    seen = set()
    for b in blocks:
        m = re.search(r"(\d+):(\d+):(\d+\.\d+) --> (\d+):(\d+):(\d+\.\d+)", b)
        if not m:
            continue
        t0 = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        if t0 < start or t0 >= end:
            continue
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in b.split("\n")[1:]]
        for l in lines:
            if l and "-->" not in l and l not in seen:
                seen.add(l)
                total += len(l.split())
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--vtt")
    ap.add_argument("--words", help="json list of {word,start,end} or {'words':[...]}")
    ap.add_argument("--sheet")
    a = ap.parse_args()

    orb = cv2.ORB_create(400)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    samples, hist_acc = [], np.zeros(18 * 3 * 3)
    lum, sat, satpct, black = [], [], [], []
    flat, edges, ncol, satcol = [], [], [], []
    moving, speeds, resid, cuts = [], [], [], []
    thumbs = []
    prev = prev_g = prev_h = None
    n = 0
    for f in read_frames(a.video, a.start, a.end):
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
        h = hsv_hist(f)
        if n % 15 == 0:
            samples.append(f.reshape(-1, 3)[::23])
            hist_acc += h / h.sum()
            v = hsv[..., 2] / 255.0
            s = hsv[..., 1] / 255.0
            lum.append(float(v.mean()))
            sat.append(float(s.mean()))
            satpct.append(float(((s > 0.5) & (v > 0.3)).mean()))
            black.append(float((v < 0.06).mean()))
            # flat-vector fingerprint
            gf = g.astype(np.float32)
            mu = cv2.blur(gf, (3, 3))
            var = cv2.blur(gf * gf, (3, 3)) - mu * mu
            flat.append(float((var < 9).mean()))
            edges.append(float((cv2.Canny(g, 60, 160) > 0).mean()))
            q = (f // 16).astype(np.int32)
            codes = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]
            cnt = np.sort(np.bincount(codes.ravel(), minlength=4096))[::-1]
            ncol.append(int(np.searchsorted(np.cumsum(cnt), 0.9 * cnt.sum()) + 1))
            m = v > 0.25
            satcol.append(float(s[m].mean()) if m.any() else 0.0)
        if n % 45 == 0 and a.sheet:
            thumbs.append((n / FPS, f.copy()))
        if prev is not None:
            hc = cv2.compareHist(np.float32(prev_h / prev_h.sum()), np.float32(h / h.sum()), cv2.HISTCMP_BHATTACHARYYA)
            is_cut = hc > 0.35
            # a flash or strobe fires the detector on many consecutive frames: count changes
            # less than 0.5 s after the previous cut as part of that same cut (v2, after the MAX run)
            recent = any(cuts[-15:])
            cuts.append(bool(is_cut and not recent))
            if is_cut and recent:
                is_cut = True  # still skip motion estimation on this frame
            gm = None if is_cut else global_motion(prev_g, g, orb, bf)
            if gm is None:
                moving.append(False)
                warped = prev_g
            else:
                dx, dy, sc = gm[:3]
                shift = math.hypot(dx, dy)
                mv = shift > 0.15 * W / 1920 * 6 or abs(sc - 1) > 0.0015
                moving.append(mv)
                if mv:
                    speeds.append(shift * 1920 / W * FPS)
                warped = cv2.warpAffine(prev_g, gm[3], (W, H), borderMode=cv2.BORDER_REPLICATE) if len(gm) > 3 else prev_g
            r = np.abs(g.astype(np.int16) - warped.astype(np.int16))
            border = 4
            r = r[border:-border, border:-border]
            resid.append(0.0 if is_cut else float((r > 25).mean()))
        prev, prev_g, prev_h = f, g, h
        n += 1

    dur = n / FPS
    if n < 10:
        sys.exit("too few frames")
    px = np.concatenate(samples).astype(np.float64)
    cen, share = kmeans(px, 8)
    order = np.argsort(-share)
    palette = [{"hex": hexc(cen[i]), "share": round(float(share[i]), 4)} for i in order]
    darkest = cen[np.argmin(cen.sum(1))]

    resid = np.array(resid)
    animating = resid > 0.002
    # event = a cut, or a jump in (camera-compensated) on-screen change: smoothed residual
    # rises to >= 1.8x its level 10 frames earlier and above 0.6 % of pixels; 10-frame refractory.
    sm = np.convolve(resid, np.ones(6) / 6, mode="same")
    events = 0
    last = -99
    for i in range(len(sm)):
        if cuts[i]:
            events += 1
            last = i
            continue
        if i - last < 10 or i < 10:
            continue
        if sm[i] > 0.006 and sm[i] >= 1.8 * max(sm[i - 10], 0.002):
            events += 1
            last = i
    ncuts = int(np.sum(cuts))
    cut_idx = [0] + [i + 1 for i, c in enumerate(cuts) if c] + [n]
    shots = np.diff(cut_idx) / FPS

    narration_words = None
    if a.vtt:
        narration_words = vtt_words(a.vtt, a.start or 0, a.end or 1e9)
    elif a.words:
        w = json.load(open(a.words, encoding="utf-8"))
        w = w.get("words", w) if isinstance(w, dict) else w
        s0, s1 = a.start or 0, a.end or 1e9
        narration_words = sum(1 for x in w if s0 <= x.get("start", 0) < s1)

    rep = {
        "video": a.video,
        "start": a.start,
        "end": a.end,
        "duration_s": round(dur, 2),
        "frames_analyzed": n,
        "palette": palette,
        "hsv_hist": [round(float(x), 6) for x in (hist_acc / hist_acc.sum())],
        "darkest_hex": hexc(darkest),
        "pure_black_pct": round(100 * float(np.mean(black)), 2),
        "mean_lum": round(float(np.mean(lum)), 3),
        "mean_sat": round(float(np.mean(sat)), 3),
        "saturated_pct": round(100 * float(np.mean(satpct)), 2),
        "flat_pct": round(100 * float(np.mean(flat)), 1),
        "edge_pct": round(100 * float(np.mean(edges)), 2),
        "colors_90": round(float(np.median(ncol)), 1),
        "sat_colored": round(float(np.mean(satcol)), 3),
        "camera_moving_pct": round(100 * float(np.mean(moving)), 1),
        "camera_speed_px_s": round(float(np.median(speeds)), 1) if speeds else 0.0,
        "animating_pct": round(100 * float(np.mean(animating)), 1),
        "events_per_s": round(events / dur, 3),
        "cuts_per_min": round(ncuts / dur * 60, 2),
        "median_shot_s": round(float(np.median(shots)), 2),
        "narration_wps": round(narration_words / dur, 2) if narration_words is not None else None,
        "series": {
            "resid": [round(float(x), 5) for x in resid],
            "moving": [int(x) for x in moving],
            "cuts": [int(x) for x in cuts],
        },
    }
    json.dump(rep, open(a.out, "w"), indent=1)

    if a.sheet and thumbs:
        cols = 6
        rows = math.ceil(len(thumbs) / cols)
        sheet = np.full((rows * (H + 16), cols * W, 3), 20, np.uint8)
        for i, (t, im) in enumerate(thumbs):
            r, c = divmod(i, cols)
            y = r * (H + 16)
            sheet[y:y + H, c * W:(c + 1) * W] = im
            cv2.putText(sheet, f"{(a.start or 0) + t:6.1f}s", (c * W + 4, y + H + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1)
        cv2.imwrite(a.sheet, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])

    short = {k: v for k, v in rep.items() if k not in ("series", "hsv_hist")}
    print(json.dumps(short, indent=1))


if __name__ == "__main__":
    main()
