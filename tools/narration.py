"""Transcribe a video's narration with word timestamps (Groq Whisper) -> words.json.

Usage: python -I narration.py VIDEO OUT.json
Reads GROQ_API_KEY from the environment or ~/.config/watch/.env.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid


def key():
    k = os.environ.get("GROQ_API_KEY")
    if k:
        return k
    p = os.path.expanduser("~/.config/watch/.env")
    for line in open(p, encoding="utf-8"):
        if line.startswith("GROQ_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("no GROQ_API_KEY")


def main():
    video, out = sys.argv[1], sys.argv[2]
    tmp = os.path.join(tempfile.gettempdir(), f"narr_{uuid.uuid4().hex}.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", tmp], check=True)
    audio = open(tmp, "rb").read()
    os.remove(tmp)
    b = uuid.uuid4().hex
    parts = []
    for name, val in [("model", "whisper-large-v3"), ("response_format", "verbose_json"),
                      ("timestamp_granularities[]", "word"), ("language", "en")]:
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode())
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode() + audio + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=b"".join(parts),
                                 headers={"Authorization": f"Bearer {key()}", "Content-Type": f"multipart/form-data; boundary={b}",
                                          "User-Agent": "measure-tool/1.0"})
    res = json.load(urllib.request.urlopen(req, timeout=300))
    words = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in res.get("words", [])]
    json.dump({"text": res.get("text", ""), "words": words}, open(out, "w", encoding="utf-8"), indent=1)
    dur = words[-1]["end"] - words[0]["start"] if words else 0
    print(f"{len(words)} words, speech span {dur:.1f}s")


if __name__ == "__main__":
    main()
