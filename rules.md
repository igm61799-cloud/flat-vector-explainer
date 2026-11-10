# Rules the five runs taught

Measured on the experiment's results (`similarity.py`, reference bands are the 20-80 % range of the reference clips).

1. **Measure after the first render.** Medium, high, xhigh and max each wrote a measuring script and fixed what it showed (medium: "too dark/dull/flat"). Low never checked and scored lowest.
2. **Keep coloured pixels saturated.** Target saturation of pixels brighter than 25 %: 0.68-0.76. Xhigh lowered its background saturation to bring the *share* of saturated pixels down to the reference mean and fell to 0.55 — it scored below high. Don't trade colour boldness for any other metric.
3. **Almost no pure black.** In 8 of 10 reference clips under 2.5 % of pixels are below 6 % brightness; the darkest colours are deep navy / purple (#0A0539, #020631, #130836…). Don't open on a black frame and don't fill the inside of a black hole with #000 over large areas for long.
4. **Frames need detail.** Every run came out too flat and clean at first. Targets: flat fills 62-77 %, 33-73 colour bins covering 90 % of the frame, 5-12 % edge pixels. Add layers: dust, small stars, soft nebula blobs, secondary objects.
5. **Motion budget.** Camera moving in ~54 % of frames; something animating in ~70 %; a new element or action about every 1.5-2 s; hard cuts ~4-7 per minute, median shot ~7 s.
6. **Narration 2.4-2.7 words/s.** Put shots and sound effects on word timestamps.
7. **A flash is one cut.** A white flash fires histogram cut detectors on every frame; `measure.py` v2 merges detections within 0.5 s.
8. **Listen to the mix.** All five runs checked audio only by numbers (levels, spectrograms, Whisper). Level checks miss bad sound.
9. **Windows + faster-whisper:** CUDA can fail on a missing `cublas64_12.dll`; fall back to CPU int8.
10. **Same idea every time.** Four of five runs independently chose "astronaut on a tether lowered from a spaceship, with clocks". If you want something original, ask for three concepts first and pick one.
11. **Effort.** Low ≈ $1.35 / 4 min, high ≈ $5 / 24 min (score 71), max ≈ $17.5 / 57 min (score 83) at API prices. High is the best draft setting; max for the one you publish.
