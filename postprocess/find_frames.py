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
  python find_frames.py tension_damage_P0.csv --strains 0.05,0.12,0.26
  python find_frames.py cooling_damage_P0.csv --temps 1050,750,500,250,23

  --strains  변형률 [%] 목록  (tension_damage*.csv 에서)
  --temps    온도 [C] 목록    (cooling/heating_damage*.csv 에서)

출력: 각 목표값의 프레임 번호 + 실제값 + 그대로 붙여넣을 --frames 줄.
      (tension_stress_strain*.csv 는 Increment 단위라 프레임 번호가
       없다 -- tension_damage*.csv 를 쓸 것.)
"""
from __future__ import print_function
import sys
import csv


def fnum(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def main():
    args = sys.argv[1:]
    strains = temps = None
    if '--strains' in args:
        i = args.index('--strains')
        strains = [float(x) for x in args[i + 1].split(',')]
    if '--temps' in args:
        i = args.index('--temps')
        temps = [float(x) for x in args[i + 1].split(',')]
    paths = [a for a in args if a.lower().endswith('.csv')]
    if not paths or (strains is None and temps is None):
        print(__doc__)
        return 1
    path = paths[0]

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
    print('')
    print('  %-10s %-8s %-12s' % ('want', 'frame', 'actual'))
    picks = []
    for wv in wants:
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
        print('  %-10s %-8d %-12s%s'
              % ('%g%s' % (wv, unit), best,
                 '%.4f%s' % (per[best] * scale, unit), note))
    print('')
    print('  --frames %s' % ','.join(str(p) for p in picks))
    print('  (make_odb_images.py / extract_damage_histogram.py 에 그대로)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
