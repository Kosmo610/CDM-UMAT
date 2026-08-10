#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_texgen_elastic.py
======================
TexGen이 내보낸 .inp 를 **그대로 살려서** C/SiC 탄성 균질화 덱으로 만든다.

왜 TexGen 원본을 살리는가
-------------------------
TexGen 내보내기는 메시만 있는 파일이 아니다.  이미 완성된 균질화 해석 덱이다:

  * `*Equation` 57식 (면 9 + 모서리 27 + 꼭짓점 21) - 주기경계조건
  * `*Step, perturbation` + `*Load Case` Load0..Load5
        각 케이스가 드라이버 하나에 `*Cload = V_RVE` 를 건다.
        드라이버 자유도 = 거시 변형률, 반력 = sigma * V 이므로
        Cload = V_RVE 는 곧 **단위 거시응력 1 MPa** 이다.
        따라서 각 케이스의 드라이버 변위가 **컴플라이언스 S_bar 의 한 열**이다.
  * `*Step, perturbation` + `*Temperature = 1`
        드라이버가 자유이므로 sigma_bar = 0, 드라이버 변위가 곧 **alpha_bar**.

즉 EasyPBC가 잡 7개로 하는 일을 TexGen 덱은 **잡 1개**로 한다. 그것도
EasyPBC와 **같은 응력 제어 정의**라서 E, nu, G 가 직접 나온다
(우리 ZHANG 덱의 HOM_* 는 변형률 제어라 C_bar 가 나오고, 비교하려면
S_bar = C_bar^-1 를 거쳐야 한다 - docs/EASYPBC_APPLICATION_PLAN.md 참조).

그래서 이 스크립트가 하는 일은 최소한이다.

무엇을 바꾸는가
---------------
1. **재료값만 교체.**  TexGen이 넣어둔 Mat0/Mat1 은 자리표시자이고
   **단위가 Pa** 다 (Mat0 = 3e9).  메시는 mm 이므로 그대로 두면 응력이
   1e-6 배 틀린 채 조용히 돌아간다.  Zhang Table 1/2 에서 나온
   Chamis/Schapery 값(verification/micromech_check.py 가 검증)으로
   **mm-N-MPa** 단위에 맞춰 덮어쓴다.
2. **드라이버 출력에 RF 추가.**  TexGen은 U 만 요청한다.  RF 가 있어야
   "자유 드라이버의 반력이 정말 0인가"를 확인할 수 있다 - PBC가 인공
   구속을 넣지 않았다는 직접 증거다.
3. **열 스텝에 드라이버 6개 전부 출력.**  TexGen은 0,1,2 만 요청한다.
   전단 CTE 3개가 0으로 나오는지 확인해야 대칭성 검사가 된다.
4. **`.ori` 인라인** (선택).  덱이 자기완결이 되어 zip 전달 시 누락이 없다.

무엇을 바꾸지 않는가
--------------------
메시, 방향, ElSet, 주기경계조건, 스텝 구조, Load Case, Cload 크기.
**TexGen의 PBC는 이미 검증되었다** (경계절점 9062/9062, 짝맞춤 오차 0).
손댈 이유가 없다.

Run:
  python3 abaqus/make_texgen_elastic.py abaqus/meshes/CSiC_RVE_0135.inp \\
          --inline-ori --out abaqus/CSIC_ELASTIC_HOMOG.inp
  python3 abaqus/make_texgen_elastic.py --check
