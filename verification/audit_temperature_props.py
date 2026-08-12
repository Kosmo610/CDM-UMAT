# -*- coding: utf-8 -*-
"""온도 의존 물성 감사 (Zhang 2022 재현용)

질문: **온도가 우리 모델의 물성에 실제로 영향을 주는가?**
      그리고 논문 Table 1/2 에 우리가 안 쓴 온도 의존값이 있는가?

해석을 새로 돌리지 않고 소스와 덱만 읽어서 답한다. 세 가지를 본다.

  (1) UMAT 오염추적(taint) — TEMP/DTEMP 에서 출발해 대입문을 따라가며
      "온도에서 유래한 변수" 집합을 닫힐 때까지 넓힌다. 그 집합이
      물성변수나 STRESS/CTAN 에 닿으면 온도 의존, 상태변수(SV)에만
      닿으면 진단용일 뿐이다.
  (2) 덱 물성카드 — 온도표(추가 데이터행/`dependencies=`)를 가진
      카드가 있는지. `*User Material` 은 Abaqus 문법상 온도표를 가질
      수 없다는 점도 같이 확인한다.
  (3) 논문 Table 1/2 재고 — 논문이 온도 의존으로 준 값이 있는지.

사용법:

    python verification/audit_temperature_props.py \
        src/UMAT_CSIC_RVE_DAMAGE_V2_7P.for abaqus/ZHANG2022_T1000_V2_0.inp

덱은 여러 개 줘도 된다. 인자를 안 주면 저장소 기본값을 쓴다.
"""

import os
import re
import sys

# ---------------------------------------------------------------- (1) UMAT

# 고정형식: 1열 C/c/*/! 은 주석, 6열이 공백/0 이 아니면 계속행.
def read_fixed_form(path):
    """고정형식 Fortran 을 '논리적 한 문장' 리스트로 만든다.

    반환: [(첫줄번호, 합쳐진 문장), ...]  — 주석 제거, 72열 절단 반영.
    """
    stmts = []
    with open(path, 'r') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip('\n').rstrip('\r')
            if not line.strip():
                continue
            if line[0] in 'CcDd*!':
                continue
            body = line[6:72] if len(line) > 6 else ''
            cont = len(line) > 5 and line[5] not in (' ', '0')
            if cont and stmts:
                stmts[-1] = (stmts[-1][0], stmts[-1][1] + body)
            else:
                stmts.append((lineno, body))
    return stmts


DECL = re.compile(r'^\s*(DOUBLE\s+PRECISION|REAL|INTEGER|LOGICAL|CHARACTER'
                  r'|IMPLICIT|SUBROUTINE|FUNCTION|COMMON|DIMENSION|PARAMETER'
                  r'|SAVE|EXTERNAL|INCLUDE|END|CALL)\b', re.I)
SUBHEAD = re.compile(r'^\s*SUBROUTINE\s+([A-Z][A-Z0-9_]*)', re.I)
# 한 줄 IF: `IF (...) 실행문` 에서 실행문만 떼어낸다.
IFPREFIX = re.compile(r'^\s*IF\s*\(', re.I)
ASSIGN = re.compile(r'^\s*([A-Z][A-Z0-9_]*)\s*(\([^()]*\))?\s*=(?!=)(.*)$', re.I)
# 식별자 + (선택) 괄호 첨자. 첨자가 정수 리터럴이면 원소 단위로 구분한다.
REF = re.compile(r'([A-Z][A-Z0-9_]*)\s*(\(\s*(\d+)\s*\))?', re.I)

# 물성/거동에 닿으면 "온도 의존" 이라고 판정할 이름들.
PROPERTY_NAMES = set("""E E1 E2 E3 NU NU12 NU13 NU23 G12 G13 G23
XT XC YT YC S12 S13 S23 AT AC A1T A1C ATT ATC
DMAXT DMAXC DMAX1 ETA GFT GF1T C0 CD CTAN STRESS DDSDDE""".split())
ARRAYS = ('SV', 'STATEV', 'P', 'PROPS')     # 원소 단위로 추적할 배열


def strip_if(stmt):
    """한 줄 IF 의 조건부를 떼고 실행문만 돌려준다 (없으면 그대로)."""
    if not IFPREFIX.match(stmt):
        return stmt
    i = stmt.index('(')
    depth = 0
    for j in range(i, len(stmt)):
        if stmt[j] == '(':
            depth += 1
        elif stmt[j] == ')':
            depth -= 1
            if depth == 0:
                return stmt[j + 1:]
    return stmt


def refs(expr):
    """식 안의 참조를 정규화한다. 정수 첨자면 `SV(12)`, 아니면 `SV`."""
    out = set()
    for name, _, idx in REF.findall(expr):
        name = name.upper()
        if idx and name in ARRAYS:
            out.add('%s(%s)' % (name, idx))
        else:
            out.add(name)
    return out


def split_subroutines(stmts):
    """[(루틴명, [(줄번호, 문장), ...]), ...] 로 나눈다."""
    routines, cur = [], None
    for lineno, s in stmts:
        m = SUBHEAD.match(s)
        if m:
            cur = (m.group(1).upper(), [])
            routines.append(cur)
        if cur is not None:
            cur[1].append((lineno, s))
    return routines


