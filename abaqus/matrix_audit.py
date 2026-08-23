#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matrix_audit.py -- is the 9-case matrix a controlled experiment?
================================================================
    python3 abaqus/matrix_audit.py --check          # generate + audit, no solver
    python3 abaqus/matrix_audit.py --emit DIR       # decks + RUN_MANIFEST.md

The thermal-shock matrix is 3 severities x 3 TRS treatments, and its entire
scientific content is DIFFERENCES: B vs C is the thesis' main claim (C1),
L vs M vs H is the severity axis (C2).  A difference is only attributable if
the decks differ in nothing else.  M7 proved that by construction -- the deck
reproduced byte-identically and the change was the diff.  This file holds the
whole matrix to the same standard, before any solver time is spent:

  within a severity, across TRS
      A vs C   may differ ONLY in: the heading, the *Expansion block's
               presence, the initial temperature, and the presence of the
               Manufacturing_Cooldown step.  Every cycle step must be
               byte-identical -- if the cycling drifts between TRS cases, the
               B-C comparison measures deck drift, not TRS.
      B vs C   may differ ONLY in: the heading and macro card slot 26 (the
               damage freeze).  And they MUST differ there -- a B deck whose
               freeze is missing silently degenerates into a second C.

  within a TRS case, across severities
      L/M/H share T_hi = 900 and T_lo = 300 by design (the severity lives in
      the film coefficient of the SHARED heat job), so two mech decks of the
      same TRS case may differ ONLY in the heading and the *Temperature
      file= references to their heat jobs.

  heat decks
      may differ ONLY in the heading and the *Sfilm coefficient.

