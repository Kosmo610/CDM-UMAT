"""V2_6 얀 크랙밴드 정규화 재료점 검증 (FE 해석 불필요).

UMAT 의 얀 종방향 인장 응답을 파이썬으로 재구현해서, 요소 크기를
바꿔가며 "단위 균열면적당 소산에너지" 를 적분한다.

이론 (UMAT 의 KDAMAGE_TARGET 에서 직접 유도)
--------------------------------------------------------------
  d(r) = 1 - exp[A(1-r)]/r ,  r = E1*e/XT  (유효응력 기준)
  sig  = (1-d)*E1*e = exp[A(1-r)]/r * XT*r = XT*exp[A(1-r)]

  즉 연화구간의 응력은 정확히 XT*exp[A(1-r)] 이고, 최대점은 r=1
  에서 sig=XT 이다. 단위 면적당 에너지는

    Gf = le * [ 탄성분 + 연화분 ]
       = le * [ XT^2/(2*E1) + XT^2/(A*E1) ]
       = le * g0 * (1 + 2/A)          , g0 = XT^2/(2*E1)

  이를 A 에 대해 풀면

    A = 2*g0*le / (Gf - g0*le)

  이것이 UMAT V2_6 이 쓰는 식이며, 여기서 수치적으로 확인한다.

주의: DMAX1 상한이 걸리면 잔류강성 (1-DMAX1)*E1 이 남아 응력이
0 으로 내려가지 않으므로 적분이 발산한다. 따라서 정규화 자체의
검증은 상한 없이(DMAX=1) 수행하고, 상한의 영향은 따로 보고한다.
"""
from __future__ import print_function
import math
import sys

# ---- UMAT 카드에서 그대로 가져온 얀 물성 -----------------------------
E1 = 254967.228042      # PROPS 2  (MPa)  Chamis 균질화, 검증완료
XT = 421.0              # PROPS 11 (MPa)  Table 3 역보정값
DMAX1 = 0.95            # PROPS 22        손상 상한
G0 = XT * XT / (2.0 * E1)


def a1teff(gf1t, celent):
    """UMAT V2_6 의 크랙밴드 블록과 동일한 산식."""
    gle = G0 * celent
    if gf1t > 1.02 * gle:
        a = 2.0 * gle / (gf1t - gle)
    else:
        a = 50.0
    return min(50.0, max(1.0e-2, a))


def sigma(e, a, dmax):
    """재료점 응력. UMAT 의 손상식을 그대로 따른다."""
    r = E1 * e / XT
    if r <= 1.0:
        return E1 * e
    d = 1.0 - math.exp(a * (1.0 - r)) / r
    d = min(dmax, max(0.0, d))
    return (1.0 - d) * E1 * e


def energy_per_area(a, le, dmax, rmax=400.0, n=800000):
    """le * 적분(sig de). 단위 N/mm (= 단위 균열면적당 에너지)."""
    emax = rmax * XT / E1
    de = emax / n
    tot = 0.0
    prev = sigma(0.0, a, dmax)
    for i in range(1, n + 1):
        cur = sigma(i * de, a, dmax)
        tot += 0.5 * (prev + cur) * de
        prev = cur
    return tot * le


