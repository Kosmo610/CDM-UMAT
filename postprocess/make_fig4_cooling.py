#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_fig4_cooling.py   (일반 Python 3 + matplotlib, abaqus 불필요)
===================================================================
extract_cooling_damage.py 가 뽑아놓은 냉각 이력 CSV 를 여러 개 모아
논문 Fig.4 와 같은 형식으로 겹쳐 그린다.

extract_cooling_damage.py 는 실행 1개당 대조표를 화면에 찍는다.
이 스크립트는 그 위 단계다 -- 여러 실행을 한 축에 올려놓고
"어느 손잡이가 곡선의 어디를 움직였나" 를 가른다. PAPERFAITH
체인(P0/P1/P2)의 판정이 정확히 이 비교다.

읽는 파일:
    cooling_damage<TAG>.csv        (extract_cooling_damage.py 산출물)

그리는 것:
    fig4_cooling_damage.png        논문 Fig.4 대응 - 3패널 겹침
    summary_cooling_vs_paper.csv   아래 표를 파일로

사용법:
    python3 make_fig4_cooling.py [폴더 ...] [--out 출력폴더]

    python3 make_fig4_cooling.py E:/LTH/Try_P0 E:/LTH/Try_P1 E:/LTH/Try_P2
    python3 make_fig4_cooling.py E:/LTH --out E:/LTH      # 하위폴더 자동
    python3 make_fig4_cooling.py .

폴더를 여러 개 나열하면 태그가 겹쳐도 폴더명을 붙여 구분한다.

논문 Fig.4 (Zhang et al. 2022) 목표치:
    기지        ~1000 C 개시,  845 C 에서 100%,  23 C 에서 100%
    얀 횡방향     530 C 개시,   23 C 에서 88%
    얀 종방향    냉각 중 ~0%   (인장에서만 손상)
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
_KO_FONTS = ['Malgun Gothic', 'NanumGothic', 'Nanum Gothic', 'AppleGothic',
             'Noto Sans CJK KR', 'Noto Sans KR', 'UnDotum', 'Gulim']
_HAVE = {f.name for f in fm.fontManager.ttflist}
KO = next((f for f in _KO_FONTS if f in _HAVE), None)
if KO:
    matplotlib.rcParams['font.family'] = KO
matplotlib.rcParams['axes.unicode_minus'] = False


def L(ko, en):
    return ko if KO else en


# ---- 논문 Fig.4 목표치 ----------------------------------------------------
PAPER = {'m_onset': 1000.0, 'm_100_at': 845.0, 'm_final': 100.0,
         'y_onset': 530.0, 'y_final': 88.0,
         'yl_final': 0.0}

# ---- 태그 -> 표시이름 (make_paper_figures.py 의 TAGMAP 과 같은 관례) ------
TAGMAP = {
    '': 'base',
    '_P0': 'P0  Weibull off',
    '_P1': 'P1  +MCRIT=1',
    '_P2': 'P2  +Yt=50',
    '_LONG': 't23_long (base)',
    '_23C': '23C',
    '_noTRS': 'no residual',
    '_500D': '500C direct',
    '_1000D': '1000C direct',
    '_GFC': 'GF corrected',
}
# 체인 순서대로 색을 고정한다. 순서가 곧 "손잡이를 하나씩 더한 순서" 라
# 색이 섞이면 그림을 읽을 수 없다.
ORDER = ['_LONG', '_P0', '_P1', '_P2']
COLORS = ['#666666', '#1f77b4', '#ff7f0e', '#2ca02c',
          '#d62728', '#9467bd', '#8c564b', '#17becf']

# 냉각 끝점만 알고 있는 과거 실행. 곡선은 없지만 판정표에는 올린다.
# (extract_cooling_damage.py 가 없던 시절 tension_damage 첫 줄에서 읽은 값)
KNOWN_ENDPOINT = {
    't23_long (recorded)': {'m_final': 72.01, 'y_final': 20.5,
                            'm_onset': 620.0, 'y_onset': 415.0},
}


def label_of(tag, folder=None, dup=False):
    name = TAGMAP.get(tag) or tag.lstrip('_') or 'base'
    if dup and folder:
        name = '%s [%s]' % (name, os.path.basename(folder.rstrip('/\\')))
    return name


