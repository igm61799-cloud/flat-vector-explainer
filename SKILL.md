---
name: flat-vector-explainer
description: Make a 60-second educational explainer in a flat-vector animation style (bold colours, no outlines, glow, a camera that never stops), measured frame by frame against reference clips and scored 0-100. Use when the user wants an animated explainer "in the style of" a flat-vector education channel, wants to match a measured style report, or wants to score how close a video gets to a reference style.
---

# Flat-vector explainer

Everything here came out of one experiment: the same prompt run at five effort levels, every result measured with the tools in `tools/`. The numbers and rules below are what that experiment found, not taste.

## What you get

- `reference/style_report.json` — the target fingerprint, measured at 30 fps on 10 reference clips (450 s, 13,500 frames): palette, saturation, flatness, colour count, edges, pure black, camera motion, animation, new-element rate, cuts, narration speed.
- `reference/clips/*.json` — the per-clip measurements the similarity score compares against (numbers only, no frames).
- `tools/measure.py` — measure any video the same way (`--words words.json` adds narration speed).
- `tools/narration.py` — word timestamps via Whisper (Groq API, `GROQ_API_KEY`).
- `tools/similarity.py` — 0-100 score against the reference clips.
- `tools/cost.py` — tokens and API-price estimate of a Claude Code run, from its transcript.
- `PROMPT.md` — the prompt used for the experiment.
- `rules.md` — what the five runs got right and wrong. Read it before you start.

## Workflow

1. Read `PROMPT.md`, `rules.md` and `reference/style_report.json`.
2. Write a ~150-word script (≈2.5 words/s for 60 s). Voice it; get word timestamps (`tools/narration.py`).
3. Plan 8-10 shots on word anchors. Draw everything from vector primitives (paths, circles, rounded rects, gradients, glow) in any stack (skia-python, Remotion/SVG, canvas).
4. Render a first cut, then **measure yourself**:
   ```bash
   python -I tools/narration.py final.mp4 words.json
   python -I tools/measure.py final.mp4 --words words.json --out me.json --sheet me.jpg
   python -I tools/similarity.py me.json
   ```
   Fix the lowest-scoring metrics, not the ones closest to failing a band (see `rules.md` #2), and re-measure.
5. Sound: voiceover on top; synthesized SFX on the events; a ducked music bed. **Listen to it.** No run in the experiment did.

## Score reference (same tool)

| What | Score |
|---|---|
| Real reference clips, each scored against the other nine | median ~80 (44-91) |
| Held-out clips from the same channel | 65-85 |
| Screen recording | 60 |
| Realistic 3D render | 36 |
| Experiment: low / medium / high / xhigh / max | 62.6 / 63.7 / 71.0 / 67.4 / 83.2 |

The score is a yardstick, not a judge: it can't see drawing quality or story. Watch the result.
