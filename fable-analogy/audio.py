"""fable(たとえ話: まると はかり)の音: かわいい楽器の合成 BGM + 効果音を、無音の mp4 に重ねる(声なし)。
  python audio.py renders/silent.mp4 renders/final_raw.mp4
時刻は index.html の動き(本編の時刻 t。動画の時刻は t + PO)に合わせる。先頭 PO 秒はポスター。
BGM: オルゴール(高い音の鉄琴風)のメロディ + 弦をはじくベース + 軽いハット。C-F-G-C の明るい進行。
     「あれ?」の場面(ガーン〜はかりにのせる前)は音量を下げて、はかりに乗せてからまた戻す。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_audio"))
import synth_audio as s  # noqa: E402

s.DUR = DUR = 26.0
SR = s.SR
PO = 1.0  # ポスターの長さ(本編の時刻に足す)


def A(t):
    """本編の時刻 → 動画の時刻"""
    return PO + t


# ---- 楽器・効果音(synth_audio のものに足りない分) ----
def musicbox(f, d=0.55):
    t = s.t_(d)
    x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 14)
         + 0.18 * np.sin(2 * np.pi * 5 * f * t) * np.exp(-t * 28)) * np.exp(-t * 6.5)
    return x * s.env(len(t), 0.003, 0.05)


def boing(f0=330.0, d=0.2, up=1.7):
    """ぴょん: 音程が速く上がって、すっと消える"""
    t = s.t_(d)
    u = t / d
    f = f0 * (1 + (up - 1) * np.sin(np.pi * u * 0.5))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * s.env(len(t), 0.004, 0.09) * 0.55


def knock(f=190.0):
    """箱が揺れてコトッ"""
    t = s.t_(0.09)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.3 * t)) * np.exp(-t * 45)


def flap():
    """箱のふたがぱかっと開く"""
    n = s.pop() * 0.8
    w = s.whoosh(0.16)
    out = np.zeros(max(len(n), len(w)))
    out[: len(n)] += n
    out[: len(w)] += w * 0.5
    return out


def gaan():
    """ガーン: 低い金属の響き + ひしゃげる下降音 + 打撃"""
    d = 1.15
    t = s.t_(d)
    clang = sum(np.sin(2 * np.pi * f * t + k) * g for k, (f, g) in enumerate(((196, 1.0), (208, 0.9), (277, 0.6), (415, 0.45), (587, 0.3)))) * np.exp(-t * 3.2)
    hit = s.rng.uniform(-1, 1, len(t)) * np.exp(-t * 45) * 0.9
    drop = np.sin(2 * np.pi * np.cumsum(170 * np.exp(-t * 2.2) + 40) / SR) * np.exp(-t * 4.5)
    x = clang * 0.3 + hit + drop * 0.9
    return x / np.abs(x).max()


def dosun():
    """ドスン: 重いものが落ちる"""
    d = 0.6
    t = s.t_(d)
    body = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 18)) / SR) * np.exp(-t * 7)
    noise = s.rng.uniform(-1, 1, len(t)) * np.exp(-t * 40) * 0.5
    return body + noise


def blip(f, d=0.045):
    t = s.t_(d)
    return np.sin(2 * np.pi * f * t) * s.env(len(t), 0.002, 0.03) * 0.6


def sparkle():
    """きらきら: 高い音が3つ上がる"""
    out = np.zeros(int(SR * 0.9))
    for i, m in enumerate((88, 93, 97, 100)):
        s.put(out, s.marimba(s.midi(m), 0.4), i * 0.06, 0.7)
    return out


def slide_sad():
    """あれ?: すっと下がる音"""
    d = 0.75
    t = s.t_(d)
    f = 440 - 150 * (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * s.env(len(t), 0.02, 0.3) * 0.5


def don():
    """ドン!: 打ち込み"""
    th, po = s.thud(), s.pop() * 0.6
    th[: len(po)] += po
    return th


# ---- BGM ----
BGM = dict(bpm=104, prog=[60, 65, 67, 60], lead=[0, 4, 7, 4, 12, 7, 4, 7], voice=musicbox,
           drums={"hat": True}, swing=0.2)


def bgm_track():
    x = s.song(**BGM)[: int(SR * DUR)]
    beat = 60 / BGM["bpm"]
    bar = beat * 4
    for b in range(int(DUR / bar) + 1):  # 弦をはじくベース(1拍目と3拍目)
        root = BGM["prog"][b % len(BGM["prog"])]
        for k in (0, 2):
            s.put(x, s.pluck(s.midi(root - 12), 0.5), b * bar + k * beat, 0.5)
    return x / np.abs(x).max()


def bgm_gain():
    """BGM の音量の波(動画の時刻、0〜1)。冒頭と終わりはフェード、ガーン〜はかりの前は小さく"""
    pts = [(0, 0), (0.3, 1), (A(8.0), 1), (A(8.15), 0.15), (A(8.6), 0.4), (A(11.4), 0.4), (A(12.2), 1),
           (DUR - 1.8, 1), (DUR, 0)]
    tt = np.arange(int(SR * DUR)) / SR
    return np.interp(tt, [p[0] for p in pts], [p[1] for p in pts])


# ---- 効果音 ----
def sfx():
    x = np.zeros(int(SR * DUR))
    put = s.put
    # ポスター: 小さなドン
    put(x, don(), 0.03, 0.55)
    put(x, s.whoosh(0.3), 0.55, 0.25)
    # まるが入ってきて、ぴょんぴょん
    for at, g in ((0.15, 0.35), (0.68, 0.35), (1.2, 0.4)):
        put(x, boing(300), A(at), g)
    put(x, s.whoosh(0.5), A(0.0), 0.2)
    # 箱 A を選ぶ(大きなぴょん)+きらきら
    put(x, boing(380, 0.28, 1.9), A(3.55), 0.6)
    put(x, sparkle(), A(3.6), 0.45)
    put(x, boing(330, 0.16), A(4.6), 0.3)
    # 箱が揺れる → ビリッとテープ → ぱかっ → 袋が弾む
    for at, g in ((6.3, 0.6), (6.65, 0.6), (7.05, 0.9)):
        put(x, knock(), A(at), g)
    put(x, s.tear(), A(6.85), 0.7)
    put(x, flap(), A(7.1), 0.6)
    put(x, s.pop(), A(7.5), 0.35)
    for i, m in enumerate((84, 88, 91)):
        put(x, s.marimba(s.midi(m), 0.3), A(7.75 + 0.07 * i), 0.4)
    # ガーン(まるが跳ねて驚く)
    put(x, boing(520, 0.22, 2.0), A(8.1), 0.45)
    put(x, gaan(), A(8.12), 0.9)
    put(x, slide_sad(), A(9.3), 0.4)
    # 箱 B がはける → 箱 A を持ち上げる → はかり登場(ずざっ)→ 箱をのせる
    put(x, s.whoosh(0.6), A(11.0), 0.4)
    put(x, boing(300, 0.2, 1.5), A(11.75), 0.4)
    put(x, s.whoosh(0.45), A(11.55), 0.45)
    put(x, s.thud(), A(11.95), 0.45)
    put(x, s.thud(), A(12.4), 0.7)
    # はかりの針(ばねで揺れて 3 で止まる)
    for i, at in enumerate((12.45, 12.54, 12.64, 12.76, 12.9, 13.07, 13.28, 13.55)):
        put(x, blip(1700 + 120 * (i % 3), 0.035), A(at), 0.55)
    put(x, s.pop(), A(12.92), 0.5)  # 「3kg」が出る
    # 箱 A をぽいっ → 針が 0 へ
    put(x, s.whoosh(0.5), A(15.0), 0.5)
    for i, at in enumerate((15.05, 15.17, 15.3, 15.45)):
        put(x, blip(2300 - 160 * i, 0.03), A(at), 0.45)
    # 箱 B が飛んできて、ドスン。針が 10 まで一気に
    put(x, s.whoosh(0.55), A(15.45), 0.5)
    put(x, dosun(), A(16.15), 1.0)
    put(x, s.pop(), A(16.2), 0.55)  # 「10kg」が出る
    for i in range(10):
        put(x, blip(1500 + 190 * i, 0.03), A(16.19 + 0.02 * i), 0.5)
    for at, f in ((16.46, 2500), (16.7, 2200), (16.95, 2000)):
        put(x, blip(f, 0.03), A(at), 0.3)
    put(x, boing(520, 0.2, 1.9), A(16.85), 0.45)
    put(x, s.pop(), A(16.95), 0.4)  # 「！？」の吹き出し
    # カードが落ちてくる
    put(x, s.whoosh(0.35), A(18.45), 0.35)
    put(x, s.thud(), A(19.05), 0.35)
    put(x, s.pop(), A(19.05), 0.4)
    put(x, s.thud(), A(19.55), 0.35)
    put(x, s.pop(), A(19.55), 0.4)
    # まるが喜ぶ: きらきら + ぴょん
    put(x, sparkle(), A(19.4), 0.5)
    for at, g in ((19.0, 0.4), (20.2, 0.4), (22.9, 0.35), (23.8, 0.35)):
        put(x, boing(330, 0.2), A(at), g)
    put(x, boing(400, 0.3, 1.9), A(21.45), 0.6)
    # 数字が数え上がる(カウント)
    for i in range(14):
        put(x, blip(1500 + 90 * i, 0.03), A(19.5 + 0.06 * i), 0.38)
    for i in range(12):
        put(x, blip(1200 + 80 * i, 0.03), A(20.0 + 0.065 * i), 0.38)
    # 「3.3倍」が ドン!
    put(x, don(), A(21.28), 1.0)
    put(x, s.chime(), A(21.5), 0.4)
    # ブランド名に切り替わる チャイム
    put(x, s.chime(), A(22.2), 0.55)
    return x


def main(src, dst):
    bgm = bgm_track() * bgm_gain()
    mix = bgm * 0.30 + sfx() * 0.45
    mix = mix / max(1.0, np.abs(mix).max() / 0.92)
    wav = Path(dst).with_suffix(".wav")
    s.write_wav(wav, mix)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", str(dst)], check=True)
    wav.unlink()
    print("ok", dst)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
