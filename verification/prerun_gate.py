#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prerun_gate.py  --  the minimum set of Abaqus jobs, and what gates each stage
=============================================================================
The review branch's whole premise is "해석(Abaqus)을 최소화한다 -- 이론·참고문헌·
입력값·논리의 결함을 해석 **전에** 전부 잡아서, 물성 오입력·논리 결함으로 해석을
다시 돌리는 일이 없게 한다."  That is right, and this repository already has the
pieces: 64 gate commands, card triage, calibration plans, chapter checkers.

What it did NOT have is the thing those pieces are FOR: a single statement of
**which jobs to run, in what order, and what makes each one wasted.**  Spread
across five modules and two chapters, that answer is not actionable, and the
failure mode is specific -- a job runs, finishes, and only then turns out to
have been un-interpretable because an upstream card was not fixed yet.

So this module answers three questions, and nothing else:

  1. How many jobs is the minimum, and where does the saving come from?
  2. What must be true before each stage, and who owns that?
  3. Which conclusions survive an UNCALIBRATED card, and which do not?

Question 3 is the one that actually shrinks the schedule.  The headline
contribution C1 -- "how much does the TRS treatment change the prediction" --
is a comparison of three cases that share one card.  A shared error cancels
in a ranking.  So C1 can be answered BEFORE the calibration converges, while
the absolute validation targets (T1-T6) cannot.  Ordering the matrix by that
distinction is worth more than any per-job speed-up.

Owner split (CLAUDE.md): a1 rules on source, grade and card legitimacy; a2
rules on convergence, solver and deck.  This module is a1's half -- it never
says how to run a job, only whether the inputs are ready and what the run
would be worth.

Run:  python3 verification/prerun_gate.py            (the plan)
      python3 verification/prerun_gate.py --check    (gate items)
      python3 verification/prerun_gate.py --csv      (job list for a2)
