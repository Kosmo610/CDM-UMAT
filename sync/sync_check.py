#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_check.py  --  the postbox between the two agent branches
==============================================================
Two chats work the same repository on two branches.  Neither can see the
other's commits, and neither runs unless the user prompts it, so "I will
notice when they change something" is not a mechanism -- it is a hope.

This is the mechanism.  It fetches the other agent's branch, reads the
outbox file that agent OWNS, and compares it against what this side has
recorded as read.  Anything new is printed.  Anything new and `blocking`
makes this script exit non-zero, and since it sits in CLAUDE.md's
pre-commit list, that stops the commit until it is dealt with.

Ownership is the whole design (sync/PROTOCOL.md): every file has exactly
one writer, so the two branches can be merged in any order without this
folder ever conflicting.

WHAT IT VERIFIES, not just relays
---------------------------------
A `band` message from a1 names a card slot and an independent literature
range.  That range is supposed to end up as a row in
verification/check_card_ranges.py.  This script goes and looks.  So
acknowledging a message without acting on it is visible, which is the
difference between a postbox and a checklist nobody reads.

Run:  python3 sync/sync_check.py             # what is new from the other side
      python3 sync/sync_check.py --ack a1-0003
      python3 sync/sync_check.py --ack-all
      python3 sync/sync_check.py --selftest  # no network, deterministic
