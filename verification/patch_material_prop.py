#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""`*User Material` 상수 **한 칸**만 바꾼다.

왜 손으로 안 고치는가
---------------------
얀 카드는 38 개 상수가 8 개씩 5 줄에 흩어져 있다. "11 번" 이 몇째
줄 몇째 토큰인지 세다가 틀리면 엉뚱한 물성이 바뀌고, 그 해석은
며칠 뒤에야 이상하다는 걸 알게 된다. 이 스크립트가 대신 센다.

§4 규칙("배치 비교는 변수 하나만") 을 지키기 위한 도구다. 그래서
한 번에 슬롯 하나만 받는다.

P3 배치 (얀 XT 를 논문 자신의 값으로):

    python patch_material_prop.py --material YARN --slot 11 \
           --value 2835.0 Try_P3\\*.inp            # 미리보기
    python patch_material_prop.py --material YARN --slot 11 \
           --value 2835.0 --apply Try_P3\\*.inp    # 적용(+ .bak)

바꾸기 전 값을 항상 찍는다. 기대한 값(421.0)이 아니면 멈추게 하려면
--expect 421.0 을 같이 준다 — 엉뚱한 덱에 적용하는 사고를 막는다.

읽기만:

    python patch_material_prop.py --material YARN --slot 11 --show *.inp
