# -*- coding: utf-8 -*-
"""手工复核拍速：给两个强音头与中间拍数，自动试 N±2，选出与音头最贴合的一组。
用法： python check_tempo.py <audio> <t1> <t2> <N> [fps]
  t1/t2 = 两个强音头的时间（秒），N = 你数出来的拍数（工具会顺带试 N-2..N+2）
"""
import sys, wave, subprocess, tempfile, os
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC, t1, t2, N = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
FPS = float(sys.argv[5]) if len(sys.argv) > 5 else 30.0

def load(path):
    if path.lower().endswith(".wav"):
        with wave.open(path, "rb") as w:
            sr, ch = w.getframerate(), w.getnchannels()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        if ch == 2:
            x = x.reshape(-1, 2).mean(axis=1)
        return x, sr
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "44100", tmp], check=True)
    with wave.open(tmp, "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    os.remove(tmp)
    return x, sr

x, sr = load(SRC)
NFFT, HOP = 2048, 512
idx = np.arange(NFFT)[None, :] + HOP * np.arange(1 + (len(x) - NFFT) // HOP)[:, None]
S = np.abs(np.fft.rfft(x[idx] * np.hanning(NFFT)[None, :], axis=1))
freqs = np.fft.rfftfreq(NFFT, 1.0 / sr)
low = (freqs >= 20) & (freqs <= 150)
flux = np.concatenate([[0.0], np.maximum(0.0, np.diff(S, axis=0)).sum(axis=1)])
flux_low = np.concatenate([[0.0], np.maximum(0.0, np.diff(S[:, low], axis=0)).sum(axis=1)])
env = sr / HOP
flux = flux - flux.mean(); flux[flux < 0] = 0
flux_low = flux_low - flux_low.mean(); flux_low[flux_low < 0] = 0
base = float(flux.mean()) + 1e-9
base_low = float(flux_low.mean()) + 1e-9
dur = len(flux) / env

def evaluate(n):
    period = (t2 - t1) / n
    if period <= 0.15 or period > 2.0:
        return None
    grid = t1 + np.arange(n + 1) * period
    grid = grid[grid < dur - 0.1]
    if len(grid) < 3:
        return None
    idxs = np.clip((grid * env).astype(int), 0, len(flux) - 1)
    raw = float(flux[idxs].mean())
    raw_low = float(flux_low[idxs].mean())
    # 与同拍数、随机相位的网格比较，消除"拍越多分越高"的偏差
    rnd_scores = []
    for j in range(8):
        off = (j - 4) * period / 9.0
        g2 = grid + off
        g2 = g2[(g2 >= 0) & (g2 < dur - 0.1)]
        if len(g2) < 3: continue
        i2 = np.clip((g2 * env).astype(int), 0, len(flux) - 1)
        rnd_scores.append(float(flux[i2].mean()))
    mu = float(np.mean(rnd_scores)) if rnd_scores else 0.0
    sd = float(np.std(rnd_scores)) + 1e-9
    score = (raw - mu) / sd
    # 低频段（底鼓）同样做随机相位基线
    rnd_low = []
    for j in range(8):
        off = (j - 4) * period / 9.0
        g2 = grid + off
        g2 = g2[(g2 >= 0) & (g2 < dur - 0.1)]
        if len(g2) < 3: continue
        i2 = np.clip((g2 * env).astype(int), 0, len(flux_low) - 1)
        rnd_low.append(float(flux_low[i2].mean()))
    mu2 = float(np.mean(rnd_low)) if rnd_low else 0.0
    sd2 = float(np.std(rnd_low)) + 1e-9
    score_low = (raw_low - mu2) / sd2
    # 相位质感：每拍 ±0.3 拍内找局部峰，看偏移分布
    offs = []
    half = int(0.3 * period * env)
    for g in grid:
        c = int(g * env)
        lo, hi = max(0, c - half), min(len(flux), c + half + 1)
        if hi > lo:
            offs.append((lo + int(np.argmax(flux[lo:hi]))) / env - g)
    offs = np.array(offs) if offs else np.array([0.0])
    return dict(n=n, bpm=60.0 / period, period=period, score=score, score_low=score_low,
                med=float(np.median(offs)), maxabs=float(np.abs(offs).max()), grid=grid)

print(f"audio {dur:.2f}s; pair {t1:.3f} -> {t2:.3f}s; N given {N}")
cands = [evaluate(n) for n in range(N - 2, N + 3)]
cands = [c for c in cands if c]
cands.sort(key=lambda c: -(c["score_low"] * 1.5 + c["score"]))
print("  N    BPM      period    z_all  z_low  median_off  max_off")
for c in cands:
    print(f"  {c['n']:<4d} {c['bpm']:7.2f}  {c['period']:.4f}s  {c['score']:5.2f}  {c['score_low']:5.2f}   {c['med']*1000:+6.0f} ms  {c['maxabs']*1000:5.0f} ms")
best = cands[0]
print(f"\nBEST: N={best['n']}  BPM={best['bpm']:.3f}  period={best['period']:.4f}s = {best['period']*FPS:.3f}f @{FPS:g}fps")
print(f"first beat t1={t1:.3f}s；拍点覆盖 {best['grid'][0]:.2f}–{best['grid'][-1]:.2f}s / 全片 {dur:.1f}s")
print(f"相位：中位偏移 {best['med']*1000:+.0f}ms（建议把 t1 挪到 t1+{best['med']:+.3f}s），最大 {best['maxabs']*1000:.0f}ms")
if abs(best["med"]) > 0.05:
    print("!! 中位偏移 >50ms：首拍应当修正后再写进代码")
if best["maxabs"] > 0.25:
    print("!! 仍有拍点离最近音头 >250ms：这段可能不是规则节拍，换一段重数 N")
print("\n把 BEST 那行的 BPM 与修正后的 t1 写进代码常量；再用 beat(n)=t1+n*period 抽查 30/90/150s。")