def fnum(s):
    """빈 칸 / nan 을 None 으로 통일한다."""
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if v != v:                      # nan
        return None
    return v


def read_cooling(path, ascending=False):
    """cooling/heating_damage<TAG>.csv -> {열이름: [값...]}. 시간순 정렬.

    냉각은 온도 내림차순 = 시간순, 승온은 오름차순 = 시간순이다.
    """
    with open(path, 'r') as f:
        rd = csv.DictReader(f)
        raw = [r for r in rd]
    if not raw:
        return None
    cols = {}
    for k in raw[0].keys():
        if k is None:
            continue
        cols[k] = [fnum(r.get(k)) for r in raw]
    T = cols.get('Temp_degC')
    if not T or all(t is None for t in T):
        return None
    sgn = 1.0 if ascending else -1.0
    idx = sorted(range(len(T)),
                 key=lambda i: (-1e9 if T[i] is None else sgn * T[i]))
    return dict((k, [v[i] for i in idx]) for k, v in cols.items())


def avg_cols(d, keys):
    """여러 열의 프레임별 평균. 값이 없는 열은 빼고 평균한다."""
    have = [k for k in keys if k in d]
    if not have:
        return None
    n = len(d[have[0]])
    out = []
    for i in range(n):
        v = [d[k][i] for k in have if d[k][i] is not None]
        out.append(sum(v) / len(v) if v else None)
    return out


def onset(T, y, th=0.5):
    """손상률이 처음 th[%] 를 넘는 온도."""
    if not y:
        return None
    for t, v in zip(T, y):
        if v is not None and v > th:
            return t
    return None


def reaches(T, y, th=99.5):
    """손상률이 처음 th[%] 에 도달하는 온도. 끝까지 못 가면 None."""
    if not y:
        return None
    for t, v in zip(T, y):
        if v is not None and v >= th:
            return t
    return None


def final(y):
    if not y:
        return None
    for v in reversed(y):
        if v is not None:
            return v
    return None


def discover(folders, stem='cooling_damage'):
    """폴더들에서 <stem>*.csv 를 찾아 (tag, folder, path) 목록으로."""
    found = []
    seen = set()
    for fo in folders:
        pats = [os.path.join(fo, stem + '*.csv'),
                os.path.join(fo, '*', stem + '*.csv')]
        for p in pats:
            for path in sorted(glob.glob(p)):
                rp = os.path.abspath(path)
                if rp in seen:
                    continue
                seen.add(rp)
                base = os.path.basename(path)
                m = re.match(stem + r'(.*)\.csv$', base, re.I)
                tag = m.group(1) if m else ''
                found.append((tag, os.path.dirname(rp), rp))
    # 태그 중복이면 폴더명을 라벨에 붙인다
    cnt = {}
    for tag, _, _ in found:
        cnt[tag] = cnt.get(tag, 0) + 1
    # 체인 순서 -> 그 외는 발견 순서
    def key(item):
        tag = item[0]
        return (ORDER.index(tag) if tag in ORDER else 99, tag)
    found.sort(key=key)
    return [(t, fo, p, cnt[t] > 1) for t, fo, p in found]


