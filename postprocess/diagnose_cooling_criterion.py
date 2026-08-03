"""냉각 odb 진단: 논문 Eq.15(von Mises) 로 바꾸면 기지 손상이 늘어나는가?

새 해석이 필요 없다. 이미 가지고 있는 냉각 단계 odb 를 그대로 읽는다.

배경
----
논문은 845 degC 에서 기지 손상요소가 100% 라고 보고하는데, 우리 모델은
같은 온도에서 0.15% 밖에 안 된다. 원인 후보 중 하나가 파손기준이다.

  논문 Eq.15 : von Mises 등가응력 / Xm,t   (I1 >= 0)
  V2_4       : 최대주응력(Rankine) / Xm,t  (게이트 없음)

von Mises 와 최대주응력의 비는 응력상태에 따라 0~2 배로 달라진다.

  (s, s, 0)  면내 등2축   -> Mises/MaxPrin = 1.00  (이득 없음)
  (s, s, -s) 3축 혼합     -> Mises/MaxPrin = 2.00  (2배)
  (s, s, s)  정수압       -> Mises/MaxPrin = 0.00  (오히려 손해)

따라서 기지 핫스팟의 실제 삼축 상태를 봐야 판정된다. 이 스크립트가
온도별로 그 비를 뽑아준다.

사용법
------
  abaqus python diagnose_cooling_criterion.py <cooling>.odb [--step STEPNAME]

출력
----
  cooling_criterion_diag.csv
    각 프레임(온도)마다 기지 요소의
      MaxPrin  평균/최대/상위1%
      Mises    평균/최대/상위1%
      비율     Mises/MaxPrin
      기준초과요소비율  (MaxPrin>=Xt) vs (Mises>=Xt)  <- 핵심 비교
"""
from __future__ import print_function
import sys
import os
import csv

from odbAccess import openOdb

XT_MATRIX = 310.0          # 논문 Table 2. Weibull 평균
COOL_STEP_DEFAULT = 'Manufacturing_Cooling'
_LOG = []


def log(m):
    print(m)
    _LOG.append(str(m))


def _sc(v):
    try:
        return v[0]
    except (TypeError, IndexError):
        return v


def csv_open(p):
    if sys.version_info[0] < 3:
        return open(p, 'wb')
    return open(p, 'w', newline='')


def pct(sorted_vals, q):
    """정렬된 리스트에서 상위 q 분위 (q=0.99 이면 상위 1%)."""
    if not sorted_vals:
        return float('nan')
    i = int(q * (len(sorted_vals) - 1))
    return sorted_vals[i]


def main():
    args = sys.argv[1:]
    if not args:
        print('usage: abaqus python diagnose_cooling_criterion.py '
              '<odb> [--step NAME]')
        sys.exit(1)
    step = COOL_STEP_DEFAULT
    if '--step' in args:
        i = args.index('--step')
        if i + 1 < len(args):
            step = args[i + 1]
    path = [a for a in args if not a.startswith('--') and a != step][0]

    log('opening %s' % path)
    odb = openOdb(path=path, readOnly=True)
    try:
        log('steps: %s' % ', '.join(odb.steps.keys()))
        if step not in odb.steps:
            log('[error] step "%s" 없음' % step)
            sys.exit(2)
        st = odb.steps[step]
        inst = odb.rootAssembly.instances
        iname = list(inst.keys())[0]
        ia = inst[iname]
        if 'Matrix' not in ia.elementSets:
            log('[error] elementSet "Matrix" 없음. 사용 가능: %s'
                % ', '.join(ia.elementSets.keys()))
            sys.exit(2)
        mset = ia.elementSets['Matrix']

        out = os.path.join(os.path.dirname(os.path.abspath(path)) or '.',
                           'cooling_criterion_diag.csv')
        f = csv_open(out)
        w = csv.writer(f)
        w.writerow(['Frame', 'StepTime', 'Temp_estimate_degC',
                    'n_pts',
                    'MaxPrin_avg', 'MaxPrin_p99', 'MaxPrin_max',
                    'Mises_avg', 'Mises_p99', 'Mises_max',
                    'ratio_Mises_over_MaxPrin_avg',
                    'ratio_at_p99',
                    'pct_over_Xt_by_MaxPrin', 'pct_over_Xt_by_Mises',
                    'I1_avg', 'pct_I1_positive'])

        nfr = len(st.frames)
        log('frames: %d' % nfr)
        for fi in range(nfr):
            fr = st.frames[fi]
            if 'S' not in fr.fieldOutputs:
                continue
            S = fr.fieldOutputs['S'].getSubset(region=mset)
            mp, mi, i1 = [], [], []
            for v in S.values:
                mp.append(v.maxPrincipal)
                mi.append(v.mises)
                d = v.data
                i1.append(d[0] + d[1] + d[2])
            n = len(mp)
            if n == 0:
                continue
            mps = sorted(mp)
            mis = sorted(mi)
            # 냉각은 1050 -> 23 을 step time 0..1 로 선형 주행한다고 가정
            temp = 1050.0 - (1050.0 - 23.0) * fr.frameValue
            a_mp = sum(mp) / n
            a_mi = sum(mi) / n
            p99_mp = pct(mps, 0.99)
            p99_mi = pct(mis, 0.99)
            over_mp = 100.0 * sum(1 for x in mp if x >= XT_MATRIX) / n
            over_mi = 100.0 * sum(1 for x in mi if x >= XT_MATRIX) / n
            a_i1 = sum(i1) / n
            pos_i1 = 100.0 * sum(1 for x in i1 if x >= 0.0) / n
            w.writerow([fi, fr.frameValue, temp, n,
                        a_mp, p99_mp, mps[-1],
                        a_mi, p99_mi, mis[-1],
                        (a_mi / a_mp) if a_mp else '',
                        (p99_mi / p99_mp) if p99_mp else '',
                        over_mp, over_mi, a_i1, pos_i1])
            if fi % 10 == 0 or fi == nfr - 1:
                log('  frame %3d  T~%7.1f C | MaxPrin avg %7.2f p99 %7.2f | '
                    'Mises avg %7.2f p99 %7.2f | over-Xt  MaxPrin %6.2f%%  '
                    'Mises %6.2f%%'
                    % (fi, temp, a_mp, p99_mp, a_mi, p99_mi, over_mp, over_mi))
        f.close()
        log('wrote %s' % out)
    finally:
        odb.close()
        try:
            fh = open('diagnostics_criterion.txt', 'w')
            fh.write('\n'.join(_LOG))
            fh.close()
        except Exception:
            pass
    print('done.')


if __name__ == '__main__':
    main()
