"""Measure all reference clips and aggregate them into style_report.json.

Usage: python -I tools/measure/measure_refs.py PROJECT_DIR
"""
import json
import os
import subprocess
import sys

import numpy as np

P = os.path.abspath(sys.argv[1])
here = os.path.join(P, "tools", "measure")
clips = json.load(open(os.path.join(here, "clips.json")))
outdir = os.path.join(P, "references", "measure")
os.makedirs(outdir, exist_ok=True)

SCALARS = ["pure_black_pct", "mean_lum", "mean_sat", "saturated_pct", "flat_pct", "edge_pct", "colors_90", "sat_colored", "camera_moving_pct",
           "camera_speed_px_s", "animating_pct", "events_per_s", "cuts_per_min", "median_shot_s",
           "narration_wps"]

reports = []
for c in clips:
    out = os.path.join(outdir, f"{c['id']}_{c['start']}.json")
    if not os.path.exists(out):
        vtt = os.path.join(P, "references", "full", c["id"] + ".en.vtt")
        cmd = [sys.executable, "-I", os.path.join(here, "measure.py"),
               os.path.join(P, "references", "full", c["id"] + ".mp4"),
               "--start", str(c["start"]), "--end", str(c["end"]), "--out", out,
               "--sheet", out.replace(".json", ".jpg")]
        if os.path.exists(vtt):
            cmd += ["--vtt", vtt]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(out))
    r["note"] = c["note"]
    reports.append(r)
    print(c["id"], {k: r[k] for k in SCALARS})

agg = {"clips": len(reports), "seconds": sum(r["duration_s"] for r in reports),
       "frames": sum(r["frames_analyzed"] for r in reports), "metrics": {}}
for k in SCALARS:
    v = np.array([r[k] for r in reports if r[k] is not None], float)
    agg["metrics"][k] = {"mean": round(float(v.mean()), 4), "std": round(float(v.std()), 4),
                         "min": round(float(v.min()), 4), "max": round(float(v.max()), 4)}
hist = np.mean([r["hsv_hist"] for r in reports], axis=0)
agg["hsv_hist"] = [round(float(x), 6) for x in hist]

# pooled palette: merge clip palettes weighted by share, re-cluster
cols, w = [], []
for r in reports:
    for p in r["palette"]:
        cols.append([int(p["hex"][i:i + 2], 16) for i in (1, 3, 5)])
        w.append(p["share"])
cols, w = np.array(cols, float), np.array(w)
rng = np.random.default_rng(0)
idx = rng.choice(len(cols), 10, replace=False, p=w / w.sum())
cen = cols[idx].copy()
for _ in range(50):
    lab = ((cols[:, None] - cen[None]) ** 2).sum(-1).argmin(1)
    for j in range(len(cen)):
        m = lab == j
        if m.any():
            cen[j] = np.average(cols[m], axis=0, weights=w[m])
share = np.array([w[lab == j].sum() for j in range(len(cen))]) / w.sum()
order = np.argsort(-share)
agg["palette"] = [{"hex": "#%02X%02X%02X" % tuple(int(x) for x in cen[i]), "share": round(float(share[i]), 4)}
                  for i in order if share[i] > 0]
agg["darkest_hex"] = min((p["hex"] for p in agg["palette"]), key=lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5)))
agg["per_clip"] = [{k: r[k] for k in ["video", "start", "end", "note", "darkest_hex"] + SCALARS} for r in reports]
json.dump(agg, open(os.path.join(P, "references", "style_report.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in agg.items() if k not in ("hsv_hist", "per_clip")}, indent=1))