"""

from __future__ import print_function
import argparse
import io
import os
import re
import shutil
import sys

MATERIAL = re.compile(r'^\s*\*material\b', re.I)
KEYWORD = re.compile(r'^\s*\*[^*]')
COMMENT = re.compile(r'^\s*\*\*')
USERMAT = re.compile(r'^\s*\*user\s+material\b', re.I)
NAMEOPT = re.compile(r'name\s*=\s*([^,\r\n]+)', re.I)
# 한 토큰 = 앞뒤 공백 + 숫자 + 쉼표
TOKEN = re.compile(r'(\s*)([^,\s][^,]*?)(\s*)(,|$)')


def read_lines(path):
    with io.open(path, 'r', encoding='utf-8', errors='surrogateescape',
                 newline='') as fh:
        return fh.readlines()


def write_lines(path, lines):
    with io.open(path, 'w', encoding='utf-8', errors='surrogateescape',
                 newline='') as fh:
        fh.writelines(lines)


def find_usermat(lines, want):
    """[(줄번호, 재료이름), ...] — 이름에 want 가 들어간 재료의 *User Material."""
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
        if USERMAT.match(line) and current \
                and want.upper() in current.upper():
            hits.append((i, current))
    return hits


def data_lines(lines, start):
    out = []
    k = start + 1
    while k < len(lines):
        if COMMENT.match(lines[k]) or KEYWORD.match(lines[k]):
            break
        if lines[k].strip():
            out.append(k)
        k += 1
    return out


def locate(lines, dls, slot):
    """slot(1-based) 이 어느 줄 어느 토큰인지. (줄번호, 매치, 현재값)."""
    n = 0
    for k in dls:
        body = lines[k].rstrip('\r\n')
        for m in TOKEN.finditer(body):
            if not m.group(2).strip():
                continue
            n += 1
            if n == slot:
                return k, m, m.group(2).strip()
    return None, None, None


def count_consts(lines, dls):
    n = 0
    for k in dls:
        for m in TOKEN.finditer(lines[k].rstrip('\r\n')):
            if m.group(2).strip():
                n += 1
    return n


def patch_one(lines, um_line, name, slot, value, expect, show):
    dls = data_lines(lines, um_line)
    if not dls:
        return False, 'ERROR  %s: *User Material 에 데이터줄이 없다' % name
    total = count_consts(lines, dls)
    k, m, old = locate(lines, dls, slot)
    if k is None:
        return False, ('ERROR  %s: 슬롯 %d 이 없다 (상수 %d 개뿐)'
                       % (name, slot, total))
    if show:
        return False, ('       %s: 상수 %d 개, 슬롯 %d = %s'
                       % (name, total, slot, old))
    if expect is not None:
        try:
            same = abs(float(old) - float(expect)) < 1e-12
        except ValueError:
            same = (old == expect)
        if not same:
            return False, ('ERROR  %s: 슬롯 %d 이 %s 인데 --expect %s '
                           '였다. 손대지 않음.' % (name, slot, old, expect))
    if old == value:
        return False, ('SKIP   %s: 슬롯 %d 이 이미 %s' % (name, slot, value))

    body = lines[k].rstrip('\r\n')
    eol = lines[k][len(body):]
    a, b = m.start(2), m.end(2)
    lines[k] = body[:a] + value + body[b:] + eol
    return True, ('OK     %s: 슬롯 %d  %s -> %s  (상수 %d 개, %d 행)'
                  % (name, slot, old, value, total, k + 1))


SELF_DECK = """*Material, Name=SIC_MATRIX_DAMAGE
*User Material, constants=22
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
250.0, 100000.0, 1.15, 0.75, 0.50, 30.0
*Material, Name=CSIC_YARN_DAMAGE
*User Material, constants=38
1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.2475, 0.3958, 26431.5
26431.5, 15876.6, 421.0, 1956.0, 80.0, 350.0, 120.0, 120.0
100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02
0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 0.03962
12.5, 0.0, 0.0, 700.0, 3.0, 8000.0
*Expansion, type=ORTHO, zero=1050.
"""


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp()
    fails = []

    def run(tag, argv, want_line, want_absent=None):
        path = os.path.join(tmp, tag + '.inp')
        with io.open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(SELF_DECK)
        quiet = io.StringIO() if str is not bytes else io.BytesIO()
        keep, sys.stdout = sys.stdout, quiet
        try:
            rc = main(argv + [path])
        finally:
            sys.stdout = keep
        got = io.open(path, encoding='utf-8').read()
        ok = (want_line in got)
        if want_absent is not None:
            ok = ok and (want_absent not in got)
        print('  %-26s %s  (rc=%d)' % (tag, 'PASS' if ok else 'FAIL', rc))
        if not ok:
            fails.append(tag)
            print(quiet.getvalue())
        return rc

    print('자체시험')
    # 1) P3 그 자체: 얀 슬롯 11  421 -> 2835
    run('yarn-slot11-421to2835',
        ['--material', 'YARN', '--slot', '11', '--value', '2835.0',
         '--apply', '--no-backup'],
        '26431.5, 15876.6, 2835.0, 1956.0,')
    # 2) 기지가 절대 안 변해야 한다 (기지 슬롯 11 = 0.10)
    run('matrix-untouched',
        ['--material', 'YARN', '--slot', '11', '--value', '2835.0',
         '--apply', '--no-backup'],
        '0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031')
    # 3) 줄이 넘어가는 슬롯. 얀 카드는 8 개씩 끊기므로 33 이 5째 줄
    #    첫 칸(12.5)이다. 32 는 4째 줄 마지막이라 줄넘김을 안 본다 --
    #    처음에 32 로 짰다가 자체시험이 SKIP 을 물어와 잡았다.
    run('slot33-first-of-new-line',
        ['--material', 'YARN', '--slot', '33', '--value', '9.99',
         '--apply', '--no-backup'],
        '9.99, 0.0, 0.0, 700.0,')
    # 3b) 줄 마지막 칸도 정확히 잡는가 (32 = 4째 줄 끝)
    run('slot32-last-of-line',
        ['--material', 'YARN', '--slot', '32', '--value', '0.5',
         '--apply', '--no-backup'],
        '1.15, 0.75, 0.50, 0.5')
    # 4) --expect 불일치면 거부
    run('expect-mismatch-refused',
        ['--material', 'YARN', '--slot', '11', '--value', '2835.0',
         '--expect', '999.0', '--apply', '--no-backup'],
        '15876.6, 421.0,', want_absent='2835.0')
    # 5) 미리보기는 파일을 안 건드린다
    run('preview-writes-nothing',
        ['--material', 'YARN', '--slot', '11', '--value', '2835.0'],
        '15876.6, 421.0,', want_absent='2835.0')
    # 6) 범위 밖 슬롯 거부
    rc = run('slot-out-of-range',
             ['--material', 'YARN', '--slot', '99', '--value', '1.0',
              '--apply', '--no-backup'],
             '15876.6, 421.0,')
    if rc == 0:
        print('  %-26s FAIL  (rc 이 0 이면 안 된다)' % 'slot-99-rc')
        fails.append('slot-99-rc')

    shutil.rmtree(tmp)
    print('')
    if fails:
        print('자체시험 실패: %s' % ', '.join(fails))
        return 1
    print('자체시험 통과 -- 지정 재료의 지정 슬롯 하나만 바뀐다.')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='*User Material 상수 한 칸만 교체')
    ap.add_argument('decks', nargs='*')
    ap.add_argument('--material', default='YARN',
                    help='재료 이름에 들어갈 문자열 (기본 YARN)')
    ap.add_argument('--slot', type=int, help='1-based PROPS 번호')
    ap.add_argument('--value', help='새 값 (문자열 그대로 씀)')
    ap.add_argument('--expect', help='바꾸기 전 값이 이것이 아니면 거부')
    ap.add_argument('--show', action='store_true', help='현재 값만 본다')
    ap.add_argument('--apply', action='store_true', help='실제로 쓴다')
    ap.add_argument('--no-backup', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.decks:
        ap.error('덱을 하나 이상 지정하거나 --selftest')
    if args.slot is None:
        ap.error('--slot 이 필요하다')
    if not args.show and args.value is None:
        ap.error('--value 가 필요하다 (읽기만 하려면 --show)')

    changed = 0
    errors = 0
    for path in args.decks:
        if not os.path.isfile(path):
            print('ERROR  %s: 파일이 없다' % path)
            errors += 1
            continue
        lines = read_lines(path)
        hits = find_usermat(lines, args.material)
        print('%s' % path)
        if not hits:
            print('  SKIP   %s 재료의 *User Material 을 못 찾음'
                  % args.material)
            continue
        touched = False
        for um_line, name in hits:
            ok, msg = patch_one(lines, um_line, name, args.slot,
                                args.value, args.expect, args.show)
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
            changed += 1
        elif touched:
            print('  (미리보기 -- 쓰지 않았다. 적용하려면 --apply)')

    if not args.show:
        print('')
        print('고친 파일 %d 개, 오류 %d 건' % (changed, errors))
        print('§4: 한 배치에서 슬롯은 하나만 바꾼다. 나머지는 고정.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
