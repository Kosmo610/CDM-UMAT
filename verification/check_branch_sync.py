#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_branch_sync.py  --  두 에이전트가 서로의 새 정보를 알아차리는 장치
==========================================================================
이 논문은 두 채팅(에이전트)이 나눠서 진행한다.

  에이전트 1  논문 조사 · 물성 정리   claude/paper-reference-research-pksw5p
  에이전트 2  코드 작성 · 해석 결과   claude/thesis-csic-thermal-shock-5m53iv

둘은 서로의 대화를 볼 수 없다.  기억도 공유하지 않는다.  공유하는 것은 저장소
하나뿐이므로, **저장소가 통신선이고 커밋이 메시지이며 병합이 배달이다.**

문제는 "배달 왔다"고 알려주는 것이 없다는 점이다.  상대가 내 판정을 뒤집는
발견을 해도, 내가 먼저 확인하지 않으면 모른 채 계속 간다.  실제로 그런 일이
있었다 -- 에이전트 2가 refs/[08]에서 얀 Xt의 카드값이 다발 강도임을 찾아냈는데,
에이전트 1은 그것을 모른 채 "독립 근거 있음(IN)"으로 분류한 상태를 유지하고
있었다 (docs/BRANCH_PROTOCOL.md 2.1).

이 스크립트가 그 알림이다.  **양쪽이 같은 명령을 돌리면, 각자 자기 입장에서
"상대가 뭘 했고 나는 뭘 안 읽었는지"를 본다.**  브랜치 이름으로 역할을 스스로
판단하므로 인자가 필요 없다.

무엇을 보는가
------------
  1. 상대 브랜치에 내가 아직 병합하지 않은 커밋이 있는가
  2. 내 앞으로 온 우편함(TO_*.md)에 미처리 항목이 있는가
  3. 상대가 **내가 최종 판정하는 영역**의 파일을 건드렸는가
     -> 이것이 가장 중요하다.  내 판정을 뒤집는 발견일 수 있다.
  4. 내가 상대에게 보낼 것을 우편함에 적어 두었는가

언제 돌리는가 (CLAUDE.md 규칙)
-----------------------------
  * 세션을 시작할 때  -- 상대가 그동안 뭘 했는지 먼저 본다
  * 커밋하기 전에    -- 내 변경이 상대 발견과 어긋나지 않는지 본다

종료 코드
--------
  0  읽지 않은 것 없음
  1  ★ 처리할 것이 있음 (미병합 커밋 / 미처리 우편 / 영역 침범)
  2  git 문제로 판단 불가

Run:  python3 verification/check_branch_sync.py
      python3 verification/check_branch_sync.py --selftest
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --------------------------------------------------------------------------
# 두 에이전트의 정의.  브랜치 이름이 곧 역할이다.
# --------------------------------------------------------------------------
AGENTS = {
    "A1": dict(
        name="에이전트 1 — 논문 조사 · 물성 정리",
        branch="claude/paper-reference-research-pksw5p",
        inbox="docs/TO_LITERATURE.md",     # 내가 받는 곳
        outbox="docs/TO_ANALYSIS.md",      # 내가 보내는 곳
        # 내가 최종 판정하는 영역 (BRANCH_PROTOCOL.md 3.2)
        domain=("data/literature/", "data/properties/",
                "docs/REFS_", "docs/DOWNLOAD_LIST",
                "verification/check_card_ranges.py",
                "verification/verify_bibliography.ps1"),
        adjudicates="값의 출처·신뢰등급·카드 적법성, 장별 인용",
    ),
    "A2": dict(
        name="에이전트 2 — 코드 작성 · 해석 결과",
        branch="claude/thesis-csic-thermal-shock-5m53iv",
        inbox="docs/TO_ANALYSIS.md",
        outbox="docs/TO_LITERATURE.md",
        domain=("src/", "abaqus/", "postprocess/", "dist/"),
        adjudicates="코드가 값을 쓰는 방식, 수렴·솔버·덱·UMAT",
    ),
}

REMOTE = "origin"


