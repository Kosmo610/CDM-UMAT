#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_runs.py  --  완주한 런 전부를 논문 Table 3 과 한 표에 놓는다

"어느 런이 논문에 제일 가까운가" 를 매번 손으로 세지 않으려고 만들었다.
CSV 폴더 하나만 주면 그 안의 tension_stress_strain_*.csv 를 전부 찾아
강도 / 최대점 변형률 / 초기강성 / 재경화 폭을 뽑고, 태그에서 온도를
읽어 논문 값과 대조한다. odb 를 읽지 않으므로 몇 초면 끝난다.

**강도는 반드시 첫 하중강하 직전의 국부최대다** (find_frames.local_peak
를 그대로 임포트한다). 재경화 때문에 곡선의 전역 최대는 꼬리에 있고,
그걸 강도로 쓰면 P4T1000 이 -0.1 % 가 아니라 +4.6 % 로 보인다.
이탈장부 §5.30(D) 참조 -- 실제로 밟았던 함정이다.

사용법  (일반 python, abaqus 불필요)
------
  python compare_runs.py allcsv2
  python compare_runs.py allcsv2 --md
  python compare_runs.py --selftest

  --md        마크다운 표로 출력 (장부에 붙여넣기용)
  --selftest  해석·CSV 없이 판정 로직만 검사
