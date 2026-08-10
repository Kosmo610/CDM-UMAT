# -*- coding: utf-8 -*-
"""
extract_texgen_homog.py   (abaqus python 으로 실행)
==================================================
TexGen 원생 균질화 덱(make_texgen_elastic.py 산출)의 ODB에서
컴플라이언스 S_bar, 강성 C_bar, 공학상수, 열팽창 alpha_bar 를 뽑는다.

    abaqus python postprocess/extract_texgen_homog.py <잡이름>

읽는 것
-------
스텝 1 "Isothermal linear perturbation step"
    Load0..Load5 = 프레임 6개.  각 케이스가 드라이버 j 에 Cload = V_RVE 를
    걸었으므로 거시응력은 sigma_j = 1 MPa, 나머지는 0.
    드라이버 자유도 = 거시 변형률이므로

        S_bar[i][j] = U(driver_i)  in load case j            [1/MPa]

    즉 프레임 하나가 컴플라이언스의 한 **열**이다. 역행렬이 필요 없다.

스텝 2 "Thermomechanical step"
    dT = 1 degC, 드라이버 자유 -> sigma_bar = 0

        alpha_bar_i = U(driver_i)                            [1/degC]

    i = 3,4,5 (전단) 는 0 이어야 한다.  0이 아니면 방향 매핑이나 메시
    대칭성에 문제가 있다는 신호다.

드라이버 매핑 (abaqus/meshes/README.md 에서 검증됨)
    0 = e_x   1 = e_y   2 = e_z   3 = e_xy   4 = e_xz   5 = e_yz
    전단 드라이버의 자유도 값은 **공학 전단변형률** gamma 다.
    구속식이 면 하나에만 변위 점프를 주는 단순전단이기 때문이다
    (Delta u_x across y-faces = H * D3  ->  D3 = du_x/dy = gamma_xy).
    따라서 G_xy = 1 / S_bar[3][3] 로 바로 나온다.

공학상수 (응력 제어라 컴플라이언스에서 직접)
    E1 = 1/S11        nu12 = -S21/S11      nu13 = -S31/S11
    E2 = 1/S22        nu21 = -S12/S22      nu23 = -S32/S22
    E3 = 1/S33        nu31 = -S13/S33      nu32 = -S23/S33
    G12 = 1/S44       G13  = 1/S55         G23  = 1/S66

    ** 이 E1 은 EasyPBC 의 E11 과 같은 정의다(단축 응력).
       ZHANG 덱의 HOM_E11 은 변형률 제어라 C_bar_11 이 나오며 5~20 %
       더 크다.  비교 전에 반드시 이 표를 거칠 것. **

검산
----
  * S_bar 대칭성:  S[i][j] 와 S[j][i] 가 같아야 한다 (Maxwell-Betti).
    비대칭이 크면 해석이 수렴하지 않았거나 구속식이 잘못된 것이다.
  * 자유 드라이버 반력: 하중을 안 건 드라이버의 RF 는 0 이어야 한다.
    0이 아니면 PBC가 인공 구속을 넣고 있다는 뜻이다.
  * 평직 대칭성: E1 ~ E2, alpha_x ~ alpha_y.
"""
from __future__ import print_function

import os
import sys

try:
    from odbAccess import openOdb
except ImportError:
    sys.exit("이 스크립트는 'abaqus python' 으로 실행해야 한다 (odbAccess 필요).")

try:
    import numpy as np
except ImportError:
    np = None

NDRV = 6
DRIVER_SET = "CONSTRAINTSDRIVER%d"
LABELS = ["xx", "yy", "zz", "xy", "xz", "yz"]
ELAS_STEP_HINT = "isothermal"
THERM_STEP_HINT = "thermomechanical"


def driver_labels(odb):
    """드라이버 6개의 절점 라벨을 어셈블리 절점집합에서 읽는다."""
    out = []
    ra = odb.rootAssembly
    for i in range(NDRV):
        name = DRIVER_SET % i
        if name not in ra.nodeSets:
            sys.exit("ERROR: 절점집합 %s 이 ODB에 없다. TexGen 덱이 맞는가?" % name)
        nodes = ra.nodeSets[name].nodes
        flat = []
        for grp in nodes:
            for n in grp:
                flat.append(n.label)
        if len(flat) != 1:
            sys.exit("ERROR: %s 에 절점이 %d개다. 1개여야 한다." % (name, len(flat)))
        out.append(flat[0])
    return out


