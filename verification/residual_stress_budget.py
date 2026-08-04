#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
residual_stress_budget.py
=========================
845 degC 에서 기지 손상 100% 라는 논문 결과를, 열잔류응력 수지만으로
재현할 수 있는지 해석 없이 판정한다.

배경
----
diagnose_cooling_criterion.py (CSIC_t23.odb, 냉각 102 프레임, 기지 적분점
91,554 개) 결과:

  845 degC 에서 기지 최대주응력의 *최댓값* 이 140.0 MPa.
  Xm = 310 MPa 의 45% 에 불과해서 어떤 파손기준을 써도 손상 0%.
  -> 파손기준은 원인이 아니다. 잔류응력 크기 자체가 부족하다.

필요 응력증가율 = 310 MPa / (1050-845) K = 1.51 MPa/K
모델 실측       =  90.9 MPa / 205 K       = 0.443 MPa/K   (29%)

이 스크립트는 "우리가 고칠 수 있는 물성" 을 전부 흔들어서 1.51 MPa/K
에 도달 가능한지 본다. 검사 대상:

  (1) 얀 횡방향 CTE 균질화 식 (Chamis vs Schapery vs 혼합률)
  (2) 얀 축방향 CTE
  (3) 무응력 온도 T0
  (4) 상(phase) 강성 배분 자체

