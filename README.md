# flat-vector-explainer

A Claude skill: make a 60-second flat-vector explainer and score it against a measured reference style (0-100).

Install: copy this folder into `~/.claude/skills/` (Claude Code) or your project's `.claude/skills/`, then ask Claude for "a 60-second flat-vector explainer about <topic>".

Requirements: Python 3.10+ with `opencv-python` and `numpy`, ffmpeg on PATH; a `GROQ_API_KEY` for narration timing.

The reference numbers were measured from 10 clips of Kurzgesagt – In a Nutshell (https://www.youtube.com/@kurzgesagt). Only numbers are included — no frames, artwork or audio. The style belongs to the artists who built it; go watch the real thing.