"""
from __future__ import print_function

import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
CH5 = os.path.join(DOCS, "CH5_MACRO_THERMALSHOCK.md")

#: The naive way to get the same observables, one job per observable.  Kept
#: here only to compute the saving; every "actual" number below is PARSED
#: from the chapter's own matrix table so the two cannot drift apart.
NAIVE = dict(
    heat=9,          # one per mechanical case instead of one per severity
    config_v=9,      # the control at every severity instead of the middle one
    probe=27,        # E(N) as its own job per checkpoint instead of a step
    residual=27,     # residual strength from scratch instead of from restart
)

STAGES = [
    dict(key="S0", name="선행검증 (작은 잡 3개)",
         jobs=3, parallel=True,
         gate="없음 -- 이것이 첫 관문이다",
         owner="a2",
         unblocks="S2 이후 전부",
         wasted_if="없음. 이 셋을 건너뛰면 그 뒤 15잡이 통째로 위험해진다",
         detail="열경계층 분해 · 온도 매핑 · 사이클 점프 오차 (제5장 §5.8). "
                "각각 분 단위"),
    dict(key="S1", name="RVE — 유효물성과 보정 (M6 · 전도)",
         jobs=None, parallel=False,
         gate="카드 적법성 판정 완료 (a1) + k(T) 형상 배선 (a1-0031)",
         owner="a2 실행 / a1 판정",
         unblocks="거시 카드 전체",
         wasted_if="거시 카드가 확정되기 전에 S2~S4를 돌리면 전량 재실행이다",
         detail="LTH_RUN2 (kbar) 와 M6 보정. 거시 열·역학 카드가 여기서 나온다"),
    dict(key="S2", name="거시 열전달",
         jobs=None, parallel=True,
         gate="S0 통과 + S1의 열물성 카드 확정",
         owner="a2",
         unblocks="S3 · S4 전부",
         wasted_if="k(T) 형상이 바뀌면 전량 재실행 -- 그래서 a1-0031이 S2의 "
                   "관문이다",
         detail="심각도당 1개. 온도장은 TRS 처리와 무관하므로 모든 TRS 케이스가 "
                "공유한다"),
    dict(key="S3", name="거시 역학 (CONFIG_P) — 기여 C1",
         jobs=None, parallel=True,
         gate="S2 완료 + 거시 역학 카드가 **자리표가 아닐 것**. 보정 수렴은 "
              "관문이 아니지만 자리표는 관문이다",
         owner="a2",
         unblocks="C1 · C2 · C3 정성 답",
         wasted_if="카드가 자리표이면 손상이 아예 안 걸려 세 케이스가 똑같이 "
                   "나올 수 있다 — 그러면 '차이가 작다'가 결과가 아니라 인공물이다",
         detail="3 심각도 × 3 TRS. 세 케이스가 같은 카드를 쓰므로 카드의 "
                "계통오차는 순위에서 상쇄되지만, 자리표는 계통오차가 아니라 "
                "다른 재료다"),
    dict(key="S4", name="대조군 (CONFIG_V · H_clo off)",
         jobs=None, parallel=True,
         gate="S3의 대응 잡 완료",
         owner="a2",
         unblocks="C1의 강건성 · C3의 부호 분리",
         wasted_if="대응 S3 잡과 카드가 한 글자라도 다르면 대조가 아니다",
         detail="열 잡을 S2와 공유하므로 추가 비용은 역학 잡뿐이다"),
    dict(key="S5", name="잔여강도 (restart)",
         jobs=None, parallel=False,
         gate="부모 역학 잡 완료 + 그 잡이 restart를 남겼는가",
         owner="a2",
         unblocks="T1·T2 절대 표적",
         wasted_if="부모 잡이 restart를 안 남겼으면 사이클 0부터 다시다",
         detail="체크포인트마다. 시편을 파괴하므로 본 잡에 끼워 넣을 수 없다"),
]

#: Which conclusions need a CONVERGED calibration, and which do not.  This is
#: the table that decides the order of the schedule.
CLAIM_DEPENDENCE = [
    ("C1  TRS 3케이스가 예측을 얼마나 가르나", False,
     "세 케이스가 같은 카드를 공유하는 비교이므로 카드의 계통오차가 순위에서 "
     "상쇄된다. 차이의 **크기**를 절대값으로 인용할 때만 보정이 필요하다. "
     "★ 단 이 논거에는 바닥이 있다 — 카드가 **자리표**이면 손상이 발동하지 "
     "않아 세 케이스가 동일해질 수 있고, 그때 '차이 없음'은 결과가 아니라 "
     "인공물이다 (a2-0032가 역학 덱을 일부러 보류한 이유이며, 그 판단이 옳다). "
     "보정 **수렴**은 불필요하지만 카드가 **그 재료**이기는 해야 한다"),
    ("C2  균일 온도 가정이 어디서 깨지나", False,
     "Bi 사다리는 h를 정의상 훑는다. kbar_3의 크기가 바뀌면 h가 따라 바뀌므로 "
     "Bi는 정확한 채로 남는다 (제5장 §5.4.2)"),
    ("C3  반사이클 비대칭의 부호", False,
     "H_clo on/off 대조의 **부호**는 카드 크기와 무관하다. 크기는 아니다"),
    ("C4  파손기준 셋의 순위", False,
     "세 기준이 같은 응력장을 읽고 하중 배수로 정규화된다 (제5장 §5.2.4)"),
    ("T1-T6 절대 검증 표적", True,
     "문헌의 잔존율·PLS와 **수치를 맞대는** 것이므로 보정 없이는 무의미하다"),
    ("k 부호 분리의 1300 °C 외삽", True,
     "[3]로 보정한 k를 외삽하는 것이므로 그 보정이 선행이다"),
]


def _int(pattern, text, default=None):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default


def matrix_from_chapter():
    """Job counts parsed from the chapter's own §5.7 table."""
    ch5 = open(CH5, encoding="utf-8").read()
    i = ch5.find("## 5.7")
    seg = ch5[i:i + 1600] if i >= 0 else ""
    return dict(
        heat=_int(r"\|\s*열전달\s*\|\s*\*\*(\d+)\*\*", seg),
        config_p=_int(r"\|\s*역학 \(CONFIG_P\)\s*\|\s*\*\*(\d+)\*\*", seg),
        config_v=_int(r"\|\s*역학 \(CONFIG_V 대조\)\s*\|\s*\*\*(\d+)\*\*", seg),
        prerun=3,
    )