def fig_cooling(runs, outdir):
    """논문 Fig.4 대응 3패널: 기지 / 얀 횡 / 얀 종."""
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8))
    panels = [
        (L('기지 (matrix)', 'matrix'), 'matrix',
         [('m_onset', PAPER['m_onset']), ('m_100', PAPER['m_100_at'])]),
        (L('얀 횡방향 (yarn transverse)', 'yarn transverse'), 'ytrans',
         [('y_onset', PAPER['y_onset'])]),
        (L('얀 종방향 (yarn longitudinal)', 'yarn longitudinal'), 'ylong', []),
    ]
    for ax, (title, key, marks) in zip(axes, panels):
        for i, r in enumerate(runs):
            y = r[key]
            if not y:
                continue
            T = r['T']
            xy = [(t, v) for t, v in zip(T, y)
                  if t is not None and v is not None]
            if not xy:
                continue
            ax.plot([p[0] for p in xy], [p[1] for p in xy], '-',
                    color=COLORS[i % len(COLORS)], lw=1.8, label=r['label'])
        # 논문 목표치. 범례 위치는 곡선이 비어 있는 쪽으로 패널마다 다르다
        # (x 축이 뒤집혀 있어 기지는 오른쪽 아래가, 얀은 왼쪽 위가 빈다).
        if key == 'matrix':
            ax.axvline(PAPER['m_onset'], color='k', ls=':', lw=1.0)
            ax.plot([PAPER['m_100_at']], [100.0], 'k*', ms=13,
                    label=L('논문 Fig.4', 'paper Fig.4'))
            ax.annotate('845C 100%', xy=(PAPER['m_100_at'], 100.0),
                        xytext=(6, -14), textcoords='offset points',
                        fontsize=8)
            loc = 'lower right'
        elif key == 'ytrans':
            ax.axvline(PAPER['y_onset'], color='k', ls=':', lw=1.0)
            ax.plot([23.0], [PAPER['y_final']], 'k*', ms=13,
                    label=L('논문 Fig.4', 'paper Fig.4'))
            ax.annotate('23C 88%', xy=(23.0, PAPER['y_final']),
                        xytext=(-10, 4), textcoords='offset points',
                        fontsize=8, ha='right')
            loc = 'upper left'
        else:
            ax.plot([23.0], [0.0], 'k*', ms=13,
                    label=L('논문 Fig.4', 'paper Fig.4'))
            loc = 'upper left'
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(L('온도 [C]', 'temperature [C]'))
        ax.set_xlim(1060, 0)                 # 냉각 방향 = 왼쪽에서 오른쪽
        ax.set_ylim(-3, 105)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc=loc)
    axes[0].set_ylabel(L('손상 요소 비율 [%]', 'damaged elements [%]'))
    fig.suptitle(L('냉각 중 손상 이력 -- 논문 Fig.4 대조',
                   'cooling damage history vs paper Fig.4'), fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(outdir, 'fig4_cooling_damage.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_heating(runs, outdir):
    """논문 Fig.6 대응 3패널: 승온 중 손상요소율 (변화 없음이 목표)."""
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8))
    panels = [(L('기지 (matrix)', 'matrix'), 'matrix', 100.0),
              (L('얀 횡방향 (yarn transverse)', 'yarn transverse'),
               'ytrans', 88.0),
              (L('얀 종방향 (yarn longitudinal)', 'yarn longitudinal'),
               'ylong', 0.0)]
    for ax, (title, key, ptarget) in zip(axes, panels):
        for i, r in enumerate(runs):
            y = r[key]
            if not y:
                continue
            xy = [(t, v) for t, v in zip(r['T'], y)
                  if t is not None and v is not None]
            if not xy:
                continue
            ax.plot([p[0] for p in xy], [p[1] for p in xy], '-',
                    color=COLORS[i % len(COLORS)], lw=1.8, label=r['label'])
        ax.axhline(ptarget, color='k', ls='--', lw=1.2, alpha=0.7,
                   label=L('논문 Fig.6', 'paper Fig.6'))
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(L('온도 [C]', 'temperature [C]'))
        ax.set_xlim(0, 1060)              # 승온 방향 = 왼쪽에서 오른쪽
        ax.set_ylim(-3, 105)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc='center right')
    axes[0].set_ylabel(L('손상 요소 비율 [%]', 'damaged elements [%]'))
    fig.suptitle(L('승온 중 손상 이력 -- 논문 Fig.6 대조 (논문: 변화 없음)',
                   'heating damage history vs paper Fig.6 '
                   '(paper: no change)'), fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(outdir, 'fig6_heating_damage.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def load_runs(found, ascending):
    runs = []
    for tag, folder, path, dup in found:
        d = read_cooling(path, ascending=ascending)
        if d is None:
            print('  [skip] %s (빈 파일)' % os.path.basename(path))
            continue
        ytr = avg_cols(d, ['Warp_PctTrans', 'Weft_PctTrans'])
        ylo = avg_cols(d, ['Warp_PctLong', 'Weft_PctLong'])
        runs.append({'tag': tag, 'label': label_of(tag, folder, dup),
                     'path': path,
                     'T': d['Temp_degC'],
                     'matrix': d.get('Matrix_PctDamaged'),
                     'ytrans': ytr, 'ylong': ylo})
        print('read %-28s  %3d frames  %s'
              % (runs[-1]['label'], len(d['Temp_degC']),
                 os.path.basename(folder)))
    return runs


def main():
    args = sys.argv[1:]
    outdir = None
    if '--out' in args:
        i = args.index('--out')
        if i + 1 < len(args):
            outdir = args[i + 1]
        args = args[:i] + args[i + 2:]
    folders = [a for a in args if not a.startswith('--')] or ['.']
    outdir = outdir or folders[0]
    if not os.path.isdir(outdir):
        outdir = '.'

    found = discover(folders)
    hfound = discover(folders, 'heating_damage')
    if not found and not hfound:
        print('cooling_damage*.csv / heating_damage*.csv not found in: %s'
              % ', '.join(folders))
        print('먼저 각 폴더에서:')
        print('  abaqus python ..\\extract_cooling_damage.py <job>.odb '
              '--stride 2 --tag _P0')
        print('  (승온은 --step Heating_500C 등을 추가)')
        return 1

    # ---- 승온 (논문 Fig.6) ----------------------------------------------
    if hfound:
        hruns = load_runs(hfound, ascending=True)
        if hruns:
            png6 = fig_heating(hruns, outdir)
            print('')
            print('  === paper Fig.6 (heating: start -> end, change) ===')
            for r in hruns:
                def se(y):
                    v = [x for x in (y or []) if x is not None]
                    return (v[0], v[-1]) if v else (None, None)
                m0, m1 = se(r['matrix'])
                t0, t1 = se(r['ytrans'])
                print('    %-28s m %5.1f->%5.1f (%+.2f) | yT %5.1f->%5.1f'
                      ' (%+.2f)'
                      % (r['label'], m0 or 0, m1 or 0, (m1 or 0) - (m0 or 0),
                         t0 or 0, t1 or 0, (t1 or 0) - (t0 or 0)))
            print('    paper: matrix 100->100, yarnT ~88->~89 (no change)')
            print('wrote %s' % png6)
    if not found:
        return 0

    runs = load_runs(found, ascending=False)
    if not runs:
        return 1

    png = fig_cooling(runs, outdir)

    # ---- 판정표 ----------------------------------------------------------
    hdr = ['run', 'matrix_onset_C', 'matrix_100pct_C', 'matrix_at23C_pct',
           'yarnT_onset_C', 'yarnT_at23C_pct', 'yarnL_at23C_pct']
    rows = [['PAPER Fig.4', PAPER['m_onset'], PAPER['m_100_at'],
             PAPER['m_final'], PAPER['y_onset'], PAPER['y_final'],
             PAPER['yl_final']]]
    for name, k in KNOWN_ENDPOINT.items():
        rows.append([name, k['m_onset'], '', k['m_final'],
                     k['y_onset'], k['y_final'], ''])
    for r in runs:
        rows.append([r['label'],
                     onset(r['T'], r['matrix']),
                     reaches(r['T'], r['matrix']),
                     final(r['matrix']),
                     onset(r['T'], r['ytrans']),
                     final(r['ytrans']),
                     final(r['ylong'])])

    def cell(v):
        if v is None:
            return 'never'
        if v == '':
            return '-'
        return '%.1f' % v if isinstance(v, float) else str(v)

    w = max(len(str(r[0])) for r in rows) + 2
    print('')
    print('  %-*s %10s %10s %10s %10s %10s %10s'
          % (w, 'run', 'm.onset', 'm.100%', 'm@23C', 'yT.onset',
             'yT@23C', 'yL@23C'))
    for r in rows:
        print('  %-*s %10s %10s %10s %10s %10s %10s'
              % (w, r[0], cell(r[1]), cell(r[2]), cell(r[3]),
                 cell(r[4]), cell(r[5]), cell(r[6])))

    out = os.path.join(outdir, 'summary_cooling_vs_paper.csv')
    with open(out, 'w', newline='') as f:
        wtr = csv.writer(f)
        wtr.writerow(hdr)
        for r in rows:
            wtr.writerow(['' if v is None else v for v in r])

    print('')
    print('wrote %s' % png)
    print('wrote %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
