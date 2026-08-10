#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate.py — 보정 그래프의 A3+A4 노드 (곡선 → 지표·손실·게이트 판정)
====================================================================
`extract_ss_curve.py`가 뽑은 *_ss.csv (eps_xx, sigma_xx_MPa)를 읽어

  1. 온도별 지표 계산: 극한강도 sigma_ult, 초기기울기 E0, 피크 변형률
  2. Table 3 목표 대비 스칼라 손실(loss) 계산  ← 조건부 엣지의 판정값
  3. Stage 게이트 PASS/FAIL 판정 (CALIBRATION_GUIDE §3의 A–E)
  4. ledger.json의 최신 iteration에 결과 기록
  5. 다음에 돌릴 knob 제안 출력 (GUIDE §2의 지배 파라미터 표)

사용법:
    python3 calibration/evaluate.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv
    python3 calibration/evaluate.py Job-*_ss.csv --stage C --tol 0.05
    python3 calibration/evaluate.py ... --no-ledger    # 원장 기록 없이 평가만

표준 Python 3만 필요(matplotlib 불필요). 그림 비교는 기존
postprocess/plot_compare.py를 그대로 쓰면 된다.
"""
import argparse
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.json")

TARGETS = {23: 128.45, 500: 179.42, 1000: 199.15}      # Table 3 (paper sim)
EXPERIM = {23: (116.17, 8.78), 500: (160.19, 14.83), 1000: (173.28, 12.94)}
APPLIED_STRAIN = {23: 0.0015, 500: 0.0032, 1000: 0.0048}  # 인장스텝 적용변형

# GUIDE §2: 관측량 -> 지배 knob (판정 후 제안 출력용)
KNOB_HINTS = [
    ("초기기울기(E0)가 논문 곡선보다 높음", "Yt/S23을 낮춰 냉각 예비손상 증가"),
    ("초기기울기(E0)가 낮음", "Yt/S23을 올려 예비손상 감소"),
    ("23C 극한강도가 목표(128.45)보다 낮음", "Xt 또는 X_PO 상향"),
    ("23C 극한강도가 높음", "Xt 또는 X_PO 하향"),
    ("파단이 너무 취성적(급락)", "rF·X_PO 상향, K1 하향으로 tail 연장"),
    ("잔류변형 부족(곡선이 너무 선형)", "SY0 하향 또는 HISO 하향"),
    ("온도 추세(23<500<1000)가 어긋남", "카드가 아닌 냉각 수렴/CTE 점검 (GUIDE §2)"),
]


def temp_of(path):
    b = os.path.basename(path).upper()
    for T, tag in [(1000, "1000"), (500, "500"), (23, "RT23"), (23, "_23")]:
        if tag in b:
            return T
    return None


def load_curve(path):
    eps, sig = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            eps.append(float(row["eps_xx"]))
            sig.append(float(row["sigma_xx_MPa"]))
    if len(eps) < 3:
        raise RuntimeError("curve too short: " + path)
    return eps, sig


def metrics(eps, sig):
    """극한강도, 초기기울기(피크 이전 초반 20 % 구간 최소제곱), 피크 변형률."""
    ult = max(sig)
    ipk = sig.index(ult)
    n0 = max(3, int(0.2 * (ipk + 1)))
    xs, ys = eps[:n0], sig[:n0]
    mx, my = sum(xs) / n0, sum(ys) / n0
    den = sum((x - mx) ** 2 for x in xs)
    e0 = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den else 0.0
    return {"sigma_ult_MPa": round(ult, 2),
            "E0_MPa": round(e0, 0),
            "eps_at_peak": round(eps[ipk], 6),
            "eps_end": round(eps[-1], 6),
            "completed": eps[-1] >= 0.95 * max(eps)}


def evaluate(files, stage, tol):
    per_T, missing = {}, []
    for p in files:
        T = temp_of(p)
        if T is None:
            print("skip (온도 태그 인식 불가):", p)
            continue
        eps, sig = load_curve(p)
        per_T[T] = metrics(eps, sig)
        # 해석이 적용변형 근처까지 갔는지 (Stage A 게이트)
        per_T[T]["reached_applied"] = eps[-1] >= 0.9 * APPLIED_STRAIN[T]
    for T in TARGETS:
        if T not in per_T:
            missing.append(T)

    # 스칼라 손실: 목표 대비 상대오차 RMS (있는 온도만)
    errs = [(per_T[T]["sigma_ult_MPa"] - TARGETS[T]) / TARGETS[T]
            for T in per_T if T in TARGETS]
    loss = round(math.sqrt(sum(e * e for e in errs) / len(errs)), 4) if errs else None

    def rel_ok(T):
        return (T in per_T and
                abs(per_T[T]["sigma_ult_MPa"] - TARGETS[T]) / TARGETS[T] <= tol)

    gates = {
        # A: 세 해석 모두 적용변형까지 수렴·완주했는가 (안정성)
        "A": not missing and all(per_T[T]["reached_applied"] for T in per_T),
        # B: 초기기울기·비선형은 논문 '그림' 기준 → 수치 게이트는 완주 여부만,
        #    E0 값을 출력하니 논문 Fig.11과 눈으로 비교해 판단할 것
        "B": 23 in per_T and per_T[23]["reached_applied"],
        # C: 23 °C 극한강도가 목표 ±tol 이내
        "C": rel_ok(23),
        # D: 곡선 형상(잔류변형) — 수치 목표 없음, C 유지가 전제
        "D": rel_ok(23),
        # E: 세 온도 모두 ±tol 이내 + 단조증가 추세
        "E": (all(rel_ok(T) for T in TARGETS) and not missing and
              per_T[23]["sigma_ult_MPa"] < per_T[500]["sigma_ult_MPa"]
              < per_T[1000]["sigma_ult_MPa"]),
    }
    return per_T, missing, loss, gates


def print_report(per_T, missing, loss, gates, stage, tol):
    print("=" * 64)
    print("%-7s %10s %10s %9s %12s %10s" %
          ("T[C]", "sim[MPa]", "목표[MPa]", "오차[%]", "E0[GPa]", "완주"))
    print("-" * 64)
    for T in sorted(per_T):
        m = per_T[T]
        tgt = TARGETS.get(T)
        err = (m["sigma_ult_MPa"] - tgt) / tgt * 100 if tgt else float("nan")
        print("%-7d %10.2f %10.2f %8.2f%% %12.1f %10s" %
              (T, m["sigma_ult_MPa"], tgt or 0, err, m["E0_MPa"] / 1000.0,
               "yes" if m["reached_applied"] else "NO"))
    for T in missing:
        print("%-7d %10s %10.2f       (곡선 없음)" % (T, "-", TARGETS[T]))
    print("-" * 64)
    print("loss (상대오차 RMS): %s   tol: ±%.0f%%" %
          (loss, tol * 100))
    print("게이트:", "  ".join("%s:%s" % (s, "PASS" if ok else "fail")
                              for s, ok in sorted(gates.items())))
    if stage:
        print(">> Stage %s 판정: %s" %
              (stage, "PASS — 다음 단계로" if gates[stage]
               else "FAIL — knob 조정 후 재실행"))
    print()
    print("다음 knob 제안 (CALIBRATION_GUIDE §2):")
    for sym, act in KNOB_HINTS:
        print("  - %s -> %s" % (sym, act))
    print("=" * 64)


def update_ledger(per_T, missing, loss, gates, stage):
    if not os.path.exists(LEDGER):
        print("(ledger.json 없음 — make_cards.py를 먼저 실행하면 기록됩니다)")
        return
    with open(LEDGER) as f:
        led = json.load(f)
    if not led["iterations"]:
        print("(ledger에 iteration 없음 — 기록 생략)")
        return
    it = led["iterations"][-1]
    it["results"] = {str(T): per_T[T] for T in per_T}
    it["loss"] = loss
    it["gates"] = {k: bool(v) for k, v in gates.items()}
    if stage and it.get("stage") is None:
        it["stage"] = stage
    with open(LEDGER, "w") as f:
        json.dump(led, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("ledger: iteration %d 결과 기록 (loss=%s)" % (it["iter"], loss))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("csv", nargs="+", help="*_ss.csv (extract_ss_curve.py 출력)")
    ap.add_argument("--stage", default=None, choices=list("ABCDE"))
    ap.add_argument("--tol", type=float, default=0.05,
                    help="강도 상대오차 허용치 (기본 0.05 = ±5%%)")
    ap.add_argument("--no-ledger", action="store_true")
    args = ap.parse_args(argv)

    per_T, missing, loss, gates = evaluate(args.csv, args.stage, args.tol)
    if not per_T:
        print("읽을 수 있는 곡선이 없습니다."); return 1
    print_report(per_T, missing, loss, gates, args.stage, args.tol)
    if not args.no_ledger:
        update_ledger(per_T, missing, loss, gates, args.stage)
    # 종료코드로도 게이트 전달 (셸 스크립트 체이닝용)
    if args.stage:
        return 0 if gates[args.stage] else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