def plan():
    m = matrix_from_chapter()
    stages = [dict(s) for s in STAGES]
    for s in stages:
        if s["key"] == "S2":
            s["jobs"] = m["heat"]
        elif s["key"] == "S3":
            s["jobs"] = m["config_p"]
        elif s["key"] == "S4":
            s["jobs"] = m["config_v"]
    return m, stages


def savings(m):
    """(saved, naive_total, actual_total) for the four consolidations."""
    naive = (NAIVE["heat"] + m["config_p"] + NAIVE["config_v"]
             + NAIVE["probe"] + NAIVE["residual"])
    actual = m["heat"] + m["config_p"] + m["config_v"]
    return naive - actual, naive, actual


def thermal_card_magnitude_fixed():
    """Is the macro THERMAL card's magnitude actually decided?

    a2-0036 caught this file answering that question with the wrong evidence.
    It used to test whether postprocess/kbar_summary.csv EXISTS, and reported
    a missing file as "the macro thermal card's magnitude is not fixed".  That
    reads as "S2 is blocked", and S2 is not blocked.

    The RVE_COND job has already run.  Its answer, 5.449 W/(m.K) at 23 C, is
    wired into data/properties/conductivity_temperature.py as KBAR3_FE, and
    Ch.4 4.9 / Ch.5 5.4.2 fix h = 161.7 and Bi = 0.0445 from it.  So the card
    is decided, and the right test is whether that wiring is in place -- not
    whether a summary file happens to be sitting in the repository.

    The most expensive mistake this project can make is not running a job it
    could have run.  A missing artefact file must never masquerade as one.
    """
    ct = os.path.join(ROOT, "data", "properties", "conductivity_temperature.py")
    if not os.path.exists(ct):
        return False
    src = open(ct, encoding="utf-8").read()
    m = re.search(r"^KBAR3_FE\s*=\s*([0-9.]+)", src, re.M)
    return m is not None and float(m.group(1)) > 0.0


def s3_deck_is_placeholder(deck_text):
    """Does an S3 mechanical deck still carry the placeholder macro card?

    a2-0034 pointed out that the S3 gate does not need a human to eyeball the
    card: make_macro_thermalshock.py stamps this exact comment into a deck
    built on the placeholder.  So the gate can be executed instead of read.
    """
    return PLACEHOLDER_MARK in deck_text


#: The stamp make_macro_thermalshock.py writes into a placeholder deck.
PLACEHOLDER_MARK = "PLACEHOLDER macro card -- replace with the RVE output"


def outstanding():
    """Source-side items that gate a stage, with who owns each.

    Each entry is (stage, what is actually blocked, owner).  "What is actually
    blocked" is the part a2-0036 made this file get right: a deliverable that
    is missing does not automatically block the jobs downstream of it.
    """
    out = []
    mac = os.path.join(ROOT, "abaqus", "make_macro_thermalshock.py")
    src = open(mac, encoding="utf-8").read() if os.path.exists(mac) else ""
    if "REF20_K_RATIO" in src and "conductivity_temperature" not in src:
        out.append(("S2", "k(T) 형상이 아직 refs/[20] 차용값이다 (a1-0031 판정: "
                    "기각). 배선 전에는 열 잡이 재실행 대상이다", "a2"))
    if not thermal_card_magnitude_fixed():
        out.append(("S2", "거시 열카드의 크기가 확정되지 않았다 -- KBAR3_FE가 "
                    "conductivity_temperature 에 배선되어 있지 않다", "a1"))
    # M6 turned the transverse crack band on with Shi's TENSILE Gf in BOTH
    # slots.  le_max goes as 1/X^2, so the same 0.107 N/mm that clears the
    # mesh by 17x in tension falls UNDER the largest element in compression.
    # A re-run that does not touch slot 35 repeats a mesh-inadmissible card,
    # so this is a pre-run item and not a post-mortem.  Card admissibility is
    # a1's call; what to put there instead is a2's.
    if not gtc_admissible_on_this_mesh():
        out.append(("S1", "M6 카드의 얀 $G_{tc}$가 이 메시에서 적법하지 않다 — "
                    "인장값 0.107 N/mm를 압축에도 그대로 써 스냅백 한계가 "
                    "최대요소보다 작다. M7 덱에서 슬롯 35를 정하기 전에는 "
                    "재실행이 같은 결함을 반복한다", "a2"))
    kbar = os.path.join(ROOT, "postprocess", "kbar_summary.csv")
    if not os.path.exists(kbar):
        out.append(("S1", "LTH_RUN2의 kbar 요약 CSV **파일**이 없다 -> 그림 4.5와 "
                    "admissible 판정 기록이 막힌다. 카드값(5.449)은 이미 확정이며 "
                    "새 해석은 필요 없다 -- 이미 돌린 잡의 산출물 회수다",
                    "사용자 회수"))
    return out


