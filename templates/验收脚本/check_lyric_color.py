# -*- coding: utf-8 -*-
"""字幕带颜色取样，验证红→蓝之类的渐变。
用法： python check_lyric_color.py <video.mp4> [t1 t2 ...]
"""
import subprocess, sys, os, tempfile
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FILM = sys.argv[1]
TIMES = [float(x) for x in sys.argv[2:]] or [5, 50, 100, 150, 200, 260]
for t in TIMES:
    fd, p = tempfile.mkstemp(suffix=".png"); os.close(fd)
    subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",FILM,"-frames:v","1","-y",p], check=True)
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)[100:290, 380:1540]
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    mask = (mx > 90) & (sat > 0.35)
    if mask.sum() < 50:
        print(f"{t:6.1f}s  no colored pixels"); os.remove(p); continue
    m = a[mask].mean(axis=0)
    print(f"{t:6.1f}s  RGB=({m[0]:5.1f},{m[1]:5.1f},{m[2]:5.1f})  n={int(mask.sum())}")
    os.remove(p)
