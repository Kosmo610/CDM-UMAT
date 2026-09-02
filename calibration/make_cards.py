#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_cards.py — 보정 그래프의 A0 노드 (파라미터 → 3온도 V2_0 덱)
================================================================
파라미터 dict 하나로 세 온도(RT23/T500/T1000)의 `*User Material` 카드를
동시에 갱신한다. 세 덱의 카드는 항상 동일하게 유지된다(온도독립 가정,
Zhang 2022 §3.2.3). 실행할 때마다 `calibration/ledger.json`에 새 iteration
항목을 기록해 시행착오를 추적한다.

사용법:
    # 다음 iteration 생성: 직전 채택 파라미터에서 knob만 바꿔서
    python3 calibration/make_cards.py --stage B --set Yt=70 --set S23=90 \
        --note "cooled-state 초기기울기 낮추기"

    # Stage A 기저 확인용 (소성 OFF, Eq.18 OFF)
    python3 calibration/make_cards.py --stage A --baseline

    # 덱은 건드리지 않고 카드 내용만 미리보기
    python3 calibration/make_cards.py --set Xt=2900 --dry-run

설정 가능한 knob 이름 (CALIBRATION_GUIDE.md §1과 동일):
    yarn  : Xt Xc Yt Yc S12 S13 S23 A1t A1c Att Atc G1t G1c Gtt Gtc
            X_PO rF K1 eta_y
    matrix: Gm_t Gm_c SY0 HISO eta_m
