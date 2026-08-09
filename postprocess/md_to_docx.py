#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_to_docx.py  --  combine the thesis chapters into one Word (.docx) file
=========================================================================
The user reviews the full draft in Word (their request, 2026-08-07), so
unlike md_to_pdf.py -- which unwraps $...$ into plain glyphs because those
are phone-reading PDFs -- this keeps the math and lets pandoc turn it into
native Word equations (OMML).

  chapters   docs/CH1_*.md ... CH7_*.md, numeric order, auto-discovered
  cover      generated live: chapter titles from each file's first heading,
             pending-result slot counts COUNTED from the files, the ledger
             total READ from Ch.3's own table -- nothing on the cover is
             hand-typed, so nothing on it can go stale
  page flow  one page break between the cover and every chapter
  engine     pandoc via pypandoc (pip install pypandoc-binary).  Hard
             dependency, no silent fallback: a half-converted file that
             looks like the deliverable is worse than an error.

Run:
    python3 postprocess/md_to_docx.py
    python3 postprocess/md_to_docx.py --name 논문초안_제1-7장 --stamp 0807_1810
    python3 postprocess/md_to_docx.py --selftest
"""
from __future__ import print_function

import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from md_to_pdf import kst_stamp, loosen_lists  # noqa: E402

#: docs/THESIS_PLAN.md calls this the draft topic; the cover labels it 가제.
TITLE = ("C/SiC 복합재의 반복 열충격에 의한 강성·강도 열화 예측 — "
         "열잔류응력(TRS) 모델링 방식의 영향을 중심으로 한 2-스케일 CDM 해석")
BRANCH = "claude/paper-reference-research-pksw5p"

#: raw OpenXML page break; needs the raw_attribute extension (pandoc default)
PAGE_BREAK = ('\n\n```{=openxml}\n'
              '<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n'
              '```\n\n')


#: bar characters preceded by one of these are structural, not abs-value
_BAR_KEEP = ("\\left", "\\right", "\\big", "\\Big", "\\bigl", "\\bigr",
             "\\Bigl", "\\Bigr", "\\bigm", "\\Bigm", "\\")


def _fix_body(body):
    """Normalise one math snippet so its OMML renders outside Word too.

    Found by rendering the real draft through LibreOffice and hunting the
    inverted question marks; each rule below is one observed breakage.
    Everything rewrites to \\left ... \\right delimiters, which are the
    same OMML element as \\left( -- verified to render in both readers.
    """
    body = body.replace("\\lvert", "\\left|").replace("\\rvert", "\\right|")
    # evaluated-at bar:  f \big|_{x}  ->  f \left.\right|_{x}
    body = body.replace("\\big|_", "\\left.\\right|_")
    # superscripted bracket:  [x]^{n}  chokes, \exp[x] alone is fine
    body = re.sub(r"\[([^][]*)\]\^", r"\\left[\1\\right]^", body)
    # half-open interval [0,1)
    body = re.sub(r"\[([0-9, .]+)\)", r"\\left[\1\\right)", body)
    # pair the remaining bare |...| as delimiters, left to right
    bare = [i for i, c in enumerate(body) if c == "|"
            and not body[:i].endswith(_BAR_KEEP)]
    if bare and len(bare) % 2 == 0:
        out, opened = list(body), False
        for i in bare:
            out[i] = "\\right|" if opened else "\\left|"
            opened = not opened
        body = "".join(out)
    return body


def fix_math(text):
    """Apply _fix_body inside every $...$ / $$...$$, and nowhere else.

    Fenced code blocks are passed through untouched -- a $ in a shell
    snippet is not math, and rewriting it would corrupt the command."""
    def one(m):
        if m.group(1) is not None:
            return "$$" + _fix_body(m.group(1)) + "$$"
        body = _fix_body(m.group(2))
        # "$= x$" starts with a binary operator no renderer likes; the
        # "=" reads identically as plain text, so hoist it out
        if body.lstrip().startswith("="):
            return "= $" + body.lstrip()[1:].lstrip() + "$"
        return "$" + body + "$"

    out = []
    for seg in re.split(r"(^```.*?^```[ \t]*$)", text, flags=re.M | re.S):
        if seg.startswith("```"):
            out.append(seg)
        else:
            out.append(re.sub(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$", one, seg,
                              flags=re.S))
    return "".join(out)


def find_chapters(root=ROOT):
    docs = os.path.join(root, "docs")
    out = []
    for f in os.listdir(docs):
        m = re.match(r"CH([1-7])_[A-Z_]+\.md$", f)
        if m:
            out.append((int(m.group(1)), os.path.join(docs, f)))
    out.sort()
    return [p for _, p in out]


def first_heading(text):
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "(제목 없음)"


def ledger_total(root=ROOT):
    """Ch.3's own grand total -- same regex check_ch3_numbers.py uses."""
    p = os.path.join(root, "docs", "CH3_VERIFICATION.md")
    if not os.path.exists(p):
        return None
    m = re.search(r"\*\*합계\*\*[^|]*\|[^|]*\|\s*\*\*(\d+)\*\*",
                  open(p, encoding="utf-8").read())
    return int(m.group(1)) if m else None


FIG_SLOT = re.compile(r"\[(?:그림|표) \d+\.\w+ 자리\]")


def build_cover(chapter_paths, stamp):
    rows, unresolved = [], 0
    for p in chapter_paths:
        txt = open(p, encoding="utf-8").read()
        rows.append((first_heading(txt),
                     len(re.findall(r"\[결과 대기", txt)),
                     len(FIG_SLOT.findall(txt))))
        unresolved += txt.count("미확정 1건")
    lines = [
        "# 논문 초안 — 제1–7장 합본",
        "",
        "**제목(가제):** " + TITLE,
        "",
        "**생성:** %s (KST) · 브랜치 `%s` · CDM-UMAT" % (stamp, BRANCH),
        "",
        "| 장 | `[결과 대기]` 자리 | 그림·표 자리 |",
        "|---|---|---|",
    ]
    for title, n, nf in rows:
        lines.append("| %s | %d | %d |" % (title, n, nf))
    lines += [
        "",
        "- 해석 결과 수치는 아직 없다(M1 병목, 거시 매트릭스 실행 전). 결과가",
        "  들어갈 자리는 본문에 `[결과 대기 — …]`로 표시되어 있고, 위 표의",
        "  개수가 그 전부다. 그 밖의 모든 수치는 문헌·코드·덱에서 이미 확정된",
        "  값이다.",
        "- 그림·그래프·표가 들어갈 자리는 본문에 `[그림 N.M 자리]` 상자로 표시했다.",
        "  상자마다 **내용 / 재료(무엇으로 만드는지) / 제작 가능 시점**을 적었다 —",
        "  \"지금 제작 가능\"은 해석 결과 없이도 만들 수 있는 그림이다.",
    ]
    if unresolved:
        lines += [
            "- 검증 표적 중 **미확정 %d건**(제6장 §6.2.3: 굽힘 프로브, "
            "$H_{clo}$ 대조 잡)은" % unresolved,
            "  해석 세션(a2)의 판정을 기다리는 중이다.",
        ]
    total = ledger_total()
    if total:
        lines += [
            "- 본문 수치는 저장소의 자동 검증 **%d개 항목**(제3장 §3.1 장부)"
            % total,
            "  으로 커밋마다 고정된다.",
        ]
    return "\n".join(lines) + "\n"


def combine(chapter_paths, stamp):
    parts = [build_cover(chapter_paths, stamp)]
    for p in chapter_paths:
        parts.append(loosen_lists(open(p, encoding="utf-8").read()))
    return fix_math(PAGE_BREAK.join(parts))


def verify(path, nparts):
    """Static checks on the produced docx; raises if it is not deliverable."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))
    stats = dict(
        hangul=len(re.findall(u"[가-힣]", text)),
        breaks=xml.count('<w:br w:type="page"/>'),
        omath=xml.count("<m:oMath"),
        stray_dollar=text.count("$"),
        kb=os.path.getsize(path) // 1024,
    )
    problems = []
    if stats["hangul"] < 1000:
        problems.append("almost no Hangul survived (%d)" % stats["hangul"])
    if stats["breaks"] != nparts - 1:
        problems.append("expected %d page breaks, found %d"
                        % (nparts - 1, stats["breaks"]))
    if "<<<<<<<" in text:
        problems.append("a merge-conflict marker reached the document")
    if problems:
        raise RuntimeError("docx failed verification: " + "; ".join(problems))
    return stats


def convert(name=None, stamp=None, outdir=None, chapter_paths=None):
    import pypandoc
    stamp = stamp or kst_stamp()
    name = name or "논문초안_제1-7장"
    outdir = outdir or os.path.join(ROOT, "dist")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    chapter_paths = chapter_paths or find_chapters()
    out = os.path.join(outdir, "%s_%s.docx" % (name, stamp))
    pypandoc.convert_text(
        combine(chapter_paths, stamp), "docx", format="markdown",
        outputfile=out,
        extra_args=["--resource-path", os.path.join(ROOT, "docs")])
    return out, verify(out, nparts=1 + len(chapter_paths))


# --------------------------------------------------------------------------
def selftest():
    """Logic checks everywhere; the pandoc round-trip only where it can run.

    Same shape as md_to_pdf.py --selftest: the check COUNT must not depend on
    the container, so the two pandoc-dependent lines report SKIP instead of
    disappearing when pypandoc is not installed.
    """
    ok, skipped = [], []

    def t(name, cond, detail=""):
        ok.append(cond)
        print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("md_to_docx.py --selftest")

    chapters = find_chapters()
    t("all seven chapters are discovered in order",
      len(chapters) == 7 and
      [int(re.search(r"CH(\d)_", os.path.basename(p)).group(1))
       for p in chapters] == list(range(1, 8)),
      ", ".join(os.path.basename(p) for p in chapters))

    t("first_heading reads the h1",
      first_heading("# 제1장 서론\n본문") == "제1장 서론")

    cover = build_cover(chapters, "0101_0000")
    t("cover carries the draft title marked 가제",
      "가제" in cover and TITLE in cover)
    ch6 = open(chapters[5], encoding="utf-8").read()
    n_unres = ch6.count("미확정 1건")
    t("cover's unresolved count is counted, not typed",
      ("미확정 %d건" % n_unres in cover) if n_unres
      else "미확정" not in cover, "%d in Ch.6" % n_unres)
    total = ledger_total()
    t("cover's ledger total is read from Ch.3 itself",
      total is not None and ("%d개 항목" % total) in cover, str(total))

    t("the page break is a raw openxml block",
      'w:type="page"' in PAGE_BREAK and "{=openxml}" in PAGE_BREAK)

    fixed = fix_math(r"$\frac{|\tilde\sigma_{11}|}{X_c}$, $\lvert C\rvert$, "
                     r"$= 6^{1/3}$, $d \in [0,1)$, $[x/(E\alpha^2)]^{1/2}$")
    t("math snippets are normalised for non-Word renderers",
      r"{\left|\tilde\sigma_{11}\right|}" in fixed
      and "\\lvert" not in fixed
      and "= $6^{1/3}$" in fixed
      and r"\left[0,1\right)" in fixed
      and r"\left[x/(E\alpha^2)\right]^" in fixed)
    t("KST stamp is MMDD_HHMM",
      bool(re.match(r"^\d{4}_\d{4}$", kst_stamp())))

    try:
        import pypandoc  # noqa: F401
        have = True
    except ImportError:
        have = False
    if have:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="md2docx_")
        src = os.path.join(tmp, "CH1_TEST.md")
        with open(src, "w", encoding="utf-8") as f:
            f.write("# 한글 장\n\n수식 $\\bar G_f = 2$ 와 표.\n\n"
                    "| 항목 | 값 |\n|---|---|\n"
                    + "| 공극률과 손상 변수 | 십 퍼센트 |\n" * 200)
        try:
            out, st = convert(name="t", stamp="0101_0000", outdir=tmp,
                              chapter_paths=[src])
            t("a docx is produced and verified", st["kb"] > 5,
              "%(kb)d kB, %(hangul)d hangul" % st)
            t("inline math became a Word equation", st["omath"] >= 1,
              "%d oMath" % st["omath"])
        except Exception as exc:                            # noqa: BLE001
            t("a docx is produced and verified", False, str(exc)[:100])
            t("inline math became a Word equation", False)
    else:
        for name in ("a docx is produced and verified",
                     "inline math became a Word equation"):
            skipped.append(name)
            print("  SKIP  %-52s %s" % (name, "pypandoc not installed"))

    if skipped:
        print("\n  %d skipped (environment, not code): pip install "
              "pypandoc-binary" % len(skipped))
    print("\n%s" % ("ALL %d SELFTESTS PASS" % len(ok) if all(ok)
                    else "FAILED %d of %d" % (ok.count(False), len(ok))))
    return 0 if all(ok) else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    name = stamp = None
    i = 0
    while i < len(argv):
        if argv[i] == "--name":
            name = argv[i + 1]
            i += 2
        elif argv[i] == "--stamp":
            stamp = argv[i + 1]
            i += 2
        else:
            i += 1
    out, stats = convert(name=name, stamp=stamp)
    print("wrote %s" % out)
    print("  %(kb)d kB · hangul %(hangul)d · page breaks %(breaks)d · "
          "equations %(omath)d · stray $ %(stray_dollar)d" % stats)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