"""
from __future__ import print_function

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

AGENTS = {
    "a1": dict(branch="claude/paper-reference-research-pksw5p",
               role="논문 조사·물성 정리"),
    "a2": dict(branch="claude/thesis-csic-thermal-shock-5m53iv",
               role="코드 작성·해석 결과"),
}
OTHER = {"a1": "a2", "a2": "a1"}

#: Kinds that only one side can send, because they assert something only
#: that side has the authority to assert: a1 rules on where a number came
#: from and whether it may enter a card, a2 rules on what the code does
#: with it.  Everything else is bidirectional.
#:
#: `finding` and `changed` used to be a2-only, which was wrong and a1 hit
#: it on their first real batch -- seven messages flagged as malformed for
#: reporting findings, which is exactly what a literature agent does when
#: it reads a paper and the paper contradicts us.  The restriction encoded
#: an assumption about who discovers things, and that assumption was not
#: true in either direction.
KINDS_ONLY_A1 = ("band", "value", "ref", "verdict")
KINDS_ONLY_A2 = ("need",)
KINDS_BOTH = ("finding", "changed", "question")
KINDS_FROM_A1 = KINDS_ONLY_A1 + KINDS_BOTH
KINDS_FROM_A2 = KINDS_ONLY_A2 + KINDS_BOTH
GRADES = ("fulltext", "digitized", "abstract", "secondary")

CARD_TABLES = {"matrix": "MATRIX", "yarn": "YARN", "macro": "MACRO"}

#: Editing territory, absorbed from a1's check_branch_sync.py (a1-0004).
#: This is NOT the same thing as the sync/ ownership table: that one is
#: absolute and makes the folder merge-proof, this one is advisory.  Both
#: agents legitimately edit the shared chapters, so crossing a line here is
#: reported to the other side rather than treated as an error -- the failure
#: mode being guarded against is a silent edit nobody mentions, not the edit.
#: Anything not listed is shared and never warned about.
TERRITORY = {
    "a1": ("refs/", "data/literature/", "docs/CH1_INTRODUCTION.md",
           "docs/CH2_LITERATURE_REVIEW.md", "docs/REFS_CANDIDATES.md",
           "docs/DOWNLOAD_LIST", "docs/KAISER_JUDGMENT.md",
           "sync/outbox_a1.json", "sync/state_a1.json"),
    "a2": ("src/", "abaqus/", "postprocess/", "verification/",
           "sync/sync_check.py", "sync/PROTOCOL.md",
           "sync/outbox_a2.json", "sync/state_a2.json"),
}


# ==========================================================================
# small helpers
# ==========================================================================
def git(*args):
    """Run git and return (stdout, returncode).  Never raises."""
    p = subprocess.Popen(("git",) + args, cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return out.decode("utf-8", "replace"), p.returncode


def outbox_path(who):
    return "sync/outbox_%s.json" % who


def state_path(who):
    return os.path.join(HERE, "state_%s.json" % who)


def whoami():
    """Which agent is running this, decided by the checked-out branch.

    Guessing wrong would make an agent read its own outbox and acknowledge
    its own messages, so an unrecognised branch is a hard stop rather than
    a default.
    """
    out, rc = git("rev-parse", "--abbrev-ref", "HEAD")
    branch = out.strip()
    for who, meta in AGENTS.items():
        if meta["branch"] == branch:
            return who, branch
    return None, branch


def fetch(branch, tries=4):
    """Fetch one branch, backing off 2/4/8/16 s as CLAUDE.md requires.

    A network failure is NOT a verification failure -- the mail that is
    already local still gets checked.  Only the freshness claim is lost,
    and the caller says so out loud.
    """
    for i in range(tries):
        out, rc = git("fetch", "origin", branch)
        if rc == 0:
            return True, ""
        if i < tries - 1:
            time.sleep(2 ** (i + 1))
    return False, out.strip().splitlines()[-1] if out.strip() else "unknown"


def read_outbox(ref, who):
    """Read an outbox as of `ref` (a git ref, or None for the worktree)."""
    if ref is None:
        path = os.path.join(ROOT, outbox_path(who))
        if not os.path.exists(path):
            return None, "not present in the worktree"
        text = io.open(path, encoding="utf-8").read()
    else:
        text, rc = git("show", "%s:%s" % (ref, outbox_path(who)))
        if rc != 0:
            return None, "not present on %s" % ref
    try:
        return json.loads(text), ""
    except ValueError as exc:
        return None, "malformed JSON: %s" % exc


def load_state(who):
    path = state_path(who)
    if not os.path.exists(path):
        return {"agent": who, "read": []}
    try:
        return json.loads(io.open(path, encoding="utf-8").read())
    except ValueError:
        return {"agent": who, "read": []}


def save_state(who, state):
    state["read"] = sorted(set(state.get("read", [])))
    io.open(state_path(who), "w", encoding="utf-8").write(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


# ==========================================================================
# message validation -- a malformed message is worse than none
# ==========================================================================
def validate(msg, sender):
    """Return a list of complaints about one message.

    The point is to fail on the SENDER's side of the fence.  A message with
    no `action` and `blocking: true` cannot be acted on, and a `band` with
    no grade is a number with no provenance, which CLAUDE.md forbids from
    entering a card at all.
    """
    bad = []
    for field in ("id", "date", "kind", "subject", "body"):
        if not msg.get(field):
            bad.append("missing %s" % field)
    mid = msg.get("id", "?")
    if not re.match(r"^%s-\d{4}$" % sender, str(mid)):
        bad.append("id %r is not %s-NNNN" % (mid, sender))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(msg.get("date", ""))):
        bad.append("date %r is not YYYY-MM-DD" % msg.get("date"))
    allowed = KINDS_FROM_A1 if sender == "a1" else KINDS_FROM_A2
    if msg.get("kind") not in allowed:
        bad.append("kind %r is not one of %s" % (msg.get("kind"), list(allowed)))
    if msg.get("blocking") and not msg.get("action"):
        bad.append("blocking with no action -- nothing to do")
    if msg.get("kind") in ("band", "value"):
        if msg.get("grade") not in GRADES:
            bad.append("grade %r is not one of %s" % (msg.get("grade"), list(GRADES)))
        if not msg.get("source"):
            bad.append("no source")
    if msg.get("kind") == "band":
        lo, hi = msg.get("lo"), msg.get("hi")
        if lo is None or hi is None:
            bad.append("band with no lo/hi")
        elif lo > hi:
            bad.append("lo %g > hi %g" % (lo, hi))
        if not msg.get("unit"):
            bad.append("band with no unit")
    slot = msg.get("slot")
    if slot is not None:
        if slot.get("card") not in CARD_TABLES:
            bad.append("slot card %r is not %s"
                       % (slot.get("card"), list(CARD_TABLES)))
        if not isinstance(slot.get("index"), int):
            bad.append("slot index is not an integer")
    return bad


# ==========================================================================
# did the band actually get applied?
# ==========================================================================
def audit_rows(text, table):
    """Pull (index, lo, hi) out of one table in check_card_ranges.py.

    Parsed rather than imported: importing runs the whole audit, which
    reads a deck zip and is slow, and this script has to stay cheap enough
    to sit in front of every commit.
    """
    m = re.search(r"(?ms)^%s = \[(.*?)^\]" % table, text)
    if not m:
        return []
    rows = []
    for r in re.finditer(r"\(\s*(\d+)\s*,\s*\"[^\"]*\"\s*,\s*([-\w.eE+]+)\s*,"
                         r"\s*(None|[-\w.eE+]+)\s*,\s*(None|[-\w.eE+]+)\s*,",
                         m.group(1)):
        idx = int(r.group(1))
        try:
            lo = None if r.group(3) == "None" else float(r.group(3))
            hi = None if r.group(4) == "None" else float(r.group(4))
        except ValueError:
            continue
        rows.append((idx, lo, hi))
    return rows


def band_applied(msg, text):
    """True if check_card_ranges.py already carries this band.

    Returns (applied, detail).  A band whose slot is not in the table at
    all is a different message from one whose slot is there with a
    different range -- the second means somebody moved it.
    """
    slot = msg.get("slot")
    if not slot or msg.get("lo") is None:
        return None, "no slot to check"
    table = CARD_TABLES.get(slot.get("card"))
    rows = [r for r in audit_rows(text, table) if r[0] == slot.get("index")]
    if not rows:
        return False, "slot %s(%d) is not in the audit table" % (
            slot.get("card"), slot.get("index"))
    for idx, lo, hi in rows:
        if lo is None or hi is None:
            continue
        if (abs(lo - msg["lo"]) <= 1e-6 * max(1.0, abs(msg["lo"]))
                and abs(hi - msg["hi"]) <= 1e-6 * max(1.0, abs(msg["hi"]))):
            return True, "audit table carries %g-%g" % (lo, hi)
    have = ", ".join("%s-%s" % (lo, hi) for _, lo, hi in rows)
    return False, "audit table has %s, message says %g-%g" % (
        have, msg["lo"], msg["hi"])


# ==========================================================================
# the report
# ==========================================================================
def report(me, no_fetch=False, from_ref=None):
    """Print what the other side has said and return an exit code."""
    them = OTHER[me]
    meta = AGENTS[them]
    print("=" * 74)
    print("sync_check.py  --  나는 %s (%s), 상대는 %s (%s)"
          % (me, AGENTS[me]["role"], them, meta["role"]))
    print("=" * 74)

    if from_ref:
        # Reading a named commit rather than the branch tip.  Used to look at
        # what the other side said BEFORE a merge, and to exercise this path
        # in a test without touching the real branches.
        print("\n  (--from-ref %s)" % from_ref)
        head, rc = git("rev-parse", "--short", from_ref)
        print("  읽는 지점: %s" % (head.strip() if rc == 0 else "없는 ref"))
        box, err = read_outbox(from_ref if rc == 0 else None, them)
        return _report_box(me, them, box, err)

    ref = "origin/" + meta["branch"]
    if no_fetch:
        print("\n  (--no-fetch: 로컬에 있는 %s 만 본다)" % ref)
    else:
        ok, err = fetch(meta["branch"])
        if ok:
            print("\n  fetched %s" % meta["branch"])
        else:
            print("\n  !! fetch 실패 (%s).  로컬 사본으로 계속한다 --" % err)
            print("     네트워크 문제는 검증 실패가 아니지만, 아래 내용은")
            print("     최신이 아닐 수 있다.")

    head, rc = git("rev-parse", "--short", ref)
    print("  상대 브랜치 HEAD: %s"
          % (head.strip() if rc == 0 else "없음 (아직 push 안 됨?)"))

    box, err = read_outbox(ref if rc == 0 else None, them)
    return _report_box(me, them, box, err)


def owner_of(path):
    """Which agent's territory a path falls in, or None for shared."""
    for who, prefixes in TERRITORY.items():
        for p in prefixes:
            if path == p or path.startswith(p):
                return who
    return None


