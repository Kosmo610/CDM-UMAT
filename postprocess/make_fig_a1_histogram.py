#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_fig_a1_histogram.py   (일반 Python 3 + matplotlib, abaqus 불필요)
=====================================================================
extract_damage_histogram.py 가 뽑아놓은 단계점 히스토그램 CSV 를 모아
논문 부록 Fig.A1~A3 대응 그림을 그린다.

읽는 파일:
    damage_hist<TAG>_f<프레임>.csv       (extract_damage_histogram.py 산출)

그리는 것:
    figA1_hist<TAG>.png        단계(행) x 상·모드(열) 막대 히스토그램
    figA1_shape<TAG>.png       단계별 평균 손상변수 / 저손상 비율 추이
    damage_hist_shape<TAG>.csv 위 숫자 표

사용법:
    python3 make_fig_a1_histogram.py [폴더 ...] [--out 출력폴더]

    python3 make_fig_a1_histogram.py E:/LTH/Try_P0 --out E:/LTH

왜 로그 축인가
--------------
우리 결과는 손상변수가 사실상 **이봉(bimodal)** 이다. 손상된 요소의
90 % 이상이 상한 바로 아래 한 칸에 몰려 있고 나머지 칸은 0.1 % 미만
이다. 선형 축으로 그리면 그 한 칸 말고는 아무것도 안 보이므로
y 축을 로그로 둔다. 대신 각 패널에 sum% / 평균 / 상한칸 점유율을
숫자로 같이 적어 형태를 읽을 수 있게 한다.

논문 대조선
-----------
Zhang 2022 Fig.A1~A3 에서 읽어낸 두 가지를 세로 점선으로 같이 긋는다.

  d = 0.85   논문 히스토그램의 사실상 상한 (우리 DMAX 0.95/0.90)
  d = 0.40   논문에는 이보다 작은 손상요소가 거의 없다

두 선은 **판정 기준이 아니라 대조선**이다. 원문 그림 판독값이므로
등록부 §5.14(C) 의 단서와 함께 읽을 것.
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

_KO_FONTS = ['Malgun Gothic', 'NanumGothic', 'Nanum Gothic', 'AppleGothic',
             'Noto Sans CJK KR', 'Noto Sans KR', 'UnDotum', 'Gulim']
_HAVE = {f.name for f in fm.fontManager.ttflist}
KO = next((f for f in _KO_FONTS if f in _HAVE), None)
if KO:
    matplotlib.rcParams['font.family'] = KO
matplotlib.rcParams['axes.unicode_minus'] = False


def L(ko, en):
    return ko if KO else en


# extract_damage_histogram.py 와 같은 순서·이름
GROUPS = ['Matrix', 'Warp_Long', 'Warp_Trans', 'Weft_Long', 'Weft_Trans']
GLABEL = {'Matrix': L('기지', 'matrix'),
          'Warp_Long': L('워프 종', 'warp long'),
          'Warp_Trans': L('워프 횡', 'warp trans'),
          'Weft_Long': L('위프 종', 'weft long'),
          'Weft_Trans': L('위프 횡', 'weft trans')}
GCOLOR = {'Matrix': '#8c564b', 'Warp_Long': '#d62728',
          'Warp_Trans': '#9467bd', 'Weft_Long': '#2ca02c',
          'Weft_Trans': '#17becf'}

# 논문 Fig.A1~A3 판독 대조선 (등록부 §5.14(C))
PAPER_DMAX = 0.85
PAPER_DLOW = 0.40

FLOOR = 1.0e-3          # 로그축 바닥 [%]


