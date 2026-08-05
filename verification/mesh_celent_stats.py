#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesh_celent_stats.py
====================
덱의 메쉬를 직접 읽어 요소 특성길이(CELENT) 분포를 내고, 크랙밴드
파괴에너지(얀 PROPS 32 = GF1T, 기지 PROPS 16 = Gf)가 의도한 연화
지수를 실제로 만들어내는지 검증한다. FE 해석 불필요.

배경
----
GF1T = 0.03962 N/mm 는 "fine 메쉬(le=0.0570 mm)에서 A1TEFF 가 정확히
2.0 이 되도록" 역산한 값이었다. 그런데 그 0.0570 은 fine 메쉬 값이
아니었다. 5.39 mm^3 / 26,000 요소(coarse) = 0.0592 이고, 실제
fine 메쉬(174,405 요소)는 0.0314 다. 74% 큰 값을 쓴 셈이라
A1TEFF 가 2.0 이 아니라 0.77 이 되어 훨씬 연성적으로 거동했고,
23 C 강도가 125.81 -> 139.43 MPa (+10.8%) 로 올라갔다.

Abaqus 의 CELENT 는 3-D 연속체 요소에서 (요소 체적)^(1/3) 이다.
이 스크립트는 C3D4 체적을 직접 적분해 그 값을 낸다.

사용법
------
  python3 mesh_celent_stats.py <deck>.inp
"""
from __future__ import print_function
import re
import sys

# 얀 / 기지 카드에서 크랙밴드에 관여하는 값 (검증완료 물성)
# DERIVED=True  : "명목 A 를 재현하도록 역산했다" 고 주장하는 값이므로
#                 어긋나면 곧 오류다.
# DERIVED=False : 수렴/강도를 보며 경험적으로 맞춘 값이라 A=2.0 과
#                 일치할 이유가 없다. 아래 비교는 참고용이다.
YARN = dict(E=254967.228042, XT=421.0, GF=0.03962, NOMINAL_A=2.0,
            SETS=('Yarn0', 'Yarn1', 'Yarn2', 'Yarn3'),
            PROP='PROPS 32 GF1T', DERIVED=True)
MATRIX = dict(E=350000.0, XT=310.0, GF=0.018, NOMINAL_A=2.0,
              SETS=('Matrix',), PROP='PROPS 16 Gf', DERIVED=False)


def read_mesh(path):
    """*Node 와 *Element(C3D4), *ElSet 을 읽는다."""
    nodes, elems, mode = {}, {}, None
    for ln in open(path, errors='replace'):
        t = ln.strip()
        if t.startswith('*'):
            u = t.upper()
            mode = ('N' if u.startswith('*NODE')
                    else 'E' if u.startswith('*ELEMENT,') else None)
            continue
        p = t.split(',')
        try:
            if mode == 'N' and len(p) >= 4:
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
            elif mode == 'E' and len(p) >= 5:
                elems[int(p[0])] = tuple(int(x) for x in p[1:5])
        except ValueError:
            pass
    s = open(path, errors='replace').read()
    sets = {}
    for m in re.finditer(r'\*ElSet, ElSet=(\w+)\n(.*?)(?=\n\*)', s, re.S):
        sets[m.group(1)] = [int(x) for x in re.split(r'[,\s]+', m.group(2))
                            if x.strip().isdigit()]
    return nodes, elems, sets


def tet_volume(nodes, conn):
    a, b, c, d = (nodes[n] for n in conn)
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    w = [d[i] - a[i] for i in range(3)]
    det = (u[0] * (v[1] * w[2] - v[2] * w[1])
           - u[1] * (v[0] * w[2] - v[2] * w[0])
           + u[2] * (v[0] * w[1] - v[1] * w[0]))
    return abs(det) / 6.0


def a_eff(gf, g0, le):
    """UMAT 의 크랙밴드 블록과 동일한 산식."""
    gle = g0 * le
    a = 2.0 * gle / (gf - gle) if gf > 1.02 * gle else 50.0
    return min(50.0, max(1.0e-2, a))


def report(name, cfg, nodes, elems, sets):
    ids = []
    for s in cfg['SETS']:
        ids += sets.get(s, [])
    if not ids:
        print(' [skip] %s: elset 없음' % name)
        return
    vols = [tet_volume(nodes, elems[e]) for e in ids if e in elems]
    le = sorted(v ** (1.0 / 3.0) for v in vols)
    n, tot = len(le), sum(vols)
    vw = sum(v * v ** (1.0 / 3.0) for v in vols) / tot

    def q(p):
        return le[int(p * (n - 1))]

    g0 = cfg['XT'] ** 2 / (2.0 * cfg['E'])
    a = sorted(a_eff(cfg['GF'], g0, x) for x in le)
    lim = cfg['GF'] / (1.02 * g0)
    clamped = sum(1 for x in a if x >= 49.99)
    target = 2.0 * g0 * vw

    print('=' * 72)
    print(' %s   (%d 요소, %s = %.6f N/mm)' % (name, n, cfg['PROP'], cfg['GF']))
    print('=' * 72)
    print('   CELENT  최소 %.5f  중앙 %.5f  최대 %.5f  체적가중평균 %.5f'
          % (le[0], q(0.5), le[-1], vw))
    print('   A_eff   중앙 %.3f  평균 %.3f  (p05 %.3f  p95 %.3f)'
          % (a[n // 2], sum(a) / n, a[int(0.05 * n)], a[int(0.95 * n)]))
    print('   snap-back 한계 le = %.5f  -> %s (클램프 %d 개)'
          % (lim, '안전' if lim > le[-1] else '*** 초과 ***', clamped))
    print('   명목 A=%.1f 를 재현하는 값 = 2*g0*le_vw = %.6f N/mm'
          % (cfg['NOMINAL_A'], target))
    off = 100.0 * (cfg['GF'] / target - 1.0)
    if cfg['DERIVED']:
        print('   현재 값 대비 %+.1f%%  -> %s'
              % (off, '일치' if abs(off) < 5 else '*** 재보정 필요 ***'))
    else:
        print('   현재 값 대비 %+.1f%%  (경험 보정치라 일치할 필요는 없음)'
              % off)
    print()


def main():
    if len(sys.argv) < 2:
        print('usage: python3 mesh_celent_stats.py <deck>.inp')
        return 1
    nodes, elems, sets = read_mesh(sys.argv[1])
    print('노드 %d, 요소 %d\n' % (len(nodes), len(elems)))
    report('얀 (종방향 크랙밴드)', YARN, nodes, elems, sets)
    report('기지 (인장 크랙밴드)', MATRIX, nodes, elems, sets)
    print(' 참고: 전체 체적 / 요소수 로 잡은 평균 요소크기')
    tv = sum(tet_volume(nodes, c) for c in elems.values())
    print('   %d 요소, 총 체적 %.6f mm^3 -> (V/N)^(1/3) = %.5f'
          % (len(elems), tv, (tv / len(elems)) ** (1.0 / 3.0)))
    print('   26,000 요소였다면 %.5f  <- 0.0570 은 여기서 나온 값으로 보인다'
          % ((tv / 26000.0) ** (1.0 / 3.0)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