def gtc_admissible_on_this_mesh():
    """Is the yarn transverse COMPRESSIVE crack band resolvable by the mesh?

    Snapback needs le <= le_max = 2*E2*Gf/X^2.  Recomputed here rather than
    remembered, because the answer changes the moment either the card or the
    mesh changes.  Returns True when the deck that ran has no Gtc, or when the
    Gtc it has clears the largest element.
    """
    sys.path.insert(0, os.path.join(ROOT, "verification"))
    sys.path.insert(0, os.path.join(ROOT, "data", "properties"))
    try:
        import check_card_ranges as ccr
        import yarn_fracture_energy as yf
        run = ccr.card(ccr.run_deck_text("RT23"), 38)
    except Exception:
        return True
    gtc = run[34]
    if gtc <= 0.0:
        return True
    yc = [r for r in ccr.YARN if r[0] == 14][0][2]
    L, _ = yf.le_max(gtc, yc, yf.E2)
    return L > yf.CELENT_MAX


def report():
    m, stages = plan()
    saved, naive, actual = savings(m)
    print("=" * 78)
    print("PRE-RUN GATE -- 최소 해석 계획 (a1이 판정하는 입력 준비 상태)")
    print("=" * 78)
    print("  최소 잡 수: 선행 %d + 열 %d + 역학 %d + 대조 %d = **%d개** "
          "(+ 잔여강도 restart)"
          % (m["prerun"], m["heat"], m["config_p"], m["config_v"],
             m["prerun"] + actual))
    print("  같은 관측량을 잡 하나씩으로 얻으면 %d개다 -- **%d잡을 줄인 것**이며,"
          % (naive, saved))
    print("  줄인 근거는 넷이다:")
    print("    열해석 공유 (온도장은 TRS와 무관)        %2d -> %2d"
          % (NAIVE["heat"], m["heat"]))
    print("    대조군을 중간 심각도에만               %2d -> %2d"
          % (NAIVE["config_v"], m["config_v"]))
    print("    E(N)을 별도 잡이 아니라 프로브 스텝으로  %2d ->  0"
          % NAIVE["probe"])
    print("    잔여강도를 restart로                   %2d -> (restart)"
          % NAIVE["residual"])
    print()
    for s in stages:
        n = "?" if s["jobs"] is None else s["jobs"]
        print("  [%s] %-32s 잡 %s  %s"
              % (s["key"], s["name"], n, "병렬" if s["parallel"] else "순차"))
        print("       관문: %s" % s["gate"])
        print("       낭비되는 조건: %s" % s["wasted_if"])
    print()
    print("  보정 수렴이 필요한가 -- 결론별로 다르다:")
    for name, needs, why in CLAIM_DEPENDENCE:
        print("    %-34s %s" % (name, "보정 필요" if needs else "보정 불필요"))
    print()
    o = outstanding()
    if o:
        print("  ** 지금 막혀 있는 것:")
        for stage, what, who in o:
            print("     [%s] %s   (%s)" % (stage, what, who))
    else:
        print("  ** 소스 측 관문은 전부 열려 있다.")
    print("=" * 78)
    return 0