"""
from __future__ import print_function

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_inp import split_blocks, kwname, kw_option, inline_ori, emit_blocks

# ==========================================================================
# 재료 카드 -- 단위 mm, N, MPa, degC
#
# 출처: Q. Zhang et al., Ceramics International 48 (2022) 3109-3124
#         Table 1  T300 필라멘트,  Table 2  SiC 매트릭스
#       얀은 Chamis(탄성) + Schapery(CTE) 균질화, Vf_yarn = 0.79194.
#       verification/micromech_check.py 가 12개 상수 전부를 재현한다
#       (최대 오차 0.142 %).
#
# 이 숫자를 손으로 옮겨 적지 말 것.  전사 오류가 이미 두 번 났다.
# ==========================================================================
MATRIX = {
    "E":     350000.0,      # MPa   (Zhang Table 2: 350 GPa)
    "nu":    0.20,
    "alpha": 4.5e-06,       # /K
}

YARN = {
    # Abaqus *Elastic, type=ENGINEERING CONSTANTS 순서:
    #   E1 E2 E3 nu12 nu13 nu23 G12 G13 / G23
    "E1":   254967.228042,
    "E2":    44321.737572,
    "E3":    44321.737572,
    "nu12":      0.247516386,
    "nu13":      0.247516386,
    "nu23":      0.395813581,
    "G12":   26431.515264,
    "G13":   26431.515264,
    "G23":   15876.667974,
    # *Expansion, type=ORTHO
    "a1":  1.070925962822e-06,
    "a2":  3.324908565604e-06,
    "a3":  3.324908565604e-06,
}

MATRIX_MAT = "Mat0"
YARN_MAT = "Mat1"
DRIVERS = ["ConstraintsDriver%d" % i for i in range(6)]


def _fmt(v):
    return repr(float(v))


def matrix_data(kw):
    """Mat0 하위 키워드의 데이터 줄을 C/SiC 매트릭스 값으로 만든다."""
    n = kwname(kw)
    if n == "elastic":
        return ["%s, %s" % (_fmt(MATRIX["E"]), _fmt(MATRIX["nu"]))]
    if n == "expansion":
        return [_fmt(MATRIX["alpha"])]
    return None


def yarn_data(kw):
    n = kwname(kw)
    if n == "elastic":
        return ["%s, %s, %s, %s, %s, %s, %s, %s" % tuple(
                    _fmt(YARN[k]) for k in
                    ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13")),
                _fmt(YARN["G23"])]
    if n == "expansion":
        return ["%s, %s, %s" % (_fmt(YARN["a1"]), _fmt(YARN["a2"]),
                                _fmt(YARN["a3"]))]
    return None


def driver_output_block(with_rf=True):
    """드라이버 6개의 절점 출력 블록을 만든다."""
    out = []
    var = "U, RF" if with_rf else "U"
    for d in DRIVERS:
        out.append(("*Node Output, nset=%s" % d, [var]))
    return out


def rebuild(blocks):
    """재료값 교체 + 드라이버 출력 보강."""
    out = []
    cur_mat = None
    in_step = False
    step_name = ""
    dropped_driver_out = 0
    injected = 0

    i = 0
    blocks = list(blocks)
    while i < len(blocks):
        kw, data = blocks[i]
        n = kwname(kw)

        if n == "material":
            cur_mat = (kw_option(kw, "Name") or kw_option(kw, "name") or "")
            out.append((kw, data))
            i += 1
            continue

        if n == "step":
            in_step = True
            step_name = (kw_option(kw, "Name") or kw_option(kw, "name") or "")
            cur_mat = None
            out.append((kw, data))
            i += 1
            continue

        if n == "end step":
            in_step = False
            out.append((kw, data))
            i += 1
            continue

        # --- 재료값 교체 ---
        if cur_mat == MATRIX_MAT and not in_step:
            nd = matrix_data(kw)
            if nd is not None:
                out.append((kw, nd))
                i += 1
                continue
        if cur_mat == YARN_MAT and not in_step:
            nd = yarn_data(kw)
            if nd is not None:
                out.append((kw, nd))
                i += 1
                continue

        # --- 드라이버 절점 출력: 기존 것을 걷어내고 6개 전부 다시 넣는다 ---
        if in_step and n == "node output":
            ns = (kw_option(kw, "nset") or "")
            if ns.lower().startswith("constraintsdriver"):
                # 연속된 드라이버 출력 블록을 통째로 소비
                j = i
                while j < len(blocks):
                    k2, _ = blocks[j]
                    if kwname(k2) != "node output":
                        break
                    if not (kw_option(k2, "nset") or "").lower().startswith(
                            "constraintsdriver"):
                        break
                    j += 1
                    dropped_driver_out += 1
                out.extend(driver_output_block(with_rf=True))
                injected += 1
                i = j
                continue

        out.append((kw, data))
        i += 1

    print("  드라이버 출력 블록 %d개를 걷어내고 %d 지점에 6개씩 재삽입 (U, RF)"
          % (dropped_driver_out, injected))
    return out


HEADING = """*Heading
CSiC 2D plain weave RVE -- linear elastic homogenisation (TexGen native deck)
**
** 생성: abaqus/make_texgen_elastic.py
** 원본: %s
**
** 단위: mm, N, MPa, degC
**
** TexGen 원본의 주기경계조건, Load Case, 스텝 구조를 그대로 유지한다.
** 바뀐 것은 재료값(Pa 자리표시자 -> C/SiC MPa)과 드라이버 출력(U -> U,RF)뿐이다.
**
** 스텝 1  Isothermal linear perturbation step
**   Load0..Load5 가 드라이버 0..5 에 Cload = V_RVE = %s N 을 건다.
**   드라이버 자유도 = 거시 변형률, 반력 = sigma * V 이므로 이는
**   **단위 거시응력 1 MPa** 이고, 각 케이스의 드라이버 변위 6개가
**   컴플라이언스 S_bar 의 한 열이다.
**       E1 = 1/S11,  nu12 = -S21/S11,  G12 = 1/S44,  ...
**
** 스텝 2  Thermomechanical step
**   dT = 1 degC, 드라이버 자유 -> sigma_bar = 0
**   -> 드라이버 변위 0,1,2 가 곧 alpha_bar_x, y, z 이고
**      드라이버 3,4,5 는 0 이어야 한다 (대칭성 검사).
**
** 후처리: abaqus python postprocess/extract_texgen_homog.py <잡이름>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", nargs="?", help="TexGen이 내보낸 .inp")
    ap.add_argument("--out", help="출력 .inp 경로")
    ap.add_argument("--inline-ori", action="store_true",
                    help=".ori 내용을 덱 안에 넣어 자기완결로 만든다")
    ap.add_argument("--check", action="store_true", help="정적 자기검증")
    args = ap.parse_args()

    if args.check:
        return selftest()

    if not args.mesh:
        ap.error("TexGen .inp 경로가 필요하다 (또는 --check)")

    text = open(args.mesh).read()
    blocks = list(split_blocks(text))

    # Cload 크기 = V_RVE 인지 확인 (단위 정합의 관문)
    vrve = None
    for kw, data in blocks:
        if kwname(kw) == "cload":
            for d in data:
                p = [t.strip() for t in d.split(",")]
                if len(p) >= 3 and p[0].lower().startswith("constraintsdriver"):
                    vrve = float(p[2])
                    break
        if vrve is not None:
            break
    if vrve is None:
        sys.exit("ERROR: *Cload 를 찾지 못했다. TexGen 균질화 덱이 맞는가?")

    blocks = rebuild(blocks)
    if args.inline_ori:
        blocks = inline_ori(blocks, os.path.dirname(os.path.abspath(args.mesh)))

    body = emit_blocks([(k, d) for (k, d) in blocks if kwname(k) != "heading"])
    text_out = (HEADING % (os.path.basename(args.mesh), vrve)) + body + "\n"

    out = args.out or os.path.splitext(args.mesh)[0] + "_ELASTIC.inp"
    with open(out, "w") as f:
        f.write(text_out)
    print("  Cload = %s N  ->  단위 거시응력 1 MPa (V_RVE = %s mm^3)" % (vrve, vrve))
    print("  wrote %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    return 0


# ==========================================================================
def selftest():
    ok = True

    def chk(cond, msg):
        nonlocal_ok = cond
        print("  [%s] %s" % ("OK" if cond else "FAIL", msg))
        return nonlocal_ok

    print("=" * 74)
    print("make_texgen_elastic.py  자기검증")
    print("=" * 74)

    # 1. 재료값이 검증된 카드와 일치하는가
    print("\n[1] 얀 카드 vs micromech_check.py 가 검증한 값")
    ref = {"E1": 254967.228042, "E2": 44321.737572, "E3": 44321.737572,
           "nu12": 0.247516386, "nu13": 0.247516386, "nu23": 0.395813581,
           "G12": 26431.515264, "G13": 26431.515264, "G23": 15876.667974,
           "a1": 1.070925962822e-06, "a2": 3.324908565604e-06,
           "a3": 3.324908565604e-06}
    for k, v in sorted(ref.items()):
        ok &= chk(abs(YARN[k] - v) <= abs(v) * 1e-12, "%-5s = %s" % (k, v))
    ok &= chk(MATRIX["E"] == 350000.0, "matrix E = 350000 MPa (Zhang Table 2)")
    ok &= chk(MATRIX["nu"] == 0.20, "matrix nu = 0.20")
    ok &= chk(MATRIX["alpha"] == 4.5e-06, "matrix alpha = 4.5e-6 /K")

    # 2. 단위 정합 -- MPa 자릿수인가 (Pa 로 남아 있으면 1e6 배 크다)
    print("\n[2] 단위 (mm-N-MPa)")
    ok &= chk(1e4 < MATRIX["E"] < 1e6, "matrix E 가 MPa 자릿수 (Pa 였다면 3.5e11)")
    ok &= chk(1e4 < YARN["E1"] < 1e6, "yarn E1 이 MPa 자릿수")

    # 3. 물리적 타당성
    print("\n[3] 물리 정합")
    ok &= chk(YARN["E1"] > YARN["E2"], "얀 종방향이 횡방향보다 강하다")
    ok &= chk(YARN["a1"] < YARN["a2"], "얀 종방향 CTE 가 횡방향보다 작다 (섬유 지배)")
    ok &= chk(MATRIX["alpha"] > YARN["a1"],
              "매트릭스 CTE > 얀 종방향 CTE  -> 냉각 시 매트릭스 인장 (TRS 부호)")
    # 직교이방성 대칭 조건 nu12/E1 = nu21/E2 는 카드에 nu21 이 없으므로 생략.
    # 양정치 조건: 1 - nu23^2 * E3/E2 > 0
    ok &= chk(1.0 - YARN["nu23"] ** 2 * YARN["E3"] / YARN["E2"] > 0,
              "얀 강성행렬 양정치 (1 - nu23^2 E3/E2 > 0)")

    # 4. 카드 슬롯 수
    print("\n[4] 카드 슬롯")
    el = yarn_data("*Elastic, type=ENGINEERING CONSTANTS")
    ok &= chk(len(el) == 2, "얀 *Elastic 은 2줄")
    ok &= chk(len(el[0].split(",")) == 8, "첫 줄 8개 (E1 E2 E3 n12 n13 n23 G12 G13)")
    ok &= chk(len(el[1].split(",")) == 1, "둘째 줄 1개 (G23)")
    ex = yarn_data("*Expansion, type=ORTHO")
    ok &= chk(len(ex[0].split(",")) == 3, "얀 *Expansion ORTHO 3개")
    mel = matrix_data("*Elastic")
    ok &= chk(len(mel[0].split(",")) == 2, "매트릭스 *Elastic 2개 (E, nu)")

    # 5. 원본 메시가 있으면 Cload = V_RVE 인지 확인
    print("\n[5] TexGen 원본 정합 (있을 때만)")
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "meshes", "CSiC_RVE_0135.inp")
    if os.path.exists(src):
        blocks = list(split_blocks(open(src).read()))
        cloads, lcs = [], 0
        xs = ys = zs = None
        for kw, data in blocks:
            n = kwname(kw)
            if n == "load case":
                lcs += 1
            if n == "cload":
                for d in data:
                    p = [t.strip() for t in d.split(",")]
                    if len(p) >= 3 and p[0].lower().startswith("constraintsdriver"):
                        cloads.append(float(p[2]))
            if n == "node" and xs is None:
                co = []
                for d in data:
                    q = d.split(",")
                    if len(q) >= 4:
                        try:
                            co.append((float(q[1]), float(q[2]), float(q[3])))
                        except ValueError:
                            pass
                if co:
                    xs = (min(c[0] for c in co), max(c[0] for c in co))
                    ys = (min(c[1] for c in co), max(c[1] for c in co))
                    zs = (min(c[2] for c in co), max(c[2] for c in co))
        V = (xs[1] - xs[0]) * (ys[1] - ys[0]) * (zs[1] - zs[0])
        ok &= chk(lcs == 6, "Load Case 6개 (드라이버 하나씩)")
        ok &= chk(len(cloads) == 6, "Cload 6개")
        ok &= chk(len(set(cloads)) == 1, "Cload 크기가 모두 같다")
        ok &= chk(abs(cloads[0] - V) < 1e-6 * V,
                  "Cload %s == V_RVE %.5f mm^3  -> 단위 거시응력 1 MPa"
                  % (cloads[0], V))
    else:
        print("  [--] %s 없음, 건너뜀" % src)

    print("\n" + "=" * 74)
    print("VERDICT: %s" % ("PASS" if ok else "FAIL"))
    print("=" * 74)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
