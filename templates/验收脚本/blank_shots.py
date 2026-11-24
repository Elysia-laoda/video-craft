# -*- coding: utf-8 -*-
"""逐镜抽检：每镜在 15% / 50% / 85% 抽一帧，量亮度与对比，找"空镜/糊镜"。

用法：
  python blank_shots.py <video.mp4> [manifest.json] [--min-bright 9] [--min-std 6]
manifest 里每行需要 from（帧）与 dur（帧）；没有 manifest 时按固定步长均分。
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

video = sys.argv[1]
manifest = None
for a in sys.argv[2:]:
    if a.endswith(".json"):
        manifest = a
min_bright = 9.0
min_std = 6.0
args = sys.argv[2:]
if "--min-bright" in args:
    min_bright = float(args[args.index("--min-bright") + 1])
if "--min-std" in args:
    min_std = float(args[args.index("--min-std") + 1])

if manifest:
    rows = json.load(open(manifest, encoding="utf-8"))
else:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", video], capture_output=True).stdout.decode().strip())
    n = max(1, int(dur // 4))
    step = dur / n
    rows = [{"id": str(i), "comp": "shot%02d" % i, "from": i * step * 30, "dur": step * 30} for i in range(n)]

tmp = tempfile.mkdtemp()
bad = []
print("%-4s %-18s %-22s %s" % ("id", "comp", "brightness(15/50/85)", "std"))
for r in rows:
    vals, stds = [], []
    for frac in (0.15, 0.5, 0.85):
        t = (r["from"] + r["dur"] * frac) / 30.0
        p = os.path.join(tmp, "f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video,
                        "-frames:v", "1", p], check=True)
        a = np.asarray(Image.open(p).convert("L").resize((160, 90)), dtype=np.float32)
        vals.append(float(a.mean()))
        stds.append(float(a.std()))
    flag = ""
    if min(vals) < min_bright or min(stds) < min_std:
        flag = "  <-- 空/糊"
        bad.append((r.get("comp"), [round(v, 1) for v in vals], [round(s, 1) for s in stds]))
    print("%-4s %-18s %-22s %s%s" % (r.get("id", "?"), r.get("comp", "?"),
          "/".join("%.1f" % v for v in vals), "/".join("%.1f" % s for s in stds), flag))

print()
print("suspect shots: %d / %d" % (len(bad), len(rows)))
for b in bad:
    print("  ", b)
print("判据：亮度 >= %.0f、对比 >= %.0f（片尾字幕卡可例外）" % (min_bright, min_std))
