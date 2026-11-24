# -*- coding: utf-8 -*-
"""单文件动效密度速量。用法： python mad.py <video.mp4>"""
import subprocess, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FILM = sys.argv[1]
raw = subprocess.run(["ffmpeg","-v","error","-i",FILM,"-vf","fps=6,scale=160:90,format=gray",
                      "-f","rawvideo","-pix_fmt","gray","-"], capture_output=True).stdout
n = len(raw)//(160*90)
fr = np.frombuffer(raw[:n*160*90], dtype=np.uint8).reshape(-1,90,160).astype(np.float32)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1,2))
print(f"P10 {np.percentile(d,10):.3f} | med {np.median(d):.3f} | min {d.min():.3f} | max {d.max():.2f} | frozen {(d<0.30).mean()*100:.1f}%")
