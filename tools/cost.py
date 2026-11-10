"""Tokens, wall time and API-price estimate for each run, from the Claude Code transcripts.

Usage: RUNS_PROJECT_PREFIX=C--Users-me-Desktop-proj-runs- python -I tools/cost.py [--out costs.json]
(Claude Code stores each run folder's transcripts in ~/.claude/projects/<path with separators replaced by ->.)

Prices (Claude Opus 5.5, per 1M tokens, from the claude-api skill, cached 2026-10-06):
input $4, output $20, cache read $0.20, cache write 5 min $5 (1.25x), cache write 1 h $8 (2x).
Subagent transcripts (<session>/subagents/*.jsonl) are included.
"""
import argparse
import glob
import json
import os
from datetime import datetime

PRICE = {"in": 4.0, "out": 20.0, "cr": 0.20, "cw5": 5.0, "cw1h": 8.0}
ROOT = os.path.expanduser("~/.claude/projects")
LEVELS = ["low", "medium", "high", "xhigh", "max"]


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


PREFIX = os.environ.get("RUNS_PROJECT_PREFIX", "")  # e.g. "C--Users-me-Desktop-myproject-runs-"


def run_stats(level):
    d = os.path.join(ROOT, f"{PREFIX}{level}")
    files = glob.glob(os.path.join(d, "*.jsonl")) + glob.glob(os.path.join(d, "*", "subagents", "*.jsonl"))
    tok = {"in": 0, "out": 0, "cr": 0, "cw5": 0, "cw1h": 0}
    seen = set()
    first = last = None
    turns = 0
    for f in files:
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if ts:
                t = parse_ts(ts)
                first = t if first is None or t < first else first
                last = t if last is None or t > last else last
            msg = e.get("message") or {}
            if e.get("type") != "assistant" or not isinstance(msg, dict):
                continue
            u = msg.get("usage")
            mid = msg.get("id") or e.get("uuid")
            if not u or mid in seen:  # one API response can be split over several lines
                continue
            seen.add(mid)
            turns += 1
            tok["in"] += u.get("input_tokens", 0) or 0
            tok["out"] += u.get("output_tokens", 0) or 0
            tok["cr"] += u.get("cache_read_input_tokens", 0) or 0
            cc = u.get("cache_creation") or {}
            w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
            w5 = cc.get("ephemeral_5m_input_tokens", 0) or 0
            if not cc:
                w5 = u.get("cache_creation_input_tokens", 0) or 0
            tok["cw5"] += w5
            tok["cw1h"] += w1h
    usd = sum(tok[k] * PRICE[k] for k in tok) / 1e6
    return {
        "level": level,
        "api_calls": turns,
        "tokens": tok,
        "tokens_total": sum(tok.values()),
        "output_tokens": tok["out"],
        "usd_api_estimate": round(usd, 2),
        "first": first.isoformat() if first else None,
        "last": last.isoformat() if last else None,
        "wall_min": round((last - first).total_seconds() / 60, 1) if first and last else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    res = [run_stats(l) for l in LEVELS if os.path.isdir(os.path.join(ROOT, f"{PREFIX}{l}"))]
    for r in res:
        print(f"{r['level']:7s} calls={r['api_calls']:4d} out={r['output_tokens']:>8,d} total={r['tokens_total']:>11,d} ${r['usd_api_estimate']:7.2f} wall={r['wall_min']} min")
    if a.out:
        json.dump({"prices_per_mtok": PRICE, "runs": res}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
