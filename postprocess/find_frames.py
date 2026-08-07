#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_frames.py  --  변형률/온도 -> odb 프레임 번호 찾기

논문 Fig.12/14/16 (인장 단계점 A/B/C/D 컨투어) 과 Fig.A1~A3 (단계점
히스토그램) 을 재현하려면 "그 변형률이 몇 번 프레임인가" 를 알아야
한다. 이 스크립트는 추출해 둔 CSV 에서 그걸 찾아 준다. odb 를 다시
읽지 않으므로 몇 초면 끝난다.

사용법  (일반 python, abaqus 불필요)
------
  python find_frames.py tension_damage_P0.csv --stages
  python find_frames.py tension_damage_P0.csv --strains 0.05,0.12,0.26
  python find_frames.py cooling_damage_P0.csv --temps 1050,750,500,250,23

  --stages   **논문 A/B/C(/D) 단계점을 자동으로.** 옆에 있는
             tension_stress_strain*.csv 에서 최대점(첫 하중강하)을
             찾아, 그 변형률의 5/35/70/100 % 지점을 고른다.
             논문 Fig.11 의 단계 경계가 최대점의 약 35 % / 95 %
             부근이므로 같은 자리를 잡는다.
             비율을 바꾸려면 --fracs 0.05,0.5,1.0
  --strains  변형률 [%] 목록  (tension_damage*.csv 에서)
  --temps    온도 [C] 목록    (cooling/heating_damage*.csv 에서)

출력: 각 목표값의 프레임 번호 + 실제값 + 그대로 붙여넣을 --frames 줄.
      (tension_stress_strain*.csv 는 Increment 단위라 프레임 번호가
       없다 -- tension_damage*.csv 를 쓸 것.)