def taint_routine(stmts):
    """한 루틴 안에서 TEMP/DTEMP 오염 전파. (오염집합, 증거) 반환."""
    tainted = set(['TEMP', 'DTEMP'])
    evidence, seen = [], set()
    changed = True
    while changed:                      # 고정점까지 반복
        changed = False
        for lineno, s in stmts:
            if DECL.match(s):
                continue
            body = strip_if(s)
            m = ASSIGN.match(body)
            if not m:
                continue
            lhs, sub, rhs = m.group(1).upper(), m.group(2) or '', m.group(3)
            if not (refs(rhs) & tainted):
                continue
            idx = re.match(r'\(\s*(\d+)\s*\)$', sub.replace(' ', ''))
            if idx and lhs in ARRAYS:
                target = '%s(%s)' % (lhs, idx.group(1))
            else:
                target = lhs            # 배열 첨자가 변수면 이름 단위로
            if target not in tainted:
                tainted.add(target)
                changed = True
            if (lineno, target) not in seen:
                seen.add((lineno, target))
                evidence.append((lineno, body.strip(), target))
    return tainted, evidence


def taint_umat(path):
    """루틴별 오염추적. [(루틴명, 오염집합, 증거), ...] 반환."""
    routines = split_subroutines(read_fixed_form(path))
    out = []
    for name, stmts in routines:
        joined = ' '.join(s for _, s in stmts).upper()
        if 'TEMP' not in joined:
            continue
        tainted, evidence = taint_routine(stmts)
        out.append((name, tainted, evidence))
    return out


def classify(tainted):
    """오염된 좌변을 '물성/거동' 과 '상태변수(진단)' 로 나눈다."""
    hits, diag = [], []
    for name in sorted(tainted):
        if name in ('TEMP', 'DTEMP'):
            continue
        base = name.split('(')[0]
        if base in PROPERTY_NAMES:
            hits.append(name)
        else:
            diag.append(name)
    return hits, diag


# ---------------------------------------------------------------- (2) 덱

KW = re.compile(r'^\s*\*\s*([A-Za-z ]+?)\s*(,|$)')
# 온도표를 가질 수 있는 카드 = 물성 카드 전반.
PROP_CARDS = ('elastic', 'expansion', 'density', 'plastic', 'conductivity',
              'specific heat', 'damping', 'user material', 'depvar')


def audit_deck(path):
    """물성 블록별로 카드와 데이터행 수를 센다."""
    mats = []               # [(재료명, [(카드, 옵션, 데이터행수, 첫줄), ...])]
    cur = None
    card = None
    with open(path, 'r', errors='replace') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip()
            if line.startswith('**') or not line.strip():
                continue
            if line.lstrip().startswith('*'):
                m = KW.match(line)
                name = (m.group(1) if m else '').strip().lower()
                if name == 'material':
                    mm = re.search(r'name\s*=\s*([^,\s]+)', line, re.I)
                    cur = (mm.group(1) if mm else '?', [])
                    mats.append(cur)
                    card = None
                elif cur is not None and name in PROP_CARDS:
                    opts = line.split(',', 1)[1].strip() if ',' in line else ''
                    card = [name, opts, 0, lineno]
                    cur[1].append(card)
                else:
                    card = None         # 다른 키워드가 나오면 카드 종료
                    if name in ('solid section', 'step', 'assembly', 'part'):
                        cur = None
            elif card is not None:
                card[2] += 1
    return mats


# ---------------------------------------------------------------- (3) 논문

# Zhang 2022 Table 1 (T300 섬유) / Table 2 (SiC 기지).
# 4번째 열 = 논문이 그 값을 온도의 함수로 줬는가.
PAPER = [
    ('Table 1', 'E_f1',      '230 GPa',     False),
    ('Table 1', 'E_f2=E_f3', '40 GPa',      False),
    ('Table 1', 'G_f12',     '24 GPa',      False),
    ('Table 1', 'G_f23',     '14.3 GPa',    False),
    ('Table 1', 'nu_f12',    '0.26',        False),
    ('Table 1', 'X_f,t',     '3580 MPa',    False),
    ('Table 1', 'X_f,c',     '2470 MPa',    False),
    ('Table 1', 'alpha_f1',  '-0.3e-6 /K',  False),
    ('Table 1', 'alpha_f2',  '3.1e-6 /K',   False),
    ('Table 2', 'E_m',       '350 GPa',     False),
    ('Table 2', 'G_m',       '146 GPa',     False),
    ('Table 2', 'nu_m',      '0.20',        False),
    ('Table 2', 'X_m,t=X_m,c', '310 MPa',   False),
    ('Table 2', 'alpha_m',   '4.5e-6 /K',   False),
]