그 외 슬롯(탄성상수·CTE·cutback 등)은 검증 완료라 고정이며 바꿀 수 없다.
"""
import argparse
import copy
import json
import os
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ABAQUS = os.path.join(ROOT, "abaqus")
LEDGER = os.path.join(HERE, "ledger.json")

DECKS = ["ZHANG2022_RT23_V2_0.inp",
         "ZHANG2022_T500_V2_0.inp",
         "ZHANG2022_T1000_V2_0.inp"]

# ---------------------------------------------------------------------------
# 카드 정의: 고정 슬롯은 덱의 문자열을 그대로 보존(검증된 값 훼손 방지),
# knob 슬롯만 이름으로 치환한다. 슬롯 번호는 UMAT PROPS 순서(1-기준).
# ---------------------------------------------------------------------------
# yarn 38 slots — V2_0 기본값 (문자열 = 고정, ("이름", 기본값) = knob)
YARN = [
    "1.0", "254967.228042", "44321.737572", "44321.737572",
    "0.247516386", "0.247516386", "0.395813581", "26431.515264",
    "26431.515264", "15876.667974",
    ("Xt", 2835.0), ("Xc", 1956.0), ("Yt", 80.0), ("Yc", 350.0),
    ("S12", 120.0), ("S13", 120.0), ("S23", 100.0),
    ("A1t", 2.0), ("A1c", 2.0), ("Att", 2.0), ("Atc", 2.0),
    "0.99", "0.99", ("eta_y", 0.02),
    "0.10", "3.0", "0.25", "1.0", "1.15", "0.75", "0.50",
    ("G1t", 12.5), ("G1c", 12.5), ("Gtt", 0.0), ("Gtc", 0.0),
    ("X_PO", 700.0), ("rF", 3.0), ("K1", 8000.0),
]
# matrix 22 slots
MATRIX = [
    "2.0", "350000.0", "0.20", "310.0", "310.0", "0.0", "0.0", "0.99",
    "0.99", ("eta_m", 0.02), "0.10", "3.0", "0.25", "1.0",
    ("Gm_t", 0.031), ("Gm_c", 0.031),
    ("SY0", 250.0), ("HISO", 100000.0),
    "1.15", "0.75", "0.50", "30.0",
]

YARN_HEADER = "*User Material, constants=38"
MATRIX_HEADER = "*User Material, constants=22"

KNOB_DEFAULTS = {name: val for card in (YARN, MATRIX)
                 for slot in card if isinstance(slot, tuple)
                 for name, val in [slot]}

# Stage A 기저 확인: 소성 OFF, Eq.18 OFF (CALIBRATION_GUIDE §3 Stage A)
BASELINE_OVERRIDES = {"SY0": 0.0, "X_PO": 0.0}


def fmt(v):
    """카드 숫자 서식: 정수형 float은 'X.0', 그 외는 %g."""
    f = float(v)
    if f == int(f) and abs(f) < 1e15:
        return "%.1f" % f
    return "%g" % f


def render_card(slots, params, per_line=8):
    vals = [s if isinstance(s, str) else fmt(params[s[0]]) for s in slots]
    lines = [", ".join(vals[i:i + per_line])
             for i in range(0, len(vals), per_line)]
    return "\n".join(lines)


def render_blocks(params):
    yarn = YARN_HEADER + "\n" + render_card(YARN, params)
    matrix = MATRIX_HEADER + "\n" + render_card(MATRIX, params)
    return yarn, matrix


def replace_block(text, header, new_block, nlines):
    """덱 안의 `*User Material` 블록(헤더 + 데이터 nlines줄)을 교체."""
    idx = text.find(header)
    if idx < 0:
        raise RuntimeError("card header not found: " + header)
    if text.find(header, idx + 1) >= 0:
        raise RuntimeError("card header not unique: " + header)
    end = idx
    for _ in range(nlines + 1):          # 헤더 + 데이터 줄
        end = text.index("\n", end) + 1
    return text[:idx] + new_block + "\n" + text[end:]


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER) as f:
            return json.load(f)
    return {"targets_MPa": {"23": 128.45, "500": 179.42, "1000": 199.15},
            "iterations": []}


def save_ledger(led):
    with open(LEDGER, "w") as f:
        json.dump(led, f, indent=2, ensure_ascii=False)
        f.write("\n")


def latest_params(led):
    for it in reversed(led["iterations"]):
        if it.get("params"):
            return copy.deepcopy(it["params"])
    return dict(KNOB_DEFAULTS)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VAL",
                    help="knob 하나 변경 (여러 번 가능)")
    ap.add_argument("--stage", default=None, choices=list("ABCDE"),
                    help="현재 보정 단계 (ledger에 기록)")
    ap.add_argument("--baseline", action="store_true",
                    help="Stage A 기저: SY0=0, X_PO=0 강제")
    ap.add_argument("--note", default="", help="이번 반복의 의도 메모")
    ap.add_argument("--dry-run", action="store_true",
                    help="덱/ledger를 쓰지 않고 카드만 출력")
    args = ap.parse_args(argv)

    led = load_ledger()
    params = latest_params(led)

    changed = {}
    if args.baseline:
        for k, v in BASELINE_OVERRIDES.items():
            params[k] = v
            changed[k] = v
    for kv in args.set:
        if "=" not in kv:
            ap.error("--set 형식: NAME=VALUE (예: --set Yt=70)")
        name, val = kv.split("=", 1)
        if name not in KNOB_DEFAULTS:
            ap.error("unknown knob %r. 사용 가능: %s"
                     % (name, " ".join(sorted(KNOB_DEFAULTS))))
        params[name] = float(val)
        changed[name] = float(val)

    yarn_block, matrix_block = render_blocks(params)

    if args.dry_run:
        print(matrix_block)
        print()
        print(yarn_block)
        return 0

    for deck in DECKS:
        path = os.path.join(ABAQUS, deck)
        with open(path) as f:
            txt = f.read()
        txt = replace_block(txt, MATRIX_HEADER,
                            matrix_block, nlines=3)
        txt = replace_block(txt, YARN_HEADER,
                            yarn_block, nlines=5)
        with open(path, "w") as f:
            f.write(txt)
        print("updated", os.path.relpath(path, ROOT))

    it = {
        "iter": len(led["iterations"]) + 1,
        "date": datetime.date.today().isoformat(),
        "stage": args.stage,
        "changed": changed,
        "params": params,
        "note": args.note,
        "results": None,      # evaluate.py가 채움
        "loss": None,
        "gates": None,
    }
    led["iterations"].append(it)
    save_ledger(led)
    print("ledger: iteration %d 기록 (stage %s, changed: %s)"
          % (it["iter"], args.stage or "-",
             ", ".join("%s=%s" % kv for kv in changed.items()) or "none"))
    print("다음: 세 온도 Abaqus 실행 -> extract_ss_curve.py -> "
          "calibration/evaluate.py Job-*_ss.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