def read_driver(frame, labels, var):
    """프레임에서 드라이버 6개의 var(U 또는 RF) 자유도 1 값을 읽는다."""
    if var not in frame.fieldOutputs:
        return None
    fo = frame.fieldOutputs[var]
    got = {}
    for v in fo.values:
        if v.nodeLabel in labels:
            got[v.nodeLabel] = v.data[0]          # 자유도 1
    return [got.get(l) for l in labels]


def find_step(odb, hint):
    for name in odb.steps.keys():
        if hint in name.lower():
            return odb.steps[name]
    return None


def inv6(M):
    if np is not None:
        return np.linalg.inv(np.array(M)).tolist()
    # 가우스-조던 (numpy 없을 때)
    n = 6
    A = [list(M[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-300:
            sys.exit("ERROR: S_bar 가 특이행렬이다.")
        A[c], A[p] = A[p], A[c]
        d = A[c][c]
        A[c] = [x / d for x in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0.0:
                f = A[r][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [row[n:] for row in A]


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: abaqus python extract_texgen_homog.py <잡이름>")
    job = sys.argv[1]
    if job.lower().endswith(".odb"):
        job = job[:-4]
    path = job + ".odb"
    if not os.path.exists(path):
        sys.exit("ERROR: %s 가 없다." % path)

    odb = openOdb(path, readOnly=True)
    labels = driver_labels(odb)
    print("드라이버 절점 라벨: %s" % labels)

    # ---------------- 스텝 1: 컴플라이언스 ----------------
    st = find_step(odb, ELAS_STEP_HINT)
    if st is None:
        sys.exit("ERROR: '%s' 를 포함하는 스텝이 없다. 스텝: %s"
                 % (ELAS_STEP_HINT, list(odb.steps.keys())))
    frames = [f for f in st.frames]
    # 프레임 0 이 기준상태(빈 프레임)면 버린다
    if len(frames) == NDRV + 1:
        frames = frames[1:]
    if len(frames) != NDRV:
        print("경고: 프레임이 %d개다 (기대 %d). 순서를 확인할 것."
              % (len(frames), NDRV))
        for k, f in enumerate(frames):
            print("   frame %d: %s" % (k, f.description))

    S = [[0.0] * NDRV for _ in range(NDRV)]
    print("\n[자유 드라이버 반력 검사]  하중을 안 건 드라이버의 RF 는 0 이어야 한다")
    for j, f in enumerate(frames[:NDRV]):
        u = read_driver(f, labels, "U")
        if u is None or any(x is None for x in u):
            sys.exit("ERROR: load case %d 에서 U 를 못 읽었다." % j)
        for i in range(NDRV):
            S[i][j] = u[i]
        rf = read_driver(f, labels, "RF")
        if rf is not None and not any(x is None for x in rf):
            free = max(abs(rf[i]) for i in range(NDRV) if i != j)
            print("  Load%d (%-2s):  RF[구동] = %+.4f N   RF[자유] 최대 = %.2e N   %s"
                  % (j, LABELS[j], rf[j], free,
                     "OK" if free < 1e-3 * max(abs(rf[j]), 1e-30) else "** 확인 필요 **"))

    print("\n[S_bar 대칭성]  Maxwell-Betti: S[i][j] == S[j][i]")
    worst, wij = 0.0, (0, 0)
    for i in range(NDRV):
        for j in range(i + 1, NDRV):
            sc = max(abs(S[i][j]), abs(S[j][i]), 1e-30)
            r = abs(S[i][j] - S[j][i]) / sc
            if r > worst:
                worst, wij = r, (i, j)
    print("  최대 비대칭 %.3e  (S[%d][%d] vs S[%d][%d])   %s"
          % (worst, wij[0], wij[1], wij[1], wij[0],
             "OK" if worst < 1e-3 else "** 확인 필요 **"))

    print("\n[S_bar]  1/MPa")
    for i in range(NDRV):
        print("  " + "  ".join("%12.5e" % S[i][j] for j in range(NDRV)))

    C = inv6(S)
    print("\n[C_bar = S_bar^-1]  MPa   <- Ch.5 거시 강성 카드, ZHANG 덱 HOM_* 와 비교 대상")
    for i in range(NDRV):
        print("  " + "  ".join("%12.5e" % C[i][j] for j in range(NDRV)))

    E1, E2, E3 = 1.0 / S[0][0], 1.0 / S[1][1], 1.0 / S[2][2]
    nu12, nu13 = -S[1][0] / S[0][0], -S[2][0] / S[0][0]
    nu21, nu23 = -S[0][1] / S[1][1], -S[2][1] / S[1][1]
    nu31, nu32 = -S[0][2] / S[2][2], -S[1][2] / S[2][2]
    G12, G13, G23 = 1.0 / S[3][3], 1.0 / S[4][4], 1.0 / S[5][5]

    # ---------------- 스텝 2: CTE ----------------
    a = [float("nan")] * NDRV
    st2 = find_step(odb, THERM_STEP_HINT)
    if st2 is None:
        print("\n경고: 열 스텝을 찾지 못했다. alpha_bar 는 건너뛴다.")
    else:
        f = st2.frames[-1]
        u = read_driver(f, labels, "U")
        if u is not None and not any(x is None for x in u):
            a = u
            print("\n[전단 CTE 검사]  alpha_xy, alpha_xz, alpha_yz 는 0 이어야 한다")
            sc = max(abs(a[0]), abs(a[1]), abs(a[2]), 1e-30)
            for i in (3, 4, 5):
                print("  alpha_%-2s = %+.4e   (수직 CTE의 %.2f %%)   %s"
                      % (LABELS[i], a[i], 100.0 * abs(a[i]) / sc,
                         "OK" if abs(a[i]) < 0.01 * sc else "** 확인 필요 **"))

    # ---------------- 보고 ----------------
    print("\n" + "=" * 74)
    print("균질화 유효물성   (단위 mm, N, MPa, degC)")
    print("=" * 74)
    rows = [
        ("E_xx", E1, "MPa"), ("E_yy", E2, "MPa"), ("E_zz", E3, "MPa"),
        ("G_xy", G12, "MPa"), ("G_xz", G13, "MPa"), ("G_yz", G23, "MPa"),
        ("nu_xy", nu12, "-"), ("nu_xz", nu13, "-"), ("nu_yz", nu23, "-"),
        ("nu_yx", nu21, "-"), ("nu_zx", nu31, "-"), ("nu_zy", nu32, "-"),
        ("alpha_x", a[0], "1/degC"), ("alpha_y", a[1], "1/degC"),
        ("alpha_z", a[2], "1/degC"),
    ]
    for n, v, u in rows:
        print("  %-9s %16.6g  %s" % (n, v, u))

    print("\n[평직 대칭성 검사]")
    for n, p, q in (("E_xx vs E_yy", E1, E2), ("alpha_x vs alpha_y", a[0], a[1]),
                    ("G_xz vs G_yz", G13, G23)):
        sc = max(abs(p), abs(q), 1e-30)
        d = abs(p - q) / sc * 100.0
        print("  %-20s 차이 %6.3f %%   %s" % (n, d, "OK" if d < 5.0 else "** 확인 필요 **"))

    out = job + "_homog.csv"
    with open(out, "w") as fh:
        fh.write("quantity,value,unit\n")
        for n, v, u in rows:
            fh.write("%s,%.10g,%s\n" % (n, v, u))
        fh.write("\nS_bar (1/MPa)\n")
        for i in range(NDRV):
            fh.write(",".join("%.10g" % S[i][j] for j in range(NDRV)) + "\n")
        fh.write("\nC_bar (MPa)\n")
        for i in range(NDRV):
            fh.write(",".join("%.10g" % C[i][j] for j in range(NDRV)) + "\n")
    print("\n  -> %s 에 저장했다." % out)
    odb.close()


if __name__ == "__main__":
    main()
