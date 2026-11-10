Make a 60-second educational video about "What If You Fell Into a Black Hole... Slowly?" in the style measured in `reference/style_report.json` (the flat-vector look of Kurzgesagt – In a Nutshell). Write the script, draw everything as vector graphics, animate it, and add sound: voiceover, sound effects and music, like the original. Work on your own from start to finish. Don't ask me anything.

## Technical setup (same for every run)

- Work only inside this folder. Do not read or write anything outside it, and do not download or look up videos, frames or artwork of the reference channel. The measurements are your only reference.
- Deliverable: `final.mp4` in this folder, 1920x1080, 30 fps, 55–65 seconds, with the voiceover mixed in.
- Voiceover: any TTS or a recorded voice. (The experiment used one ElevenLabs narrator voice for all runs so the comparison stayed fair.)
- Sound design like the reference channel: sound effects synced to what happens on screen (whooshes, pops, impacts, ambience) and a music bed under the narration, with the narration always clearly on top. Make the sound effects yourself (synthesize them in code) and the music either in code or with any instrumental music generator. Do not download audio from the internet.
- Pick any rendering stack you like (the experiment ran on Windows 11 with Python, Node, ffmpeg and an NVIDIA GPU).
- Keep a short `RUNLOG.md` while you work: a timestamped line for each major step, and every error or failed attempt with what you did about it.

## What the numbers in `style_report.json` mean

All metrics were computed frame by frame at 30 fps on 10 reference clips (450 s), on frames scaled to 320 px wide.

- `palette`: dominant colours (k-means) with their share of pixels. `darkest_hex`: darkest dominant colour.
- `pure_black_pct`: % of pixels with brightness below 6 %.
- `mean_lum`, `mean_sat`: mean HSV value and saturation (0–1). `sat_colored`: mean saturation of pixels brighter than 25 %. `saturated_pct`: % of pixels with saturation > 0.5 and brightness > 0.3.
- `flat_pct`: % of pixels in flat areas (3x3 local variance below 9). `edge_pct`: % of edge pixels (Canny). `colors_90`: how many of 4096 colour bins cover 90 % of the frame.
- `camera_moving_pct`: % of frames in which the whole frame moves (pan or zoom). `camera_speed_px_s`: median speed of that motion in 1920-px units per second.
- `animating_pct`: % of frames where something still changes after camera motion is removed.
- `events_per_s`: how often a new element or action starts (or a cut happens), per second.
- `cuts_per_min`, `median_shot_s`: hard cuts per minute and median shot length.
- `narration_wps`: narration words per second.
- `metrics`: mean, std, min and max across the 10 clips. `per_clip`: the values for each clip.
