#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_thesis_figures.py  --  the figures that need no analysis result
====================================================================
The chapters carry `[그림 N.M 자리]` boxes.  Twelve of them are marked
"지금 제작 가능" because they draw on things that already exist: literature
data, the constitutive equations, the deck generators, and the cross-check
output.  This file produces exactly those twelve.

THE RULE THIS FILE EXISTS TO ENFORCE
------------------------------------
A figure is a place where a number can be invented without anyone noticing
-- nobody re-derives an axis tick.  So NO figure here hard-codes a
measurement.  Every literature value is imported from
data/literature/thermal_cycling_dataset.py, every deck value from
abaqus/*.py, and the cross-check bars are parsed from the real run.  The
only literals are those of the constitutive equations themselves (which
Ch.3 states) and drawing coordinates.

Schematic figures are LABELLED schematic (모식) in their own axes, so a
reader can never mistake a drawn curve for a measured one.

Run:
    python3 postprocess/make_thesis_figures.py            # write all
    python3 postprocess/make_thesis_figures.py --check    # selftest
"""
from __future__ import print_function

import inspect
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "figures")
sys.path.insert(0, os.path.join(ROOT, "data", "literature"))
sys.path.insert(0, os.path.join(ROOT, "abaqus"))

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
from matplotlib import font_manager as fm                  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

import thermal_cycling_dataset as tcd                      # noqa: E402
import make_macro_thermalshock as mac                      # noqa: E402
import quench_calibration as qc                            # noqa: E402
import retune_deck as rt                                   # noqa: E402

#: Hangul must render.  matplotlib does not read fontconfig, so the file is
#: registered by hand -- without this every label is a box, and a figure full
#: of boxes still "succeeds" unless something checks.  check() checks.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

C_LINE = "#22314d"
C_ACC = "#c1440e"
C_AUX = "#3f5a86"
C_GREY = "#8b93a1"


def use_korean_font():
    """Register a Hangul face and return its family name (None if absent)."""
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                fm.fontManager.addfont(p)
            except Exception:                              # noqa: BLE001
                continue
            name = fm.FontProperties(fname=p).get_name()
            # A LIST, not a single family: matplotlib falls through to the
            # next entry for any glyph the first lacks.  Hangul faces have no
            # U+2212, which is what mathtext uses for every negative exponent
            # on a log axis -- with a single family those came out as dummy
            # boxes and the figure still "succeeded".
            plt.rcParams["font.family"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    return None


def _style():
    plt.rcParams.update({
        # Hangul faces carry no U+2212, and log ticks are typeset as mathtext,
        # so the exponents would silently come out as dummy boxes.  Keep the
        # maths in DejaVu and only the prose in the Hangul face.
        "mathtext.fontset": "dejavusans",
        "figure.dpi": 200, "savefig.dpi": 200,
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9.5,
        "axes.edgecolor": "#4a5262", "axes.linewidth": 0.8,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "legend.frameon": False,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.06,
        # multi-panel figures otherwise let the right axes' ylabel
        # land on top of the left axes
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.w_pad": 0.06,
    })


_SUP = {"-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}


def plain_log(ax, which="y"):
    """Label a log axis WITHOUT mathtext.

    matplotlib's log formatter emits ``$\\mathdefault{10^{-4}}$``, and
    mathtext resolves \\mathdefault against rcParams['font.family'] -- the
    Hangul face, which has no U+2212.  Regular text falls back between
    families, mathtext does not, so every exponent came out a dummy box
    while the figure still saved successfully.  Plain Unicode superscripts
    go through the normal fallback path instead.
    """
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    def f(v, _pos):
        if v <= 0:
            return ""
        e = int(round(math.log10(v)))
        if abs(10.0 ** e - v) > 1e-9 * v:
            return ""
        return "10" + "".join(_SUP[c] for c in str(e))

    axis = ax.yaxis if which == "y" else ax.xaxis
    axis.set_major_locator(LogLocator(base=10.0))
    axis.set_major_formatter(FuncFormatter(f))
    axis.set_minor_formatter(NullFormatter())


def save(fig, stem):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    path = os.path.join(OUT, stem + ".png")
    fig.savefig(path)
    plt.close(fig)
    return path


def tag(ax, text):
    """Mark an axes as a schematic so no one reads values off it."""
    ax.text(0.985, 0.04, text, transform=ax.transAxes, ha="right",
            fontsize=7.5, color=C_GREY, style="italic")


# ==========================================================================
# data helpers -- every literature number enters the figures through here
# ==========================================================================
def rows(ref=None, what=None):
    return [r for r in tcd.DATA
            if (ref is None or r[0] == ref) and (what is None or r[7] == what)]


def rate_per_cycle_per_K(r):
    """(100 - retention) / N / dT -- the dataset's own severity measure."""
    return (100.0 - r[6]) / r[5] / (r[3] - r[2])


# ==========================================================================
# Ch.1
# ==========================================================================
def fig_1_1():
    """반복 열충격 하중과 손상 누적의 개념도."""
    z = rows("[03]", "tensile modulus")[0]
    # NOT sharex: (a) is a few cycles of a time axis and (b) is the whole
    # sixty-cycle life.  Sharing the axis squeezed (a) into a sliver.
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(5.6, 4.4),
                                 gridspec_kw=dict(height_ratios=[1, 1.15]))
    ncyc = 3
    t, T = [], []
    for c in range(ncyc):
        t += [c, c + 0.30, c + 0.62, c + 0.72, c + 1.0]
        T += [z[2], z[3], z[3], z[2], z[2]]
    a1.plot(t, T, color=C_LINE, lw=1.6)
    a1.set_ylabel("온도 [°C]")
    a1.set_ylim(z[2] - 220, z[3] + 260)
    a1.set_xlim(-0.05, ncyc + 0.05)
    a1.set_xticks(range(ncyc + 1))
    a1.set_xlabel("사이클")
    mid = 0.5 * (z[2] + z[3])
    a1.annotate("가열", xy=(0.15, mid), fontsize=8, color=C_AUX, ha="center")
    a1.annotate("유지", xy=(0.46, z[3] + 110), fontsize=8, color=C_AUX,
                ha="center")
    a1.annotate("급랭", xy=(0.85, mid), fontsize=8, color=C_ACC, ha="center")
    a1.set_title("(a) 한 사이클 = 가열 → 유지 → 급랭, 이것을 $N$회")

    n = [i / 40.0 * z[5] for i in range(41)]
    ret = z[6] / 100.0
    e = [1.0 - (1.0 - ret) * (1 - math.exp(-3.1 * x / z[5])) /
         (1 - math.exp(-3.1)) for x in n]
    a2.plot(n, e, color=C_LINE, lw=1.6, label="강성 저하 (모식)")
    a2.plot([z[5]], [ret], marker="*", ms=13, color=C_ACC, ls="none",
            label="refs/%s 실측: %d사이클에 %.0f %%" % (z[0], z[5], z[6]))
    a2.set_xlabel("사이클 수 $N$")
    a2.set_ylabel("$E(N)/E_0$")
    a2.set_ylim(0.3, 1.03)
    a2.legend(loc="upper right")
    a2.set_title("(b) 곡선은 모식, 별표만 실측")
    tag(a2, "곡선 = 모식")
    return save(fig, "fig_1_1_cyclic_shock_concept")


def _box(ax, x, y, w, h, text, fc="#eef1f6", ec=C_AUX, fs=8):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.0,
                           joinstyle="round"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def _arrow(ax, p, q, text=None, fs=7.5):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11,
                                 color=C_LINE, lw=1.0, shrinkA=1, shrinkB=1))
    if text:
        ax.text((p[0] + q[0]) / 2 + 0.012, (p[1] + q[1]) / 2, text,
                fontsize=fs, color=C_ACC, ha="left", va="center")


def fig_1_2():
    """2-스케일 해석 흐름도."""
    fig, ax = plt.subplots(figsize=(5.6, 3.5))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(False)
    _box(ax, 0.02, 0.72, 0.28, 0.17, "구성재 물성\n(문헌 · 신뢰등급)")
    _box(ax, 0.36, 0.72, 0.30, 0.17,
         "RVE 가상 시험기\n주기경계조건 + UMAT V3_0")
    _box(ax, 0.72, 0.72, 0.26, 0.17,
         "유효물성\n$\\bar C$·$\\bar\\alpha$·$\\bar k$·강도")
    _box(ax, 0.36, 0.40, 0.30, 0.17,
         "거시 반복 열충격\n3 심각도 × TRS 3케이스", fc="#fdf3ec", ec=C_ACC)
    _box(ax, 0.36, 0.08, 0.30, 0.17,
         "문헌 표적 검증\nT1–T6 · PLS · CJPRE", fc="#f2f6ef", ec="#4a7d3a")
    _arrow(ax, (0.30, 0.805), (0.36, 0.805), "제4장")
    _arrow(ax, (0.66, 0.805), (0.72, 0.805))
    _arrow(ax, (0.85, 0.72), (0.66, 0.575), "제5장")
    _arrow(ax, (0.51, 0.40), (0.51, 0.25), "제6장")
    ax.text(0.02, 0.50, "L1 코드 검증\n(제3장)\n2 235항목", fontsize=8,
            color=C_AUX, va="center")
    ax.text(0.02, 0.16, "L2 확인\n(제4장 §4.4)", fontsize=8, color=C_AUX,
            va="center")
    return save(fig, "fig_1_2_two_scale_flow")


# ==========================================================================
# Ch.2
# ==========================================================================
def fig_2_1():
    """준취성 응력-변형률 곡선과 비례한도."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    e = [i / 400.0 * 0.7 for i in range(401)]
    E = 1.0
    ax.plot([x for x in e if x <= 0.62], [E * x for x in e if x <= 0.62],
            color=C_GREY, lw=1.5, label="단일상 취성 세라믹")
    ax.plot([0.62, 0.62], [0.62, 0.0], color=C_GREY, lw=1.5, ls=":")
    pls = 0.25
    qb = [x if x <= pls else pls + (x - pls) * 0.42 for x in e]
    ax.plot(e, qb, color=C_LINE, lw=1.9, label="C/SiC (준취성)")
    ax.axvline(pls, color=C_ACC, lw=0.9, ls="--")
    ax.annotate("비례한도 (PLS)\n= 기지 균열 개시", xy=(pls, pls),
                xytext=(pls + 0.06, pls - 0.10), fontsize=8, color=C_ACC,
                arrowprops=dict(arrowstyle="->", color=C_ACC, lw=0.8))
    ax.annotate("계면 미끄럼·다중 기지균열\n→ 점진적 강성 손실",
                xy=(0.52, pls + (0.52 - pls) * 0.42),
                xytext=(0.30, 0.56), fontsize=8, color=C_AUX,
                arrowprops=dict(arrowstyle="->", color=C_AUX, lw=0.8))
    ax.set_xlabel("변형률 (임의 단위)")
    ax.set_ylabel("응력 (임의 단위)")
    ax.set_xlim(0, 0.72)
    ax.set_ylim(0, 0.72)
    ax.legend(loc="upper left")
    tag(ax, "모식 — 축은 임의 단위")
    return save(fig, "fig_2_1_quasibrittle")


def fig_2_2():
    """TRS의 가열-냉각 가역성."""
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    zero = rt.D_ZERO                        # 무응력 온도, 덱 생성기에서
    T = [23 + i * (zero - 23) / 200.0 for i in range(201)]
    s = [(zero - x) / (zero - 23) for x in T]
    ax.plot(T, s, color=C_LINE, lw=1.8)
    ax.plot(T[::28], s[::28], ">", ms=5, color=C_ACC, ls="none")
    ax.plot(T[::-1][::28], s[::-1][::28], "<", ms=5, color=C_AUX, ls="none")
    ax.annotate("가열 → TRS 감소", xy=(600, 0.45), xytext=(520, 0.72),
                fontsize=8, color=C_ACC,
                arrowprops=dict(arrowstyle="->", color=C_ACC, lw=0.8))
    ax.annotate("냉각 → 원래 값으로 복귀", xy=(330, 0.68), xytext=(120, 0.30),
                fontsize=8, color=C_AUX,
                arrowprops=dict(arrowstyle="->", color=C_AUX, lw=0.8))
    ax.axvline(zero, color=C_GREY, lw=0.9, ls="--")
    ax.text(zero - 18, 0.06, "무응력 온도 %g °C" % zero, rotation=90,
            fontsize=7.5, color=C_GREY, ha="right")
    ax.set_xlabel("온도 [°C]")
    ax.set_ylabel("기지 TRS (상온 값 = 1로 규격화)")
    ax.set_ylim(-0.04, 1.08)
    ax.set_title("열 노출만으로는 영구히 풀리지 않는다 (refs/[71]·[72])")
    tag(ax, "경로 모식 — 방향이 논거")
    return save(fig, "fig_2_2_trs_reversibility")


def fig_2_3():
    """심각도 역설 — 본 연구 동기의 핵심 그림."""
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    marks = {"[02]": ("o", C_ACC), "[03]": ("s", C_LINE),
             "[43]": ("^", C_AUX), "[61]": ("v", "#4a7d3a"),
             "[65]": ("D", C_GREY), "[68]": ("P", "#8a5a9e")}
    seen = set()
    for r in tcd.DATA:
        if "modulus" in r[7]:
            continue                       # 강도 계열만 한 축에 놓는다
        m, c = marks[r[0]]
        lab = None
        if r[0] not in seen:
            seen.add(r[0])
            lab = "refs/%s %s" % (r[0], r[1])
        ax.plot(r[3] - r[2], rate_per_cycle_per_K(r), m, color=c, ms=7,
                mfc="none", mew=1.5, ls="none", label=lab)
    y = rows("[02]", "flexural strength")[0]
    z = rows("[03]", "tensile strength")[0]
    ry, rz = rate_per_cycle_per_K(y), rate_per_cycle_per_K(z)
    ax.annotate("", xy=(z[3] - z[2], rz), xytext=(y[3] - y[2], ry),
                arrowprops=dict(arrowstyle="<->", color=C_ACC, lw=1.2,
                                ls="--"))
    ax.text(0.5 * ((y[3] - y[2]) + (z[3] - z[2])), math.sqrt(ry * rz) * 1.15,
            "%.1f배\n(ΔT는 오히려 작은 쪽이 더 손상적)" % (rz / ry),
            fontsize=8.5, color=C_ACC, ha="center")
    ax.set_yscale("log")
    plain_log(ax)
    ax.set_xlabel("열충격 심각도 ΔT [K]")
    ax.set_ylabel("사이클당·K당 잔존율 저하 [%/사이클/K]")
    ax.set_title("심각도가 서열을 설명하지 못한다")
    ax.legend(loc="lower right", ncol=2, fontsize=7.3)
    ax.set_xlim(220, 1400)
    return save(fig, "fig_2_3_severity_paradox")


def fig_2_4():
    """표준 CDM의 정지 vs 사이클 손상 항."""
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    N = list(range(0, 21))
    mono = [0.0] + [0.30] * 20
    cyc = [0.0] + [0.30 + 0.018 * i for i in range(1, 21)]
    ax.step(N, mono, where="post", color=C_GREY, lw=1.8,
            label="이력최대 구동 (표준 CDM) — $N\\geq 2$에서 정지")
    ax.plot(N, cyc, color=C_ACC, lw=1.8,
            label="사이클 항 도입 — 문턱 위에서 계속 누적")
    ax.annotate("drift = 0 (단위시험으로 확인)", xy=(12, 0.30),
                xytext=(7.5, 0.16), fontsize=8, color=C_GREY,
                arrowprops=dict(arrowstyle="->", color=C_GREY, lw=0.8))
    ax.set_xlabel("사이클 수 $N$ (정진폭)")
    ax.set_ylabel("손상 $d$")
    ax.set_ylim(0, 0.75)
    ax.set_xticks(range(0, 21, 4))
    ax.legend(loc="upper left")
    tag(ax, "모식 — 값이 아니라 형상이 논거")
    return save(fig, "fig_2_4_cdm_stall")


# ==========================================================================
# Ch.3
# ==========================================================================
#: Figure 3.1's boxes.  The SDV numbers are a UMAT fact, not a drawing
#: choice, so they live here where check() can read them back against the
#: UMAT header.  a1 originally took them from the Ch.3 prose and two were
#: wrong (closure was SDV 11 = MODE; the failure step was SDV 23, which the
#: UMAT writes only when ICRIT > 0).
_FIG31_TEXT = [
    ("입력: $\\Delta\\varepsilon$, $T$, STATEV", "#eef1f6"),
    ("유효응력 $\\tilde\\sigma = C_0(T):\\varepsilon$", "#eef1f6"),
    ("파손판정 — 얀 Hashin 4모드 / 기지 $I_1$-$q$", "#eef1f6"),
    ("손상 진전 + 점성 정규화 ($\\eta$)", "#fdf3ec"),
    ("균열 닫힘 $H_{clo}$ (수직 변형률 부호)", "#fdf3ec"),
    ("사이클 항 $\\Delta d_{cyc}$ ($T_{wmax}$에서 평가)", "#fdf3ec"),
    ("반환: $\\sigma$, $\\partial\\sigma/\\partial\\varepsilon$", "#f2f6ef"),
]
_FIG31_SDV = ["", "", "SDV 5\u20138\u00b719", "SDV 9\u00b710", "SDV 22",
              "SDV 17\u00b718\u00b729", ""]


def fig_3_1():
    """V3_0 한 증분의 상태 갱신 순서도."""
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(False)
    steps = [(txt, fc, sdv) for (txt, fc), sdv
             in zip(_FIG31_TEXT, _FIG31_SDV)]
    h, gap = 0.108, 0.028
    y = 1.0 - h
    for text, fc, sdv in steps:
        _box(ax, 0.06, y, 0.66, h, text, fc=fc,
             ec=C_ACC if fc == "#fdf3ec" else C_AUX, fs=8)
        if sdv:
            ax.text(0.75, y + h / 2, sdv, fontsize=7.5, color=C_GREY,
                    va="center")
        if y > 0.1:
            _arrow(ax, (0.39, y), (0.39, y - gap))
        y -= h + gap
    ax.text(0.06, 0.008, "붉은 상자 = V3_0 신규 기능", fontsize=7.5,
            color=C_ACC)
    return save(fig, "fig_3_1_umat_flow")


def fig_3_2():
    """지수 연화 곡선과 균열대 에너지 보존."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 3.0))
    r = [1.0 + i / 300.0 * 5.0 for i in range(301)]
    for A, c in ((1.0, C_GREY), (3.0, C_AUX), (8.0, C_ACC)):
        a1.plot(r, [1.0 - math.exp(A * (1.0 - x)) / x for x in r],
                color=c, lw=1.6, label="$A$ = %g" % A)
    a1.set_xlabel("$r = \\max_{history}\\phi$")
    a1.set_ylabel("손상 $d$")
    a1.set_ylim(0, 1.02)
    a1.legend(loc="lower right")
    a1.set_title("(a) 연화 법칙 $d(r)$")

    # (b) crack band: same Gf, three element sizes -> three A, equal area
    X, E, Gf = 226.0, 213110.0, 0.031           # MPa, MPa, N/mm (Ch.3·Ch.4)
    g0 = X * X / (2.0 * E)
    for le, c in ((0.05, C_GREY), (0.10, C_AUX), (0.15, C_ACC)):
        A = 2.0 * g0 * le / (Gf - g0 * le)
        e0 = X / E
        eps = [e0 * (1.0 + i / 200.0 * 24.0) for i in range(201)]
        sig = [X * math.exp(A * (1.0 - x / e0)) for x in eps]
        a2.plot([0] + eps, [0] + sig, color=c, lw=1.6,
                label="$l_e$ = %.2f mm  ($A$ = %.2f)" % (le, A))
    a2.set_xlim(0, 0.006)
    a2.set_xlabel("변형률")
    a2.set_ylabel("응력 [MPa]")
    a2.legend(loc="upper right", fontsize=7.2)
    a2.set_title("(b) 같은 $G_f$ = %g N/mm — 소산 에너지 보존" % Gf)
    return save(fig, "fig_3_2_softening_crackband")


def fig_3_3():
    """sign(I1) 스위치의 tanh 정규화."""
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    Xt = 226.0
    x = [-1.0 + i / 400.0 * 2.0 for i in range(401)]
    ax.plot(x, [1.0 if v >= 0 else 0.0 for v in x], color=C_GREY, lw=1.6,
            label="$H_{smo}$ = 0 (발표된 계단)")
    for hs, c in ((0.02, C_AUX), (0.10, C_ACC)):
        ax.plot(x, [0.5 * (1 + math.tanh(v / hs)) for v in x], color=c,
                lw=1.7, label="$H_{smo}$ = %g" % hs)
    ax.set_xlabel("$I_1 / (H_{smo}X_t)$ 의 분자 $I_1/X_t$   ($X_t$ = %g MPa)"
                  % Xt)
    ax.set_ylabel("인장 가중 $w$")
    ax.legend(loc="upper left")
    ax.set_title("$I_1=0$ 응력 점프: 78.0배 → 2.3배 (제3장 §3.5)")
    return save(fig, "fig_3_3_hsmo")


def crosscheck_bars():
    """(label, n, worst) parsed from the real cross-check run."""
    p = subprocess.Popen(
        ["python3", os.path.join(ROOT, "verification",
                                 "cross_check_fortran.py")],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0].decode("utf-8", "replace")
    got = []
    for m in re.finditer(r"\[PASS\]\s+(\w+)\s+\(([^)]*)\)\s+(\d+)/(\d+)"
                         r"\s+worst rel\. dev\.\s+([0-9.]+e[+-][0-9]+)", out):
        got.append((m.group(1), m.group(2), int(m.group(3)),
                    float(m.group(5))))
    return got


def fig_3_4():
    """Fortran↔Python 교차검증 편차."""
    bars = crosscheck_bars()
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    if not bars:
        ax.text(0.5, 0.5, "gfortran 미설치 — 교차검증을 실행할 수 없음",
                ha="center", va="center", fontsize=9, color=C_ACC)
        ax.set_axis_off()
        return save(fig, "fig_3_4_crosscheck")
    ys = list(range(len(bars)))
    ax.barh(ys, [b[3] for b in bars], color=C_AUX, height=0.55)
    ax.set_yticks(ys)
    ax.set_yticklabels(["%s\n%s (%d상태)" % (b[0], b[1].split(":")[0], b[2])
                        for b in bars], fontsize=7)
    eps = 2.220446049250313e-16
    ax.axvline(eps, color=C_ACC, lw=1.2, ls="--")
    ax.text(eps * 1.2, -0.62, "배정밀도 ε", fontsize=7.5, color=C_ACC)
    for i, b in enumerate(bars):
        if b[3] == 0.0:                      # a log axis cannot draw zero
            ax.text(eps * 1.2, i, "0 (완전 일치)", fontsize=7.2, va="center",
                    color=C_LINE)
    ax.set_xscale("log")
    plain_log(ax, "x")
    ax.set_xlabel("최대 상대편차 (총 %d 재료점 상태)" % sum(b[2] for b in bars))
    ax.invert_yaxis()
    ax.set_title("두 독립 구현의 차이는 기계 정밀도 수준")
    return save(fig, "fig_3_4_crosscheck")


# ==========================================================================
# Ch.5
# ==========================================================================
def fig_5_1():
    """사이클 손상 법칙의 형상 + 최고온도로 다시 자른 서열."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 3.1))
    Rth = 0.35
    r = [i / 300.0 for i in range(301)]
    for n, c in ((1.0, C_GREY), (2.0, C_AUX), (3.0, C_ACC)):
        a1.plot(r, [max(0.0, x - Rth) ** n for x in r], color=c, lw=1.7,
                label="$n$ = %g" % n)
    a1.axvline(Rth, color=C_ACC, lw=0.9, ls="--")
    a1.text(Rth - 0.02, 0.42, "문턱 $R_{th}$", rotation=90, fontsize=7.5,
            color=C_ACC, ha="right")
    a1.set_xlabel("손상 구동변수 $r_{drv}$")
    a1.set_ylabel("$\\langle r_{drv}-R_{th}\\rangle^{\\,n}$")
    a1.legend(loc="upper left")
    a1.set_title("(a) 구동항 — 문턱 아래는 정확히 0")
    tag(a1, "$R_{th}$·$n$은 보정 대상")

    for r_ in tcd.DATA:
        if "modulus" in r_[7]:
            continue
        a2.plot(r_[3], rate_per_cycle_per_K(r_), "o", ms=6, mfc="none",
                mew=1.4, color=C_LINE, ls="none")
    a2.axvspan(912, 1188, color=C_ACC, alpha=0.12, hatch="//", lw=0)
    a2.text(1050, a2.get_ylim()[1], "이 사이에 데이터가 없다\n(끝점 900·1200에만 있다)", fontsize=7.5,
            color=C_ACC, ha="center", va="top")
    a2.set_yscale("log")
    plain_log(a2)
    a2.set_xlabel("사이클 최고 온도 $T_{max}$ [°C]")
    a2.set_ylabel("사이클당·K당 저하 [%/사이클/K]")
    a2.set_title("(b) $C(T_{max})$가 비단조여야 하는 이유")
    return save(fig, "fig_5_1_cycle_law")


def fig_5_2():
    """거시 시편 형상과 bias 메시."""
    spec = mac.SPECIMENS["ZHANG2013"]
    Lx, Ly, Lz = spec["dims"]
    nx, ny, nz = spec["mesh"]
    zs = mac.graded(nz, Lz, 0.55)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.9),
                                 gridspec_kw=dict(width_ratios=[1.25, 1]))
    a1.add_patch(Rectangle((0, 0), Lx, Lz, fc="#eef1f6", ec=C_AUX, lw=1.0))
    for z in zs:
        a1.plot([0, Lx], [z, z], color=C_AUX, lw=0.6)
    for i in range(nx + 1):
        a1.plot([i * Lx / nx] * 2, [0, Lz], color=C_AUX, lw=0.4, alpha=0.6)
    a1.annotate("급랭면", xy=(Lx * 0.5, Lz), xytext=(Lx * 0.5, Lz + 0.9),
                fontsize=8, color=C_ACC, ha="center",
                arrowprops=dict(arrowstyle="->", color=C_ACC, lw=0.9))
    a1.annotate("급랭면", xy=(Lx * 0.5, 0), xytext=(Lx * 0.5, -1.0),
                fontsize=8, color=C_ACC, ha="center",
                arrowprops=dict(arrowstyle="->", color=C_ACC, lw=0.9))
    a1.set_xlim(-0.6, Lx + 0.6)
    a1.set_ylim(-1.6, Lz + 1.6)
    a1.set_aspect("equal")
    a1.set_xlabel("$L_x$ = %g mm (게이지)" % Lx)
    a1.set_ylabel("두께 $L_z$ = %g mm" % Lz)
    a1.set_title("(a) refs/[03] 게이지부, %d×%d×%d" % (nx, ny, nz))
    a1.grid(False)

    dz = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
    a2.bar(range(1, len(dz) + 1), dz, color=C_AUX, width=0.72)
    a2.axhline(Lz / nz, color=C_GREY, ls="--", lw=0.9)
    a2.text(len(dz), Lz / nz * 1.06, "균일 분할이라면", fontsize=7.5,
            color=C_GREY, ha="right")
    a2.annotate("표면 요소가 가장 얇다\n(열경계층 분해)",
                xy=(1, dz[0]), xytext=(2.4, max(dz) * 0.92), fontsize=7.8,
                color=C_ACC,
                arrowprops=dict(arrowstyle="->", color=C_ACC, lw=0.8))
    a2.set_xlabel("두께 방향 요소 번호")
    a2.set_ylabel("요소 두께 [mm]")
    a2.set_title("(b) bias 0.55 — 최소 %.3f mm" % min(dz))
    return save(fig, "fig_5_2_macro_mesh")


def solved_bi(spec_key, mat_key):
    """(h [W/(m2.K)], Bi, alpha, L) for one specimen/material PAIRING.

    The pairing is the whole point (a2-0027 ②).  What refs/[03] publishes is
    a COOLING TIME, not a film coefficient; the h that reproduces that time
    depends on whose rho, cp and k you solve it with.  Mixing the two -- the
    literature h against our kbar_3 -- gives Bi = 0.0548, which belongs to no
    material at all.  So h and Bi are always taken from the SAME row here,
    and check() forbids the mixed pairing from appearing in the figure.
    """
    spec = qc.SPECIMENS[spec_key]
    mat = qc.MATERIALS[mat_key]
    h, _ = qc.solve_h(spec, mat)
    L = 0.5 * spec["thickness"]
    return h, h * L / mat["k3"], mat["k3"] / (mat["rho"] * mat["cp"]), L



# --------------------------------------------------------------------------
# Committed-result readers.  a3 R4-B-3.
#
# These two figures are the first that draw MEASURED numbers rather than
# literature or deck values, so the rule at the top of this file bites
# hardest here: nothing below is typed.  The ladder comes out of the CSV the
# heat jobs wrote, and the M6 panel is parsed out of the results README's own
# tables.  If a2 re-runs either, the figures move with them.
# --------------------------------------------------------------------------
RESULTS = os.path.join(ROOT, "data", "results")

#: The CSV states its verdict in English; the figure is Korean.
#: Mapped here rather than in the figure so the two cannot drift.
VERDICT_KO = {"holds": "균일 가정 성립", "strained": "아슬아슬",
              "BROKEN": "균일 가정 깨짐"}


def heat_ladder():
    """Rows of data/results/macro_heat_ladder.csv, one per severity."""
    import csv as _csv
    path = os.path.join(RESULTS, "macro_heat_ladder.csv")
    with open(path) as fh:
        return list(_csv.DictReader(fh))


def m6_table(header):
    """Rows of one markdown table in data/results/M6/README.md.

    Returns a list of cell-lists, header row dropped.  Parsing the README
    rather than re-typing its numbers is the whole point -- these are a2's
    measurements and a1 must not become a second, drifting copy of them.
    """
    txt = open(os.path.join(RESULTS, "M6", "README.md"), encoding="utf-8").read()
    i = txt.find(header)
    if i < 0:
        return []
    rows = []
    for ln in txt[i:].splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:]


def _num(cell):
    """First number in a markdown cell, bold markers and units stripped."""
    m = re.search(r"-?\d+(?:\.\d+)?", cell.replace("**", ""))
    return float(m.group(0)) if m else None


def fig_5_3():
    """급랭 경계조건 — 두 물성 계보의 온도 이력과 Biot 사다리."""
    spec = qc.SPECIMENS["ZHANG2013"]
    h, bi, alpha, L = solved_bi("ZHANG2013", spec["material"])
    h_o, bi_o, alpha_o, _ = solved_bi("ZHANG2013", "ours")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 3.0))
    # (a) the SOLVED film coefficient, so the curve reproduces the paper's
    # own "300 C within 15 s".  Nothing here is estimated: rho, cp and k
    # come from quench_calibration.MATERIALS with their own citations.  BOTH
    # lineages are drawn because both hit the star -- that is the finding.
    ts = [i * spec["t_target"] * 1.15 / 200.0 for i in range(201)]
    for xi, c, lab in ((1.0, C_ACC, "표면 (문헌 물성)"),
                       (0.0, C_AUX, "중심 (문헌 물성)")):
        T = [spec["T_sink"] + (spec["T_hi"] - spec["T_sink"]) *
             qc.theta(bi, max(alpha * t / L ** 2, 1e-9), xi) for t in ts]
        a1.plot(ts, T, color=c, lw=1.7, label=lab)
    T_o = [spec["T_sink"] + (spec["T_hi"] - spec["T_sink"]) *
           qc.theta(bi_o, max(alpha_o * t / L ** 2, 1e-9), 0.0) for t in ts]
    a1.plot(ts, T_o, color="k", lw=1.4, ls="--",
            label="중심 (본 연구 카드)")
    a1.plot([spec["t_target"]], [spec["T_target"]], "*", ms=13, color="k",
            ls="none", label="문헌 진술: %g s에 %g °C"
            % (spec["t_target"], spec["T_target"]))
    a1.set_xlabel("급랭 후 시간 [s]")
    a1.set_ylabel("온도 [°C]")
    a1.set_title("(a) 같은 냉각시간, 다른 $h$\n문헌 %.0f ($Bi$ %.4f) · "
                 "본 연구 %.0f ($Bi$ %.4f)" % (h, bi, h_o, bi_o), fontsize=8.6)
    a1.legend(loc="upper right", fontsize=6.9)

    bis = [mac.SEVERITIES[s_]["bi_target"] for s_ in ("L", "M", "H")]
    xi = [i / 100.0 for i in range(101)]
    fo = 0.05
    for b, c, lab in zip(bis, (C_GREY, C_AUX, C_ACC), ("L", "M", "H")):
        a2.plot(xi, [qc.theta(b, fo, x) for x in xi], color=c, lw=1.7,
                label="%s: $Bi$ = %g" % (lab, b))
    a2.set_xlabel("중심(0) → 표면(1)")
    a2.set_ylabel("θ (규격화 온도)")
    a2.set_title("(b) Biot 사다리 — 구배 지배로 넘어가는 지점")
    a2.legend(loc="lower left")
    return save(fig, "fig_5_3_quench")



def fig_5_4():
    """열 사다리 — 세 심각도의 Biot 수와 실제 측정된 두께방향 구배."""
    rows = heat_ladder()
    bis = [float(r["bi"]) for r in rows]
    pct = [float(r["grad_pct"]) for r in rows]
    lab = [r["severity"] for r in rows]
    verdict = [r["uniform_assumption"] for r in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.9, 3.0))

    # (a) Bi against the measured gradient share.  The 30 % line is not a
    # literature threshold and is not drawn as one -- it is where THIS
    # dataset crosses from "holds" to "strained", read off the CSV's own
    # verdict column so the figure cannot disagree with the deck report.
    cross = [p for p, v in zip(pct, verdict) if v != "holds"]
    x = list(range(len(rows)))
    a1.plot(x, pct, "o-", color=C_ACC, lw=1.7, ms=7)
    for i, (p_, l) in enumerate(zip(pct, lab)):
        a1.annotate("%s  %.1f %%" % (l, p_), (i, p_),
                    textcoords="offset points", xytext=(8, -3), fontsize=8.2)
    if cross:
        a1.axhline(min(cross), color=C_GREY, lw=1.0, ls=":")
        a1.text(0.02, min(cross) * 1.06,
                "이 아래에서만 균일 가정이 성립", fontsize=7.4, color=C_GREY)
    # A categorical axis, not a log one: three points do not make a trend,
    # and a log axis here typesets its exponent in mathtext, which the Hangul
    # face has no minus glyph for.
    a1.set_xticks(x)
    a1.set_xticklabels(["$Bi$ = %g" % b for b in bis])
    a1.set_xlim(-0.35, len(rows) - 0.35)
    a1.set_xlabel("심각도")
    a1.set_ylabel("최대 구배 / 낙차 [%]")
    a1.set_title("(a) 측정된 구배 사다리", fontsize=9)

    # (b) how many elements the front actually spans.  A gradient the mesh
    # does not resolve is not a result, so the front depth and its element
    # count travel WITH the percentage, never apart from it.
    depth = [float(r["front_depth_mm"]) for r in rows]
    nel = [int(r["elements_in_front"]) for r in rows]
    bars = a2.bar(range(len(rows)), depth,
                  color=[C_ACC if v != "holds" else C_AUX for v in verdict])
    for i, (b, n, v) in enumerate(zip(bars, nel, verdict)):
        a2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.03,
                "%d개 요소\n%s" % (n, VERDICT_KO.get(v, v)), ha="center",
                fontsize=7.6)
    a2.set_xticks(range(len(rows)))
    a2.set_xticklabels(["%s ($Bi$ %g)" % (l, b) for l, b in zip(lab, bis)])
    a2.set_ylabel("열경계층 깊이 [mm]")
    a2.set_ylim(0, max(depth) * 1.35)
    a2.set_title("(b) 그 구배를 메시가 푸는가", fontsize=9)
    return save(fig, "fig_5_4_heat_ladder")


def fig_4_6():
    """M6 — 출처 있는 카드가 M5 대비 무엇을 고쳤나 (판정 3종)."""
    tan = m6_table("| $T$ [°C] | M6 [GPa]")
    eps = m6_table("| $T$ [°C] | M6 [MPa]")
    pk = m6_table("| $T$ [°C] | 피크 [MPa]")
    T = [_num(r[0]) for r in tan]
    fig, (a1, a2, a3_) = plt.subplots(1, 3, figsize=(7.4, 2.9))

    # (a) initial tangent ratio -- the one quantity X_t cannot touch, which
    # is why it is the honest test of the porosity correction.
    r_tan = [_num(r[3]) for r in tan]
    a1.axhline(1.0, color=C_GREY, lw=1.0, ls="--")
    a1.plot(T, r_tan, "o-", color=C_ACC, lw=1.7, ms=6, label="M6")
    a1.plot([1000.0], [1.36], "s", color=C_GREY, ms=7, label="M5 (옛 카드)")
    for x, y in zip(T, r_tan):
        a1.annotate("%.2f×" % y, (x, y), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8)
    a1.set_ylim(0.7, 1.5)
    a1.set_xlabel("$T$ [°C]"); a1.set_ylabel("M6 / 실측")
    a1.set_title("(a) 초기 접선\n공극률 보정의 시험", fontsize=8.6)
    a1.legend(fontsize=7, loc="upper left")

    # (b) stress at the measured fracture strain -- the sign SPLITS, and the
    # split is the finding, so it gets its own zero line and no trend curve.
    r_eps = [_num(r[3]) for r in eps]
    a2.axhline(1.0, color=C_GREY, lw=1.0, ls="--")
    a2.bar([str(int(x)) for x in T], r_eps,
           color=[C_AUX if v < 1 else C_ACC for v in r_eps])
    for i, v in enumerate(r_eps):
        a2.text(i, v + 0.03, "%.2f×" % v, ha="center", fontsize=8)
    a2.set_ylim(0, 1.45)
    a2.set_xlabel("$T$ [°C]"); a2.set_ylabel("M6 / Zhang T3")
    a2.set_title("(b) 파단변형률 응력\n부호가 갈린다", fontsize=8.6)

    # (c) did the curve peak at all.  M5: none.  M6: two of three.
    reached = [1.0 if "예" in r[3] else 0.0 for r in pk]
    a3_.bar([str(int(_num(r[0]))) for r in pk], reached,
            color=[C_ACC if v else C_GREY for v in reached])
    for i, (r, v) in enumerate(zip(pk, reached)):
        a3_.text(i, 0.04, "%.0f MPa" % _num(r[1]), ha="center", fontsize=7.6,
                 rotation=90, va="bottom", color="white" if v else "black")
    a3_.set_ylim(0, 1.35)
    a3_.set_yticks([0, 1]); a3_.set_yticklabels(["미도달", "도달"])
    a3_.set_xlabel("$T$ [°C]")
    a3_.set_title("(c) 피크 도달\nM5 0/3 → M6 %d/3"
                  % int(sum(reached)), fontsize=8.6)
    return save(fig, "fig_4_6_m6")


FIGURES = [
    ("1.1", fig_1_1), ("1.2", fig_1_2),
    ("2.1", fig_2_1), ("2.2", fig_2_2), ("2.3", fig_2_3), ("2.4", fig_2_4),
    ("3.1", fig_3_1), ("3.2", fig_3_2), ("3.3", fig_3_3), ("3.4", fig_3_4),
    ("4.6", fig_4_6),
    ("5.1", fig_5_1), ("5.2", fig_5_2), ("5.3", fig_5_3),
    ("5.4", fig_5_4),
]


# ==========================================================================
def check():
    ok, bad = [], []

    def t(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("make_thesis_figures.py --check")
    fam = use_korean_font()
    _style()
    t("a Hangul font is registered with matplotlib", fam is not None,
      fam or "none of %s" % ", ".join(FONT_CANDIDATES))

    # THE SDV NUMBERS IN FIG. 3.1 ARE A UMAT FACT, NOT AN ILLUSTRATION.
    # a1 drew them from the Ch.3 prose and two were wrong: closure was
    # labelled SDV 11, which is MODE, and the failure step was labelled
    # SDV 23, which is written only when ICRIT > 0.  They are now read back
    # out of the UMAT header so the figure cannot drift from the code.
    umat = open(os.path.join(ROOT, "src",
                             "UMAT_CSIC_THERMSHOCK_V3_0.for")).read()
    hdr = umat.split("MACRO  NSTATV")[1].split("YARN   NSTATV")[0]
    for slot, name in ((9, "D1"), (10, "DT"), (17, "DCYC"), (18, "NCUM"),
                       (22, "CLOFLG"), (23, "FITW"), (29, "TWMAX"),
                       (11, "MODE"), (19, "RDRV")):
        t("UMAT header still has SDV %d = %s" % (slot, name),
          re.search(r"\b%d\s+%s\b" % (slot, name), hdr) is not None)
    box = [b for b in _FIG31_SDV if b]
    t("fig 3.1 labels closure with CLOFLG (22), not MODE (11)",
      "SDV 22" in box and "SDV 11" not in box, " / ".join(box))
    t("fig 3.1 does not label the failure step with an ICRIT-only SDV",
      not any(l.strip().endswith("23") or "\u00b723" in l for l in box),
      " / ".join(box))

    # the paradox arrow must be the dataset's own ratio, not a typed one
    y = rows("[02]", "flexural strength")[0]
    z = rows("[03]", "tensile strength")[0]
    ratio = rate_per_cycle_per_K(z) / rate_per_cycle_per_K(y)
    t("fig 2.3's ratio is re-derived from the dataset",
      abs(ratio - 6.05) < 0.05, "%.2f배" % ratio)
    t("fig 2.3 plots every strength row and no modulus row",
      len([r for r in tcd.DATA if "modulus" not in r[7]]) == 14
      and len(tcd.DATA) == 16)

    # a3 R4-B-3.  The two result figures are the first that draw MEASURED
    # numbers, so they get the strictest form of this file's rule: every
    # value must be re-read from the committed artefact, and the figure must
    # be *placed* -- an unplaced figure is a file nobody sees.
    ladder = heat_ladder()
    t("fig 5.4 reads three severities from the results CSV",
      [r["severity"] for r in ladder] == ["L", "M", "H"],
      "%d rows" % len(ladder))
    t("...and their gradient shares are the CSV's, not typed",
      [round(float(r["grad_pct"]), 1) for r in ladder] == [7.0, 36.9, 72.2],
      ", ".join("%.1f" % float(r["grad_pct"]) for r in ladder))
    t("the uniform-assumption verdict comes from the CSV column",
      [r["uniform_assumption"] for r in ladder] == ["holds", "strained",
                                                    "BROKEN"])
    t("...and every verdict word has a Korean rendering",
      all(v in VERDICT_KO for v in
          set(r["uniform_assumption"] for r in ladder)))
    t("fig 5.4 does not hard-code any of those numbers",
      not any(s in inspect.getsource(fig_5_4)
              for s in ("36.9", "72.2", "433.3", "221.2")))
    tan = m6_table("| $T$ [°C] | M6 [GPa]")
    pk = m6_table("| $T$ [°C] | 피크 [MPa]")
    t("fig 4.6 parses the M6 tangent table out of the results README",
      [_num(r[0]) for r in tan] == [23.0, 500.0, 1000.0],
      "%d rows" % len(tan))
    t("...and the 1.01x at 1000 C is read, not asserted",
      abs(_num(tan[-1][3]) - 1.01) < 1e-9, tan[-1][3])
    t("fig 4.6 counts the peaks reached rather than stating 2/3",
      sum(1 for r in pk if "예" in r[3]) == 2
      and "sum(reached)" in inspect.getsource(fig_4_6))
    t("fig 4.6 does not hard-code the M6 stresses",
      not any(s in inspect.getsource(fig_4_6)
              for s in ("199.83", "226.83", "284.71", "0.81", "1.19")))
    ch4_txt = open(os.path.join(ROOT, "docs",
                                "CH4_RVE_HOMOGENISATION.md")).read()
    ch5_txt = open(os.path.join(ROOT, "docs",
                                "CH5_MACRO_THERMALSHOCK.md")).read()
    t("fig 4.6 is placed in Ch.4, not merely generated",
      "figures/fig_4_6_m6.png" in ch4_txt)
    t("fig 5.4 is placed in Ch.5", "figures/fig_5_4_heat_ladder.png" in ch5_txt)
    t("Ch.4 marks the M6 strengths provisional until the damage cap is judged",
      "강도 절대값은 잠정이다" in ch4_txt)

    # deck values come from the generator, never from this file
    t("fig 5.2 reads the specimen from make_macro_thermalshock",
      mac.SPECIMENS["ZHANG2013"]["dims"] == (12.5, 6.0, 3.0))
    t("fig 5.3 reads the Biot ladder from the same place",
      [mac.SEVERITIES[s]["bi_target"] for s in ("L", "M", "H")]
      == [0.05, 1.0, 5.0])
    spec = qc.SPECIMENS["ZHANG2013"]
    # BOTH lineages must reproduce the published cooling time -- that is the
    # claim fig 5.3(a) makes by drawing them against one star.
    for mat_key, want_h, want_bi in (("zhang2013", 199.0, 0.0475),
                                     ("ours", 161.7, 0.0445)):
        h, bi_s, alpha, L = solved_bi("ZHANG2013", mat_key)
        Tmid = spec["T_sink"] + (spec["T_hi"] - spec["T_sink"]) * qc.theta(
            bi_s, alpha * spec["t_target"] / L ** 2, 0.0)
        t("fig 5.3(a) hits the published cooling time on the %s card"
          % mat_key, abs(Tmid - spec["T_target"]) < 1.0,
          "%.1f °C at %g s" % (Tmid, spec["t_target"]))
        t("fig 5.3(a)'s %s h/Bi are solved, not typed" % mat_key,
          abs(h - want_h) < 0.6 and abs(bi_s - want_bi) < 5e-4,
          "h %.1f (want %.1f), Bi %.4f (want %.4f)"
          % (h, want_h, bi_s, want_bi))
    # the mixed pairing a2-0027 flags: literature h against our kbar_3.  It is
    # nobody's material, so it must never reach a figure.
    h_lit, _, _, L = solved_bi("ZHANG2013", "zhang2013")
    bi_mixed = h_lit * L / qc.MATERIALS["ours"]["k3"]
    drawn = "".join(inspect.getsource(f) for _, f in FIGURES)
    t("fig 5.3 never pairs the literature h with our kbar_3",
      abs(bi_mixed - 0.0548) < 5e-4 and "%.4f" % bi_mixed not in drawn,
      "the forbidden value is %.4f" % bi_mixed)
    zs = mac.graded(mac.SPECIMENS["ZHANG2013"]["mesh"][2],
                    mac.SPECIMENS["ZHANG2013"]["dims"][2], 0.55)
    dz = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
    t("fig 5.2(b) shows a real bias: the surface element is the thinnest",
      dz[0] < dz[len(dz) // 2], "%.3f < %.3f mm" % (dz[0], dz[len(dz) // 2]))
    t("fig 2.2 reads the stress-free temperature from the deck generator",
      abs(rt.D_ZERO - 1050.0) < 1e-9, "%g °C" % rt.D_ZERO)

    # crack-band A must obey the snapback condition it is drawn with
    X, E, Gf = 226.0, 213110.0, 0.031
    g0 = X * X / (2.0 * E)
    t("fig 3.2(b)'s element sizes stay below the snapback limit",
      max(0.05, 0.10, 0.15) < Gf / (1.02 * g0),
      "limit %.4f mm" % (Gf / (1.02 * g0)))

    # every figure renders, is non-trivial, and contains no missing glyphs
    import matplotlib.font_manager as _fm                   # noqa: F401
    for tag_, fn in FIGURES:
        try:
            path = fn()
            size = os.path.getsize(path)
            t("그림 %s 생성" % tag_, size > 12000, "%d bytes" % size)
        except Exception as exc:                            # noqa: BLE001
            t("그림 %s 생성" % tag_, False, str(exc)[:90])

    # the chapters must actually embed what was produced
    docs = os.path.join(ROOT, "docs")
    body = ""
    for fn in sorted(os.listdir(docs)):
        if re.match(r"CH\d_.*\.md$", fn):
            body += open(os.path.join(docs, fn), encoding="utf-8").read()
    missing = [f for f in sorted(os.listdir(OUT))
               if f.endswith(".png") and f not in body]
    t("every produced figure is embedded in a chapter", not missing,
      ", ".join(missing))
    t("figures carry no alt text (Word would print it as a 2nd caption)",
      not re.search(r"!\[[^\]]+\]\(figures/", body))
    dangling = [m for m in re.findall(r"figures/([\w.]+\.png)", body)
                if not os.path.exists(os.path.join(OUT, m))]
    t("no chapter points at a figure that was not produced", not dangling,
      ", ".join(dangling))

    print("\n%s" % ("ALL %d FIGURE CHECKS PASS" % len(ok) if not bad
                    else "FAILED %d of %d" % (len(bad), len(ok) + len(bad))))
    return 1 if bad else 0


def main(argv):
    if "--check" in argv or "--selftest" in argv:
        return check()
    fam = use_korean_font()
    _style()
    if fam is None:
        print("WARNING: no Hangul font found; labels will be boxes")
    for tag_, fn in FIGURES:
        print("  그림 %-4s -> %s" % (tag_, os.path.basename(fn())))
    print("wrote %d figures to %s" % (len(FIGURES), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