Anything outside the whitelist fails the audit with the offending lines
printed.  The audit also writes RUN_MANIFEST.md: the dependency plan (which
jobs wait for which), the parallel groupings, and the exact commands with
cpus/memory per CLAUDE.md's core-allocation table -- generated, not typed,
so it cannot drift from the decks it describes.
"""
from __future__ import print_function

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SEVS = ("L", "M", "H")
TRS = ("A", "B", "C")
PREFIX = "TSM"

#: per CLAUDE.md's allocation table: 9 simultaneous jobs -> 3 cpus each,
#: 25 gb each (27 cores total, 2 left for the OS); 3 jobs -> 10 cpus, 70 gb.
ALLOC_9 = dict(cpus=3, memory="25gb")
ALLOC_3 = dict(cpus=10, memory="70gb")

#: whitelists: a change is legal if EITHER side of the changed pair matches
#: one of these.  Kept as data so the selftest can probe them directly.
ALLOW = {
    "trs_AC": (r"^\s*Macro thermal shock, severity", r"^\*\* TRS ",
               r"^\*Expansion", r"^\s*[-0-9.eE+, ]+$",   # expansion data line
               r"^ALLNODES, ", r"^\*Initial Conditions, type=TEMPERATURE",
               r"^\*Step, Name=Manufacturing_Cooldown", r"^Cool ",
               r"^\*Static$", r"^0\.005, 1\.0, 1e-12, 0\.05$",
               r"^\*Temperature$", r"^\*Output", r"^\*Element Output",
               r"^\*Node Output", r"^\*Restart, write", r"^\*End Step$",
               r"^S, E, ", r"^U, RF", r"^\*Energy Output",
               r"^ALLIE, ALLSD", r"^\*Field, variable=1", r"^directions=",
               r"^SDV[0-9]"),
    "trs_BC": (r"^\s*Macro thermal shock, severity", r"^\*\* TRS ",
               r"^\s*[-0-9.eE+, ]+$"),                   # the card data line
    "sev": (r"^\s*Macro thermal shock, severity",
            r"^\*\* Bi = ", r"^\*Temperature, file="),
    "heat": (r"^\s*Macro thermal shock, SHARED heat",
             r"^\*\* Bi = ", r"^SURF_LO, F, |^SURF_HI, F, ",
             r"^Quench .*h = ",                          # the step's own label
             r"^\s*[-0-9.eE+, ]+$"),                     # film data line
}


def read(d, name):
    with open(os.path.join(d, name)) as f:
        return f.read().splitlines()


def changed_pairs(a, b):
    """[(line_a, line_b)] of REPLACED lines, plus one-sided inserts as
    (line, None)/(None, line), via difflib opcodes."""
    import difflib
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        left, right = a[i1:i2], b[j1:j2]
        for k in range(max(len(left), len(right))):
            out.append((left[k] if k < len(left) else None,
                        right[k] if k < len(right) else None))
    return out


def illegal(pairs, allow_key):
    """Changed pairs where NEITHER side matches the whitelist."""
    pats = [re.compile(p) for p in ALLOW[allow_key]]
    bad = []
    for la, lb in pairs:
        # a blank line inserted as part of a legal block carries no content
        ok = (la or "") == "" or (lb or "") == ""
        for ln in (la, lb):
            if ln is not None and any(p.search(ln) for p in pats):
                ok = True
        if not ok:
            bad.append((la, lb))
    return bad


def generate(outdir, extra=()):
    """Run the real generator into outdir.  Placeholder card is fine: the
    axis audit is about deck STRUCTURE, which the card does not touch."""
    cmd = [sys.executable, os.path.join(HERE, "make_macro_thermalshock.py"),
           "--prefix", PREFIX, "--sev"] + list(SEVS) + ["--trs"] + list(TRS)
    cmd += list(extra)
    p = subprocess.Popen(cmd, cwd=outdir, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return p.returncode, out.decode("utf-8", "replace")


def mech(d, sev, trs):
    return read(d, "%s_MECH_S%s_TRS%s.inp" % (PREFIX, sev, trs))


def audit(d, t):
    """All axis checks on a directory of generated decks."""
    # ---- TRS axis, within each severity ----------------------------------
    for sev in SEVS:
        A, B, C = (mech(d, sev, t_) for t_ in TRS)
        bad = illegal(changed_pairs(A, C), "trs_AC")
        t("S%s: A vs C differ only where TRS is allowed to act" % sev,
          not bad, "; ".join("%r|%r" % p for p in bad[:2]))
        pairs = changed_pairs(B, C)
        bad = illegal(pairs, "trs_BC")
        t("S%s: B vs C differ only in the heading and the freeze slot" % sev,
          not bad, "; ".join("%r|%r" % p for p in bad[:2]))
        datachanges = [p for p in pairs
                       if p[0] and p[1]
                       and re.match(r"^\s*[-0-9.eE+, ]+$", p[0])]
        t("  and they DO differ on a card data line (the freeze is real)",
          len(datachanges) >= 1,
          "%d changed data line(s); a B with no freeze is a second C"
          % len(datachanges))
        cyc_a = [l for l in A if l.startswith("*Step, Name=Quench")
                 or l.startswith("*Step, Name=Reheat")]
        cyc_c = [l for l in C if l.startswith("*Step, Name=Quench")
                 or l.startswith("*Step, Name=Reheat")]
        t("  the cycle-step skeleton is identical across TRS",
          cyc_a == cyc_c and len(cyc_a) > 0, "%d cycle steps" % len(cyc_a))

    # ---- severity axis, within each TRS case -----------------------------
    for trs in TRS:
        L, M, H = (mech(d, s_, trs) for s_ in SEVS)
        for name, other in (("M", M), ("H", H)):
            bad = illegal(changed_pairs(L, other), "sev")
            t("TRS%s: SL vs S%s differ only in the heat-job reference"
              % (trs, name), not bad,
              "; ".join("%r|%r" % p for p in bad[:2]))
        refs = ["".join(l for l in deck if "Temperature, file=" in l)
                for deck in (L, M, H)]
        t("TRS%s: and each really reads its OWN heat job" % trs,
          all(("_S%s." % s) in r for s, r in zip(SEVS, refs)),
          "a mech deck reading another severity's heat odb would converge "
          "on the wrong quench")

    # ---- heat decks ------------------------------------------------------
    HL, HM, HH = (read(d, "%s_HEAT_S%s.inp" % (PREFIX, s)) for s in SEVS)
    for name, other in (("M", HM), ("H", HH)):
        bad = illegal(changed_pairs(HL, other), "heat")
        t("heat SL vs S%s differ only in the film coefficient" % name,
          not bad, "; ".join("%r|%r" % p for p in bad[:2]))
    t("and the three film coefficients are all different",
      len(set("".join(l for l in deck if re.match(r"^SURF_", l))
              for deck in (HL, HM, HH))) == 3,
      "Bi = 0.05 / 1 / 5 through h, not through the mesh")

    # ---- the counts a run plan depends on --------------------------------
    files = sorted(os.listdir(d))
    t("3 heat + 9 mech decks came out",
      sum(1 for f in files if "_HEAT_" in f) == 3
      and sum(1 for f in files if "_MECH_" in f) == 9,
      "%d files total" % len(files))
    t("plus the residual-strength restarts for every case",
      sum(1 for f in files if "_RESID_" in f) == 9 * 5,
      "5 checkpoints per case, restart-continued, never recomputed")


UMAT = "UMAT_CSIC_THERMSHOCK_V3_0.for"

#: The CSVs the post-processing writes and the user is asked to upload.
#: CLAUDE.md 3-2: the CSV is the deliverable, not a screenshot of a console.
#: Per-job entries are written as real globs against the real prefix, not as
#: "<잡>_probe.csv" -- a placeholder is something the user has to resolve,
#: and a glob is something they can paste.
UPLOAD_GLOB = ("_probe.csv", "_damage_map.csv", "_drivers.csv")
UPLOAD_ONCE = ("damage_ceiling_summary.csv", "cyclejump_summary.csv")


def restart_parent(path):
    """The MECH job a RESID deck restarts from, read from the deck itself.

    The name is recoverable from the filename too, but the deck states it --
    "(restart from TSM_MECH_SL_TRSA)" -- and reading the statement means a
    renamed file cannot desync the command from the deck it describes.
    """
    m = re.search(r"restart from ([A-Za-z0-9_]+)", open(path).read())
    return m.group(1) if m else None


def manifest(d):
    """RUN_MANIFEST.md -- generated from the decks that are actually there.

    Every command is COMPLETE.  It used to hand over `<RESID이름>` and
    `<부모MECH이름>` for the user to fill in, which is the blank-filling that
    CLAUDE.md forbids as of 2026-08-18: a value I do not supply is one the
    user has to derive, and if they derive it wrong it propagates through
    every following command.  The generator knows all 45 parent pairs -- it
    reads them out of the decks -- so it prints them.
    """
    files = sorted(os.listdir(d))
    heats = [f[:-4] for f in files if "_HEAT_" in f and f.endswith(".inp")]
    mechs = [f[:-4] for f in files if "_MECH_" in f and f.endswith(".inp")]
    resids = [f[:-4] for f in files if "_RESID_" in f and f.endswith(".inp")]
    # N5 must come before N10.  Sorting the names alphabetically puts N10,
    # N20, N40, N5, N60 -- a list of checkpoints out of cycle order, which
    # is the one property a reader scans it for.
    resids.sort(key=lambda n: (n.rsplit("_N", 1)[0],
                               int(n.rsplit("_N", 1)[1])
                               if n.rsplit("_N", 1)[-1].isdigit() else 0))
    L = ["# RUN_MANIFEST — 9케이스 매트릭스 실행 계획 (이 파일은 생성물이다)",
         "",
         "의존성: **열 잡 → 같은 심각도의 역학 잡** (역학이 열 ODB를 읽음).",
         "TRS A/B/C 는 서로 독립, 심각도끼리도 독립.",
         "",
         "## 1단계 — 열 잡 %d개, 서로 독립 → 창 %d개 병렬 (cpus=%d, %s)"
         % (len(heats), len(heats), ALLOC_3["cpus"], ALLOC_3["memory"]),
         ""]
    for j in heats:
        L.append("    abaqus job=%s input=%s.inp double interactive "
                 "cpus=%d memory=\"%s\"" % (j, j, ALLOC_3["cpus"],
                                            ALLOC_3["memory"]))
    L += ["",
          "## 2단계 — 역학 잡 %d개 동시 (잡당 cpus=%d, %s — 합계 27코어, "
          "OS 여유 2)" % (len(mechs), ALLOC_9["cpus"], ALLOC_9["memory"]),
          "",
          "**자기 심각도의 열 잡이 끝난 것부터 바로 시작한다** — 셋 다 기다릴 "
          "필요 없다.", ""]
    # Grouped by severity, because the dependency is per severity: the
    # three TRS cases of one severity become runnable the moment THAT
    # severity's heat job lands.  An alphabetical list hides that.
    for sev in SEVS:
        mine = [j for j in mechs if ("_S%s_" % sev) in j]
        if not mine:
            continue
        L += ["", "**%s_HEAT_S%s 가 끝나면 이 셋**:" % (PREFIX, sev)]
        for j in mine:
            L.append("    abaqus job=%s input=%s.inp user=%s double "
                     "cpus=%d memory=\"%s\""
                     % (j, j, UMAT, ALLOC_9["cpus"], ALLOC_9["memory"]))
    L += ["",
          "## 3단계 — 잔여강도 (restart, 부모 역학 잡 **이후**, 필요한 "
          "체크포인트만)",
          "",
          "%d개가 준비되어 있으나 **전부 돌리는 것이 아니다** — E(N) 프로브 "
          "곡선을 보고 고른다." % len(resids),
          "아래는 **완성된 명령**이다. 고른 줄만 그대로 복사하면 된다 — "
          "부모 잡 이름은 각 덱이 스스로 적어 둔 것을 읽어 채웠다.",
          ""]
    for j in resids:
        parent = restart_parent(os.path.join(d, j + ".inp"))
        if parent is None:
            L.append("    ** %s: 부모 잡을 덱에서 찾지 못했다 — 확인 필요" % j)
            continue
        L.append("    abaqus job=%s input=%s.inp user=%s double oldjob=%s "
                 "cpus=%d memory=\"%s\""
                 % (j, j, UMAT, parent, ALLOC_3["cpus"], ALLOC_3["memory"]))
    L += ["",
          "## 완료 후 (후처리는 cpus/memory 불필요, 잡 하나 끝날 때마다 바로)",
          "",
          "역학 잡 하나가 끝나면 그 잡에 대해 세 줄. 아래는 첫 잡의 완성 "
          "명령이고, 나머지 %d개는 **잡 이름만** 바꾸면 된다."
          % max(0, len(mechs) - 1),
          ""]
    if mechs:
        j0 = mechs[0]
        L += ["    abaqus python extract_probe.py %s.odb" % j0,
              "    abaqus python damage_map.py %s.odb" % j0,
              "    abaqus python driver_audit.py %s.odb"
              "   ← ALLSD/ALLIE 5 %% 관문. 이거 없이는 피크 인용 불가" % j0,
              ""]
    L += ["", "%d개가 다 끝난 뒤 한 번씩:" % len(mechs), ""]
    if len(mechs) >= 2:
        L.append("    python compare_cyclejump.py %s_probe.csv %s_probe.csv"
                 "   ← 점프 오차 판정 (기준, 점프 두 개를 받는다)"
                 % (mechs[0], mechs[1]))
    L += ["    python damage_ceiling.py %s_MECH_*_damage_map.csv" % PREFIX,
          "",
          "## 채팅에 올릴 파일 (콘솔 캡처가 아니라 **CSV**)",
          ""]
    for g in UPLOAD_GLOB:
        L.append("- `%s_MECH_*%s`  (%d개)" % (PREFIX, g, len(mechs)))
    for u in UPLOAD_ONCE:
        L.append("- `%s`" % u)
    L.append("")
    path = os.path.join(d, "RUN_MANIFEST.md")
    with open(path, "w") as f:
        f.write("\n".join(L))
    return path


# --------------------------------------------------------------------------
_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-62s %s" % ("PASS" if cond else "FAIL", name,
                               detail if not cond or detail else ""))


def check():
    print("=" * 78)
    print("matrix_audit.py -- the 9-case matrix as a controlled experiment")
    print("=" * 78)

    print("\n A. the audit machinery itself")
    pairs = changed_pairs(["x", "same", "y"], ["z", "same", "y", "w"])
    t("changed_pairs sees replacements and inserts",
      ("x", "z") in pairs and (None, "w") in pairs, "%s" % pairs)
    t("a legal change passes the whitelist",
      not illegal([("** TRS A: no expansion", "** TRS C: cooldown")],
                  "trs_AC"))
    t("an illegal change is caught, with the lines kept",
      illegal([("*Step, Name=Quench_to5_1", "*Step, Name=Quench_to9_1")],
              "trs_BC"))

    print("\n B. generate the real matrix (placeholder card -- structure only)")
    d = tempfile.mkdtemp(prefix="matrix_audit_")
    rc, out = generate(d)
    t("the generator emits the full matrix in one call", rc == 0,
      out.splitlines()[-1] if rc != 0 else "--sev L M H --trs A B C")
    if rc != 0:
        return
    t("  and it says out loud that the card is a placeholder",
      "PLACEHOLDER macro card" in out,
      "the real card comes from homogenize.py after M7")

    print("\n C. the axes are clean")
    audit(d, t)

    print("\n D. the manifest is generated from the decks, not typed")
    mpath = manifest(d)
    m = open(mpath).read()
    t("it exists and lists every deck it found", os.path.exists(mpath)
      and m.count("abaqus job=") >= 12, "%d job lines" % m.count("abaqus job="))
    t("  heat jobs get the 3-job allocation",
      ("cpus=%d" % ALLOC_3["cpus"]) in m and ALLOC_3["memory"] in m)
    t("  the 9 mech jobs get the 9-job allocation",
      ("cpus=%d" % ALLOC_9["cpus"]) in m and ALLOC_9["memory"] in m,
      "27 cores total, 2 left for the OS")
    t("  dependencies are stated, not implied",
      "열 잡 → 같은 심각도" in m and "부모 역학 잡" in m)
    t("  and the ALLSD/ALLIE gate is in the post-run list",
      "ALLSD/ALLIE" in m)
    t("  restarts are marked choose-after-probing, not run-all",
      "전부 돌리는 것이 아니다" in m)

    print("\n D2. the manifest hands over NO blanks (CLAUDE.md, 2026-08-18)")
    # It used to print `<RESID이름>`, `<부모MECH이름>`, `<MECH잡>.odb` and a
    # bare `...` for the user to resolve.  A value I do not supply is one
    # they have to derive, and a wrong derivation propagates through every
    # command after it -- which is exactly the rule the user added today.
    blanks = re.findall(r"<[^>\n]{1,20}>", m)
    t("no <placeholder> survives anywhere in the manifest", not blanks,
      "found %s" % blanks[:4])
    t("  every restart line names its real parent job", m.count("oldjob=") == 45
      and "oldjob=<" not in m,
      "%d oldjob= lines, all resolved from the decks themselves"
      % m.count("oldjob="))
    t("  and the parent really is that deck's own MECH job",
      all(("oldjob=%s_MECH_S%s_TRS%s" % (PREFIX, s, r)) in m
          for s in SEVS for r in TRS),
      "read from '(restart from ...)' in the deck, not guessed from the name")
    t("  checkpoints are listed in CYCLE order, not alphabetical",
      m.find("_TRSA_N5 ") < m.find("_TRSA_N10 ") < m.find("_TRSA_N20 "),
      "N5 before N10; sorting names alphabetically hid the ordering")
    t("  the mech jobs are grouped by the heat job they wait for",
      all(("%s_HEAT_S%s 가 끝나면" % (PREFIX, s)) in m for s in SEVS),
      "the dependency is per severity, so the list is too")
    t("  the post-run example is a real job name, not <잡>",
      ("extract_probe.py %s_MECH_" % PREFIX) in m)
    t("  and compare_cyclejump gets the two inputs its parser wants",
      len([ln for ln in m.splitlines()
           if "compare_cyclejump.py" in ln and ln.count("_probe.csv") == 2]),
      "it reads argv[0] and argv[1]; one argument would crash")
    t("the upload list is globs against the real prefix, not placeholders",
      ("%s_MECH_*_probe.csv" % PREFIX) in m and "<잡>" not in m,
      "a glob can be pasted; a placeholder has to be resolved")

    print("\n E. a broken matrix would actually be caught")
    # sabotage: give one severity's C deck a different cycle count, the way a
    # half-edited generator would.  The audit must refuse it.
    victim = os.path.join(d, "%s_MECH_SM_TRSC.inp" % PREFIX)
    src = open(victim).read()
    open(victim, "w").write(src.replace("Quench_to5_1", "Quench_to7_1"))
    caught = []

    def probe(name, cond, detail=""):
        caught.append((name, cond))

    audit(d, probe)
    t("a renamed cycle step in ONE deck fails the audit",
      any(not ok for _n, ok in caught),
      "%d of %d audit lines went red" % (sum(1 for _n, ok in caught if not ok),
                                         len(caught)))
    open(victim, "w").write(src)
    caught2 = []
    audit(d, lambda n, c, dd="": caught2.append((n, c)))
    t("  and restoring the deck restores the audit",
      all(ok for _n, ok in caught2))


def main(argv):
    if "--check" in argv or "--selftest" in argv:
        check()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % ", ".join(n for n in _BAD[:3]))
            print("=" * 78)
            return 1
        print("ALL %d MATRIX-AUDIT CHECKS PASS "
              "(the 9 cases differ only where they claim to)" % len(_OK))
        print("=" * 78)
        return 0
    if "--emit" in argv:
        outdir = argv[argv.index("--emit") + 1]
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        extra = [a for a in argv if a not in ("--emit", outdir)]
        rc, out = generate(outdir, extra)
        print(out)
        if rc != 0:
            return rc
        audit(outdir, t)
        if _BAD:
            print("AXIS AUDIT FAILED -- decks NOT fit to ship")
            return 1
        print("wrote %s" % manifest(outdir))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
