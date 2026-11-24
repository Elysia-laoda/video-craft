# -*- coding: utf-8 -*-
"""逐镜音效合成：读 manifest，按场景类别铺一条 300 s 立体声轨。

用法：
  python sfx_synth.py <manifest.json> <out.wav> [--duration 300] [--peak 0.7]

设计：
  - 每个镜头至少一个音效事件，落在镜头起点后 0.1 s
  - 爆炸/金属/心跳类镜头在 62% 处补第二击
  - 峰值归一化到 --peak（默认 0.7 ≈ −3 dB），成片混音时再整体限幅
"""
import json, sys, wave
import numpy as np

SR = 48000
manifest, out_path = sys.argv[1], sys.argv[2]
DUR = 300.0
PEAK = 0.7
for i, a in enumerate(sys.argv):
    if a == "--duration":
        DUR = float(sys.argv[i + 1])
    if a == "--peak":
        PEAK = float(sys.argv[i + 1])

N = int(SR * DUR)
out = np.zeros((N, 2), dtype=np.float32)
rows = json.load(open(manifest, encoding="utf-8"))


def rnd(seed):
    return np.random.default_rng(seed)


def env_ad(n, a, d):
    e = np.ones(n, dtype=np.float32)
    aa = min(max(1, int(a * SR)), n)
    e[:aa] = np.linspace(0, 1, aa)
    tail = n - aa
    if tail > 0:
        dd = min(max(1, int(d * SR)), tail)
        e[aa:aa + dd] = np.exp(-np.linspace(0, 5, dd))
        e[aa + dd:] = 0
    return e


def band(n, lo, hi, seed):
    x = rnd(seed).standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    m = ((f >= lo) & (f <= hi)).astype(np.float32)
    k = max(3, int(n * 0.01))
    m = np.convolve(m, np.ones(k) / k, mode="same")
    y = np.fft.irfft(X * m, n).astype(np.float32)
    return y / max(1e-6, np.abs(y).max())


def sweep(n, f0, f1):
    f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)


def s_snow(seed, d=2.6):
    n = int(d * SR)
    return (band(n, 700, 6000, seed) * 0.5 + band(n, 180, 900, seed + 1) * 0.5) * env_ad(n, 0.35, d * 0.8)


def s_radio(seed, d=0.22):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1180 * t).astype(np.float32) * 0.7 + np.sin(2 * np.pi * 590 * t).astype(np.float32) * 0.3
    return x * env_ad(n, 0.004, 0.16)


def s_boom(seed, d=1.1):
    n = int(d * SR)
    return (sweep(n, 95, 34) * 0.85 + band(n, 40, 320, seed) * 0.45) * env_ad(n, 0.005, 0.95)


def s_metal(seed, d=0.55):
    n = int(d * SR)
    return (band(n, 2600, 12000, seed) * 0.7 + band(n, 420, 1800, seed + 2) * 0.4) * env_ad(n, 0.002, 0.45)


def s_heart(seed, d=1.0):
    n = int(d * SR); seg = np.zeros(n, dtype=np.float32)
    k = min(int(0.3 * SR), n); t = np.arange(k) / SR
    seg[:k] = np.sin(2 * np.pi * 55 * t).astype(np.float32) * env_ad(k, 0.006, 0.24)
    i2 = int(0.42 * SR); k2 = min(int(0.24 * SR), max(0, n - i2))
    if k2 > 0:
        t2 = np.arange(k2) / SR
        seg[i2:i2 + k2] += np.sin(2 * np.pi * 48 * t2).astype(np.float32) * env_ad(k2, 0.006, 0.2) * 0.55
    return seg


def s_whoosh(seed, d=0.9):
    n = int(d * SR)
    e = np.exp(-np.linspace(0, 3.0, n)).astype(np.float32)
    e[:int(0.1 * SR)] *= np.linspace(0, 1, int(0.1 * SR))
    return band(n, 300, 4200, seed) * e


def s_broadcast(seed, d=1.8):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.5 + np.sin(2 * np.pi * 110 * t).astype(np.float32) * 0.3
    return (x * (1 + 0.4 * np.sin(2 * np.pi * 3.2 * t)).astype(np.float32)) * env_ad(n, 0.02, 1.5)


def s_door(seed, d=0.8):
    n = int(d * SR)
    return (sweep(n, 72, 40) * 0.8 + band(n, 90, 700, seed) * 0.3) * env_ad(n, 0.004, 0.65)


def s_click(seed, d=0.09):
    n = int(d * SR)
    return band(n, 1600, 9000, seed) * env_ad(n, 0.001, 0.07)


def s_air(seed, d=1.4):
    n = int(d * SR)
    return band(n, 60, 300, seed) * env_ad(n, 0.4, 1.0) * 0.5


GEN = {"snow": s_snow, "radio": s_radio, "boom": s_boom, "metal": s_metal, "heart": s_heart,
       "whoosh": s_whoosh, "broadcast": s_broadcast, "door": s_door, "click": s_click, "air": s_air}
DEFAULT_KIND = "air"       # 未登记场景用空气底噪
# 按 comp 名映射音色 —— 换成你自己的场景名即可
MAP = {}


def kind_of(comp):
    if comp in MAP:
        return MAP[comp]
    low = comp.lower()
    for key, kind in (("snow", "snow"), ("ice", "snow"), ("radio", "radio"), ("signal", "radio"),
                      ("boom", "boom"), ("explo", "boom"), ("metal", "metal"), ("cut", "metal"),
                      ("heart", "heart"), ("door", "door"), ("gate", "door"), ("click", "click"),
                      ("ship", "whoosh"), ("fly", "whoosh"), ("broadcast", "broadcast")):
        if key in low:
            return kind
    return DEFAULT_KIND


def place(sig, t0, gain, pan):
    i0 = int(t0 * SR)
    if i0 >= N or i0 < 0:
        return
    n = min(len(sig), N - i0)
    s = sig[:n] * gain
    l = np.sqrt((1 - pan) / 2)
    r = np.sqrt((1 + pan) / 2)
    out[i0:i0 + n, 0] += s * l
    out[i0:i0 + n, 1] += s * r


count = 0
for idx, row in enumerate(rows):
    comp = row.get("comp", "?")
    t0 = row["from"] / 30.0
    dur = row["dur"] / 30.0
    kind = kind_of(comp)
    place(GEN[kind](idx + 3), t0 + 0.10, 0.30 if kind in ("boom", "metal", "whoosh", "broadcast") else 0.22,
          (idx % 5 - 2) * 0.12)
    count += 1
    if kind in ("boom", "metal", "heart") and dur > 2.2:
        place(GEN[kind](idx + 101), t0 + dur * 0.62, 0.20, (idx % 3 - 1) * 0.18)
        count += 1

peak = float(np.abs(out).max())
out = out / max(peak, 1e-9) * PEAK
pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
with wave.open(out_path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("events: %d  raw peak: %.3f  ->  %s" % (count, peak, out_path))
print("下一步：ffmpeg -i %s -b:a 192k %s" % (out_path, out_path.replace(".wav", ".mp3")))
