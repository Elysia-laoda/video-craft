# -*- coding: utf-8 -*-
"""量音乐：给出**候选**拍速（自相关峰）与逐 2s 电平，并提示如何复核。

用法： python analyze_music.py <audio.wav|mp3> [fps]

约定：这里的 BPM 只是候选。音头密集的曲子自相关会锁到伪拍
（默认 BGM 实测：自动 111.25 / 首拍 0.372，人工复核后是 110.00 / 0.348）。
确认值见 references/09-曲目参数.md；务必用 check_tempo.py 复核后再写常量。
"""
import sys, wave, subprocess, tempfile, os
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if len(sys.argv) < 2:
    print("用法: python analyze_music.py <audio.wav|mp3> [fps]")
    print("例:   python analyze_music.py D:\\music\\bgm.mp3 30")
    sys.exit(2)

SRC = sys.argv[1]
FPS = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0


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
dur = len(x) / sr
print(f"file: {dur:.3f}s @ {sr}Hz  peak={np.abs(x).max():.3f}")

NFFT, HOP = 2048, 512
idx = np.arange(NFFT)[None, :] + HOP * np.arange(1 + (len(x) - NFFT) // HOP)[:, None]
S = np.abs(np.fft.rfft(x[idx] * np.hanning(NFFT)[None, :], axis=1))
env = sr / HOP
flux = np.concatenate([[0.0], np.maximum(0.0, np.diff(S, axis=0)).sum(axis=1)])
flux = flux - flux.mean()
flux[flux < 0] = 0

# --- 自相关：只取候选 ---
curve = []
for bpm in np.arange(55, 200, 0.25):
    lag = int(round(60.0 / bpm * env))
    if lag < 2 or lag >= len(flux) // 2:
        continue
    ac = float(np.dot(flux[:-lag], flux[lag:]) / (len(flux) - lag))
    curve.append((bpm, ac))

peaks = []
for i in range(1, len(curve) - 1):
    bpm, ac = curve[i]
    if ac >= curve[i - 1][1] and ac >= curve[i + 1][1] and ac > 0:
        if not peaks or bpm - peaks[-1][0] > 2.0:
            peaks.append((bpm, ac))
peaks.sort(key=lambda r: -r[1])
top = sorted(peaks[:3], key=lambda r: -r[1])


def phase_for(bpm):
    period = 60.0 / bpm
    best_ph, best_v = 0.0, -1.0
    for ph in np.arange(0, period, 1.0 / env):
        k = int(round(ph * env))
        seg = flux[k::max(1, int(round(period * env)))]
        v = float(seg.mean()) if len(seg) else -1.0
        if v > best_v:
            best_v, best_ph = v, ph
    return best_ph


print("\n== 候选拍速（自相关，仅供起步）==")
for bpm, ac in top:
    ph = phase_for(bpm)
    print(f"  {bpm:7.2f} BPM  首拍 {ph:.3f}s  每拍 {60/bpm:.4f}s = {60/bpm*FPS:.3f}f  (ac={ac:.3g})")

print("\n!! 不要直接采信上面任何一个：")
print("   1) 已知曲目先查 references/09-曲目参数.md（默认 BGM = 110.00 BPM / 首拍 0.348s）")
print("   2) 否则跑 check_tempo.py <音频> <t1> <t2> <N>，用 60–90s 基线 + 低频段 z 分数定案")

known = "AI的小曲"
if known in os.path.basename(SRC):
    print("\n!! 这是默认 BGM：确认值 110.00 BPM / 首拍 0.348s / 每拍 0.5455s（已用 check_tempo 复核）")

blk = 2 * sr
print("\nRMS per 2s (dBFS):")
line = []
for i in range(0, len(x), blk):
    seg = x[i:i + blk]
    r = float(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    line.append(f"{i // sr:3d}:{20 * np.log10(r):5.1f}")
    if len(line) == 12:
        print("  " + " ".join(line))
        line = []
if line:
    print("  " + " ".join(line))