"""
from __future__ import print_function
import sys
import os
import csv
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_frames import local_peak

# 논문 Table 3 (해석값) 과 Fig.11/13/15 최대점 변형률 [%]
PAPER = {23: (128.45, 0.3200), 500: (179.42, 0.2600), 1000: (199.15, 0.3100)}

E0_HI = 0.05        # 초기강성 최소제곱 상한 [% 변형률]


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def temp_of(tag):
    """런 태그 -> 온도 [C].  P4T500 -> 500,  P3 -> 23."""
    up = tag.upper()
    for T in (1000, 500):
        if 'T%d' % T in up:
            return T
    return 23


def read_curve(path):
    """tension_stress_strain*.csv -> (eps [%], sig [MPa])."""
    eps, sig = [], []
    with open(path, 'r') as f:
        for r in csv.DictReader(f):
            e, s = fnum(r.get('eps_xx_mech')), fnum(r.get('sigma_xx_MPa'))
            if e is None or s is None:
                continue
            eps.append(e * 100.0)
            sig.append(s)
    return eps, sig


def init_stiffness(eps, sig, hi=E0_HI):
    """0~hi % 최소제곱 기울기 [GPa].  eps 는 %, sig 는 MPa."""
    sxx = sxy = 0.0
    for e, s in zip(eps, sig):
        if 0.0 <= e <= hi:
            sxx += e * e
            sxy += e * s
    if sxx <= 0.0:
        return float('nan')
    return sxy / sxx / 10.0          # MPa/% -> GPa


def measure(eps, sig):
    """곡선 하나 -> dict.  strength/peak_eps/confirmed/E0/rehard/end_eps."""
    if not sig:
        return None
    k = local_peak(sig)
    confirmed = k is not None
    if k is None:
        k = max(range(len(sig)), key=lambda i: sig[i])
    tail = sig[k:]
    rehard = (max(tail) - min(tail)) if confirmed else 0.0
    return dict(strength=sig[k], peak_eps=eps[k], confirmed=confirmed,
                E0=init_stiffness(eps, sig), rehard=rehard,
                end_eps=eps[-1])


def collect(folder):
    """폴더 -> [(tag, T, meas)] 온도·오차순 정렬."""
    out = []
    pat = os.path.join(folder, 'tension_stress_strain_*.csv')
    for path in sorted(glob.glob(pat)):
        base = os.path.basename(path)
        tag = base[len('tension_stress_strain_'):-len('.csv')]
        eps, sig = read_curve(path)
        m = measure(eps, sig)
        if m is None:
            continue
        T = temp_of(tag)
        ps, pe = PAPER[T]
        m['serr'] = (m['strength'] - ps) / ps * 100.0
        m['eerr'] = (m['peak_eps'] - pe) / pe * 100.0
        m['stretch'] = m['end_eps'] / pe
        out.append((tag, T, m))
    out.sort(key=lambda r: (r[1], abs(r[2]['serr'])))
    return out


def state_str(m):
    if not m['confirmed']:
        return '**봉우리 없음 -- 하한**'
    return '연화 (뒤 +%.1f MPa)' % m['rehard']


def report(rows, md=False):
    if md:
        print('| 런 | T | 강도 | 오차 | 최대점 % | 오차 | E0 | 끝/논문 | 상태 |')
        print('|---|---|---|---|---|---|---|---|---|')
        fmt = ('| %s | %d | %.2f | %+.1f %% | %.4f | %+.1f %% | %.1f '
               '| %.2f배 | %s |')
    else:
        print('%-10s %5s | %8s %9s | %8s %9s | %6s | %6s | %s' %
              ('run', 'T', '강도', '오차', '최대점%', '오차',
               'E0', '끝/논문', '상태'))
        print('-' * 100)
        fmt = ('%-10s %5d | %8.2f %+8.1f%% | %8.4f %+8.1f%% | %6.1f '
               '| %5.2f배 | %s')
    for tag, T, m in rows:
        print(fmt % (tag, T, m['strength'], m['serr'], m['peak_eps'],
                     m['eerr'], m['E0'], m['stretch'], state_str(m)))

    print()
    print('=== 온도별 순위 (|강도오차|) ===')
    for T in (23, 500, 1000):
        same = [r for r in rows if r[1] == T]
        if not same:
            continue
        print('%5d C : %s' % (T, '  '.join(
            '%s %+.1f%%%s' % (tag, m['serr'],
                              '' if m['confirmed'] else '(하한)')
            for tag, _, m in same)))

    print()
    print('=== 온도 강화 (500 -> 1000 C).  논문 +11.0 % ===')
    by = {}
    for tag, T, m in rows:
        by.setdefault(tag.replace('T500', '').replace('T1000', ''), {})[T] = m
    for card in sorted(by):
        d = by[card]
        if 500 in d and 1000 in d:
            g = (d[1000]['strength'] - d[500]['strength']) / d[500]['strength']
            print('%-10s : %6.1f -> %6.1f  %+6.1f %%' %
                  (card, d[500]['strength'], d[1000]['strength'], g * 100.0))


# ---------------------------------------------------------------- 자체시험
def selftest():
    n = [0]

    def ck(cond, what):
        n[0] += 1
        if not cond:
            raise AssertionError('FAIL: ' + what)

    ck(temp_of('P4T500') == 500, 'P4T500 -> 500')
    ck(temp_of('P3T1000') == 1000, 'P3T1000 -> 1000')
    ck(temp_of('P0') == 23, 'P0 -> 23')
    ck(temp_of('p2t1000') == 1000, '소문자 태그')
    ck(temp_of('P4') == 23, 'P4 -> 23')

    # 재경화 곡선: 봉우리 뒤 떨어졌다가 다시 올라간다.
    # 전역최대는 꼬리에 있지만 강도는 첫 봉우리여야 한다. (§5.30D)
    win = 25
    up = [float(i) for i in range(win + 1)]              # 0..25 상승
    dn = [25.0 - 1.2 * i for i in range(1, win + 6)]     # 급강하
    tail = [dn[-1] + 2.0 * i for i in range(1, 60)]      # 재경화, 전역최대
    sig = up + dn + tail
    eps = [0.01 * i for i in range(len(sig))]
    m = measure(eps, sig)
    ck(m['confirmed'], '재경화 곡선에서 국부최대를 찾아야')
    ck(abs(m['strength'] - 25.0) < 1e-9, '강도는 첫 봉우리 25.0')
    ck(max(sig) > 25.0, '전역최대는 꼬리에 있다 (함정 성립)')
    ck(m['strength'] < max(sig), '강도가 전역최대보다 작아야')
    ck(m['rehard'] > 0.0, '재경화 폭이 잡혀야')

    # 단조증가 곡선: 봉우리 없음 -> 하한
    sig2 = [float(i) for i in range(200)]
    eps2 = [0.01 * i for i in range(200)]
    m2 = measure(eps2, sig2)
    ck(not m2['confirmed'], '단조증가는 봉우리 없음')
    ck(abs(m2['strength'] - 199.0) < 1e-9, '하한은 곡선 끝값')

    # 초기강성: 60 GPa = 600 MPa/%
    eps3 = [0.001 * i for i in range(200)]
    sig3 = [600.0 * e for e in eps3]
    ck(abs(init_stiffness(eps3, sig3) - 60.0) < 1e-6, 'E0 60 GPa')

    # 빈 곡선
    ck(measure([], []) is None, '빈 곡선은 None')

    # 논문 기준값이 Table 3 그대로인가
    ck(abs(PAPER[23][0] - 128.45) < 1e-9, 'Table 3 23 C')
    ck(abs(PAPER[500][0] - 179.42) < 1e-9, 'Table 3 500 C')
    ck(abs(PAPER[1000][0] - 199.15) < 1e-9, 'Table 3 1000 C')

    print('자체시험 %d개 통과' % n[0])


def main(argv):
    if '--selftest' in argv:
        selftest()
        return 0
    args = [a for a in argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    folder = args[0]
    if not os.path.isdir(folder):
        print('폴더가 없다: %s' % folder)
        return 2
    rows = collect(folder)
    if not rows:
        print('tension_stress_strain_*.csv 를 못 찾았다: %s' % folder)
        return 2
    report(rows, md=('--md' in argv))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