def selftest(umat):
    """음성 대조 — 온도 의존을 일부러 심으면 정말 잡히는가.

    "0 건" 이라는 판정은 감사기가 무엇이든 잡을 수 있을 때만 의미가
    있다. 원본을 메모리에서 변이시켜 검출되는지 확인한다.
    """
    import tempfile
    src = open(umat).read().split('\n')
    out = []
    for ln in src:
        out.append(ln)
        if ln.startswith('      TEND=TEMP+DTEMP'):
            out.append('      E=E*(1.0D0-1.0D-4*TEND)')      # 심은 결함
    fd, path = tempfile.mkstemp(suffix='.for')
    os.close(fd)
    with open(path, 'w') as fh:
        fh.write('\n'.join(out))
    try:
        found = []
        for _, tainted, _ in taint_umat(path):
            found += classify(tainted)[0]
        ok = 'E' in found
        print('  변이체에서 검출된 물성: %s' % (', '.join(sorted(set(found)))
                                              or '없음'))
        print('  음성 대조: %s' % ('통과 — 감사기가 실제로 잡는다' if ok
                                 else '**실패 — 감사기를 믿을 수 없다**'))
        return 0 if ok else 1
    finally:
        os.remove(path)


def main(argv):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    args = [a for a in argv[1:] if a != '--selftest']
    do_self = '--selftest' in argv[1:]
    if args:
        umat, decks = args[0], args[1:]
    else:
        umat = os.path.join(here, 'src', 'UMAT_CSIC_RVE_DAMAGE_V2_7P.for')
        decks = [os.path.join(here, 'abaqus', d) for d in
                 ('ZHANG2022_RT23_V2_0.inp', 'ZHANG2022_T500_V2_0.inp',
                  'ZHANG2022_T1000_V2_0.inp')]

    print('=' * 68)
    print('(1) UMAT 오염추적 — TEMP/DTEMP 가 어디까지 번지는가')
    print('    %s' % umat)
    print('=' * 68)
    hits = []
    for name, tainted, evidence in taint_umat(umat):
        h, diag = classify(tainted)
        hits += h
        print('  [%s]' % name)
        for lineno, stmt, target in evidence:
            print('    L%-5d %-44s -> %s' % (lineno, stmt[:44], target))
        print('    물성/거동에 닿는 것 : %s' % (', '.join(h) if h else '없음'))
        print('    상태변수/진단만     : %s' % (', '.join(diag) or '없음'))
        print()
    print('  판정: %s' % ('온도 의존 물성 있음 (위 목록 확인)' if hits else
                        '**온도 의존 물성 0 건.** TEMP/DTEMP 는 손상개시온도'
                        ' 기록에만 쓰인다'))
    if do_self:
        print()
        if selftest(umat):
            return 2

    print()
    print('=' * 68)
    print('(2) 덱 물성카드 — 온도표를 가진 카드가 있는가')
    print('=' * 68)
    any_table = False
    for deck in decks:
        if not os.path.exists(deck):
            print('  (없음) %s' % deck)
            continue
        print('  %s' % os.path.basename(deck))
        for name, cards in audit_deck(deck):
            print('    재료 %s' % name)
            for card, opts, nrow, lineno in cards:
                dep = 'dependencies' in opts.lower()
                temp_table = (card in ('elastic', 'expansion', 'density',
                                       'conductivity') and nrow > 1) or dep
                any_table = any_table or temp_table
                flag = '<-- 온도표' if temp_table else '상수'
                print('      L%-7d *%-14s 데이터행 %-3d %-9s %s'
                      % (lineno, card, nrow, flag, opts[:28]))
        print()
    print('  판정: %s' % ('온도표 있음' if any_table else
                        '**온도표 0 건.** 모든 물성이 전 온도 공통 상수다'))
    print('  참고: `*User Material` 은 Abaqus 문법상 온도표를 못 가진다.')
    print('        UMAT 물성을 온도 의존으로 만들려면 (1) 처럼 코드 안에서')
    print('        TEMP 로 직접 보간하는 수밖에 없다 — 지금은 안 한다.')

    print()
    print('=' * 68)
    print('(3) 논문 Table 1/2 — 논문이 온도 의존으로 준 값이 있는가')
    print('=' * 68)
    ndep = 0
    for tbl, sym, val, dep in PAPER:
        ndep += bool(dep)
        print('  %-8s %-12s %-12s %s' % (tbl, sym, val,
                                         '온도 의존' if dep else '단일값'))
    print()
    print('  논문 온도 의존 항목 %d / %d' % (ndep, len(PAPER)))
    print('  판정: %s' % ('논문에 온도 의존값 있음' if ndep else
                        '**논문도 전부 단일값.** 3.2.3 절이 alpha_m 을 명시적'
                        '으로 "temperature independent" 라 적는다'))

    print()
    print('=' * 68)
    print('종합')
    print('=' * 68)
    if not hits and not any_table and not ndep:
        print('  우리 모델 온도 의존 물성 0, 논문 온도 의존 물성 0 —')
        print('  **양쪽이 일치한다. "고온 물성 누락" 가설은 기각된다.**')
        print('  논문의 온도 강화(+55 %)는 물성이 아니라 오직')
        print('  열잔류응력 이력에서 나올 수밖에 없다.')
        return 0
    print('  불일치 발견 — 위 (1)(2)(3) 판정 참조.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