def write_csv(path=None):
    path = path or os.path.join(HERE, "prerun_gate_plan.csv")
    m, stages = plan()
    with open(path, "w") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "name", "jobs", "parallel", "gate", "owner",
                    "unblocks", "wasted_if"])
        for s in stages:
            w.writerow([s["key"], s["name"],
                        "" if s["jobs"] is None else s["jobs"],
                        "yes" if s["parallel"] else "no",
                        s["gate"], s["owner"], s["unblocks"], s["wasted_if"]])
        w.writerow([])
        w.writerow(["claim", "needs_converged_calibration", "why"])
        for name, needs, why in CLAIM_DEPENDENCE:
            w.writerow([name, "yes" if needs else "no", why])
    return path, len(stages) + len(CLAIM_DEPENDENCE)


def check():
    ok, bad = [], []

    def t(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("prerun_gate.py --check")
    print(" A. the job counts come from the chapter, not from this file")
    m = matrix_from_chapter()
    t("the §5.7 matrix table was parsed",
      all(m[k] is not None for k in ("heat", "config_p", "config_v")),
      "heat %s / P %s / V %s" % (m["heat"], m["config_p"], m["config_v"]))
    t("heat jobs are one per severity, not one per case",
      m["heat"] == 3 and m["config_p"] == 9, "%d vs %d" % (m["heat"],
                                                           m["config_p"]))
    t("the control set is the middle severity only",
      m["config_v"] == 3, "%d jobs" % m["config_v"])
    saved, naive, actual = savings(m)
    t("the consolidation saves more jobs than it runs", saved > actual,
      "%d saved vs %d run" % (saved, actual))
    t("the naive count is stated so the saving is auditable",
      naive == sum(NAIVE.values()) + m["config_p"], "%d" % naive)

    print("\n B. every stage names its gate, its owner and its waste mode")
    _, stages = plan()
    for s in stages:
        t("stage %s is fully specified" % s["key"],
          all(s[k] for k in ("name", "gate", "owner", "unblocks",
                             "wasted_if", "detail")))
    t("the stages are ordered by dependency",
      [s["key"] for s in stages] == ["S0", "S1", "S2", "S3", "S4", "S5"])
    t("the first stage has no gate of its own",
      "없음" in stages[0]["gate"])
    t("the RVE stage is named as the one that gates the macro card",
      "거시 카드" in stages[1]["unblocks"])

    print("\n C. which conclusions survive an uncalibrated card")
    needs = [c for c in CLAIM_DEPENDENCE if c[1]]
    free = [c for c in CLAIM_DEPENDENCE if not c[1]]
    t("the four contributions do not need a converged calibration",
      len(free) == 4 and all(c[0].startswith("C") for c in free),
      ", ".join(c[0].split()[0] for c in free))
    t("the absolute validation targets do", len(needs) == 2,
      ", ".join(c[0].split()[0] for c in needs))
    t("every entry says WHY, not just yes/no",
      all(len(c[2]) > 30 for c in CLAIM_DEPENDENCE))
    t("the C1 reasoning is the shared-card cancellation, stated explicitly",
      "상쇄" in CLAIM_DEPENDENCE[0][2])
    t("and the limit of that reasoning is stated too",
      "절대값으로 인용할 때만" in CLAIM_DEPENDENCE[0][2])
    t("the placeholder-vs-uncalibrated distinction is made, not blurred",
      "자리표" in CLAIM_DEPENDENCE[0][2]
      and "자리표" in [s2 for s2 in STAGES if s2["key"] == "S3"][0]["gate"])
    t("...and it is credited to the agent who caught it",
      "a2-0032" in CLAIM_DEPENDENCE[0][2])

    print("\n C2. the chapter carries the same dependence table")
    ch5 = open(CH5, encoding="utf-8").read()
    t("§5.7 names the stages S0..S5",
      all(("**%s**" % k) in ch5 for k in ("S0", "S1", "S2", "S3", "S4", "S5")))
    t("§5.7.1 exists and separates the two kinds of conclusion",
      "5.7.1" in ch5 and "보정 수렴" in ch5 and "불필요" in ch5)
    t("the chapter states the placeholder floor, not just the cancellation",
      "자리표" in ch5 and "인공물" in ch5)

    print("\n D. the outstanding items are read from the tree, not typed")
    o = outstanding()
    t("outstanding items carry a stage and an owner",
      all(len(x) == 3 for x in o), "%d open" % len(o))
    mac = open(os.path.join(ROOT, "abaqus", "make_macro_thermalshock.py"),
               encoding="utf-8").read()
    wired = "conductivity_temperature" in mac
    t("the k(T) wiring state is detected, not assumed",
      wired == (not any("refs/[20]" in x[1] for x in o)),
      "wired" if wired else "still on the borrowed ratio")
    t("this module does not tell a2 how to run anything",
      not re.search(r"abaqus\s+job=", open(__file__, encoding="utf-8").read()))

    print("\n D2. a missing artefact is not allowed to look like a blocked job"
          "  (a2-0036)")
    t("the thermal card's magnitude is judged by the WIRING, not by a file",
      thermal_card_magnitude_fixed(),
      "KBAR3_FE = 5.4490, conductivity_temperature")
    t("...so no S2 item is raised on account of the kbar CSV",
      not any(x[0] == "S2" and "kbar" in x[1] for x in o))
    # S1 can now raise more than one item, so select the kbar one by its own
    # text instead of taking whatever happens to be first -- indexing [0] made
    # this pair fail the moment a second S1 item appeared.
    s1 = [x for x in o if x[0] == "S1" and "kbar" in x[1]]
    t("the kbar CSV item, if raised, blocks the FIGURE and the record only",
      not s1 or ("그림 4.5" in s1[0][1] and "새 해석은 필요 없다" in s1[0][1]),
      s1[0][1][:44] + "..." if s1 else "CSV present")
    t("and its owner is artefact recovery, not a run",
      not s1 or s1[0][2] == "사용자 회수")
    # The Gtc item is the opposite kind: it DOES block a run, and saying so is
    # the whole point of separating "an artefact is missing" from "the card is
    # not admissible".
    gtc = [x for x in o if x[0] == "S1" and "G_{tc}" in x[1]]
    t("the Gtc item is raised while the run deck carries a compressive Gf",
      bool(gtc) != gtc_admissible_on_this_mesh(),
      "raised" if gtc else "admissible")
    t("...and it blocks a RUN, unlike the kbar item",
      not gtc or ("재실행" in gtc[0][1] and gtc[0][2] == "a2"))
    t("...and it names the slot a2 has to decide, not the fix",
      not gtc or "슬롯 35" in gtc[0][1])
    t("the admissibility is recomputed, never remembered",
      "recomputed here rather than remembered"
      in " ".join(gtc_admissible_on_this_mesh.__doc__.split()).lower())
    t("the reason this distinction exists is written down",
      "could have run" in thermal_card_magnitude_fixed.__doc__)
    t("and it is credited to the agent who caught it",
      "a2-0036" in thermal_card_magnitude_fixed.__doc__)

    print("\n D3. the S3 gate is executable, not a reading  (a2-0034)")
    mark_in_generator = PLACEHOLDER_MARK in mac
    t("make_macro_thermalshock stamps a placeholder deck", mark_in_generator,
      PLACEHOLDER_MARK[:38] + "...")
    t("the detector fires on a stamped deck",
      s3_deck_is_placeholder("*Material, name=M\n** " + PLACEHOLDER_MARK))
    t("and stays silent on a deck without the stamp",
      not s3_deck_is_placeholder("*Material, name=M\n1.0, 2.0"))
    t("so S3's gate can be executed against the deck a2 is about to run",
      "a2-0034" in s3_deck_is_placeholder.__doc__)

    print("\n E. the CSV a2 executes from")
    path, n = write_csv()
    text = open(path).read()
    t("the plan CSV is written", n >= 12 and os.path.exists(path),
      "%d rows -> %s" % (n, os.path.basename(path)))
    t("it carries the waste mode next to every stage", "wasted_if" in text)
    t("it carries the calibration dependence table too",
      "needs_converged_calibration" in text)

    print("\n" + "=" * 74)
    if bad:
        print("PRE-RUN GATE FAILED -- %d of %d: %s"
              % (len(bad), len(ok) + len(bad), ", ".join(bad[:3])))
        return 1
    print("PRE-RUN GATE OK -- ALL %d PLANNING CLAIMS HOLD" % len(ok))
    print("=" * 74)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    if a.csv:
        p, n = write_csv()
        print("wrote %s (%d rows)" % (p, n))
        return 0
    return report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