def git(*args):
    """(stdout, rc).  실패해도 예외를 던지지 않는다."""
    p = subprocess.Popen(["git"] + list(args), cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode("utf-8", "replace").strip(), p.returncode


def current_branch():
    out, rc = git("rev-parse", "--abbrev-ref", "HEAD")
    return out if rc == 0 else None


def identify(branch):
    """브랜치 이름에서 내가 누구인지 판단한다."""
    for key, a in AGENTS.items():
        if branch == a["branch"]:
            return key
    return None


def pending_items(path):
    """우편함에서 미처리 항목의 제목을 뽑는다.

    '## 처리 완료' 아래는 세지 않고, 제목에 ✅ 가 붙은 것도 처리된 것으로 본다.
    """
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None
    items, done_section = [], False
    for line in open(full, encoding="utf-8"):
        if re.match(r"^##\s", line):
            done_section = "처리 완료" in line or "완료" in line
            continue
        m = re.match(r"^###\s+(.*)$", line)
        if m and not done_section:
            title = m.group(1).strip()
            if "✅" not in title:
                items.append(title)
    return items


def report():
    print("=" * 74)
    print("check_branch_sync.py — 상대 에이전트가 무엇을 했는가")
    print("=" * 74)

    br = current_branch()
    if br is None:
        print("\n  git 저장소가 아닙니다.")
        return 2
    me = identify(br)
    if me is None:
        print("\n  현재 브랜치: %s" % br)
        print("  두 에이전트 브랜치가 아니므로 판단하지 않습니다.")
        for a in AGENTS.values():
            print("    - %s" % a["branch"])
        return 0

    other = "A2" if me == "A1" else "A1"
    MINE, OTHER = AGENTS[me], AGENTS[other]

    print("\n  나   : %s" % MINE["name"])
    print("         %s" % MINE["branch"])
    print("  상대 : %s" % OTHER["name"])
    print("         %s" % OTHER["branch"])
    print("  내가 최종 판정하는 것: %s" % MINE["adjudicates"])

    todo = []

    # ---- 0. 최신 상태로 -------------------------------------------------
    _, rc = git("fetch", REMOTE, "--quiet")
    if rc != 0:
        print("\n  ⚠️  git fetch 실패 — 아래는 마지막으로 받아둔 정보 기준입니다.")

    ref_other = "%s/%s" % (REMOTE, OTHER["branch"])
    _, rc = git("rev-parse", "--verify", ref_other)
    if rc != 0:
        print("\n  상대 브랜치를 찾을 수 없습니다: %s" % ref_other)
        return 2

    # ---- 1. 미병합 커밋 -------------------------------------------------
    print("\n" + "-" * 74)
    print(" 1. 상대가 쌓아둔 커밋 중 내가 안 받은 것")
    print("-" * 74)
    counts, _ = git("rev-list", "--left-right", "--count",
                    "HEAD...%s" % ref_other)
    try:
        mine_only, theirs_only = (int(x) for x in counts.split())
    except ValueError:
        mine_only = theirs_only = 0
    print("\n  나만 가진 커밋 %d개 / 상대만 가진 커밋 %d개" % (mine_only, theirs_only))

    incoming = []
    if theirs_only:
        log, _ = git("log", "--oneline", "--no-merges",
                     "HEAD..%s" % ref_other)
        incoming = [l for l in log.split("\n") if l.strip()]
        print("\n  ★ 안 받은 커밋:")
        for l in incoming:
            print("     %s" % l)
        todo.append("상대 브랜치 %d개 커밋 병합" % theirs_only)
    else:
        print("\n  ✔ 상대의 작업은 전부 받았습니다.")

    # ---- 2. 상대가 내 판정 영역을 건드렸는가 ----------------------------
    print("\n" + "-" * 74)
    print(" 2. ★ 상대가 '내가 최종 판정하는' 파일을 건드렸는가")
    print("-" * 74)
    crossed = []
    if theirs_only:
        files, _ = git("diff", "--name-only", "HEAD...%s" % ref_other)
        for f in files.split("\n"):
            f = f.strip()
            if f and any(f.startswith(d) for d in MINE["domain"]):
                crossed.append(f)
    if crossed:
        print("\n  ⚠️  %d개 파일 — 내 판정을 뒤집는 발견일 수 있습니다:" % len(crossed))
        for f in sorted(set(crossed)):
            print("     %s" % f)
        print("""
  이것이 이 스크립트의 존재 이유입니다.  상대가 여기를 건드렸다면
  그냥 병합하지 말고 **왜 바꿨는지 커밋 메시지를 읽으세요.**
  BRANCH_PROTOCOL.md 3.2: 판정은 내 쪽이지만, 근거가 상대에게 있으면
  상대 값을 받습니다.""")
        todo.append("내 판정 영역 %d개 파일의 변경 사유 확인" % len(set(crossed)))
    else:
        print("\n  ✔ 없음.")

    # ---- 3. 내 우편함 ---------------------------------------------------
    print("\n" + "-" * 74)
    print(" 3. 내 앞으로 온 우편 (%s)" % MINE["inbox"])
    print("-" * 74)
    inbox = pending_items(MINE["inbox"])
    if inbox is None:
        print("\n  파일이 없습니다 — 만들어야 합니다.")
        todo.append("%s 생성" % MINE["inbox"])
    elif inbox:
        print("\n  ★ 미처리 %d건:" % len(inbox))
        for t in inbox:
            print("     %s" % t)
        todo.append("우편 %d건 처리" % len(inbox))
    else:
        print("\n  ✔ 미처리 없음.")

    # ---- 4. 내가 보낼 것 ------------------------------------------------
    print("\n" + "-" * 74)
    print(" 4. 내가 상대에게 보낼 것 (%s)" % MINE["outbox"])
    print("-" * 74)
    outbox = pending_items(MINE["outbox"])
    if outbox is None:
        print("\n  파일이 없습니다 — 만들어야 합니다.")
        todo.append("%s 생성" % MINE["outbox"])
    elif outbox:
        print("\n  대기 %d건 (상대가 병합하면 읽습니다):" % len(outbox))
        for t in outbox:
            print("     %s" % t)
    else:
        print("\n  없음.  새로 알릴 것이 생기면 여기에 적으세요.")

    # ---- 정리 -----------------------------------------------------------
    print("\n" + "=" * 74)
    if todo:
        print(" ★ 할 일 %d가지" % len(todo))
        for i, t in enumerate(todo, 1):
            print("   %d. %s" % (i, t))
        print("=" * 74)
        return 1
    print(" 동기화 완료 — 처리할 것 없음")
    print("=" * 74)
    return 0


# --------------------------------------------------------------------------
def selftest():
    ok = []

    def t(name, cond, detail=""):
        ok.append(cond)
        print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("check_branch_sync.py --selftest")

    t("두 에이전트가 정의되어 있다", set(AGENTS) == {"A1", "A2"})
    t("A1의 우편함은 A2의 발신함이다",
      AGENTS["A1"]["inbox"] == AGENTS["A2"]["outbox"],
      AGENTS["A1"]["inbox"])
    t("A2의 우편함은 A1의 발신함이다",
      AGENTS["A2"]["inbox"] == AGENTS["A1"]["outbox"],
      AGENTS["A2"]["inbox"])
    t("두 영역이 겹치지 않는다",
      not (set(AGENTS["A1"]["domain"]) & set(AGENTS["A2"]["domain"])))

    t("브랜치 이름으로 역할을 판단한다",
      identify(AGENTS["A1"]["branch"]) == "A1"
      and identify(AGENTS["A2"]["branch"]) == "A2")
    t("모르는 브랜치는 조용히 넘어간다", identify("main") is None)

    for k, a in AGENTS.items():
        for box in ("inbox", "outbox"):
            p = os.path.join(ROOT, a[box])
            t("%s의 %s 파일이 있다" % (k, box), os.path.exists(p), a[box])

    # 우편함 파싱: ✅ 는 처리된 것, '처리 완료' 절 아래도 처리된 것
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sync_")
    rel = os.path.relpath(os.path.join(tmp, "box.md"), ROOT)
    with open(os.path.join(tmp, "box.md"), "w", encoding="utf-8") as f:
        f.write("# 제목\n\n## 미처리\n\n### [X1] 아직 안 함\n\n"
                "### [X2] ✅ 끝난 것\n\n## 처리 완료\n\n### [X3] 옛날 것\n")
    got = pending_items(rel)
    t("미처리만 골라낸다", got == ["[X1] 아직 안 함"], str(got))

    t("없는 파일은 None을 준다", pending_items("docs/__없음__.md") is None)

    br = current_branch()
    t("현재 브랜치를 읽는다", br is not None, br or "")
    t("현재 브랜치가 두 에이전트 중 하나다", identify(br) is not None,
      "%s -> %s" % (br, identify(br)))

    print("\n%s" % ("전체 %d항목 통과" % len(ok) if all(ok)
                    else "실패 %d / %d" % (ok.count(False), len(ok))))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else report())