def territory_report(me):
    """Files in the OTHER agent's territory that this branch has changed.

    Measured from the merge base, so it answers "what have I done to their
    files since we last agreed", not "what is different right now" -- the
    latter would list everything they have done since, which is not this
    side's business.
    """
    them = OTHER[me]
    ref = "origin/" + AGENTS[them]["branch"]
    base, rc = git("merge-base", "HEAD", ref)
    if rc != 0:
        return None, "공통조상을 못 찾음 (상대 브랜치 없음?)"
    base = base.strip()
    out, rc = git("diff", "--name-only", base, "HEAD")
    if rc != 0:
        return None, "diff 실패"
    crossed = [f for f in out.split() if owner_of(f) == them]
    return crossed, base[:7]


def _report_box(me, them, box, err):
    """The part that is the same however the outbox was located."""
    if box is None:
        print("\n  %s 의 우편함이 아직 없다 (%s)." % (them, err))
        print("  상대가 sync/PROTOCOL.md 를 따라 %s 를 만들면 여기에 나온다."
              % outbox_path(them))
        return 0

    msgs = box.get("messages", [])
    state = load_state(me)
    already = set(state.get("read", []))
    fresh = [m for m in msgs if m.get("id") not in already]

    print("\n  %s 우편함: 총 %d통, 새 것 %d통" % (them, len(msgs), len(fresh)))

    bad_any, blocking = [], []
    ranges_text = io.open(os.path.join(ROOT, "verification",
                                       "check_card_ranges.py"),
                          encoding="utf-8").read()

    for m in msgs:
        problems = validate(m, them)
        if problems:
            bad_any.append((m.get("id"), problems))

    if bad_any:
        print("\n  형식이 깨진 메시지 (상대에게 알릴 것):")
        for mid, problems in bad_any:
            print("    %-10s %s" % (mid, "; ".join(problems)))

    if not fresh:
        print("\n  새 메시지 없음.")
    for m in fresh:
        mark = "!!" if m.get("blocking") else "  "
        print("\n  %s [%s] %s  (%s, %s)"
              % (mark, m.get("id"), m.get("subject"), m.get("kind"),
                 m.get("date")))
        for line in str(m.get("body", "")).splitlines():
            print("       %s" % line)
        if m.get("grade"):
            print("       등급: %s   출처: %s" % (m["grade"], m.get("source")))
            if m["grade"] == "secondary":
                print("       ** secondary 는 논문 인용 금지 (CLAUDE.md)")
        if m.get("action"):
            print("       -> 할 일: %s" % m["action"])
        if m.get("kind") == "band":
            applied, detail = band_applied(m, ranges_text)
            if applied is True:
                print("       ✓ 이미 반영됨: %s" % detail)
            elif applied is False:
                print("       ✗ 미반영: %s" % detail)
        if m.get("blocking"):
            blocking.append(m.get("id"))

    # A band that was acknowledged but never applied is the failure this
    # script exists to make visible.
    lapsed = []
    for m in msgs:
        if m.get("kind") != "band" or m.get("id") not in already:
            continue
        applied, detail = band_applied(m, ranges_text)
        if applied is False:
            lapsed.append((m.get("id"), m.get("subject"), detail))
    if lapsed:
        print("\n  ** ack 했는데 반영은 안 된 band (--ack 는 '반영했다'는 뜻이다):")
        for mid, subj, detail in lapsed:
            print("     %-10s %s" % (mid, subj))
            print("                %s" % detail)

    crossed, detail = territory_report(me)
    if crossed:
        print("\n  ** 내가 %s 영역 파일을 고쳤다 (공통조상 %s 이후):" % (them, detail))
        for f in crossed:
            print("     %s" % f)
        print("     고친 것이 맞다면 kind:\"changed\" 로 알려 줄 것 — 경고이지")
        print("     오류가 아니다. 공유 파일(제3~5장, data/properties/, CLAUDE.md)은")
        print("     여기 나오지 않는다.")

    print("\n" + "=" * 74)
    if blocking:
        print("BLOCKING 메시지 %d통이 미처리다: %s" % (len(blocking),
                                                 ", ".join(blocking)))
        print("읽고 조치한 뒤:  python3 sync/sync_check.py --ack %s"
              % " ".join(blocking))
        print("=" * 74)
        return 1
    if bad_any:
        print("형식 오류 %d건 -- 상대에게 알려야 하지만 커밋은 막지 않는다"
              % len(bad_any))
        print("=" * 74)
        return 0
    print("미처리 BLOCKING 없음 (새 메시지 %d통)" % len(fresh))
    print("=" * 74)
    return 0


