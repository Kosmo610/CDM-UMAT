#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""덱의 *얀* *Depvar* 만 16 -> 17 로 올린다 (V2_7D 진단 SDV17 용).

왜 sed 한 줄이면 안 되는가
--------------------------
덱 하나에 *Depvar 가 두 개 있다. 기지 20, 얀 16. `16,` 를 통째로
치환하면 노드/요소 데이터의 숫자까지 바꿔서 메쉬가 조용히 깨진다.
이 스크립트는 UMAT 과 같은 규칙으로 재료를 고른다 --
UMAT 은 `INDEX(CMNAME,'YARN')` 으로 분기하므로, 여기서도 재료
이름에 YARN 이 들어간 블록만 건드린다.

하는 일
-------
1. `*Material, Name=...YARN...` 블록을 찾는다
2. 그 안의 `*Depvar` 카운트를 17 로 올린다
3. 이름줄(`1, DY1T, ...`)이 있는 덱이면 17번 설명줄을 덧붙인다.
   이름줄이 없는 덱(V2_7P 이후 권장 형식 -- SDV1/SDV2 로 표시되게
   일부러 비운 것)은 그대로 둔다.

기본은 미리보기다. 실제로 쓰려면 --apply.

    python patch_depvar_yarn.py *.inp              # 미리보기
    python patch_depvar_yarn.py --apply *.inp      # 적용(+ .bak)
    python patch_depvar_yarn.py --check *.inp      # 현재 상태만

멱등이다. 이미 17 이면 건너뛴다.
"""

from __future__ import print_function
import argparse
import io
import os
import re
import shutil
import sys

MATERIAL = re.compile(r'^\s*\*material\b', re.I)
KEYWORD = re.compile(r'^\s*\*[^*]')          # *keyword (** 주석은 제외)
COMMENT = re.compile(r'^\s*\*\*')
DEPVAR = re.compile(r'^\s*\*depvar\b', re.I)
NAMEOPT = re.compile(r'name\s*=\s*([^,\r\n]+)', re.I)
COUNTLINE = re.compile(r'^(\s*)(\d+)(\s*,?\s*)$')

NEW_COUNT = 17
SDV17_DESC = '17, YSHR1T, Shear share of longitudinal tensile criterion'


def read_lines(path):
    """줄바꿈(CRLF/LF)을 보존해서 읽는다. 덱은 윈도우에서 만들어진다."""
    with io.open(path, 'r', encoding='utf-8', errors='surrogateescape',
                 newline='') as fh:
        return fh.readlines()


def write_lines(path, lines):
    with io.open(path, 'w', encoding='utf-8', errors='surrogateescape',
                 newline='') as fh:
        fh.writelines(lines)


def eol_of(line):
    if line.endswith('\r\n'):
        return '\r\n'
    if line.endswith('\n'):
        return '\n'
    return os.linesep


def find_yarn_depvars(lines):
    """[(depvar_줄번호, 재료이름), ...] -- 얀 재료의 *Depvar 만."""
    hits = []
    current = None
    for i, line in enumerate(lines):
        if COMMENT.match(line):
            continue
        if MATERIAL.match(line):
            m = NAMEOPT.search(line)
            current = m.group(1).strip() if m else ''
            continue
        if not KEYWORD.match(line):
            continue
        # 다른 키워드를 만났다 -- *Depvar 인지 보고, 재료 문맥은 유지
        if DEPVAR.match(line) and current and 'YARN' in current.upper():
            hits.append((i, current))
    return hits


def block_extent(lines, start):
    """*Depvar 다음 데이터줄들의 범위 [a, b) 를 돌려준다."""
    a = start + 1
    b = a
    while b < len(lines):
        if COMMENT.match(lines[b]):
            break
        if KEYWORD.match(lines[b]):
            break
        b += 1
    return a, b


def patch_one(lines, dv_line, name):
    """한 블록을 손본다. (변경됨?, 메시지) 를 돌려준다. lines 는 제자리 수정."""
    a, b = block_extent(lines, dv_line)
    data = [k for k in range(a, b) if lines[k].strip()]
    if not data:
        return False, 'ERROR  %s: *Depvar 에 데이터줄이 없다' % name

    first = data[0]
    m = COUNTLINE.match(lines[first].rstrip('\r\n'))
    if not m:
        return False, ('ERROR  %s: 카운트줄을 못 읽음: %r'
                       % (name, lines[first].strip()))
    count = int(m.group(2))
    if count >= NEW_COUNT:
        return False, ('SKIP   %s: 이미 %d (멱등 -- 손대지 않음)'
                       % (name, count))
    if count != 16:
        return False, ('ERROR  %s: 16 을 기대했는데 %d 다. 손대지 않음.'
                       % (name, count))

    eol = eol_of(lines[first])
    lines[first] = '%s%d%s%s' % (m.group(1), NEW_COUNT,
                                 m.group(3).rstrip(), eol)

    # 이름줄이 있는 덱에만 17번 설명을 덧붙인다.
    named = [k for k in data[1:] if ',' in lines[k]]
    if named:
        already = any(lines[k].strip().startswith('17')
                      for k in named)
        if not already:
            lines.insert(named[-1] + 1, SDV17_DESC + eol)
            return True, ('OK     %s: 16 -> 17, 설명줄 추가' % name)
        return True, ('OK     %s: 16 -> 17 (17번 설명줄은 이미 있음)'
                      % name)
    return True, ('OK     %s: 16 -> 17 (이름줄 없는 덱 -- 그대로 유지)'
                  % name)


def report_only(lines, path):
    out = []
    current = None
    for i, line in enumerate(lines):
        if COMMENT.match(line):
            continue
        if MATERIAL.match(line):
            m = NAMEOPT.search(line)
            current = m.group(1).strip() if m else ''
            continue
        if DEPVAR.match(line) and KEYWORD.match(line):
            a, b = block_extent(lines, i)
            data = [k for k in range(a, b) if lines[k].strip()]
            n = '?'
            if data:
                m2 = COUNTLINE.match(lines[data[0]].rstrip('\r\n'))
                if m2:
                    n = m2.group(2)
            kind = 'YARN' if (current and 'YARN' in current.upper()) \
                else 'other'
            out.append('  %-24s %-6s *Depvar %s' % (current, kind, n))
    return out


NAMED = """** a comment mentioning *Depvar and YARN, must be ignored
*Material, Name=SIC_MATRIX_DAMAGE
*Depvar
20,
1, DMT, Matrix tensile damage
20, EP23, Plastic strain 23 (engineering)
*User Material, constants=22
2.0, 350000.0
*Material, Name=CSIC_YARN_DAMAGE
*Depvar
16,
1, DY1T, Yarn longitudinal tensile damage
16, YRFAC, Criterion at maximum yarn damage jump
*User Material, constants=38
1.0, 254967.0
"""

UNNAMED = """*Material, Name=CSIC_YARN_DAMAGE
*Depvar
 16,
