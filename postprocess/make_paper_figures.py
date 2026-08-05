#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_paper_figures.py   (일반 Python 3 + matplotlib, abaqus 불필요)
===================================================================
extract_tension.py 가 뽑아놓은 CSV 들을 모아 논문 대조 그림을 한 번에
그린다. 폴더만 지정하면 태그를 자동으로 찾아서 온도별로 묶는다.

읽는 파일 (extract_tension.py 산출물):
    tension_stress_strain<TAG>.csv
    tension_damage<TAG>.csv          (있으면 손상 그림도 그린다)

그리는 것:
    fig_ss_by_temperature.png   논문 Fig.11/13/15 대응 - 응력-변형률
    fig_table3_compare.png      논문 Table 3 대응 - 강도 막대
    fig_damage_by_mode.png      논문 Fig.12/14/16 대응 - 모드별 손상률
    summary_vs_paper.csv        위 숫자 표

사용법:
    python3 make_paper_figures.py [폴더 ...] [--out 출력폴더]

    python3 make_paper_figures.py E:/LTH/Try_1430
    python3 make_paper_figures.py E:/LTH/Try_1300 E:/LTH/Try_1430 --out E:/LTH
    python3 make_paper_figures.py .            # 현재 폴더

 해석을 폴더로 나눠 돌린 경우 폴더를 여러 개 나열하면 된다.
 태그가 겹치면 이름 뒤에 폴더명이 붙는다.