실행:  python3 residual_stress_budget.py
"""
from __future__ import print_function
import math

# ---- 논문 구성재 물성 (Table 1, 2) -----------------------------------------
Ef1, Ef2, Gf12, Gf23, nuf12 = 230e3, 40e3, 24e3, 14.3e3, 0.26   # T300
Em, num = 350e3, 0.20                                            # SiC
af1, af2, am = -0.3e-6, 3.1e-6, 4.5e-6

# ---- 얀 카드 (검증완료, micromech_check.py 가 0.005% 이내로 재현) ---------
YE1, YE2 = 254967.228042, 44321.737572
YA1, YA2 = 1.070925962822e-06, 3.324908565604e-06
YNU12 = 0.247516386

# ---- RVE 기하 (검증완료) ----------------------------------------------------
VF_TOTAL = 0.3946                 # RVE 전체 섬유 체적분율
T0, T_TARGET, XM = 1050.0, 845.0, 310.0

# ---- FE 실측 (diagnose_cooling_criterion.py) -------------------------------
FE_RATE = 90.91 / (T0 - T_TARGET)      # MPa/K, 845 degC 기지 평균 MaxPrin
NEED_RATE = XM / (T0 - T_TARGET)       # MPa/K, 논문 재현에 필요


def line(c='-', n=76):
    print(c * n)


def yarn_vf():
    """얀 카드의 E1 을 혼합률로 역산한 얀 내부 섬유분율."""
    return (Em - YE1) / (Em - Ef1)


def alpha2_schemes(Vf, a1):
    """얀 횡방향 CTE 를 세 가지 균질화 식으로 계산한다."""
    sq, Vm = math.sqrt(Vf), 1.0 - Vf
    out = {}
    # Chamis (현재 카드가 쓰는 식)
    out['Chamis'] = sq * af2 + (1.0 - sq) * ((1.0 + num) * am - a1 * num)
    # Schapery
    out['Schapery'] = ((1.0 + nuf12) * af2 * Vf + (1.0 + num) * am * Vm
                       - a1 * YNU12)
    # 단순 혼합률 (하한 성격)
    out['혼합률'] = Vf * af2 + Vm * am
    return out


def voigt_rate(am_, phases):
    """등변형률(Voigt) 3상 모델의 기지 응력증가율 [MPa/K].

    냉각 dT<0 에서  eps = dT * sum(V E a)/sum(V E),
                    sig_m = Em (eps - am dT)
    -> 냉각 1 K 당 기지 인장응력 = Em * (am - a_bar)
    """
    num_ = sum(V * E * a for V, E, a in phases)
    den_ = sum(V * E for V, E, a in phases)
    abar = num_ / den_
    return Em * (am_ - abar), abar


def build_phases(a_yarn_axial, a_yarn_trans, E_yarn_trans=YE2):
    """평직 RVE 를 3상으로 축약: 기지 / 하중축 얀 / 직교 얀."""
    Vy_total = VF_TOTAL / yarn_vf()          # 얀(섬유+얀내부기지) 체적분율
    Vy_each = 0.5 * Vy_total
    Vm_pure = 1.0 - Vy_total
    return [(Vm_pure, Em, am),
            (Vy_each, YE1, a_yarn_axial),
            (Vy_each, E_yarn_trans, a_yarn_trans)]


def main():
    Vf = yarn_vf()
    print('=' * 76)
    print(' 열잔류응력 수지 - 845 degC 기지손상 100% 가 물성으로 도달 가능한가')
    print('=' * 76)
    print(' 얀 내부 섬유분율 Vf = %.5f  (카드 E1 역산)' % Vf)
    print(' RVE 얀 체적분율     = %.5f' % (VF_TOTAL / Vf))
    print()
    print(' 목표:  %.3f MPa/K   (Xm=%.0f 을 %.0f->%.0f degC 에서 도달)'
          % (NEED_RATE, XM, T0, T_TARGET))
    print(' 실측:  %.3f MPa/K   (FE 기지 평균 MaxPrin)  = 목표의 %.1f%%'
          % (FE_RATE, 100 * FE_RATE / NEED_RATE))
    print()

    # ---- (1) 횡방향 CTE 균질화 식 -----------------------------------------
    line()
    print(' [1] 얀 횡방향 CTE 를 다른 식으로 바꾸면?')
    line()
    schemes = alpha2_schemes(Vf, YA1)
    print('   %-12s %14s %16s %14s' % ('식', 'a2 [1/K]', '기지와의 차 [1/K]',
                                       'Voigt [MPa/K]'))
    best = None
    for k, v in sorted(schemes.items(), key=lambda x: -x[1]):
        r, _ = voigt_rate(am, build_phases(YA1, v))
        mark = '  <- 현재 카드' if abs(v - YA2) < 1e-8 else ''
        print('   %-12s %14.4e %16.4e %14.3f%s' % (k, v, am - v, r, mark))
        if best is None or r > best[1]:
            best = (k, r)
    print()
    print('   -> 최대라도 %.3f MPa/K (%s). 목표 %.3f 의 %.1f%%.'
          % (best[1], best[0], NEED_RATE, 100 * best[1] / NEED_RATE))
    print('      횡방향 CTE 식을 바꿔서는 도달 불가능하다.')
    print('      세 식 모두 a2 >= %.3e 이라 기지(4.5e-6)와의 차가'
          % min(schemes.values()))
    print('      최대 %.3e 밖에 안 되기 때문이다.' % (am - min(schemes.values())))
    print()

    # ---- (2) 축방향 CTE ----------------------------------------------------
    line()
    print(' [2] 축방향 CTE 가 주범인가? (a1 를 낮춰서 불일치를 키운다)')
    line()
    print('   %-16s %14s %16s' % ('a1 [1/K]', 'Voigt [MPa/K]', '목표 대비'))
    for a1 in (YA1, 0.0, af1, -2.0e-6, -5.0e-6):
        r, _ = voigt_rate(am, build_phases(a1, YA2))
        tag = '  <- 현재 카드' if abs(a1 - YA1) < 1e-12 else (
              '  <- T300 섬유 축방향' if abs(a1 - af1) < 1e-12 else '')
        print('   %-16.4e %14.3f %15.1f%%%s'
              % (a1, r, 100 * r / NEED_RATE, tag))
    print()
    print('   -> 섬유 축 CTE(-0.3e-6) 를 그대로 써도 부족하다.')
    print('      얀은 축방향 강성이 커서(E1=%.0f GPa) 기지를 붙잡지만,'
          % (YE1 / 1e3))
    print('      직교 얀은 횡방향 강성이 작아(E2=%.0f GPa) 거의 못 붙잡는다.'
          % (YE2 / 1e3))
    print()

    # ---- (3) 강성 배분이 근본 원인 -----------------------------------------
    line()
    print(' [3] 근본 원인: 기지가 얀보다 단단하다')
    line()
    print('   기지     Em      = %7.0f GPa' % (Em / 1e3))
    print('   얀 축방향 E1      = %7.0f GPa   (기지의 %.2f 배)'
          % (YE1 / 1e3, YE1 / Em))
    print('   얀 횡방향 E2      = %7.0f GPa   (기지의 %.2f 배)'
          % (YE2 / 1e3, YE2 / Em))
    print()
    print('   보강재가 기지보다 무르면 기지를 구속하지 못한다. 기지가')
    print('   제 마음대로 수축하고 얀이 끌려간다. 이것이 구속효율이')
    print('   낮은 구조적 이유이며, 물성표를 바꾸지 않는 한 못 고친다.')
    print()
    print('   완전구속 상한과의 비교:')
    print('     1축 완전구속  Em*(am-a1) = %.3f MPa/K'
          % (Em * (am - YA1)))
    print('     등2축         /(1-nu)    = %.3f MPa/K'
          % (Em * (am - YA1) / (1.0 - num)))
    print('     Voigt 3상 모델           = %.3f MPa/K'
          % voigt_rate(am, build_phases(YA1, YA2))[0])
    print('     FE 실측                  = %.3f MPa/K' % FE_RATE)
    print()
    print('   논문이 요구하는 %.3f 는 등2축 완전구속(%.3f)과 거의 같다.'
          % (NEED_RATE, Em * (am - YA1) / (1.0 - num)))
    print('   즉 논문 수준이 되려면 기지가 완전히 갇혀 있어야 하는데,')
    print('   위 강성 배분에서는 원리적으로 불가능하다.')
    print()

    # ---- (4) 무응력 온도 ---------------------------------------------------
    line()
    print(' [4] 무응력 온도 T0 를 올리면?')
    line()
    need_dT = XM / FE_RATE
    print('   현재 증가율 %.3f MPa/K 로 %.0f MPa 에 도달하려면 dT = %.0f K'
          % (FE_RATE, XM, need_dT))
    print('   -> T0 = %.0f + %.0f = %.0f degC 필요.'
          % (T_TARGET, need_dT, T_TARGET + need_dT))
    print('      CVI SiC 공정온도(1000~1100 degC)를 크게 넘으므로 기각.')
    print()

    # ---- 결론 ---------------------------------------------------------------
    line('=')
    print(' 결론')
    line('=')
    print(' 845 degC 기지손상 100% 는 아래 어느 것으로도 재현 불가능하다.')
    print('   - 횡방향 CTE 균질화 식 교체      -> 최대 %.1f%%'
          % (100 * best[1] / NEED_RATE))
    print('   - 축방향 CTE 를 섬유값으로 교체  -> 여전히 부족')
    print('   - 무응력 온도 상향               -> %.0f degC 필요, 비물리적'
          % (T_TARGET + need_dT))
    print()
    biax = Em * (am - YA1) / (1.0 - num)
    print(' 구조적 이유: 기지 SiC(%.0f GPa)가 얀 횡방향(%.0f GPa)보다 %.0f 배'
          % (Em / 1e3, YE2 / 1e3, Em / YE2))
    print(' 단단하다. 보강재가 기지를 구속하지 못하므로 잔류응력이 등2축')
    print(' 완전구속 값의 %.0f%% 밖에 안 생긴다. 이는 논문 Table 1/2 물성의'
          % (100 * FE_RATE / biax))
    print(' 직접적 귀결이며 우리 구현의 오류가 아니다.')
    print()
    print(' 따라서 이 항목은 "재현 실패" 가 아니라 "논문 물성으로는')
    print(' 도달할 수 없는 값" 으로 논문에 명시하는 것이 옳다.')
    print(' 남은 설명 후보:')
    print('   (a) 논문의 100% 가 d>0(부분손상) 집계일 가능성')
    print('   (b) 논문이 기지 소성/크리프를 넣어 응력 이력이 다를 가능성')
    print('   (c) 논문이 섬유/기지 계면 손상을 별도로 세었을 가능성')
    line('=')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
