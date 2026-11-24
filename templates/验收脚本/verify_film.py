# -*- coding: utf-8 -*-
"""完整验收：规格 + 动效密度 + 逐 10s 表。
用法： python verify_film.py <video.mp4>
"""
import json, subprocess, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FILM = sys.argv[1]

probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,nb_read_frames",
                        "-show_entries", "format=duration,size", "-of", "json", FILM],
                       capture_output=True).stdout.decode("utf-8", "replace")
j = json.loads(probe)
v = next(s for s in j["streams"] if s["codec_type"] == "video")
a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
print(f"video: {v['width']}x{v['height']} @ {v['r_frame_rate']}  frames {v.get('nb_read_frames')}")
print(f"dur: {float(j['format']['duration']):.3f}s  size {int(j['format']['size'])/1048576:.1f} MB")
print(f"audio: {a['codec_name']} {a['sample_rate']}Hz {a['channels']}ch" if a else "audio: MISSING")

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", FILM, "-vf", "fps=6,scale=160:90,format=gray",
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
n = len(raw) // (160 * 90)
fr = np.frombuffer(raw[:n * 160 * 90], dtype=np.uint8).reshape(-1, 90, 160).astype(np.float32)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
peak_i = int(np.argmax(d)); mask = np.ones(len(d), bool); mask[max(0, peak_i-15):peak_i+15] = False
gap = float(np.median(d[mask]))
print("\n=== motion density ===")
print(f"P10 {np.percentile(d,10):.3f} (>=0.30) | median {np.median(d):.3f} (0.35~0.8)")
print(f"peak {d.max():.2f} @ {peak_i/6:.1f}s (>=3) | peak/gap {d.max()/max(gap,1e-6):.0f} (>=5)")
print(f"frozen(<0.30): {(d<0.30).sum()}/{len(d)} ({(d<0.30).mean()*100:.1f}%)")
print("\n=== per 10s (mean/min) ===")
row = []
for i in range(0, len(d), 60):
    seg = d[i:i+60]
    row.append(f"{i/6:5.0f}s {seg.mean():.3f}/{seg.min():.3f}")
    if len(row) == 3: print("   " + "  |  ".join(row)); row = []
if row: print("   " + "  |  ".join(row))