*User Material, constants=38
1.0, 254967.0
*Material, Name=SIC_MATRIX_DAMAGE
*Depvar
 20,
"""

ODD = """*Material, Name=CSIC_YARN_DAMAGE
*Depvar
12,
*User Material, constants=38
"""

NOYARN = """*Material, Name=SIC_MATRIX_DAMAGE
*Depvar
20,
"""


WIN_BAD = set('<>:"|?*')


def win_safe(path):
    """윈도우에서 파일명으로 쓸 수 있는 이름인가.

    이 저장소는 리눅스에서 검증하고 윈도우에서 실행한다. 리눅스는
    `>` 같은 글자를 파일명에 허용하므로, 컨테이너에서 전부 통과한
    자체시험이 사용자 PC 에서 OSError 22 로 죽는 일이 실제로 있었다.
    그래서 리눅스에서도 윈도우 규칙으로 판정한다."""
    return not (set(os.path.basename(path)) & WIN_BAD)


def selftest():
    """합성 덱으로 여섯 가지를 확인한다. 이 스크립트는 22 만 줄짜리
    되돌릴 수 없는 덱을 고치므로, 자체시험 없이 쓰지 않는다."""
    import tempfile
    tmp = tempfile.mkdtemp()
    fails = []
    seq = [0]

    def run(tag, text, expect_yarn, expect_desc, expect_rc,
            twice=False):
        # 파일명은 tag 가 아니라 일련번호로 짓는다. tag 를 파일명에 쓰면
        # `<>:"/\|?*` 가 든 시험 이름이 윈도우에서 OSError 22 로 터진다
        # (실제로 'named-16->17' 이 그렇게 터졌다). 리눅스는 허용하므로
        # 컨테이너 검증만으로는 안 잡힌다 -- 이름과 경로를 분리해 둔다.
        seq[0] += 1
        path = os.path.join(tmp, 'case%02d.inp' % seq[0])
        if not win_safe(path):
            print('  %-22s FAIL  (윈도우에서 못 쓰는 파일명: %s)'
                  % (tag, os.path.basename(path)))
            fails.append(tag)
            return ''
        with io.open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
        quiet = io.StringIO() if str is not bytes else io.BytesIO()
        keep, sys.stdout = sys.stdout, quiet
        try:
            rc = main([path, '--apply', '--no-backup'])
            if twice:
                rc = main([path, '--apply', '--no-backup'])
        finally:
            sys.stdout = keep
        with io.open(path, encoding='utf-8') as fh:
            got = fh.read()
        # 얀 카운트
        yarn_ok = ('%d,' % expect_yarn) in got.split('YARN_DAMAGE')[-1]
        # 기지 20 은 절대 변하면 안 된다
        matrix_ok = ('20,' in got) if '20,' in text else True
        desc_ok = (SDV17_DESC in got) == expect_desc
        rc_ok = (rc == expect_rc)
        ok = yarn_ok and matrix_ok and desc_ok and rc_ok
        print('  %-22s %s' % (tag, 'PASS' if ok else 'FAIL'))
        if not ok:
            fails.append(tag)
            print('     yarn=%s matrix=%s desc=%s rc=%s(%d)'
                  % (yarn_ok, matrix_ok, desc_ok, rc_ok, rc))
        return got

    print('자체시험')
    named = run('named 16->17', NAMED, 17, True, 0)
    run('unnamed-no-desc', UNNAMED, 17, False, 0)
    run('idempotent-twice', NAMED, 17, True, 0, twice=True)
    run('odd-count-refused', ODD, 12, False, 1)
    run('no-yarn-untouched', NOYARN, 20, False, 0)

    # 기지 20 이 절대 17 로 바뀌지 않는지 따로 못박는다.
    # run() 이 돌려준 내용을 그대로 쓴다 -- 경로를 다시 조립하면
    # 파일명 규칙이 바뀔 때 같이 안 따라와서 깨진다.
    head = named.split('YARN_DAMAGE')[0]
    if '20,' in head and '17,' not in head:
        print('  %-22s PASS' % 'matrix-20-untouched')
    else:
        print('  %-22s FAIL' % 'matrix-20-untouched')
        fails.append('matrix-20-untouched')

    shutil.rmtree(tmp)
    print('')
    if fails:
        print('자체시험 실패: %s' % ', '.join(fails))
        return 1
    print('자체시험 통과 -- 얀만 고치고 기지는 건드리지 않는다.')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='얀 *Depvar 만 16 -> 17 (V2_7D SDV17 용)')
    ap.add_argument('decks', nargs='*', help='.inp 파일들')
    ap.add_argument('--selftest', action='store_true',
                    help='합성 덱으로 자체시험만 하고 끝낸다')
    ap.add_argument('--apply', action='store_true',
                    help='실제로 파일을 고친다 (없으면 미리보기)')
    ap.add_argument('--check', action='store_true',
                    help='현재 *Depvar 상태만 보고하고 끝낸다')
    ap.add_argument('--no-backup', action='store_true',
                    help='--apply 시 .bak 를 남기지 않는다')
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.decks:
        ap.error('덱을 하나 이상 지정하거나 --selftest 를 쓴다')

    changed_files = 0
    errors = 0
    for path in args.decks:
        if not os.path.isfile(path):
            print('ERROR  %s: 파일이 없다' % path)
            errors += 1
            continue
        lines = read_lines(path)

        if args.check:
            print('%s' % path)
            for row in report_only(lines, path):
                print(row)
            continue

        hits = find_yarn_depvars(lines)
        if not hits:
            print('%s\n  SKIP   얀 재료의 *Depvar 를 못 찾음' % path)
            continue

        print('%s' % path)
        touched = False
        # 뒤에서부터 고친다 -- 앞에 줄을 삽입하면 뒤 인덱스가 밀린다
        for dv_line, name in sorted(hits, reverse=True):
            ok, msg = patch_one(lines, dv_line, name)
            print('  ' + msg)
            if msg.startswith('ERROR'):
                errors += 1
            touched = touched or ok

        if touched and args.apply:
            if not args.no_backup:
                shutil.copy2(path, path + '.bak')
                print('  백업   %s.bak' % os.path.basename(path))
            write_lines(path, lines)
            print('  기록   %s' % os.path.basename(path))
            changed_files += 1
        elif touched:
            print('  (미리보기 -- 쓰지 않았다. 적용하려면 --apply)')

    if not args.check:
        print('')
        if args.apply:
            print('고친 파일 %d 개, 오류 %d 건' % (changed_files, errors))
        else:
            print('미리보기 끝. 오류 %d 건. 적용하려면 --apply' % errors)
        print('')
        print('덱을 고쳤으면 UMAT 도 V2_7D 로 바꿔야 SDV17 이 채워진다.')
        print('반대로 V2_7D + *Depvar 16 조합도 안전하다 -- 진단만 꺼진다.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