"""
from __future__ import print_function
import sys
import os
import re
import csv

DEFAULT_FRACS = (0.05, 0.35, 0.70, 1.00)


def fnum(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def local_peak(sig, win=25, dropfrac=0.03):
    """첫 하중 급강하 직전의 국부최대 index. 없으면 None.
    extract_tension.py / make_paper_figures.py 와 같은 판정."""
    n = len(sig)
    if n < 2 * win + 2:
        return None
    for i in range(win, n - win):
        if sig[i] <= 0.0:
            continue
        if sig[i] == max(sig[i - win:i + win + 1]):
            if min(sig[i:]) < sig[i] * (1.0 - dropfrac):
                return i
    return None


def peak_strain(path):
    """tension_stress_strain*.csv -> (최대점 변형률[%], 강도, 확정여부).

    국부최대가 있으면 그것이 강도(연화 진입). 없으면 곡선 끝이
    강도의 하한이므로 확정여부 False.
    """
    eps, sig = [], []
    with open(path, 'r') as f:
        for r in csv.DictReader(f):
            e, s = fnum(r.get('eps_xx_mech')), fnum(r.get('sigma_xx_MPa'))
            if e is None or s is None:
                continue
            eps.append(e * 100.0)
            sig.append(s)
    if not sig:
        return None
    k = local_peak(sig)
    if k is not None:
        return (eps[k], sig[k], True)
    k = max(range(len(sig)), key=lambda i: sig[i])
    return (eps[k], sig[k], False)


def sibling_ss(dmg_path):
    """tension_damage<TAG>.csv 옆의 tension_stress_strain<TAG>.csv."""
    d, b = os.path.split(os.path.abspath(dmg_path))
    m = re.match(r'tension_damage(.*)\.csv$', b, re.I)
    if not m:
        return None
    p = os.path.join(d, 'tension_stress_strain%s.csv' % m.group(1))
    return p if os.path.exists(p) else None


def main():
    args = sys.argv[1:]
    strains = temps = None
    fracs = DEFAULT_FRACS
    if '--fracs' in args:
        i = args.index('--fracs')
        fracs = tuple(float(x) for x in args[i + 1].split(','))
    if '--strains' in args:
        i = args.index('--strains')
        strains = [float(x) for x in args[i + 1].split(',')]
    if '--temps' in args:
        i = args.index('--temps')
        temps = [float(x) for x in args[i + 1].split(',')]
    paths = [a for a in args if a.lower().endswith('.csv')]
    if not paths:
        print(__doc__)
        return 1
    path = paths[0]

    # ---- --stages: 옆 CSV 에서 최대점을 찾아 단계점 변형률을 만든다 ------
    if '--stages' in args:
        ss = sibling_ss(path)
        if ss is None:
            print('[error] tension_stress_strain*.csv 를 %s 옆에서'
                  ' 못 찾았다.' % os.path.basename(path))
            print('        --strains 로 직접 지정할 것.')
            return 2
        pk = peak_strain(ss)
        if pk is None:
            print('[error] %s 에 유효한 곡선이 없다.'
                  % os.path.basename(ss))
            return 2
        pe, ps, ok = pk
        print('peak   : %.4f%%  %.2f MPa   %s'
              % (pe, ps, '(연화 확인)' if ok else '(*** 상승중 -- 하한.'
                 ' 단계점은 잠정 ***)'))
        strains = [pe * fr for fr in fracs]
        print('stages : %s  (최대점의 %s)'
              % (', '.join('%.4f%%' % s for s in strains),
                 ', '.join('%d%%' % (100 * f) for f in fracs)))
        print('')

    if strains is None and temps is None:
        print(__doc__)
        return 1

    with open(path, 'r') as f:
        rows = [r for r in csv.DictReader(f)]
    if not rows:
        print('[error] empty csv')
        return 2
    cols = rows[0].keys()
    if 'Frame' not in cols:
        print('[error] no Frame column in %s' % path)
        if 'Increment' in cols:
            print('        tension_stress_strain*.csv 는 증분 단위라'
                  ' 프레임 번호가 없다.')
            print('        tension_damage*.csv 를 지정할 것.')
        return 2

    # 프레임당 한 값으로 정리 (tension_damage 는 상별로 행이 반복된다)
    per = {}
    key = 'Temp_degC' if temps is not None else 'eps_xx_mech'
    if key not in cols:
        print('[error] no %s column in %s' % (key, path))
        print('        --strains 은 tension_damage*.csv,'
              ' --temps 는 cooling/heating_damage*.csv 용이다.')
        return 2
    for r in rows:
        fr, v = fnum(r.get('Frame')), fnum(r.get(key))
        if fr is None or v is None:
            continue
        per[int(fr)] = v
    if not per:
        print('[error] no usable rows')
        return 2
    frames = sorted(per)

    wants = temps if temps is not None else strains
    scale = 1.0 if temps is not None else 100.0     # eps 는 CSV 에 소수
    unit = 'C' if temps is not None else '%'
    print('csv    : %s  (%d frames: %d..%d)'
          % (path, len(frames), frames[0], frames[-1]))
    stage = '--stages' in args
    print('')
    print('  %-6s %-10s %-8s %-12s'
          % ('point' if stage else '', 'want', 'frame', 'actual'))
    picks = []
    for j, wv in enumerate(wants):
        best, bd = None, None
        for fr in frames:
            d = abs(per[fr] * scale - wv)
            if bd is None or d < bd:
                best, bd = fr, d
        picks.append(best)
        note = ''
        if unit == '%' and bd is not None and bd > 0.02:
            note = '  <- off by %.3f%%' % bd
        if unit == 'C' and bd is not None and bd > 25.0:
            note = '  <- off by %.0fC' % bd
        lab = 'ABCDEFGH'[j] if (stage and j < 8) else ''
        print('  %-6s %-10s %-8d %-12s%s'
              % (lab, '%g%s' % (wv, unit), best,
                 '%.4f%s' % (per[best] * scale, unit), note))
    if len(set(picks)) < len(picks):
        print('  [warn] 중복 프레임이 있다 -- 출력 간격이 성기다.'
              ' extract_tension 을 --stride 1 로 다시 뽑을 것.')
    print('')
    print('  --frames %s' % ','.join(str(p) for p in picks))
    print('  (make_odb_images.py / extract_damage_histogram.py 에 그대로)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
