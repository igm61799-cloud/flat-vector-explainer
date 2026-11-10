"""Similarity score 0-100 of a measured clip (measure.py output) vs the reference style.

Usage: python -I similarity.py CANDIDATE.json [--refs references/measure] [--out score.json]

Each metric is compared with the reference clips' median using a robust spread
(IQR/1.35, floored), score_i = 100 * exp(-z^2 / 2). Palette = mean of the 3 best
HSV-histogram intersections with individual reference clips (the style has several
colour moods; matching one of them well counts). Final = weighted mean.
"""
import argparse
import glob
import json
import math
import os

import numpy as np

WEIGHTS = {
    "palette": 25,
    "sat_colored": 20,
    "flat_pct": 10,
    "colors_90": 5,
    "edge_pct": 5,
    "pure_black_pct": 5,
    "camera_moving_pct": 5,
    "animating_pct": 5,
    "events_per_s": 10,
    "cuts_per_min": 5,
    "narration_wps": 5,
}
FLOOR = {"sat_colored": 0.08, "flat_pct": 5, "colors_90": 25, "edge_pct": 1.0, "pure_black_pct": 3,
         "camera_moving_pct": 10, "animating_pct": 10, "events_per_s": 0.15, "cuts_per_min": 2.5,
         "narration_wps": 0.25}
LABELS = {"palette": "Colour palette", "sat_colored": "Colour saturation", "flat_pct": "Flat fills",
          "colors_90": "Colour count", "edge_pct": "Edge density", "pure_black_pct": "Pure black",
          "camera_moving_pct": "Camera in motion", "animating_pct": "Something animating",
          "events_per_s": "New element rate", "cuts_per_min": "Cut rate", "narration_wps": "Narration speed"}


def load_refs(d):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]


def score(cand, refs):
    out = {}
    h = np.array(cand["hsv_hist"])
    inter = sorted((float(np.minimum(h, np.array(r["hsv_hist"])).sum()) for r in refs), reverse=True)
    out["palette"] = {"value": round(float(np.mean(inter[:3])), 3), "score": round(100 * min(1.0, np.mean(inter[:3]) / 0.75), 1),
                      "reference": ">=0.75 overlap with a reference colour mood"}
    for k, fl in FLOOR.items():
        v = cand.get(k)
        rv = np.array([r[k] for r in refs if r.get(k) is not None], float)
        # the style has several moods, so anything inside the 20-80 % band of the
        # reference clips is a full match; outside it the score decays with distance.
        lo, hi = np.percentile(rv, [20, 80])
        sig = max((hi - lo) / 2, fl)
        ref = [round(float(lo), 3), round(float(hi), 3)]
        if v is None:
            out[k] = {"value": None, "score": None, "reference": ref}
            continue
        d = 0.0 if lo <= v <= hi else min(abs(v - lo), abs(v - hi))
        z = d / sig
        out[k] = {"value": v, "score": round(100 * math.exp(-z * z / 2), 1), "reference": ref}
    tot = wsum = 0
    for k, w in WEIGHTS.items():
        s = out[k]["score"]
        if s is not None:
            tot += w * s
            wsum += w
    return round(tot / wsum, 1), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cand")
    ap.add_argument("--refs", default=os.path.join(os.path.dirname(__file__), "..", "reference", "clips"))
    ap.add_argument("--exclude", help="substring of a reference file to leave out (leave-one-out check)")
    ap.add_argument("--out")
    a = ap.parse_args()
    refs = load_refs(a.refs)
    if a.exclude:
        refs = [r for r in refs if a.exclude not in r["video"]]
    cand = json.load(open(a.cand))
    total, parts = score(cand, refs)
    res = {"candidate": a.cand, "similarity": total, "metrics": {LABELS[k]: v for k, v in parts.items()}}
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