태그 -> 온도 매핑은 TAGMAP 에서 관리한다. 모르는 태그는 파일명에서
숫자를 찾아 추정하고, 그래도 모르면 23 C 로 둔다.
"""
from __future__ import print_function
import os
import re
import sys
import csv
import glob

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ---- 한글 폰트가 있으면 쓰고, 없으면 그림 글자만 영문으로 떨어뜨린다 ------
#      (Windows 에는 Malgun Gothic 이 있고 리눅스 컨테이너에는 없다.
#       폰트가 없는데 한글을 쓰면 전부 네모로 깨지므로 미리 갈라놓는다.)
_KO_FONTS = ['Malgun Gothic', 'NanumGothic', 'Nanum Gothic', 'AppleGothic',
             'Noto Sans CJK KR', 'Noto Sans KR', 'UnDotum', 'Gulim']
_HAVE = {f.name for f in fm.fontManager.ttflist}
KO = next((f for f in _KO_FONTS if f in _HAVE), None)
if KO:
    matplotlib.rcParams['font.family'] = KO
matplotlib.rcParams['axes.unicode_minus'] = False


def L(ko, en):
    """그림 안에 들어갈 글자. 한글 폰트가 없으면 영문을 쓴다."""
    return ko if KO else en

# ---- 논문 Table 3 (Zhang et al. 2022, Ceram. Int. 48:3109-3124) -----------
#      온도 : (해석값, 실험 평균, 실험 표준편차)  [MPa]
PAPER = {23: (128.45, 116.17, 8.78),
         500: (179.42, 160.19, 14.83),
         1000: (199.15, 173.28, 12.94)}

# ---- 태그 -> (온도, 표시이름) ---------------------------------------------
TAGMAP = {
    '': (23, '23C base'),
    '_23C': (23, '23C'),
    '_23PC': (23, '23C (pc)'),
    '_GF': (23, '23C V2_6 GF'),
    '_noTRS': (23, '23C no residual'),
    '_LONG': (23, '23C extended'),
    '_500C': (500, '500C'),
    '_peek500': (500, '500C peek'),
    '_1000C': (1000, '1000C'),
}
COLORS = {23: '#1f77b4', 500: '#d62728', 1000: '#2ca02c'}

# 진단 전용 런. 곡선 그림에는 넣되 Table 3 대조 막대에서는 뺀다.
# (예: noTRS 는 열잔류응력을 일부러 없앤 가상 조건이라 논문값과
#  나란히 세우면 예측 성능을 잘못 표현하게 된다.)
DIAGNOSTIC = {'_noTRS'}


def tag_info(tag):
    if tag in TAGMAP:
        return TAGMAP[tag]
    m = re.search(r'(\d{3,4})\s*C', tag, re.I)
    if m:
        t = int(m.group(1))
        return (t, tag.lstrip('_') or ('%dC' % t))
    return (23, tag.lstrip('_') or 'base')


def read_ss(path):
    """(eps[%], sigma[MPa]) 를 읽는다. 빈 칸은 건너뛴다."""
    e, s = [], []
    with open(path, 'r') as f:
        for row in csv.DictReader(f):
            try:
                ev = float(row['eps_xx_mech'])
                sv = float(row['sigma_xx_MPa'])
            except (TypeError, ValueError, KeyError):
                continue
            e.append(100.0 * ev)
            s.append(sv)
    return e, s


def read_damage(path):
    """{elementSet: (eps[%], PctDamaged, PctLong, PctTrans)}"""
    out = {}
    with open(path, 'r') as f:
        for row in csv.DictReader(f):
            st = row.get('ElementSet')
            if not st:
                continue
            try:
                ev = 100.0 * float(row['eps_xx_mech'])
            except (TypeError, ValueError):
                continue

            def g(k):
                try:
                    return float(row.get(k, '') or 'nan')
                except ValueError:
                    return float('nan')
            d = out.setdefault(st, ([], [], [], []))
            d[0].append(ev)
            d[1].append(g('PctDamaged'))
            d[2].append(g('PctDamaged_Long'))
            d[3].append(g('PctDamaged_Trans'))
    return out


def local_peak(s, win=25, dropfrac=0.03):
    """첫 하중 급강하 직전의 국부최대 index. 없으면 None."""
    n = len(s)
    if n < 2 * win + 2:
        return None
    for i in range(win, n - win):
        if s[i] > 0 and s[i] == max(s[i - win:i + win + 1]):
            if min(s[i:]) < s[i] * (1.0 - dropfrac):
                return i
    return None


def peak_of(e, s):
    """(강도, 그 변형률, 확정여부).

    이 곡선들은 "상승 -> 급강하 -> 재상승" 모양이다. 재상승은 DMAX
    상한이 남기는 잔류강성이 만드는 것이고 실제 시편은 첫 급강하에서
    끊어지므로, 강도는 전역최대가 아니라 그 국부최대다. 1000 C 런은
    재상승이 국부최대를 넘어서서(128.3 > 122.2) 전역최대를 쓰면
    엉뚱한 값을 강도로 읽게 된다.
    """
    if not s:
        return (float('nan'), float('nan'), False)
    n = len(s)
    lp = local_peak(s)
    if lp is not None:
        return (s[lp], e[lp], True)        # 급강하 = 물리적 파괴점
    k = max(range(n), key=lambda i: s[i])
    tail = max(1, int(0.02 * n))
    softened = (k < n - tail) and s[k] > 0 and (s[k] - s[-1]) / s[k] > 0.02
    return (s[k], e[k], softened)


def discover(folders):
    """여러 폴더에서 tension_stress_strain*.csv 를 찾아 태그별로 정리.

    해석을 폴더로 나눠 돌리면(.obj 충돌 회피) CSV 도 폴더별로 흩어진다.
    태그가 겹치면 폴더 이름을 붙여 구분한다.
    """
    found, seen = [], {}
    for folder in folders:
        for p in sorted(glob.glob(os.path.join(
                folder, 'tension_stress_strain*.csv'))):
            base = os.path.basename(p)
            tag = base[len('tension_stress_strain'):-len('.csv')]
            dmg = os.path.join(folder, 'tension_damage%s.csv' % tag)
            key = tag
            if key in seen:
                key = '%s@%s' % (tag, os.path.basename(
                    os.path.normpath(folder)))
            seen[key] = True
            found.append((tag, key, p, dmg if os.path.exists(dmg) else None))
    return found


STYLES = ['-', '--', ':', '-.']


def fig_ss(runs, outdir):
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    seen = {}
    for tag, e, s, T, name, pk in runs:
        # 같은 온도의 런이 여러 개면 색이 겹치므로 선 스타일로 구분한다
        i = seen.get(T, 0)
        seen[T] = i + 1
        ax.plot(e, s, lw=1.6, color=COLORS.get(T, '#777777'),
                ls=STYLES[i % len(STYLES)],
                alpha=0.9, label='%s  (max %.1f MPa%s)'
                % (name, pk[0], '' if pk[2] else L(', 상승중', ', rising')))
        ax.plot([pk[1]], [pk[0]], 'o' if pk[2] else '^',
                ms=6, color=COLORS.get(T, '#777777'),
                mfc='white' if not pk[2] else None, zorder=5)
    for T, (sim, exp, sd) in sorted(PAPER.items()):
        ax.axhline(sim, ls='--', lw=1.0, color=COLORS.get(T, 'k'), alpha=0.45)
        ax.annotate(L('논문', 'paper') + ' %d C  %.1f' % (T, sim), xy=(0.985, sim),
                    xycoords=('axes fraction', 'data'), ha='right',
                    va='bottom', fontsize=8,
                    color=COLORS.get(T, 'k'), alpha=0.85)
    ax.set_xlabel(L('거시 변형률', 'macro strain') + ' $\\varepsilon_{xx}$  [%]')
    ax.set_ylabel(L('거시 응력', 'macro stress') + ' $\\sigma_{xx}$  [MPa]')
    ax.set_title(L('RVE 인장 응답 vs 논문 Table 3\n'
                   'o = 연화 진입(진짜 최대점),  ^ = 아직 상승중(강도 하한)',
                   'RVE tensile response vs paper Table 3\n'
                   'o = softening reached (true peak),  '
                   '^ = still rising (lower bound)'), fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5, loc='lower right')
    fig.tight_layout()
    p = os.path.join(outdir, 'fig_ss_by_temperature.png')
    fig.savefig(p, dpi=160)
    plt.close(fig)
    return p


def fig_table3(runs, outdir):
    """온도별로 가장 멀리 간 런 하나씩 골라 논문과 비교."""
    best = {}
    for r in runs:
        if r[0].split('@', 1)[0] in DIAGNOSTIC:
            continue
        T, pk = r[3], r[5]
        if T not in best or pk[0] > best[T][5][0]:
            best[T] = r
    Ts = sorted(set(list(PAPER.keys()) + list(best.keys())))
    x = range(len(Ts))
    w = 0.27
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar([i - w for i in x], [PAPER.get(T, (float('nan'),))[0] for T in Ts],
           w, label=L('논문 해석', 'paper sim'), color='#9ecae1', edgecolor='#3182bd')
    ax.bar(list(x), [PAPER[T][1] if T in PAPER else float('nan') for T in Ts],
           w, yerr=[PAPER[T][2] if T in PAPER else 0 for T in Ts],
           capsize=4, label=L('논문 실험', 'paper exp'), color='#c7c7c7',
           edgecolor='#666666')
    vals = [best[T][5][0] if T in best else float('nan') for T in Ts]
    ax.bar([i + w for i in x], vals, w, label=L('본 모델', 'this model'),
                  color='#fdae6b', edgecolor='#e6550d')
    for i, T in enumerate(Ts):
        if T not in best:
            continue
        pk = best[T][5]
        ax.annotate('%.1f%s' % (pk[0], '' if pk[2] else L('\n(하한)', '\n(lower)')),
                    xy=(i + w, pk[0]), ha='center', va='bottom', fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(['%d °C' % T for T in Ts])
    ax.set_ylabel(L('인장 강도', 'tensile strength') + ' [MPa]')
    ax.set_title(L('Table 3 대조', 'Table 3 comparison'), fontsize=11)
    ax.grid(axis='y', alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = os.path.join(outdir, 'fig_table3_compare.png')
    fig.savefig(p, dpi=160)
    plt.close(fig)
    return p, best


def fig_damage(dmgruns, outdir):
    if not dmgruns:
        return None
    n = len(dmgruns)
    fig, axes = plt.subplots(1, n, figsize=(4.6 * n, 4.4), squeeze=False)
    for ax, (name, T, dmg) in zip(axes[0], dmgruns):
        for st, (e, pd_, pl, pt) in sorted(dmg.items()):
            up = st.upper()
            if up == 'MATRIX':
                ax.plot(e, pd_, lw=1.8, color='#444444', label=L('기지', 'matrix'))
            elif up.startswith('YARN'):
                ax.plot(e, pl, lw=1.2, alpha=0.85, label='%s %s' % (st, L('종', 'long')))
                ax.plot(e, pt, lw=1.2, ls='--', alpha=0.85,
                        label='%s %s' % (st, L('횡', 'trans')))
        ax.set_title('%s (%d C)' % (name, T), fontsize=10)
        ax.set_xlabel(L('변형률', 'strain') + ' [%]')
        ax.set_ylabel(L('손상 요소 비율', 'damaged element fraction') + ' [%]')
        ax.set_ylim(0, 100)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    p = os.path.join(outdir, 'fig_damage_by_mode.png')
    fig.savefig(p, dpi=160)
    plt.close(fig)
    return p


def main():
    args = [a for a in sys.argv[1:]]
    outdir = None
    if '--out' in args:
        i = args.index('--out')
        outdir = args[i + 1]
        del args[i:i + 2]
    folders = args if args else ['.']
    outdir = outdir or folders[0]
    missing = [f for f in folders if not os.path.isdir(f)]
    if missing:
        print('[error] 폴더가 없다: %s' % ', '.join(missing))
        return 2
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    found = discover(folders)
    if not found:
        print('[error] tension_stress_strain*.csv 가 없다: %s'
              % ', '.join(folders))
        print('        먼저 extract_tension.py 를 돌려야 한다.')
        return 2

    runs, dmgruns = [], []
    print('폴더 %d 개, 찾은 런 %d 개' % (len(folders), len(found)))
    for tag, key, ssp, dmp in found:
        T, name = tag_info(tag)
        if key != tag:
            name = '%s [%s]' % (name, key.split('@', 1)[1])
        e, s = read_ss(ssp)
        if not s:
            print('  [skip] %s : 데이터 없음' % os.path.basename(ssp))
            continue
        pk = peak_of(e, s)
        runs.append((key, e, s, T, name, pk))
        print('  %-20s %5d C  점 %5d  최대 %8.2f MPa @ %.4f %%  %s'
              % (name, T, len(s), pk[0], pk[1],
                 '연화확인' if pk[2] else '*** 상승중(하한) ***'))
        if dmp:
            d = read_damage(dmp)
            if d:
                dmgruns.append((name, T, d))

    if not runs:
        print('[error] 유효한 곡선이 없다.')
        return 2

    p1 = fig_ss(runs, outdir)
    p2, best = fig_table3(runs, outdir)
    p3 = fig_damage(dmgruns, outdir)

    sp = os.path.join(outdir, 'summary_vs_paper.csv')
    with open(sp, 'w') as f:
        w = csv.writer(f)
        w.writerow(['Tag', 'Label', 'T_degC', 'Model_MPa', 'Model_eps_pct',
                    'Softened', 'Paper_sim_MPa', 'Err_vs_sim_pct',
                    'Paper_exp_MPa', 'Paper_exp_sd', 'Within_exp_band'])
        for tag, e, s, T, name, pk in runs:
            ps = PAPER.get(T)
            err = (100.0 * (pk[0] - ps[0]) / ps[0]) if ps else ''
            band = ''
            if ps:
                band = 'Y' if abs(pk[0] - ps[1]) <= ps[2] else 'N'
            w.writerow([tag, name, T, '%.3f' % pk[0], '%.5f' % pk[1],
                        'Y' if pk[2] else 'N',
                        ps[0] if ps else '', ('%.2f' % err) if ps else '',
                        ps[1] if ps else '', ps[2] if ps else '', band])

    print()
    print('=' * 72)
    print(' 온도별 대표값 vs 논문')
    print('=' * 72)
    print(' %-6s %10s %10s %9s %10s %8s'
          % ('T[C]', '본모델', '논문해석', '오차', '논문실험', '연화'))
    for T in sorted(best):
        pk = best[T][5]
        ps = PAPER.get(T)
        if ps:
            print(' %-6d %10.2f %10.2f %8.1f%% %6.1f+-%-4.1f %8s'
                  % (T, pk[0], ps[0], 100.0 * (pk[0] - ps[0]) / ps[0],
                     ps[1], ps[2], 'Y' if pk[2] else 'N'))
        else:
            print(' %-6d %10.2f %10s %9s %10s %8s'
                  % (T, pk[0], '-', '-', '-', 'Y' if pk[2] else 'N'))
    print()
    for p in (p1, p2, p3, sp):
        if p:
            print(' wrote %s' % p)
    if any(not r[5][2] for r in runs):
        print()
        print(' *** 연화 N 인 런은 최대응력이 곡선의 끝이라 강도가 아니라')
        print('     강도의 하한이다. 목표변형률을 늘려(속도는 고정) 다시 돌릴 것.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