def fnum(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def read_hist(path):
    """damage_hist*.csv -> (bins, summary).

    bins    : [(lo, hi, {group: pct})...]
    summary : {stat: {group: value}}   stat in sum_pct/mean_d/p95_d
    """
    with open(path, 'r') as f:
        rows = [r for r in csv.reader(f)]
    if not rows:
        return None
    head = rows[0]
    idx = {}
    for g in GROUPS:
        if g in head:
            idx[g] = head.index(g)
    if not idx:
        return None
    bins, summary = [], {}
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        if r[0] in ('sum_pct', 'mean_d', 'p95_d'):
            summary[r[0]] = dict((g, fnum(r[idx[g]]) if idx[g] < len(r)
                                  else None) for g in idx)
            continue
        lo, hi = fnum(r[0]), fnum(r[1]) if len(r) > 1 else None
        if lo is None or hi is None:
            continue
        bins.append((lo, hi,
                     dict((g, fnum(r[idx[g]]) if idx[g] < len(r) else None)
                          for g in idx)))
    return (bins, summary) if bins else None


def discover(folders):
    """폴더들에서 damage_hist<TAG>_f<N>.csv 를 찾아 {tag: {frame: path}}."""
    found = {}
    for d in folders:
        for p in sorted(glob.glob(os.path.join(d, 'damage_hist*.csv'))):
            b = os.path.basename(p)
            m = re.match(r'damage_hist(.*)_f(\d+)\.csv$', b, re.I)
            if not m:
                continue
            tag, fr = m.group(1), int(m.group(2))
            found.setdefault(tag, {})[fr] = p
    return found


def shape_stats(bins, summary, g):
    """(sum%, mean, p95, 저손상비율%, 상한칸점유율%)  -- 손상요소 기준."""
    s = (summary.get('sum_pct') or {}).get(g)
    m = (summary.get('mean_d') or {}).get(g)
    p9 = (summary.get('p95_d') or {}).get(g)
    vals = [(lo, d.get(g) or 0.0) for lo, hi, d in bins]
    tot = sum(v for _, v in vals)
    if s is None or s <= 0.0:
        s = tot
    low = sum(v for lo, v in vals if lo < PAPER_DLOW)
    top = max([v for _, v in vals] or [0.0])
    r = (100.0 * low / s if s else 0.0, 100.0 * top / s if s else 0.0)
    return (s, m, p9) + r


def fig_hist(tag, frames, data, outdir):
    """단계(행) x 상·모드(열) 막대 히스토그램."""
    ncol, nrow = len(GROUPS), len(frames)
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.0 * ncol, 2.15 * nrow),
                             sharex=True, squeeze=False)
    for i, fr in enumerate(frames):
        bins, summary = data[fr]
        for j, g in enumerate(GROUPS):
            ax = axes[i][j]
            lo = [b[0] for b in bins]
            w = [(b[1] - b[0]) * 0.92 for b in bins]
            v = [max(b[2].get(g) or 0.0, 0.0) for b in bins]
            ax.bar([l + (b[1] - b[0]) / 2.0 for l, b in zip(lo, bins)],
                   [max(x, FLOOR) for x in v], width=w,
                   color=GCOLOR[g], edgecolor='none')
            ax.set_yscale('log')
            ax.set_ylim(FLOOR, 200.0)
            ax.set_xlim(0.0, 1.0)
            ax.axvline(PAPER_DMAX, color='k', ls='--', lw=0.9, alpha=0.6)
            ax.axvline(PAPER_DLOW, color='k', ls=':', lw=0.9, alpha=0.6)
            ax.grid(True, axis='y', alpha=0.25, which='both')
            s, m, p9, low, top = shape_stats(bins, summary, g)
            ax.text(0.03, 0.95,
                    'sum %.2f%%\n%s %.3f\n%s %.0f%%'
                    % (s, L('평균', 'mean'), m if m is not None else 0.0,
                       L('상한칸', 'top bin'), top),
                    transform=ax.transAxes, va='top', ha='left', fontsize=7.5,
                    bbox=dict(fc='white', ec='none', alpha=0.75, pad=1.5))
            if i == 0:
                ax.set_title(GLABEL[g], fontsize=10)
            if j == 0:
                ax.set_ylabel('frame %d\n%s' % (fr, L('요소 [%]', 'elem [%]')),
                              fontsize=8.5)
            if i == nrow - 1:
                ax.set_xlabel(L('손상변수 d', 'damage variable d'),
                              fontsize=9)
    fig.suptitle(L('논문 Fig.A1~A3 대응 -- 단계점 손상변수 분포%s\n'
                   '(y 로그축. 점선 d=0.40 / 파선 d=0.85 는 논문 판독값)'
                   % (' ' + tag.lstrip('_') if tag else ''),
                   'paper Fig.A1-A3 -- damage variable distribution%s\n'
                   '(log y. dotted d=0.40 / dashed d=0.85 read from paper)'
                   % (' ' + tag.lstrip('_') if tag else '')), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(outdir, 'figA1_hist%s.png' % tag)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(' wrote %s' % out)


def fig_shape(tag, frames, data, outdir):
    """단계별 평균 손상변수 / 저손상 비율 추이 + 논문 상한선."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    for g in GROUPS:
        mm, ll = [], []
        for fr in frames:
            s, m, p9, low, top = shape_stats(data[fr][0], data[fr][1], g)
            mm.append(m if m is not None else float('nan'))
            ll.append(low)
        a1.plot(frames, mm, 'o-', color=GCOLOR[g], label=GLABEL[g], ms=4)
        a2.plot(frames, ll, 'o-', color=GCOLOR[g], label=GLABEL[g], ms=4)
    a1.axhline(PAPER_DMAX, color='k', ls='--', lw=1.0)
    a1.text(frames[0], PAPER_DMAX,
            L(' 논문 상한 0.85', ' paper cap 0.85'), fontsize=8, va='bottom')
    a1.set_ylabel(L('손상요소 평균 손상변수', 'mean d over damaged elems'))
    a1.set_ylim(0.0, 1.0)
    a2.set_ylabel(L('d < 0.40 인 손상요소 비율 [%]',
                    'share of damaged elems with d < 0.40 [%]'))
    a2.set_ylim(0.0, 50.0)
    for a in (a1, a2):
        a.set_xlabel(L('프레임', 'frame'))
        a.grid(True, alpha=0.3)
        a.legend(fontsize=8)
    fig.suptitle(L('손상변수 분포 형태의 진행%s'
                   % (' ' + tag.lstrip('_') if tag else ''),
                   'evolution of damage-variable distribution%s'
                   % (' ' + tag.lstrip('_') if tag else '')), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = os.path.join(outdir, 'figA1_shape%s.png' % tag)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(' wrote %s' % out)


def write_shape_csv(tag, frames, data, outdir):
    out = os.path.join(outdir, 'damage_hist_shape%s.csv' % tag)
    with open(out, 'w') as f:
        f.write('Frame,Group,sum_pct,mean_d,p95_d,'
                'pct_below_0.40_of_damaged,top_bin_share_of_damaged\n')
        for fr in frames:
            for g in GROUPS:
                s, m, p9, low, top = shape_stats(data[fr][0], data[fr][1], g)
                f.write('%d,%s,%.4f,%.4f,%.4f,%.2f,%.2f\n'
                        % (fr, g, s, m if m is not None else float('nan'),
                           p9 if p9 is not None else float('nan'), low, top))
    print(' wrote %s' % out)


def main():
    args = sys.argv[1:]
    outdir = '.'
    if '--out' in args:
        i = args.index('--out')
        outdir = args[i + 1]
        args = args[:i] + args[i + 2:]
    folders = [a for a in args if not a.startswith('-')] or ['.']
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir)

    found = discover(folders)
    if not found:
        print('[error] damage_hist*_f*.csv 를 못 찾았다: %s'
              % ', '.join(folders))
        print('        extract_damage_histogram.py 를 먼저 돌릴 것.')
        return 1

    for tag in sorted(found):
        data, frames = {}, []
        for fr in sorted(found[tag]):
            h = read_hist(found[tag][fr])
            if h is None:
                print(' [skip] %s -- 형식을 못 읽었다' % found[tag][fr])
                continue
            data[fr] = h
            frames.append(fr)
        if not frames:
            continue
        print('tag %-8s frames %s'
              % (tag or '(none)', ','.join(str(f) for f in frames)))
        fig_hist(tag, frames, data, outdir)
        if len(frames) > 1:
            fig_shape(tag, frames, data, outdir)
        write_shape_csv(tag, frames, data, outdir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