def ack(me, ids, all_of_them=False, from_ref=None):
    them = OTHER[me]
    ref = from_ref or ("origin/" + AGENTS[them]["branch"])
    out, rc = git("rev-parse", "--verify", "--quiet", ref)
    box, err = read_outbox(ref if rc == 0 else None, them)
    if box is None:
        print("상대 우편함이 없다 (%s) -- ack 할 것이 없다." % err)
        return 1
    known = [m.get("id") for m in box.get("messages", [])]
    if all_of_them:
        ids = known
    unknown = [i for i in ids if i not in known]
    if unknown:
        print("그런 메시지가 없다: %s" % ", ".join(unknown))
        print("있는 것: %s" % ", ".join(known) if known else "(비어 있음)")
        return 1
    state = load_state(me)
    state["read"] = sorted(set(state.get("read", [])) | set(ids))
    state["branch"] = AGENTS[me]["branch"]
    save_state(me, state)
    print("기록함: %s" % ", ".join(ids))
    print("(--ack 는 '읽었다'가 아니라 '반영했다'는 뜻이다 -- PROTOCOL.md §4)")
    return 0


# ==========================================================================
# selftest -- deterministic, no network, so it can sit in the commit gate
# ==========================================================================
def selftest():
    print("sync_check.py selftest")
    fails = []

    def ck(name, cond, detail=""):
        if cond:
            print("  [PASS] %-56s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %-56s %s" % (name, detail))

    # ---- the ownership table is the entire conflict-freedom argument ----
    owners = {}
    proto = io.open(os.path.join(HERE, "PROTOCOL.md"), encoding="utf-8").read()
    for m in re.finditer(r"\| `(sync/[\w./]+)` \| \*\*(a1|a2)\*\* \|", proto):
        owners[m.group(1)] = m.group(2)
    ck("PROTOCOL.md declares an owner for every sync file",
       len(owners) == 6, "%d files" % len(owners))
    ck("each agent owns its own outbox and state",
       owners.get("sync/outbox_a1.json") == "a1"
       and owners.get("sync/state_a1.json") == "a1"
       and owners.get("sync/outbox_a2.json") == "a2"
       and owners.get("sync/state_a2.json") == "a2")
    ck("no file has two owners", len(set(owners)) == len(owners))
    on_disk = sorted(f for f in os.listdir(HERE) if not f.startswith("."))
    ck("every file on disk is in the ownership table",
       all(("sync/" + f) in owners for f in on_disk),
       ", ".join(f for f in on_disk if ("sync/" + f) not in owners) or "all listed")

    # ---- both agents must be resolvable, and never to the same box ----
    ck("a1 and a2 have different branches",
       AGENTS["a1"]["branch"] != AGENTS["a2"]["branch"])
    ck("OTHER is an involution and has no fixed point",
       OTHER[OTHER["a1"]] == "a1" and OTHER["a1"] != "a1")

    # ---- validation has to reject, not just accept ----
    good = dict(id="a1-0001", date="2026-08-04", kind="band",
                subject="s", body="b", action="a", grade="fulltext",
                source="refs/[08]", lo=475.0, hi=1815.0, unit="MPa",
                slot=dict(card="yarn", index=11))
    ck("a well-formed band passes", validate(good, "a1") == [])

    def mangled(**kw):
        d = dict(good)
        d.update(kw)
        return d

    for name, msg, sender in (
            ("id in the wrong namespace", mangled(id="a2-0001"), "a1"),
            ("id not zero-padded", mangled(id="a1-1"), "a1"),
            ("date not ISO", mangled(date="8/4/2026"), "a1"),
            ("a2-only kind sent by a1", mangled(kind="need"), "a1"),
            ("a1-only kind sent by a2", mangled(kind="band"), "a2"),
            ("band with no grade", mangled(grade=None), "a1"),
            ("band with an invented grade", mangled(grade="probably"), "a1"),
            ("band with no source", mangled(source=""), "a1"),
            ("band with lo > hi", mangled(lo=2000.0, hi=475.0), "a1"),
            ("band with no unit", mangled(unit=""), "a1"),
            ("blocking with no action", mangled(blocking=True, action=""), "a1"),
            ("slot naming a table that does not exist",
             mangled(slot=dict(card="tow", index=11)), "a1"),
            ("slot index that is not an integer",
             mangled(slot=dict(card="yarn", index="11")), "a1"),
            ("missing body", mangled(body=""), "a1"),
    ):
        ck("rejects: %s" % name, validate(msg, sender) != [],
           "; ".join(validate(msg, sender))[:44])

    # The relaxation itself, asserted rather than assumed: a literature
    # agent reporting a finding is the normal case, not a malformed one.
    for kind in KINDS_BOTH:
        for sender in ("a1", "a2"):
            m = mangled(kind=kind, id="%s-0001" % sender)
            m.pop("lo", None)
            m.pop("hi", None)
            ck("accepts: %-8s from %s" % (kind, sender),
               validate(m, sender) == [], "; ".join(validate(m, sender))[:40])

    # ---- the applied-band lookup has to read the real audit table ----
    text = io.open(os.path.join(ROOT, "verification", "check_card_ranges.py"),
                   encoding="utf-8").read()
    yarn = audit_rows(text, "YARN")
    matrix = audit_rows(text, "MATRIX")
    ck("audit table parses", len(yarn) > 0 and len(matrix) > 0,
       "%d yarn rows, %d matrix rows" % (len(yarn), len(matrix)))
    applied, detail = band_applied(good, text)
    ck("the yarn Xt band already in the table is seen as applied",
       applied is True, detail)
    moved = mangled(lo=475.0, hi=1900.0)
    applied, detail = band_applied(moved, text)
    ck("a band with a different hi is seen as NOT applied",
       applied is False, detail)
    absent = mangled(slot=dict(card="matrix", index=99))
    applied, detail = band_applied(absent, text)
    ck("a band for a slot that is not audited is seen as NOT applied",
       applied is False, detail)

    # ---- territory, absorbed from a1's check_branch_sync.py (a1-0004) ----
    ck("territory is declared for both agents", set(TERRITORY) == {"a1", "a2"})
    ck("a1 owns the references and the literature chapters",
       owner_of("refs/[28] Part 1.pdf") == "a1"
       and owner_of("docs/CH2_LITERATURE_REVIEW.md") == "a1"
       and owner_of("data/literature/csic_2d_offaxis.csv") == "a1")
    ck("a2 owns the solver, the decks and the checkers",
       owner_of("src/UMAT_CSIC_THERMSHOCK_V3_0.for") == "a2"
       and owner_of("abaqus/make_macro_thermalshock.py") == "a2"
       and owner_of("verification/check_card_ranges.py") == "a2")
    # The shared files are the point: both agents edit the middle chapters and
    # the property scripts, and warning about those would train everyone to
    # ignore the warning.
    for shared in ("docs/CH4_RVE_HOMOGENISATION.md", "CLAUDE.md",
                   "data/properties/porosity_stiffness.py",
                   "docs/THESIS_PLAN.md"):
        ck("shared, never warned: %s" % shared, owner_of(shared) is None)
    ck("no path can belong to both agents",
       not any(owner_of(p) == "a1" for p in TERRITORY["a2"])
       and not any(owner_of(p) == "a2" for p in TERRITORY["a1"]))
    ck("the sync ownership table and the territory table agree",
       owner_of("sync/outbox_a1.json") == "a1"
       and owner_of("sync/sync_check.py") == "a2")

    # ---- our own outbox must itself be legal ----
    box, err = read_outbox(None, "a2")
    ck("outbox_a2.json parses", box is not None, err)
    if box is not None:
        ck("outbox_a2.json declares itself as a2", box.get("agent") == "a2")
        ck("outbox_a2.json names this branch",
           box.get("branch") == AGENTS["a2"]["branch"])
        ids = [m.get("id") for m in box.get("messages", [])]
        ck("message ids are unique", len(ids) == len(set(ids)))
        ck("message ids are in order", ids == sorted(ids), ", ".join(ids))
        # One assertion for the whole mailbox, not one per message.  Counting
        # per message made the selftest total grow every time mail was sent,
        # which put Ch.3's verification count out of date on each send.
        broken = [(m.get("id"), validate(m, "a2"))
                  for m in box.get("messages", [])]
        broken = [(i, p) for i, p in broken if p]
        ck("every outgoing message is well formed (%d checked)" % len(ids),
           not broken,
           "; ".join("%s: %s" % (i, ", ".join(p)) for i, p in broken)
           or "all clean")

    if fails:
        print("\nSELFTEST FAILED: %s" % ", ".join(fails[:4]))
        return 1
    print("\nSELFTEST PASSED")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="두 에이전트 브랜치 사이의 우편함 (sync/PROTOCOL.md)")
    ap.add_argument("--ack", nargs="+", metavar="ID",
                    help="이 메시지들을 '반영했다'고 기록")
    ap.add_argument("--ack-all", action="store_true")
    ap.add_argument("--no-fetch", action="store_true",
                    help="네트워크를 쓰지 않고 로컬 사본만 본다")
    ap.add_argument("--from-ref", metavar="REF",
                    help="브랜치 끝이 아니라 지정한 커밋의 우편함을 읽는다 "
                         "(병합 전 시점 확인용)")
    ap.add_argument("--as", dest="as_agent", choices=sorted(AGENTS),
                    help="브랜치로 자동 판별되지 않을 때만")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    me, branch = whoami()
    if args.as_agent:
        me = args.as_agent
    if me is None:
        print("현재 브랜치 %r 는 어느 에이전트의 것도 아니다." % branch)
        print("등록된 브랜치:")
        for who, meta in sorted(AGENTS.items()):
            print("  %s  %s  (%s)" % (who, meta["branch"], meta["role"]))
        print("\n일부러 다른 브랜치에서 보려면 --as a1 / --as a2 를 준다.")
        return 1

    if args.ack or args.ack_all:
        return ack(me, args.ack or [], all_of_them=args.ack_all,
                   from_ref=args.from_ref)
    return report(me, no_fetch=args.no_fetch, from_ref=args.from_ref)


if __name__ == "__main__":
    sys.exit(main())
