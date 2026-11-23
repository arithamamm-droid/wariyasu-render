"""紹介動画4本の BGM・効果音を合成し(外部の音源は使わない)、mp4 に重ねる。

  python synth_audio.py <static/sns のパス> <出力フォルダ>
映像は再エンコードせず(-c:v copy)、音声トラック(AAC)だけ足す。
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 20.0
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=0.2):
    e = np.ones(n)
    na, nr = max(1, int(SR * a)), min(n, int(SR * r))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.exp(-np.linspace(0, 5, nr))
    return e


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---- 楽器 ----
def marimba(f, d=0.35):
    t = t_(d)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 30)) * np.exp(-t * 9)


def pluck(f, d=0.4):  # 弦をはじく音(Karplus-Strong)
    n, p = int(SR * d), max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return out


def epiano(f, d=0.6):
    t = t_(d)
    mod = np.sin(2 * np.pi * f * 2 * t) * 1.2 * np.exp(-t * 4)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 3.5)


def pad(f, d):
    t = t_(d)
    s = sum(np.sin(2 * np.pi * f * k * t + k) / k for k in (1, 2, 3)) + 0.5 * np.sin(2 * np.pi * f * 1.005 * t)
    return s * env(len(t), 0.3, 0.4) * 0.4


def kick(d=0.25):
    t = t_(d)
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def hat(d=0.05):
    return rng.uniform(-1, 1, int(SR * d)) * np.exp(-t_(d) * 80) * 0.5


def clap(d=0.15):
    n = rng.uniform(-1, 1, int(SR * d))
    return np.convolve(n, np.ones(8) / 8, "same") * np.exp(-t_(d) * 25)


# ---- 効果音 ----
def whoosh(d=0.35):
    n = rng.uniform(-1, 1, int(SR * d))
    for w in (3, 9):
        n = np.convolve(n, np.ones(w) / w, "same")
    x = np.linspace(0, 1, len(n))
    return n * np.sin(np.pi * x) ** 2 * 2.2


def tick():
    t = t_(0.03)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 200) * 0.6


def pop():
    t = t_(0.12)
    f = 300 + 900 * np.exp(-t * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)


def thud():
    t = t_(0.3)
    f = 45 + 60 * np.exp(-t * 25)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12)
    return body + rng.uniform(-1, 1, len(t)) * np.exp(-t * 60) * 0.3


def beep(f=1800, d=0.07):
    t = t_(d)
    return np.sign(np.sin(2 * np.pi * f * t)) * 0.18 * env(len(t), 0.002, 0.02)


def chime():
    return sum(epiano(midi(m), 1.6) * g for m, g in ((84, 0.6), (88, 0.45), (91, 0.4)))


def printer(d):
    t = t_(d)
    buzz = np.sign(np.sin(2 * np.pi * 95 * t)) * 0.12 + rng.uniform(-1, 1, len(t)) * 0.05
    gate = (np.sin(2 * np.pi * 7 * t) > -0.2).astype(float)
    return np.convolve(buzz * gate, np.ones(20) / 20, "same") * env(len(t), 0.05, 0.1)


def tear():
    n = rng.uniform(-1, 1, int(SR * 0.4))
    return n * (rng.uniform(0, 1, len(n)) > 0.6) * np.exp(-np.linspace(0, 4, len(n))) * 0.7


# ---- ミックス ----
def put(track, sig, at, gain=1.0):
    i = int(at * SR)
    j = min(len(track), i + len(sig))
    if i < len(track):
        track[i:j] += sig[: j - i] * gain


def song(bpm, prog, lead, voice, drums, swing=0.0):
    """prog: 小節ごとのコード(ルートの midi)、lead: 1小節の8分音符の音程(コードからの度数)"""
    bgm = np.zeros(int(SR * DUR))
    beat = 60 / bpm
    bar = beat * 4
    nbar = int(DUR / bar) + 1
    for b in range(nbar):
        root = prog[b % len(prog)]
        t0 = b * bar
        put(bgm, pad(midi(root - 12), bar), t0, 0.22)
        for k, step in enumerate(lead):
            if step is None:
                continue
            at = t0 + k * beat / 2 + (swing * beat / 2 if k % 2 else 0)
            put(bgm, voice(midi(root + step)), at, 0.32)
        for k in range(4):
            if "kick" in drums and k in drums["kick"]:
                put(bgm, kick(), t0 + k * beat, 0.55)
            if "clap" in drums and k in drums["clap"]:
                put(bgm, clap(), t0 + k * beat, 0.3)
            if drums.get("hat"):
                put(bgm, hat(), t0 + k * beat + beat / 2, 0.25)
    return bgm


MAJ = [0, 4, 7, 12, 16, 12, 7, 4]
P = {  # 動画ごとの BGM(テンポ・音色・コードを変えて4本が被らないように)
    "pricetag": dict(bpm=120, prog=[60, 67, 69, 65], lead=MAJ, voice=marimba, drums={"kick": (0, 2), "hat": True}),
    "receipt": dict(bpm=88, prog=[62, 57, 59, 55], lead=[0, None, 7, None, 11, None, 7, 14], voice=epiano,
                    drums={"kick": (0,), "clap": (2,), "hat": True}, swing=0.33),
    "scale": dict(bpm=108, prog=[65, 60, 62, 58], lead=[0, 7, 12, 7, 4, 7, 16, 7], voice=pluck, drums={"kick": (0, 2)}),
    "type": dict(bpm=128, prog=[57, 53, 60, 55], lead=[0, None, 12, None, 7, None, 12, None], voice=marimba,
                 drums={"kick": (0, 1, 2, 3), "clap": (1, 3), "hat": True}),
}
CUTS = {"pricetag": [4.5, 8.0, 13.0, 17.0], "receipt": [17.0], "scale": [3.5, 7.5, 12.0, 16.5], "type": [3.0, 7.0, 11.0, 16.0]}


def sfx(key):
    s = np.zeros(int(SR * DUR))
    for c in CUTS[key][:-1]:
        put(s, whoosh(), c - 0.15, 0.5)
    logo = CUTS[key][-1]
    put(s, whoosh(), logo - 0.15, 0.5)
    put(s, chime(), logo + 0.35, 0.5)
    if key == "pricetag":
        put(s, whoosh(0.5), 0.0, 0.5)
        for i, at in enumerate(np.cumsum(np.linspace(0.08, 0.22, 10)) + 0.6):  # 値札の数字が下がる
            put(s, tick(), at, 0.8)
        put(s, pop(), 3.0, 0.9)  # 1位のステッカー
        for i in range(6):  # ジャンルの値札が次々めくれる
            put(s, tick(), 8.4 + i * 0.7, 0.8)
    elif key == "receipt":
        put(s, printer(15.5), 0.4, 0.8)
        put(s, tear(), 16.7, 0.9)
    elif key == "scale":
        for at in (0.6, 8.0, 9.8, 12.6, 13.0, 17.0):
            put(s, thud(), at, 0.9)
        for at in (1.2, 4.0, 4.8, 5.6):
            put(s, beep(), at, 1.0)
    elif key == "type":
        for at in (0.2, 0.9, 1.6, 3.4, 4.6):  # 文字が打ち込まれる
            put(s, pop(), at, 0.7)
        for i in range(8):
            put(s, tick(), 11.4 + i * 0.5, 0.7)
    return s


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        st = np.repeat((x * 32767).astype(np.int16)[:, None], 2, axis=1)
        w.writeframes(st.tobytes())


def main(src, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, p in P.items():
        bgm = song(**p)
        n = len(bgm)
        fade = np.ones(n)
        fade[: int(SR * 0.3)] = np.linspace(0, 1, int(SR * 0.3))
        fade[-int(SR * 2.0):] = np.linspace(1, 0, int(SR * 2.0))
        mix = bgm / np.abs(bgm).max() * 0.35 * fade + sfx(key) * 0.6
        mix = mix / max(1.0, np.abs(mix).max() / 0.9)
        wav = out / f"{key}.wav"
        write_wav(wav, mix)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src / f"video-{key}.mp4"), "-i", str(wav),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                        "-movflags", "+faststart", str(out / f"video-{key}.mp4")], check=True)
        print("ok", key)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