def main():
    sizes = [0.0285, 0.0570, 0.1018, 0.2000]
    labels = ['fine/2', 'fine(174k)', 'coarse(26k)', 'very coarse']
    GF1T = 0.30      # N/mm, 검증용 시험값

    print('=' * 76)
    print(' V2_6 얀 종방향 크랙밴드 정규화 재료점 검증')
    print('=' * 76)
    print(' E1 = %.3f MPa, XT = %.1f MPa, g0 = XT^2/(2E1) = %.6f N/mm^2'
          % (E1, XT, G0))
    print()

    # ---- (0) 이론식 자체 검증 -----------------------------------------
    print('[0] 해석해 확인:  le*g0*(1+2/A) 가 GF1T 와 같은가')
    print('    %-12s %10s %18s %14s' % ('le [mm]', 'A1TEFF', 'le*g0*(1+2/A)', '오차 %'))
    worst0 = 0.0
    for le in sizes:
        a = a1teff(GF1T, le)
        val = le * G0 * (1.0 + 2.0 / a)
        err = abs(val / GF1T - 1.0) * 100.0
        worst0 = max(worst0, err)
        print('    %-12.4f %10.4f %18.6f %14.3e' % (le, a, val, err))
    print()

    # ---- (1) V2_5: A1T 고정, 크랙밴드 없음 -----------------------------
    A1T = 2.0
    print('[1] V2_5  (A1T = %.1f 고정) - 수치적분, 상한 없음(DMAX=1)' % A1T)
    print('    %-12s %10s %18s' % ('le [mm]', 'A_eff', 'Gf [N/mm]'))
    v25 = []
    for le, lab in zip(sizes, labels):
        g = energy_per_area(A1T, le, 1.0)
        v25.append(g)
        print('    %-12.4f %10.4f %18.6f   (%s)' % (le, A1T, g, lab))
    sp25 = max(v25) / min(v25)
    print('    -> 최대/최소 = %.2f 배. 요소크기에 비례 = 메쉬 의존\n' % sp25)

    # ---- (2) V2_6: GF1T 크랙밴드 --------------------------------------
    print('[2] V2_6  (GF1T = %.3f N/mm) - 수치적분, 상한 없음(DMAX=1)' % GF1T)
    print('    %-12s %10s %18s %14s' % ('le [mm]', 'A1TEFF', 'Gf [N/mm]', '목표대비 %'))
    v26 = []
    for le, lab in zip(sizes, labels):
        a = a1teff(GF1T, le)
        g = energy_per_area(a, le, 1.0)
        v26.append(g)
        print('    %-12.4f %10.4f %18.6f %13.3f%%   (%s)'
              % (le, a, g, (g / GF1T - 1.0) * 100.0, lab))
    sp26 = max(v26) / min(v26)
    err26 = max(abs(v / GF1T - 1.0) for v in v26) * 100.0
    print('    -> 최대/최소 = %.5f 배,  GF1T 대비 최대오차 %.3f%%\n' % (sp26, err26))

    # ---- (3) DMAX1 상한의 영향 ----------------------------------------
    print('[3] 참고: DMAX1 = %.2f 상한을 적용하면' % DMAX1)
    print('    %-12s %18s' % ('le [mm]', 'Gf(상한적용) [N/mm]'))
    for le in sizes:
        a = a1teff(GF1T, le)
        g = energy_per_area(a, le, DMAX1, rmax=60.0, n=200000)
        print('    %-12.4f %18.6f' % (le, g))
    print('    잔류강성 (1-DMAX1)*E1 = %.1f MPa 때문에 응력이 0 으로'
          % ((1 - DMAX1) * E1))
    print('    수렴하지 않아 적분이 발산한다. 상한은 수렴성 확보용이며')
    print('    최대점(강도) 판독에는 영향이 없다.\n')

    # ---- 판정 ----------------------------------------------------------
    print('=' * 76)
    print(' 판정')
    print('=' * 76)
    c0 = worst0 < 1.0e-6
    print(' [%s] 해석해가 GF1T 와 일치        (최대오차 %.3e %% < 1e-6)'
          % ('OK' if c0 else 'NG', worst0))
    c1 = sp25 > 3.0
    print(' [%s] V2_5 는 메쉬 의존           (편차 %.2f 배 > 3.0)'
          % ('OK' if c1 else 'NG', sp25))
    c2 = sp26 < 1.01
    print(' [%s] V2_6 는 메쉬 무관           (편차 %.5f 배 < 1.01)'
          % ('OK' if c2 else 'NG', sp26))
    c3 = err26 < 1.0
    print(' [%s] V2_6 소산에너지 = GF1T      (최대오차 %.3f%% < 1%%)'
          % ('OK' if c3 else 'NG', err26))
    ok = c0 and c1 and c2 and c3
    print()
    print(' 종합: %s' % ('통과 - 크랙밴드 정규화가 의도대로 동작한다'
                        if ok else '실패 - 확인 필요'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
